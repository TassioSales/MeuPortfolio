import Redis from 'ioredis';
import { config } from '../config';
import { erroSeguro, log } from '../log';

/**
 * Contadores e reservas em janela de tempo, compartilháveis entre instâncias.
 *
 * POR QUÊ
 *
 * Dois limites deste sistema viviam em `Map` dentro do processo:
 *
 *   - `whatsapp/throttle.ts` - mensagens por minuto por telefone;
 *   - `whatsapp/indisponibilidade.ts` - no máximo um aviso por telefone a cada
 *     10 minutos.
 *
 * Com UMA instância isso é correto e é o mais barato possível. Com N instâncias
 * cada uma tem a sua contagem e **o limite efetivo vira N x o configurado** -
 * sem nenhum aviso, porque nada quebra: o sistema só passa silenciosamente a
 * deixar entrar 20 mensagens por minuto POR INSTÂNCIA em vez de 20 no total.
 * Era o que impedia escalar horizontalmente por CONTA DESTES CONTADORES. Hoje o
 * bloqueio é outro e é maior: o banco é um arquivo SQLite, que aceita um
 * escritor só (ver src/db/client.ts). Enquanto for assim, `REDIS_URL` resolve um
 * problema que não chega a acontecer - e continua aqui porque a alternativa era
 * jogar fora a única parte pronta para a frota.
 *
 * COMO
 *
 * Uma interface, duas implementações, escolhidas no boot por `REDIS_URL`:
 *
 *   - **sem `REDIS_URL`** -> memória, com exatamente o comportamento de antes.
 *     Este é o padrão, e é o certo enquanto o `render.yaml` não declarar
 *     `numInstances`. Nenhuma dependência nova entra no caminho da requisição.
 *   - **com `REDIS_URL`** -> Redis, com as operações em Lua para serem atômicas
 *     numa ida só.
 *
 * E o detalhe que mais importa: **falha do Redis não desliga o limite**, ela cai
 * para a implementação em memória. Fechar (recusar tudo) descartaria mensagem de
 * gente real em silêncio; abrir (permitir tudo) removeria o único controle de
 * abuso que existe depois da validação de assinatura. Degradar para "o limite de
 * antes, por instância" é a única das três que não troca um problema por outro
 * pior.
 */

export interface Janelas {
  /**
   * Soma 1 ao contador da chave e devolve o total da janela atual. Cria a
   * janela (com prazo `janelaMs`) quando ela não existe.
   */
  incrementar(chave: string, janelaMs: number, agora?: number): Promise<number>;

  /**
   * Devolve 1 ao contador, sem esticar a janela. Não faz nada se a janela já
   * virou - decrementar ali roubaria cota da janela nova.
   */
  devolver(chave: string, janelaMs: number, agora?: number): Promise<void>;

  /**
   * Tenta reservar a chave por `janelaMs`. `true` para quem chegou primeiro,
   * `false` para quem encontrou a reserva já feita.
   */
  reservar(chave: string, janelaMs: number, agora?: number): Promise<boolean>;

  /** Só para testes: esquece tudo que está em memória. */
  _limpar(): void;

  /** Encerra a conexão, se houver. Chamado no shutdown. */
  encerrar(): Promise<void>;
}

// --- memória ------------------------------------------------------------------

// Trava de segurança: nenhum cenário real chega perto disso, mas garante que o
// Map não vire um vetor de exaustão de memória. Vinha do throttle.ts original.
const MAX_CHAVES = 50_000;

// Cada entrada carrega o seu próprio prazo. No throttle.ts original a janela era
// uma constante do módulo; aqui o mesmo Map atende janelas diferentes (1 minuto
// do throttle, 10 minutos do aviso de indisponibilidade), e é isso que permite a
// varredura periódica abaixo expirar cada chave pelo prazo certo.
type Contador = { total: number; janelaInicio: number; janelaMs: number };

// De quanto em quanto tempo varrer o que expirou. Sem isso o Map só encolheria
// ao bater em MAX_CHAVES - bounded, mas desperdiçando memória à toa entre picos.
const VARREDURA_MS = 60_000;

export function janelasEmMemoria(): Janelas {
  const contadores = new Map<string, Contador>();

  const expirar = (agora: number): void => {
    for (const [chave, contador] of contadores) {
      if (agora - contador.janelaInicio >= contador.janelaMs) contadores.delete(chave);
    }
  };

  // `unref` evita que este timer segure o processo vivo no shutdown - vinha
  // assim do throttle.ts original, e é o que faz `npm test` terminar sozinho.
  const timer = setInterval(() => expirar(Date.now()), VARREDURA_MS);
  timer.unref();

  /** A entrada, se a janela dela ainda estiver valendo. */
  const vigente = (chave: string, agora: number): Contador | undefined => {
    const atual = contadores.get(chave);
    if (!atual) return undefined;
    return agora - atual.janelaInicio >= atual.janelaMs ? undefined : atual;
  };

  return {
    async incrementar(chave, janelaMs, agora = Date.now()) {
      const atual = vigente(chave, agora);

      if (!atual) {
        if (!contadores.has(chave) && contadores.size >= MAX_CHAVES) {
          expirar(agora);
          // Ainda cheio depois da limpeza: devolve um total que qualquer limite
          // recusa, em vez de deixar o Map crescer sem teto.
          if (contadores.size >= MAX_CHAVES) return Number.MAX_SAFE_INTEGER;
        }
        contadores.set(chave, { total: 1, janelaInicio: agora, janelaMs });
        return 1;
      }

      atual.total += 1;
      return atual.total;
    },

    async devolver(chave, janelaMs, agora = Date.now()) {
      const atual = vigente(chave, agora);
      if (!atual) return; // janela já virou: decrementar roubaria da janela nova
      if (atual.total > 0) atual.total -= 1;
    },

    async reservar(chave, janelaMs, agora = Date.now()) {
      if (vigente(chave, agora)) return false;

      if (!contadores.has(chave) && contadores.size >= MAX_CHAVES) expirar(agora);
      contadores.set(chave, { total: 1, janelaInicio: agora, janelaMs });
      return true;
    },

    _limpar() {
      contadores.clear();
    },

    async encerrar() {
      clearInterval(timer);
      contadores.clear();
    },
  };
}

// --- Redis --------------------------------------------------------------------

// INCR e o prazo da janela numa operação só.
//
// A alternativa de duas idas (INCR e depois PEXPIRE se o total for 1) tem um
// buraco real: o processo que morre entre as duas deixa uma chave SEM prazo, e
// aquele telefone fica bloqueado para sempre. Em Lua o Redis executa o script
// inteiro sem intercalar outro comando, então esse estado intermediário não
// chega a existir.
export const LUA_INCREMENTAR = [
  "local total = redis.call('INCR', KEYS[1])",
  "if total == 1 then redis.call('PEXPIRE', KEYS[1], ARGV[1]) end",
  'return total',
].join('\n');

// Devolve a cota SEM tocar no prazo: a janela continua sendo a que era (DECR não
// mexe em TTL). O guarda de zero evita contador negativo caso algum caminho
// devolva duas vezes a mesma mensagem.
export const LUA_DEVOLVER = [
  "local atual = redis.call('GET', KEYS[1])",
  "if atual and tonumber(atual) > 0 then return redis.call('DECR', KEYS[1]) end",
  'return 0',
].join('\n');

/**
 * O pouco da interface do ioredis que este módulo usa.
 *
 * Declarado à parte para o teste poder injetar um dublê em vez de exigir um
 * Redis de pé — a mesma ideia do `EVOLUTION_URL` apontando para a Evolution de
 * mentira. Ver test/fake-redis.ts, incluindo a lista do que ele NÃO simula.
 */
export interface ClienteRedis {
  eval(script: string, numChaves: number, ...args: (string | number)[]): Promise<unknown>;
  set(
    chave: string,
    valor: string,
    modoPrazo: 'PX',
    prazoMs: number,
    modoSeAusente: 'NX'
  ): Promise<string | null>;
  quit(): Promise<unknown>;
  disconnect(): void;
}

function criarCliente(url: string): Redis {
  const cliente = new Redis(url, {
    // Os prazos existem para não deixar a requisição do webhook pendurada: a
    // quem entrega o webhook desiste de esperar o 200 em poucos segundos, e nesse caso é melhor
    // cair no caminho de memória do que segurar o lote inteiro.
    commandTimeout: 1_000,
    connectTimeout: 3_000,
    maxRetriesPerRequest: 1,
    // Sem fila offline: com ela, um comando disparado durante a queda ficaria
    // esperando a reconexão em vez de falhar - e é a falha que aciona o
    // fallback para memória.
    enableOfflineQueue: false,
    lazyConnect: true,
  });

  // Sem um listener de `error`, o ioredis promove falha de conexão a exceção não
  // tratada e derruba o processo - exatamente o oposto do que este módulo
  // existe para fazer.
  cliente.on('error', (err) => {
    log.warn(erroSeguro(err), 'Redis indisponível: limites caem para memória');
  });
  cliente.connect().catch(() => {
    /* o listener acima já registrou; a primeira operação tenta de novo */
  });

  return cliente;
}

export function janelasNoRedis(url: string, prefixo: string, duble?: ClienteRedis): Janelas {
  const cliente: ClienteRedis = duble ?? (criarCliente(url) as unknown as ClienteRedis);
  // O fallback é a implementação de memória inteira, viva desde o boot: quando o
  // Redis falha, o limite volta a valer por instância - que é o comportamento
  // que este projeto teve até aqui, e não "sem limite".
  const memoria = janelasEmMemoria();
  const chaveDe = (chave: string): string => `${prefixo}:${chave}`;

  return {
    async incrementar(chave, janelaMs, agora) {
      try {
        const total = await cliente.eval(LUA_INCREMENTAR, 1, chaveDe(chave), String(janelaMs));
        return Number(total);
      } catch (err) {
        log.warn(erroSeguro(err), 'Redis falhou em incrementar: usando memória');
        return await memoria.incrementar(chave, janelaMs, agora);
      }
    },

    async devolver(chave, janelaMs, agora) {
      try {
        await cliente.eval(LUA_DEVOLVER, 1, chaveDe(chave));
      } catch (err) {
        log.warn(erroSeguro(err), 'Redis falhou em devolver: usando memória');
        await memoria.devolver(chave, janelaMs, agora);
      }
    },

    async reservar(chave, janelaMs, agora) {
      try {
        // `SET ... PX ... NX` já é atômico: devolve OK para quem criou a chave e
        // null para quem a encontrou. Não precisa de Lua.
        const resultado = await cliente.set(chaveDe(chave), '1', 'PX', janelaMs, 'NX');
        return resultado === 'OK';
      } catch (err) {
        log.warn(erroSeguro(err), 'Redis falhou em reservar: usando memória');
        return await memoria.reservar(chave, janelaMs, agora);
      }
    },

    _limpar() {
      memoria._limpar();
    },

    async encerrar() {
      try {
        await cliente.quit();
      } catch {
        cliente.disconnect(); // já estava fora: encerra sem esperar resposta
      }
    },
  };
}

// --- escolha feita uma vez, no boot -------------------------------------------

export const janelas: Janelas = config.redisUrl
  ? janelasNoRedis(config.redisUrl, config.redisPrefixo)
  : janelasEmMemoria();

export const usandoRedis = Boolean(config.redisUrl);
