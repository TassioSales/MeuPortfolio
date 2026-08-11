/**
 * Paleta dos gráficos.
 *
 * Os valores vieram da paleta de referência do guia de visualização e foram
 * conferidos com o validador (bandas de luminosidade, piso de croma, separação
 * para daltonismo e contraste com a superfície) nos dois modos. Não troque um
 * hex isolado sem revalidar a paleta inteira: a ordem dos slots é o mecanismo
 * de segurança para CVD, não escolha estética.
 */

/** Slots categóricos — identidade de série. Usados em ordem fixa, nunca ciclados. */
export const SERIES = {
  light: ["#2a78d6", "#eb6834"],
  dark: ["#3987e5", "#d95926"],
} as const;

/**
 * Rampa ordinal do funil: um hue, claro→escuro.
 *
 * Começa no passo 250 (`#86b6ef`) porque o passo mais próximo da superfície
 * precisa de ao menos 2:1 de contraste — passos mais claros sumiriam no fundo.
 */
export const FUNNEL_RAMP = {
  light: ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"],
  dark: ["#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4"],
} as const;

/** Tinta e apoios — texto nunca usa a cor da série. */
export const INK = {
  light: { primary: "#0b0b0b", secondary: "#52514e", grid: "#e4e7ec", surface: "#ffffff" },
  dark: { primary: "#ffffff", secondary: "#c3c2b7", grid: "#383835", surface: "#1a1a19" },
} as const;

export type ChartMode = "light" | "dark";

/** Segundos em texto curto: 45s, 2min, 1h20. */
export function formatSeconds(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = seconds / 60;
  if (minutes < 60) return `${minutes.toFixed(minutes < 10 ? 1 : 0)}min`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h${String(Math.round(minutes % 60)).padStart(2, "0")}`;
}

/** "2026-08-11" → "11/08" (eixo compacto). */
export function formatDayShort(iso: string): string {
  const [, month, day] = iso.split("-");
  return `${day}/${month}`;
}
