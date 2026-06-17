const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'

export interface GitHubUser {
  login: string
  name: string
  avatar_url: string
  bio: string
  company: string
  location: string
  public_repos: number
  followers: number
  following: number
  created_at: string
  html_url: string
}

export interface LanguageStat {
  language: string
  bytes: number
  percentage: number
}

export interface RepoSummary {
  name: string
  description: string
  stars: number
  forks: number
  language: string
  updated_at: string
  html_url: string
  topics: string[]
}

export interface YearlyActivity {
  year: number
  count: number
}

export interface Metrics {
  total_repos: number
  total_stars: number
  total_forks: number
  languages: LanguageStat[]
  top_repos: RepoSummary[]
  repos_by_year: YearlyActivity[]
  most_used_language: string
}

export interface UserMetricsResponse {
  user: GitHubUser
  metrics: Metrics
}

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`)
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error((body as { error: string }).error || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export async function fetchUserMetrics(username: string): Promise<UserMetricsResponse> {
  return apiFetch<UserMetricsResponse>(`/api/user/${encodeURIComponent(username)}`)
}

export async function fetchLanguages(username: string): Promise<{ languages: LanguageStat[] }> {
  return apiFetch<{ languages: LanguageStat[] }>(`/api/user/${encodeURIComponent(username)}/languages`)
}

export async function fetchInsights(username: string): Promise<{ insights: string[] }> {
  return apiFetch<{ insights: string[] }>(`/api/user/${encodeURIComponent(username)}/insights`)
}
