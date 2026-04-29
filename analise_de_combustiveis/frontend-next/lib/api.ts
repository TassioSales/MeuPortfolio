import {
  ComparisonPoint,
  ForecastPoint,
  FuelName,
  FuelSummary,
  HistoryPoint,
  InsightPayload,
  MarketSignal,
  ExplorerPayload,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

async function fetchJSON<T>(path: string): Promise<T> {
  try {
    const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
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
) {
  const params = new URLSearchParams({ 
    fuel, 
    state, 
    view, 
    compare_with: compareWith, 
    city 
  });
  if (startDate) params.append("start_date", startDate);
  if (endDate) params.append("end_date", endDate);
  return fetchJSON<InsightPayload>(`/api/v1/insights?${params.toString()}`);
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
