export function fmt(value: number, decimals = 2): string {
  return new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

export function fmtCurrency(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value)
}

export function fmtBig(value: number): string {
  if (value >= 1e9) return `R$ ${fmt(value / 1e9, 1)}bi`
  if (value >= 1e6) return `R$ ${fmt(value / 1e6, 1)}mi`
  return fmtCurrency(value)
}

export function changeColor(pct: number): string {
  return pct >= 0 ? 'text-positive' : 'text-negative'
}

export function changeSign(pct: number): string {
  return pct >= 0 ? `+${fmt(pct)}%` : `${fmt(pct)}%`
}
