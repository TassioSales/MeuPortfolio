const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'

export interface GitHubUser {
  login: string
  name: string
  avatar_url: string
  bio: string
  company: string
  location: string
  blog: string
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

export interface ContributionDay {
  date: string
  count: number
}

export interface ContributionWeek {
  days: ContributionDay[]
}

export interface ContributionsResponse {
  total_contributions: number
  weeks: ContributionWeek[]
  error?: string
}

// --- Mistral key ---
export function getMistralKey(): string {
  if (typeof window === 'undefined') return ''
  return localStorage.getItem('devmetrics_mistral_key') || ''
}

export function setMistralKey(key: string): void {
  if (typeof window === 'undefined') return
  if (key) {
    localStorage.setItem('devmetrics_mistral_key', key)
  } else {
    localStorage.removeItem('devmetrics_mistral_key')
  }
}

// --- Search history ---
const HISTORY_KEY = 'devmetrics_history'

export function getHistory(): string[] {
  if (typeof window === 'undefined') return []
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
  } catch {
    return []
  }
}

export function addToHistory(username: string): void {
  if (typeof window === 'undefined') return
  const history = getHistory().filter((u) => u.toLowerCase() !== username.toLowerCase())
  history.unshift(username)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 6)))
}

// --- URL state ---
export function getUsernameFromURL(): string {
  if (typeof window === 'undefined') return ''
  return new URLSearchParams(window.location.search).get('u') || ''
}

export function setUsernameInURL(username: string): void {
  if (typeof window === 'undefined') return
  const newURL = username
    ? `${window.location.pathname}?u=${encodeURIComponent(username)}`
    : window.location.pathname
  window.history.pushState({}, '', newURL)
}

// --- API ---
async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, options)
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: 'Erro desconhecido' }))
    throw new Error((body as { error: string }).error || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export async function fetchUserMetrics(username: string): Promise<UserMetricsResponse> {
  return apiFetch<UserMetricsResponse>(`/api/user/${encodeURIComponent(username)}`)
}

export async function fetchInsights(username: string): Promise<{ insights: string[] }> {
  const key = getMistralKey()
  const headers: HeadersInit = {}
  if (key) headers['X-Mistral-Key'] = key
  return apiFetch<{ insights: string[] }>(
    `/api/user/${encodeURIComponent(username)}/insights`,
    { headers }
  )
}

export async function fetchContributions(username: string): Promise<ContributionsResponse> {
  return apiFetch<ContributionsResponse>(
    `/api/user/${encodeURIComponent(username)}/contributions`
  )
}
