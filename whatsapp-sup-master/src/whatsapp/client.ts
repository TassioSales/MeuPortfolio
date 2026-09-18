import { config } from '../config';
import { log, mascararTelefones } from '../log';

/**
 * Endpoint de envio da Evolution API v2.
 *
 * A instância vai no CAMINHO, não no corpo — é a diferença estrutural para a
 * Graph, onde o identificador do número ficava na URL e o destinatário no corpo.
 * Aqui a URL identifica QUAL número nosso fala; o corpo diz com quem.
 */
const API_URL = `${config.evolutionUrl.replace(/\/+$/, '')}/message/sendText/${config.evolutionInstancia}`;

export type CorpoWhatsApp = Record<string, unknown>;

export type ResultadoEnvio = {
  ok: boolean;
  status: number;
  /** true quando repetir não vai ajudar (token inválido, destinatário inválido...). */
  permanente: boolean;
  erro?: string;
  /** Espera pedida no header `Retry-After`, em ms. Ver `esperaPedida`. */
  esperarMs?: number;
};

/** Ajustes por chamada. Ver `postarComRetry`. */
export type OpcoesEnvio = {
  /** Quantas tentativas fazer. Padrão: `ENVIOS_TENTATIVAS`. */
  tentativas?: number;
  /** Instante (em `Date.now()`) a partir do qual não vale começar outra tentativa. */
  ateMs?: number;
};

export function corpoTexto(telefone: string, texto: string): CorpoWhatsApp {
  return { number: telefone, text: texto };
}

/**
 * Monta um menu como TEXTO NUMERADO, e não como botão ou lista.
 *
 * Por que não há mais formato interativo aqui: a Evolution conversa com o
 * WhatsApp pelo Baileys, e mensagem de botão/lista não renderiza de forma
 * confiável nesse caminho — o WhatsApp restringiu esses formatos a quem usa a
 * API oficial. Um botão que não aparece é pior que não existir: a pessoa recebe
 * um cartão vazio e não tem como responder.
 *
 * Texto numerado funciona em qualquer cliente, em qualquer versão, e já era o
 * caminho principal do menu de assuntos — que sempre pediu "responda com o
 * número" justamente porque o rótulo da lista era cortado em 24 caracteres.
 *
 * A NUMERAÇÃO É A POSIÇÃO na lista recebida, começando em 1. Quem interpreta a
 * resposta tem de reconstruir a MESMA lista, na mesma ordem — ver
 * `opcoesDaConfirmacao` em conversation/handler.ts.
 */
export function menuNumerado(
  texto: string,
  opcoes: { id: string; texto: string }[],
  instrucao = 'Responda com o número da opção.'
): string {
  const linhas = opcoes.map((o, i) => `${i + 1}. ${o.texto}`).join('\n');
  return `${texto}\n\n${linhas}\n\n${instrucao}`;
}

/**
 * Um menu de opções, entregue como texto numerado.
 *
 * Substitui `corpoBotoes` e `corpoLista`, que montavam os formatos interativos
 * da Meta. Com eles foram embora os cinco limites que existiam só por causa
 * daqueles formatos: 3 botões, 10 linhas de lista, e os cortes de 20 e 24
 * caracteres nos títulos — que obrigavam a abreviar rótulo de assunto e eram a
 * razão de o menu de assuntos SEMPRE ter pedido o número.
 *
 * Sem esses tetos, uma consequência prática: um menu longo deixou de perder
 * opção em silêncio. O que existe agora é uma mensagem comprida, que o WhatsApp
 * entrega inteira.
 */
export function corpoEscolha(
  telefone: string,
  texto: string,
  opcoes: { id: string; texto: string }[],
  instrucao?: string
): CorpoWhatsApp {
  return corpoTexto(telefone, menuNumerado(texto, opcoes, instrucao));
}

const espera = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** 429 e 5xx são transitórios; os demais 4xx não adianta repetir. */
function ehTransitorio(status: number): boolean {
  return status === 408 || status === 429 || status >= 500;
}

function backoffMs(tentativa: number): number {
  const base = 300 * 2 ** tentativa; // 300, 600, 1200...
  return base + Math.floor(Math.random() * 200); // jitter evita rajada sincronizada
}

/**
 * Lê o `Retry-After` da resposta.
 *
 * Em 429, quem recusou costuma DIZER quanto esperar. Antes, o 429 era tratado
 * como qualquer falha transitória e a espera saía do `backoffMs` - ou seja,
 * chutando. Chutar baixo faz bater de novo no limite e queimar tentativa; chutar
 * alto atrasa mensagem que já podia ter saído.
 *
 * Com a Evolution no caminho, o `Retry-After` pode vir dela ou de um proxy à
 * frente dela. Tanto faz: o que ele diz é quanto esperar, e obedecer continua
 * sendo melhor do que chutar.
 *
 * O header aceita dois formatos, segundos ou data HTTP, e os dois aparecem na
 * prática dependendo do proxy no caminho.
 */
function esperaPedida(res: Response): number | undefined {
  const bruto = res.headers.get('retry-after')?.trim();
  if (!bruto) return undefined;

  if (/^\d+$/.test(bruto)) return Number(bruto) * 1_000;

  const instante = Date.parse(bruto);
  if (Number.isNaN(instante)) return undefined;
  // Data no passado (relógios fora de sincronia) vira 0, não espera negativa.
  return Math.max(0, instante - Date.now());
}

// Teto para a espera pedida. Acima disso não vale segurar a linha de
// execução esperando: melhor devolver, deixar a mensagem pendente e deixar o
// varredor da outbox - que tem a própria espera crescente e ninguém do outro
// lado aguardando - tentar mais tarde.
const MAX_ESPERA_PEDIDA_MS = 60_000;

const TIMEOUT_POR_TENTATIVA_MS = 8_000;

/**
 * Posta na Evolution repetindo falhas transitórias.
 *
 * `ateMs` é o que impede o retry de estourar o tempo que a Evolution espera pelo
 * 200 do webhook: quem chama de dentro de uma requisição passa um instante limite
 * (compartilhado por todo o lote) e aqui não se começa tentativa que não caiba
 * nele. O que sobrar fica pendente na outbox e sai pelo varredor, que não tem
 * ninguém esperando do outro lado.
 */
export async function postarComRetry(
  corpo: CorpoWhatsApp,
  opts: OpcoesEnvio = {}
): Promise<ResultadoEnvio> {
  const maxTentativas = opts.tentativas ?? config.enviosTentativas;
  const ateMs = opts.ateMs ?? Infinity;

  let ultimo: ResultadoEnvio = { ok: false, status: 0, permanente: false, erro: 'sem tentativa' };

  for (let tentativa = 0; tentativa < maxTentativas; tentativa++) {
    if (tentativa > 0) {
      // Quando veio um Retry-After, obedece; senão, backoff próprio.
      // `?? ` e não `||`: um Retry-After de 0 significa "pode tentar de novo
      // agora", e não "usa o teu backoff".
      const pausa = ultimo.esperarMs ?? backoffMs(tentativa - 1);

      // Espera longa demais para segurar aqui: sai e deixa para o varredor.
      if (pausa > MAX_ESPERA_PEDIDA_MS) break;

      // Se o orçamento acaba antes mesmo do backoff terminar, não vale esperar:
      // devolve agora e deixa a linha pendente.
      if (Date.now() + pausa >= ateMs) break;
      await espera(pausa);
    }

    const restanteMs = ateMs - Date.now();
    if (restanteMs <= 0) break;

    try {
      const res = await fetch(API_URL, {
        method: 'POST',
        headers: {
          // A Evolution autentica por `apikey`, e não por `Authorization:
          // Bearer`. Mandar o Bearer aqui não dá erro claro: ela responde 401
          // como se a chave estivesse errada.
          apikey: config.evolutionApiKey,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(corpo),
        signal: AbortSignal.timeout(Math.min(TIMEOUT_POR_TENTATIVA_MS, restanteMs)),
      });

      if (res.ok) return { ok: true, status: res.status, permanente: false };

      const erro = mascararTelefones(await res.text()).slice(0, 500);
      ultimo = {
        ok: false,
        status: res.status,
        permanente: !ehTransitorio(res.status),
        erro,
        esperarMs: esperaPedida(res),
      };
      if (ultimo.permanente) return ultimo;
    } catch (err) {
      // Rede fora, DNS, timeout: sempre vale repetir.
      ultimo = {
        ok: false,
        status: 0,
        permanente: false,
        erro: mascararTelefones(err instanceof Error ? err.message : String(err)).slice(0, 200),
      };
    }
  }

  return ultimo;
}

/**
 * Envio que NÃO passa pelo banco.
 *
 * Existe para o aviso de indisponibilidade: quando o banco está inacessível, o
 * caminho normal (outbox) não funciona, mas falar com a Evolution é só HTTP.
 */
export async function enviarDireto(
  telefone: string,
  texto: string,
  opts: OpcoesEnvio = {}
): Promise<ResultadoEnvio> {
  return postarComRetry(corpoTexto(telefone, texto), opts);
}
