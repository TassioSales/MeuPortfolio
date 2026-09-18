// Logger do processo + helpers para não vazar dado pessoal (telefone, nome,
// texto do chamado) nos logs.

/**
 * Mascara sequências longas de dígitos - na prática, telefones.
 * "5511998877665" vira "***7665".
 */
export function mascararTelefones(texto: string): string {
  return texto.replace(/\d{8,}/g, (m) => `***${m.slice(-4)}`);
}

/**
 * Reduz um erro ao que é útil para depurar, sem despejar o objeto inteiro.
 *
 * Importa porque erros do Prisma podem carregar os parâmetros da query - ou
 * seja, telefone, nome e o texto do chamado - direto para o log.
 */
export function erroSeguro(err: unknown): Record<string, string> {
  if (err instanceof Error) {
    const codigo = (err as { code?: unknown }).code;
    return {
      tipo: err.name,
      ...(typeof codigo === 'string' ? { codigo } : {}),
      // Trunca: mensagens de validação do Prisma podem incluir o objeto `data`.
      mensagem: mascararTelefones(err.message).slice(0, 300),
    };
  }
  return { tipo: 'desconhecido', mensagem: mascararTelefones(String(err)).slice(0, 300) };
}

/**
 * Logger único para o código que não está dentro de uma rota.
 *
 * Antes, o varredor da outbox usava `console.error` direto: saída sem estrutura,
 * fora do formato do pino e alheia à configuração de `redact` do servidor. O
 * boot injeta aqui o logger do Fastify (`usarLogger`) e todo mundo escreve no
 * mesmo lugar. Scripts avulsos (retenção) e testes caem no fallback, que ainda
 * emite uma linha JSON.
 */
export type Logger = {
  info: (obj: unknown, msg?: string) => void;
  warn: (obj: unknown, msg?: string) => void;
  error: (obj: unknown, msg?: string) => void;
};

function linhaJson(nivel: string, obj: unknown, msg?: string): void {
  const corpo = obj !== null && typeof obj === 'object' ? obj : { detalhe: obj };
  process.stderr.write(`${JSON.stringify({ nivel, ...corpo, ...(msg ? { msg } : {}) })}\n`);
}

const fallback: Logger = {
  info: (obj, msg) => linhaJson('info', obj, msg),
  warn: (obj, msg) => linhaJson('warn', obj, msg),
  error: (obj, msg) => linhaJson('error', obj, msg),
};

let destino: Logger = fallback;

/** Chamado uma vez no boot para o processo passar a usar o logger do Fastify. */
export function usarLogger(logger: Logger): void {
  destino = logger;
}

export const log: Logger = {
  info: (obj, msg) => destino.info(obj, msg),
  warn: (obj, msg) => destino.warn(obj, msg),
  error: (obj, msg) => destino.error(obj, msg),
};
