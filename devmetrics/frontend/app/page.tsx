'use client'

import { useState, useEffect, useRef } from 'react'
import Image from 'next/image'
import {
  Github, Star, GitFork, Users, MapPin, Building2,
  Search, Loader2, ExternalLink, Calendar, Settings,
  Key, TrendingUp, CheckCircle2, Clock, X,
} from 'lucide-react'
import StatsCard from '@/components/StatsCard'
import LanguageChart from '@/components/LanguageChart'
import AIInsights from '@/components/AIInsights'
import SettingsModal from '@/components/SettingsModal'
import ActivityHeatmap from '@/components/ActivityHeatmap'
import {
  fetchUserMetrics,
  fetchInsights,
  getMistralKey,
  getHistory,
  addToHistory,
  getUsernameFromURL,
  setUsernameInURL,
  type UserMetricsResponse,
} from '@/lib/api'

const LANG_COLORS: Record<string, string> = {
  Python: '#3572A5', JavaScript: '#f1e05a', TypeScript: '#2b7489',
  Go: '#00ADD8', Rust: '#dea584', Java: '#b07219', 'C++': '#f34b7d',
  C: '#555555', Ruby: '#701516', PHP: '#4F5D95', Swift: '#ffac45',
  Kotlin: '#F18E33', 'Jupyter Notebook': '#DA5B0B', HTML: '#e34c26',
  CSS: '#563d7c', Shell: '#89e051', Dart: '#00B4AB', Vue: '#41b883',
}
function langColor(lang: string) {
  return LANG_COLORS[lang] || '#8b949e'
}

export default function Home() {
  const [username, setUsername] = useState('')
  const [data, setData] = useState<UserMetricsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const [hasKey, setHasKey] = useState(false)
  const [history, setHistory] = useState<string[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const historyRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setHasKey(!!getMistralKey())
    setHistory(getHistory())
    const u = getUsernameFromURL()
    if (u) {
      setUsername(u)
      doSearch(u)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // close history on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        historyRef.current && !historyRef.current.contains(e.target as Node) &&
        inputRef.current && !inputRef.current.contains(e.target as Node)
      ) {
        setShowHistory(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const doSearch = async (u: string) => {
    if (!u.trim()) return
    setLoading(true)
    setError(null)
    setData(null)
    setShowHistory(false)
    try {
      const result = await fetchUserMetrics(u.trim())
      setData(result)
      addToHistory(u.trim())
      setHistory(getHistory())
      setUsernameInURL(u.trim())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao buscar dados')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    doSearch(username)
  }

  const handleHistorySelect = (u: string) => {
    setUsername(u)
    doSearch(u)
  }

  const handleSettingsSave = () => {
    setHasKey(!!getMistralKey())
  }

  const maxYear = data?.metrics.repos_by_year
    ? Math.max(...data.metrics.repos_by_year.map((y) => y.count), 1)
    : 1

  const memberSince = data?.user.created_at
    ? new Date(data.user.created_at).getFullYear()
    : null

  return (
    <main className="min-h-screen" style={{ background: 'var(--bg)' }}>
      {/* Header */}
      <header style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)' }}>
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center"
                 style={{ background: 'rgba(56,139,253,0.15)' }}>
              <TrendingUp className="w-4 h-4" style={{ color: 'var(--blue-light)' }} />
            </div>
            <span className="font-bold text-[16px]" style={{ color: 'var(--text)' }}>DevMetrics</span>
            <span className="hidden sm:inline text-[12px] px-2 py-0.5 rounded-full"
                  style={{ background: 'var(--surface2)', color: 'var(--muted)', border: '1px solid var(--border)' }}>
              GitHub Analytics
            </span>
          </div>

          <div className="flex items-center gap-2">
            {hasKey ? (
              <div className="hidden sm:flex items-center gap-1.5 text-[12px] px-2.5 py-1 rounded-full"
                   style={{ background: 'rgba(63,185,80,0.12)', color: 'var(--green)', border: '1px solid rgba(63,185,80,0.25)' }}>
                <CheckCircle2 className="w-3 h-3" />
                IA configurada
              </div>
            ) : (
              <button
                onClick={() => setShowSettings(true)}
                className="hidden sm:flex items-center gap-1.5 text-[12px] px-2.5 py-1 rounded-full"
                style={{ background: 'rgba(163,113,247,0.1)', color: 'var(--purple)', border: '1px solid rgba(163,113,247,0.25)' }}
              >
                <Key className="w-3 h-3" />
                Configurar IA
              </button>
            )}
            <button onClick={() => setShowSettings(true)} className="btn-ghost border-0 p-2" title="Configurações">
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Search */}
        <div className="max-w-2xl mx-auto mb-10 animate-fade-in">
          <h1 className="text-[28px] font-bold text-center mb-2" style={{ color: 'var(--text)' }}>
            Analise qualquer perfil do{' '}
            <span className="gradient-text">GitHub</span>
          </h1>
          <p className="text-center text-[14px] mb-6" style={{ color: 'var(--muted)' }}>
            Métricas detalhadas, heatmap de contribuições e insights gerados por IA
          </p>

          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="flex-1 relative">
              <Github className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 z-10" style={{ color: 'var(--muted)' }} />
              <input
                ref={inputRef}
                type="text"
                value={username}
                onChange={(e) => { setUsername(e.target.value) }}
                onFocus={() => history.length > 0 && setShowHistory(true)}
                placeholder="Username do GitHub..."
                className="input-field pl-10 pr-8"
                style={{ padding: '11px 32px 11px 38px' }}
                autoComplete="off"
              />
              {username && (
                <button
                  type="button"
                  onClick={() => { setUsername(''); setShowHistory(false) }}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--muted)' }}
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}

              {/* History dropdown */}
              {showHistory && history.length > 0 && (
                <div
                  ref={historyRef}
                  className="absolute top-full left-0 right-0 mt-1 card z-50 overflow-hidden"
                  style={{ boxShadow: '0 8px 24px rgba(1,4,9,0.6)' }}
                >
                  <div className="px-3 py-2 text-[11px] font-medium uppercase tracking-wide"
                       style={{ color: 'var(--muted)', borderBottom: '1px solid var(--border)' }}>
                    Buscas recentes
                  </div>
                  {history.map((u) => (
                    <button
                      key={u}
                      type="button"
                      onClick={() => handleHistorySelect(u)}
                      className="w-full flex items-center gap-2.5 px-3 py-2.5 text-[13px] text-left transition-colors"
                      style={{ color: 'var(--text)' }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--surface2)')}
                      onMouseLeave={(e) => (e.currentTarget.style.background = '')}
                    >
                      <Clock className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--muted)' }} />
                      {u}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading
                ? <><Loader2 className="w-4 h-4 animate-spin" />Buscando...</>
                : <><Search className="w-4 h-4" />Analisar</>
              }
            </button>
          </form>
        </div>

        {/* Error */}
        {error && (
          <div className="max-w-2xl mx-auto mb-6 rounded-lg p-4 text-[14px] flex items-center gap-2"
               style={{ background: 'rgba(248,81,73,0.1)', border: '1px solid rgba(248,81,73,0.4)', color: 'var(--red)' }}>
            <Github className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Results */}
        {data && (
          <div className="space-y-5">
            {/* Profile */}
            <div className="card card-accent p-6 animate-fade-in">
              <div className="flex flex-col sm:flex-row gap-5">
                <div className="relative flex-shrink-0">
                  <Image
                    src={data.user.avatar_url}
                    alt={data.user.login}
                    width={88}
                    height={88}
                    className="rounded-full"
                    style={{ border: '2px solid var(--border)' }}
                  />
                  {memberSince && (
                    <div className="absolute -bottom-1 -right-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full"
                         style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--muted)' }}>
                      {memberSince}
                    </div>
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div>
                      <h2 className="text-[22px] font-bold" style={{ color: 'var(--text)' }}>
                        {data.user.name || data.user.login}
                      </h2>
                      <p className="text-[13px]" style={{ color: 'var(--muted)' }}>
                        @{data.user.login}
                      </p>
                    </div>
                    <a
                      href={data.user.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-ghost text-[12px] py-1.5 flex-shrink-0"
                    >
                      <Github className="w-3.5 h-3.5" />
                      Ver no GitHub
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>

                  {data.user.bio && (
                    <p className="text-[13px] mt-2 mb-3 leading-relaxed" style={{ color: '#c9d1d9' }}>
                      {data.user.bio}
                    </p>
                  )}

                  <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-[12px]" style={{ color: 'var(--muted)' }}>
                    <span className="flex items-center gap-1.5">
                      <Users className="w-3.5 h-3.5" />
                      <strong style={{ color: 'var(--text)' }}>{data.user.followers.toLocaleString('pt-BR')}</strong> seguidores
                      <span className="opacity-40 mx-0.5">·</span>
                      <strong style={{ color: 'var(--text)' }}>{data.user.following.toLocaleString('pt-BR')}</strong> seguindo
                    </span>
                    {data.user.company && (
                      <span className="flex items-center gap-1.5">
                        <Building2 className="w-3.5 h-3.5" />
                        {data.user.company}
                      </span>
                    )}
                    {data.user.location && (
                      <span className="flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5" />
                        {data.user.location}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatsCard icon="repo" label="Repositórios" value={data.metrics.total_repos} delay={0} />
              <StatsCard icon="star" label="Estrelas" value={data.metrics.total_stars} delay={50} />
              <StatsCard icon="fork" label="Forks" value={data.metrics.total_forks} delay={100} />
              <StatsCard icon="lang" label="Top Linguagem" value={data.metrics.most_used_language || 'N/A'} delay={150} />
            </div>

            {/* Heatmap */}
            <ActivityHeatmap username={data.user.login} />

            {/* Chart + AI */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {data.metrics.languages?.length > 0 && (
                <LanguageChart languages={data.metrics.languages} />
              )}
              <AIInsights username={data.user.login} fetchInsightsFn={fetchInsights} />
            </div>

            {/* Top Repos */}
            {data.metrics.top_repos?.length > 0 && (
              <div className="animate-fade-in-4">
                <h3 className="text-[15px] font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--text)' }}>
                  <Star className="w-4 h-4" style={{ color: 'var(--yellow)' }} />
                  Principais Repositórios
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {data.metrics.top_repos.map((repo, i) => (
                    <a
                      key={repo.name}
                      href={repo.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="card p-4 group block"
                      style={{ animationDelay: `${i * 40}ms` }}
                    >
                      <div className="flex items-start justify-between mb-2 gap-2">
                        <h4
                          className="font-semibold text-[13px] truncate group-hover:underline"
                          style={{ color: 'var(--blue-light)' }}
                        >
                          {repo.name}
                        </h4>
                        <ExternalLink className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                                      style={{ color: 'var(--muted)' }} />
                      </div>

                      {repo.description && (
                        <p className="text-[12px] mb-3 line-clamp-2 leading-relaxed" style={{ color: 'var(--muted)' }}>
                          {repo.description}
                        </p>
                      )}

                      {repo.topics?.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-3">
                          {repo.topics.slice(0, 3).map((topic) => (
                            <span key={topic} className="tag">{topic}</span>
                          ))}
                        </div>
                      )}

                      <div className="flex items-center gap-4 text-[11px]" style={{ color: 'var(--muted)' }}>
                        {repo.language && (
                          <span className="flex items-center gap-1.5">
                            <span className="w-2.5 h-2.5 rounded-full"
                                  style={{ background: langColor(repo.language) }} />
                            {repo.language}
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <Star className="w-3 h-3" /> {repo.stars}
                        </span>
                        <span className="flex items-center gap-1">
                          <GitFork className="w-3 h-3" /> {repo.forks}
                        </span>
                      </div>
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Timeline */}
            {data.metrics.repos_by_year?.length > 0 && (
              <div className="card card-accent p-6 animate-fade-in-5">
                <h3 className="text-[15px] font-semibold mb-6 flex items-center gap-2" style={{ color: 'var(--text)' }}>
                  <Calendar className="w-4 h-4" style={{ color: 'var(--muted)' }} />
                  Repositórios Criados por Ano
                </h3>
                <div className="flex items-end gap-2" style={{ height: '100px' }}>
                  {data.metrics.repos_by_year.map((item) => {
                    const height = maxYear > 0 ? (item.count / maxYear) * 100 : 0
                    return (
                      <div key={item.year} className="flex flex-col items-center gap-1.5 flex-1 group">
                        <span className="text-[11px] font-medium opacity-0 group-hover:opacity-100 transition-opacity"
                              style={{ color: 'var(--blue-light)' }}>
                          {item.count}
                        </span>
                        <div className="w-full rounded-t-sm relative overflow-hidden"
                             style={{ height: `${Math.max(height, 4)}%`, minHeight: '4px' }}>
                          <div className="absolute inset-0 transition-all"
                               style={{ background: 'linear-gradient(to top, #1f6feb, #388bfd)', opacity: 0.7 }} />
                          <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity"
                               style={{ background: 'linear-gradient(to top, #388bfd, #58a6ff)' }} />
                        </div>
                        <span className="text-[10px]" style={{ color: 'var(--muted)' }}>
                          {item.year}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Empty state */}
        {!data && !loading && !error && (
          <div className="text-center py-20 animate-fade-in">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-5"
                 style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
              <Github className="w-8 h-8" style={{ color: 'var(--border-hover)' }} />
            </div>
            <h2 className="text-[18px] font-semibold mb-2" style={{ color: 'var(--muted)' }}>
              Busque um perfil do GitHub
            </h2>
            <p className="text-[13px] mb-6" style={{ color: '#6e7681' }}>
              Digite qualquer username acima para visualizar as métricas e análises
            </p>

            {history.length > 0 && (
              <div className="flex flex-wrap justify-center gap-2 mb-6">
                {history.map((u) => (
                  <button
                    key={u}
                    onClick={() => handleHistorySelect(u)}
                    className="btn-ghost text-[12px] py-1.5"
                  >
                    <Clock className="w-3 h-3" />
                    {u}
                  </button>
                ))}
              </div>
            )}

            {!hasKey && (
              <button
                onClick={() => setShowSettings(true)}
                className="btn-ghost mx-auto"
                style={{ display: 'inline-flex' }}
              >
                <Key className="w-3.5 h-3.5" />
                Configurar chave Mistral AI para insights
              </button>
            )}
          </div>
        )}
      </div>

      {showSettings && (
        <SettingsModal
          onClose={() => setShowSettings(false)}
          onSave={handleSettingsSave}
        />
      )}
    </main>
  )
}
