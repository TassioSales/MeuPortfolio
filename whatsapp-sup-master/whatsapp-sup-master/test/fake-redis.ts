import { ClienteRedis, LUA_DEVOLVER, LUA_INCREMENTAR } from '../src/estado/janelas';

/**
 * Redis de mentira, em memória.
 *
 * Deixa o caminho de `janelasNoRedis` rodar sem um servidor de pé: prefixo de
 * chave, argumentos dos scripts, leitura do retorno e o fallback para memória
 * quando o comando estoura.
 *
 * O que ele NÃO simula, e por isso não pode ser testado aqui:
 *   - a atomicidade de verdade. Aqui não existe concorrência, então este dublê
 *     não prova que o Lua evita a corrida entre INCR e PEXPIRE — ele só fixa a
 *     SEMÂNTICA que o Lua tem de ter (ver o reconhecimento por texto abaixo);
 *   - a expiração pelo relógio do servidor Redis. O prazo aqui é conferido
 *     contra um `agora` que o teste controla, porque exercitar a virada de
 *     janela de 10 minutos em tempo real não é teste, é espera;
 *   - reconexão, `commandTimeout`, `enableOfflineQueue` e o resto do
 *     comportamento de rede do ioredis;
 *   - qualquer comando fora dos três que este módulo usa.
 *
 * Um Redis de verdade continua sendo necessário para provar os dois primeiros.
 */

type Entrada = { valor: number; expiraEm: number };

export type FakeRedis = ClienteRedis & {
  /** Relógio que o teste controla. */
  agora: number;
  /** Ligado, todo comando estoura — é o que exercita o fallback para memória. */
  falhar: boolean;
  /** Chaves vivas neste instante, para asserção direta. */
  chaves(): string[];
  /** Valor de uma chave viva, ou undefined. */
  valor(chave: string): number | undefined;
  /** Quantos comandos chegaram (prova que o caminho do Redis foi usado). */
  comandos: number;
  encerrado: boolean;
};

export function criarFakeRedis(): FakeRedis {
  const dados = new Map<string, Entrada>();

  const fake: FakeRedis = {
    agora: 1_000_000,
    falhar: false,
    comandos: 0,
    encerrado: false,

    chaves() {
      return [...dados.entries()]
        .filter(([, e]) => e.expiraEm > fake.agora)
        .map(([k]) => k)
        .sort();
    },

    valor(chave) {
      const entrada = dados.get(chave);
      return entrada && entrada.expiraEm > fake.agora ? entrada.valor : undefined;
    },

    async eval(script, numChaves, ...args) {
      fake.comandos++;
      if (fake.falhar) throw new Error('fake-redis: comando recusado');
      if (numChaves !== 1) throw new Error(`fake-redis: esperava 1 chave, veio ${numChaves}`);
      const chave = String(args[0]);
      const viva = fake.valor(chave) !== undefined;

      // Reconhece o script pelo TEXTO, contra a constante exportada. É de
      // propósito: mexer no Lua sem ajustar este dublê faz o teste falhar aqui,
      // com "script desconhecido", em vez de passar em falso contra uma
      // semântica que o Redis de verdade não tem mais.
      if (script === LUA_INCREMENTAR) {
        const prazoMs = Number(args[1]);
        if (!viva) {
          // INCR numa chave ausente dá 1, e só nesse caso o PEXPIRE roda.
          dados.set(chave, { valor: 1, expiraEm: fake.agora + prazoMs });
          return 1;
        }
        const entrada = dados.get(chave)!;
        entrada.valor += 1; // DECR/INCR não mexem no TTL
        return entrada.valor;
      }

      if (script === LUA_DEVOLVER) {
        if (!viva) return 0; // GET de chave ausente dá nil: o script não decrementa
        const entrada = dados.get(chave)!;
        if (entrada.valor > 0) entrada.valor -= 1; // sem tocar em expiraEm
        return entrada.valor;
      }

      throw new Error('fake-redis: script desconhecido — o Lua mudou em src/estado/janelas.ts?');
    },

    async set(chave, valor, modoPrazo, prazoMs, modoSeAusente) {
      fake.comandos++;
      if (fake.falhar) throw new Error('fake-redis: comando recusado');
      if (modoPrazo !== 'PX' || modoSeAusente !== 'NX') {
        throw new Error(
          `fake-redis: só implementa SET ... PX ... NX (veio ${modoPrazo}/${modoSeAusente})`
        );
      }
      if (fake.valor(chave) !== undefined) return null; // NX: já existe, não sobrescreve
      dados.set(chave, { valor: Number(valor), expiraEm: fake.agora + prazoMs });
      return 'OK';
    },

    async quit() {
      fake.encerrado = true;
      dados.clear();
      return 'OK';
    },

    disconnect() {
      fake.encerrado = true;
    },
  };

  return fake;
}
