// Funções propositalmente quebradas, usadas pelos testes. Cada uma reproduz um bug real
// encontrado em biblioteca de utilitários de produção.

/** Bug: sem "@" na entrada, o domínio sai como o texto "undefined". */
export function extractBaseEmail(email: string): string {
  const [localPart, domain] = email.split("@");
  return `${localPart?.split("+")[0]}@${domain}`;
}

/** Bug: assinatura promete aceitar a entrada, mas lança com null. */
export function stripMarkdown(markdown: string): string {
  return markdown.replace(/[*_`#]/g, "");
}

/** Bug: lança em referência circular, apesar de prometer sempre devolver string. */
export function serialize(value: object): string {
  return JSON.stringify(value);
}

/** Bug: soma que devolve NaN sem avisar. */
export function totalWithTax(amount: number): string {
  return `R$ ${(amount * 1.1).toFixed(2)}`;
}

declare const location: { readonly pathname: string };

/** Só funciona no navegador: não é bug, é ambiente. A ferramenta deve pular, não reportar. */
export function currentPath(suffix: string): string {
  return `${location.pathname}${suffix}`;
}
