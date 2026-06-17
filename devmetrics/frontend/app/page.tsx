'use client'

import { useState } from 'react'
import Image from 'next/image'
import {
  Github,
  Star,
  GitFork,
  Users,
  MapPin,
  Building2,
  Search,
  Loader2,
  ExternalLink,
  Calendar,
} from 'lucide-react'
import StatsCard from '@/components/StatsCard'
import LanguageChart from '@/components/LanguageChart'
import AIInsights from '@/components/AIInsights'
import { fetchUserMetrics, fetchInsights, type UserMetricsResponse } from '@/lib/api'

export default function Home() {
  const [username, setUsername] = useState('')
  const [data, setData] = useState<UserMetricsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim()) return
    setLoading(true)
    setError(null)
    setData(null)
    try {
      const result = await fetchUserMetrics(username.trim())
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-[#0d1117]">
      {/* Header */}
      <header className="border-b border-[#30363d] bg-[#161b22]">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center gap-3">
          <Github className="w-7 h-7 text-white" />
          <h1 className="text-xl font-semibold text-white">DevMetrics</h1>
          <span className="text-[#8b949e] text-sm ml-1">GitHub Analytics Dashboard</span>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Search */}
        <form onSubmit={handleSearch} className="flex gap-3 mb-8">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8b949e]" />
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter GitHub username..."
              className="w-full pl-10 pr-4 py-2.5 bg-[#21262d] border border-[#30363d] rounded-lg text-[#e6edf3] placeholder-[#8b949e] focus:outline-none focus:border-[#388bfd] focus:ring-1 focus:ring-[#388bfd] text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2.5 bg-[#238636] hover:bg-[#2ea043] text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            {loading ? 'Loading...' : 'Analyze'}
          </button>
        </form>

        {/* Error */}
        {error && (
          <div className="bg-[#2d1215] border border-[#f85149] rounded-lg p-4 mb-6 text-[#f85149] text-sm">
            {error}
          </div>
        )}

        {/* Results */}
        {data && (
          <div className="space-y-6">
            {/* User profile */}
            <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-6">
              <div className="flex flex-col sm:flex-row gap-6">
                <Image
                  src={data.user.avatar_url}
                  alt={data.user.login}
                  width={96}
                  height={96}
                  className="rounded-full border-2 border-[#30363d]"
                />
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-white">{data.user.name || data.user.login}</h2>
                  <p className="text-[#8b949e] text-sm mb-2">@{data.user.login}</p>
                  {data.user.bio && <p className="text-[#e6edf3] mb-3 text-sm">{data.user.bio}</p>}
                  <div className="flex flex-wrap gap-4 text-sm text-[#8b949e]">
                    {data.user.company && (
                      <span className="flex items-center gap-1.5">
                        <Building2 className="w-4 h-4" /> {data.user.company}
                      </span>
                    )}
                    {data.user.location && (
                      <span className="flex items-center gap-1.5">
                        <MapPin className="w-4 h-4" /> {data.user.location}
                      </span>
                    )}
                    <span className="flex items-center gap-1.5">
                      <Users className="w-4 h-4" />
                      <span>
                        <strong className="text-[#e6edf3]">{data.user.followers}</strong> followers
                      </span>
                      <span className="mx-1">·</span>
                      <span>
                        <strong className="text-[#e6edf3]">{data.user.following}</strong> following
                      </span>
                    </span>
                  </div>
                </div>
                <a
                  href={data.user.html_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-[#388bfd] hover:underline h-fit"
                >
                  View on GitHub <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>

            {/* Stats cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatsCard icon="repo" label="Public Repos" value={data.metrics.total_repos} />
              <StatsCard icon="star" label="Total Stars" value={data.metrics.total_stars} />
              <StatsCard icon="fork" label="Total Forks" value={data.metrics.total_forks} />
              <StatsCard icon="lang" label="Top Language" value={data.metrics.most_used_language || 'N/A'} />
            </div>

            {/* Language chart + AI insights */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {data.metrics.languages && data.metrics.languages.length > 0 && (
                <LanguageChart languages={data.metrics.languages} />
              )}
              <AIInsights username={data.user.login} fetchInsightsFn={fetchInsights} />
            </div>

            {/* Top repos */}
            {data.metrics.top_repos && data.metrics.top_repos.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-white mb-4">Top Repositories</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {data.metrics.top_repos.map((repo) => (
                    <a
                      key={repo.name}
                      href={repo.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="bg-[#161b22] border border-[#30363d] rounded-lg p-4 hover:border-[#388bfd] transition-colors group"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="text-[#388bfd] font-medium text-sm group-hover:underline truncate">
                          {repo.name}
                        </h4>
                        <ExternalLink className="w-3.5 h-3.5 text-[#8b949e] flex-shrink-0 ml-2 mt-0.5" />
                      </div>
                      {repo.description && (
                        <p className="text-[#8b949e] text-xs mb-3 line-clamp-2">{repo.description}</p>
                      )}
                      <div className="flex items-center gap-4 text-xs text-[#8b949e]">
                        {repo.language && (
                          <span className="flex items-center gap-1.5">
                            <span className="w-2.5 h-2.5 rounded-full bg-[#388bfd]" />
                            {repo.language}
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <Star className="w-3.5 h-3.5" /> {repo.stars}
                        </span>
                        <span className="flex items-center gap-1">
                          <GitFork className="w-3.5 h-3.5" /> {repo.forks}
                        </span>
                      </div>
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Repos by year */}
            {data.metrics.repos_by_year && data.metrics.repos_by_year.length > 0 && (
              <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-[#8b949e]" /> Repository Timeline
                </h3>
                <div className="flex items-end gap-2 h-24">
                  {data.metrics.repos_by_year.map((item) => {
                    const maxCount = Math.max(...data.metrics.repos_by_year.map((y) => y.count))
                    const height = maxCount > 0 ? (item.count / maxCount) * 100 : 0
                    return (
                      <div key={item.year} className="flex flex-col items-center gap-1 flex-1">
                        <span className="text-xs text-[#8b949e]">{item.count}</span>
                        <div
                          className="w-full bg-[#1f6feb] rounded-sm"
                          style={{ height: `${height}%`, minHeight: '4px' }}
                        />
                        <span className="text-xs text-[#8b949e]">{item.year}</span>
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
          <div className="text-center py-24">
            <Github className="w-16 h-16 text-[#30363d] mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-[#8b949e] mb-2">Search for a GitHub user</h2>
            <p className="text-[#8b949e] text-sm">Enter any GitHub username above to see their analytics</p>
          </div>
        )}
      </div>
    </main>
  )
}
