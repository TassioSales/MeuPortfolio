import type { MacroResponse, HistoryPoint, MarketResponse, RegionalData, StatusResponse } from '@/lib/types'

const BASE = '/api/backend'

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { next: { revalidate: 300 } })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const api = {
  macro: () => fetchJSON<MacroResponse>('/macro'),
  history: (indicator: string, days = 90) =>
    fetchJSON<HistoryPoint[]>(`/history/${indicator}?days=${days}`),
  market: () => fetchJSON<MarketResponse>('/market'),
  regional: () => fetchJSON<RegionalData[]>('/regional'),
  status: () => fetchJSON<StatusResponse>('/status'),
}
