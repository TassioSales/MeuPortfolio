export type FuelName = "gasolina" | "etanol" | "diesel" | "glp" | "gnv";

export interface FuelSummary {
  product: string;
  state: string;
  average_price: number;
  volatility: number;
  dollar: number;
  brent: number;
  ipca: number;
  price_direction: string;
}

export interface HistoryPoint {
  week: string;
  state: string;
  city: string;
  product: string;
  average_price: number;
  volatility: number;
  average_buy_price: number;
}

export interface ForecastPoint {
  week: string;
  predicted: number;
  minimum: number;
  maximum: number;
  scenario: string;
}

export interface ComparisonPoint {
  week: string;
  primary_fuel: string;
  compared_fuel: string;
  primary_price: number;
  compared_price: number;
  advantage_percent: number;
  recommended_fuel: string;
}

export interface InsightPayload {
  title: string;
  summary: string;
  bullets: string[];
  source: string;
}

export interface MarketSignal {
  month: string;
  state: string;
  product: string;
  sales_volume_m3: number;
  processed_m3: number;
  produced_m3: number;
  supply_demand_ratio: number;
  refinery_gap_m3: number;
  market_regime: string;
}

export interface ExplorerTable {
  table: string;
  row_count: number;
  sample_rows: Record<string, string | number | null>[];
}

export interface ExplorerPayload {
  warehouse_path: string;
  tables: ExplorerTable[];
}

export interface RankingEntry {
  position: number;
  state: string;
  product: string;
  price: number;
  volatility: number;
  change_week_pct: number;
}

export interface TrendPoint {
  week: string;
  price: number;
  change_abs: number;
  change_pct: number;
}

export interface NationalStats {
  product: string;
  national_avg: number;
  min_price: number;
  max_price: number;
  min_state: string;
  max_state: string;
  state_count: number;
  change_week_pct: number;
}
