import type {
  ComparisonPoint,
  ForecastPoint,
  FuelName,
  FuelSummary,
  HistoryPoint,
  InsightPayload,
  MarketSignal,
  ExplorerPayload,
  RankingEntry,
  TrendPoint,
  NationalStats,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

async function fetchJSON<T>(path: string, extraHeaders?: Record<string, string>): Promise<T> {
  try {
    const response = await fetch(`${API_URL}${path}`, {
      cache: "no-store",
      headers: extraHeaders,
    });
    if (!response.ok) {
      throw new Error(`API error ${response.status}`);
    }
    const payload = await response.json();
    return payload.data as T;
  } catch (error) {
    if (error instanceof TypeError || (error instanceof Error && error.message.includes("fetch"))) {
      throw new Error("API offline");
    }
    throw error;
  }
}

async function fetchArray<T>(path: string): Promise<T[]> {
  const payload = await fetchJSON<T[] | null>(path);
  return Array.isArray(payload) ? payload : [];
}

export async function getOverview(fuel: FuelName, state: string, startDate?: string, endDate?: string) {
  const params = new URLSearchParams({ fuel, state });
  if (startDate) params.append("start_date", startDate);
  if (endDate) params.append("end_date", endDate);
  return fetchArray<FuelSummary>(`/api/v1/overview?${params.toString()}`);
}

export async function getHistory(fuel: FuelName, state: string, city: string, startDate?: string, endDate?: string) {
  const params = new URLSearchParams({ fuel, state, city });
  if (startDate) params.append("start_date", startDate);
  if (endDate) params.append("end_date", endDate);
  return fetchArray<HistoryPoint>(`/api/v1/history?${params.toString()}`);
}

export async function getCities(fuel: FuelName, state: string) {
  return fetchArray<string>(`/api/v1/cities?fuel=${fuel}&state=${state}`);
}

export async function getForecast(fuel: FuelName, state: string, startDate?: string, endDate?: string) {
  const params = new URLSearchParams({ fuel, state });
  if (startDate) params.append("start_date", startDate);
  if (endDate) params.append("end_date", endDate);
  return fetchArray<ForecastPoint>(`/api/v1/forecast?${params.toString()}`);
}

export async function getComparison(fuel: FuelName, compareWith: FuelName, state: string, startDate?: string, endDate?: string) {
  const params = new URLSearchParams({ fuel, compare_with: compareWith, state });
  if (startDate) params.append("start_date", startDate);
  if (endDate) params.append("end_date", endDate);
  return fetchArray<ComparisonPoint>(`/api/v1/compare?${params.toString()}`);
}

export async function getMap(fuel: FuelName) {
  return fetchArray<FuelSummary>(`/api/v1/map?fuel=${fuel}`);
}

export async function getInsights(
  fuel: FuelName,
  state: string,
  view: string,
  compareWith = "",
  city = "",
  startDate?: string,
  endDate?: string,
  mistralKey?: string,
) {
  const params = new URLSearchParams({
    fuel,
    state,
    view,
    compare_with: compareWith,
    city,
  });
  if (startDate) params.append("start_date", startDate);
  if (endDate) params.append("end_date", endDate);
  const headers: Record<string, string> = {};
  if (mistralKey) headers["X-Mistral-Key"] = mistralKey;
  return fetchJSON<InsightPayload>(`/api/v1/insights?${params.toString()}`, headers);
}

export async function getMarket(fuel: FuelName, state: string, startDate?: string, endDate?: string) {
  const params = new URLSearchParams({ fuel, state });
  if (startDate) params.append("start_date", startDate);
  if (endDate) params.append("end_date", endDate);
  return fetchArray<MarketSignal>(`/api/v1/market?${params.toString()}`);
}

export async function getExplorer() {
  return fetchJSON<ExplorerPayload>(`/api/v1/explorer`);
}

export async function getFuels() {
  return fetchArray<FuelName>(`/api/v1/fuels`);
}

export async function getRanking(fuel: FuelName, order: "asc" | "desc" = "desc", limit = 0) {
  const params = new URLSearchParams({ fuel, order });
  if (limit > 0) params.append("limit", String(limit));
  return fetchArray<RankingEntry>(`/api/v1/ranking?${params.toString()}`);
}

export async function getTrends(fuel: FuelName, state: string, startDate?: string, endDate?: string) {
  const params = new URLSearchParams({ fuel, state });
  if (startDate) params.append("start_date", startDate);
  if (endDate) params.append("end_date", endDate);
  return fetchArray<TrendPoint>(`/api/v1/trends?${params.toString()}`);
}

export async function getStats(fuel: FuelName, startDate?: string, endDate?: string) {
  const params = new URLSearchParams({ fuel });
  if (startDate) params.append("start_date", startDate);
  if (endDate) params.append("end_date", endDate);
  return fetchJSON<NationalStats>(`/api/v1/stats?${params.toString()}`);
}
