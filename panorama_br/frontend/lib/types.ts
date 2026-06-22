export interface MacroIndicator {
  value: number
  unit: string
  ref_date: string
  updated_at: string
}

export interface MacroResponse {
  indicators: Record<string, MacroIndicator>
  last_updated: string
}

export interface HistoryPoint {
  date: string
  value: number
}

export interface StockItem {
  symbol: string
  name: string
  price: number
  change_pct: number
  volume: number
  market_cap: number
  updated_at: string
}

export interface MarketResponse {
  ibovespa: StockItem | null
  stocks: StockItem[]
  last_updated: string
}

export interface RegionalData {
  uf: string
  year: number
  state_name: string
  region: string
  pib: number
  pib_per_capita: number
  population: number
  desemprego: number
}

export interface StatusResponse {
  status: string
  pipeline_last_run: string
  records_count: number
}
