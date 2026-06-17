const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export interface ShortURL {
  id: number;
  short_code: string;
  original_url: string;
  created_at: string;
  click_count: number;
}

export interface ShortenResponse {
  short_code: string;
  short_url: string;
  original_url: string;
}

export interface DailyStat {
  date: string;
  count: number;
}

export async function shortenURL(url: string): Promise<ShortenResponse> {
  const res = await fetch(`${API_BASE}/api/shorten`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { error?: string }).error ?? "Failed to shorten URL");
  }
  return res.json();
}

export async function listURLs(): Promise<ShortURL[]> {
  const res = await fetch(`${API_BASE}/api/urls`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch URLs");
  return res.json();
}

export async function getStats(code: string): Promise<DailyStat[]> {
  const res = await fetch(`${API_BASE}/api/urls/${code}/stats`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}
