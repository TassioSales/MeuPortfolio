/**
 * Tema claro, escuro ou o do sistema.
 *
 * Três opções e não duas: "seguir o sistema" é o padrão porque quem já
 * configurou o computador para escuro não deveria ter que configurar de novo
 * aqui — e porque é a única escolha que continua certa quando a preferência do
 * sistema muda sozinha ao anoitecer.
 *
 * A escolha vive no `localStorage`, não em cookie nem no servidor: é
 * preferência de aparelho, não de conta. A mesma pessoa pode querer escuro no
 * notebook da madrugada e claro no computador do escritório.
 */

export type Tema = "claro" | "escuro" | "sistema";

export const CHAVE_DO_TEMA = "advogai:tema";

export function eTema(valor: unknown): valor is Tema {
  return valor === "claro" || valor === "escuro" || valor === "sistema";
}

export function lerTemaSalvo(): Tema {
  if (typeof window === "undefined") return "sistema";
  const salvo = window.localStorage.getItem(CHAVE_DO_TEMA);
  return eTema(salvo) ? salvo : "sistema";
}

export function preferenciaDoSistema(): "claro" | "escuro" {
  if (typeof window === "undefined" || !window.matchMedia) return "claro";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "escuro"
    : "claro";
}

/** O tema que de fato vai à tela. */
export function temaEfetivo(tema: Tema): "claro" | "escuro" {
  return tema === "sistema" ? preferenciaDoSistema() : tema;
}

export function aplicarTema(tema: Tema): void {
  if (typeof document === "undefined") return;
  document.documentElement.classList.toggle("dark", temaEfetivo(tema) === "escuro");
}

/**
 * O script que roda antes da primeira pintura.
 *
 * Sem ele a página nasce clara e vira escura quando o React monta — um flash
 * branco na cara de quem escolheu escuro justamente para não levar um. Por isso
 * é string inline e não componente: precisa executar antes do React existir.
 *
 * Silencioso em caso de erro de propósito: `localStorage` estoura em navegação
 * privada de alguns navegadores, e o preço de falhar aqui seria a página não
 * renderizar.
 */
export const SCRIPT_ANTI_PISCADA = `
(function(){try{
  var t = localStorage.getItem(${JSON.stringify(CHAVE_DO_TEMA)}) || "sistema";
  var escuro = t === "escuro" || (t === "sistema" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches);
  if (escuro) document.documentElement.classList.add("dark");
}catch(e){}})();
`.trim();
