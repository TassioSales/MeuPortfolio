'use client'

import { useState } from 'react'
import { Sparkles, Loader2, ChevronRight } from 'lucide-react'

interface AIInsightsProps {
  username: string
  fetchInsightsFn: (username: string) => Promise<{ insights: string[] }>
}

export default function AIInsights({ username, fetchInsightsFn }: AIInsightsProps) {
  const [insights, setInsights] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loaded, setLoaded] = useState(false)

  const handleLoad = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchInsightsFn(username)
      setInsights(result.insights)
      setLoaded(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate insights')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-6">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="w-5 h-5 text-[#e3b341]" />
        <h3 className="text-lg font-semibold text-white">AI Insights</h3>
        <span className="text-xs text-[#8b949e] bg-[#21262d] px-2 py-0.5 rounded-full">
          Mistral AI
        </span>
      </div>

      {!loaded && !loading && (
        <div>
          <p className="text-[#8b949e] text-sm mb-4">
            Get AI-powered analysis of this developer&apos;s profile, strengths, and trends.
          </p>
          <button
            onClick={handleLoad}
            className="flex items-center gap-2 px-4 py-2 bg-[#21262d] hover:bg-[#30363d] border border-[#30363d] text-[#e6edf3] text-sm rounded-lg transition-colors"
          >
            <Sparkles className="w-4 h-4 text-[#e3b341]" />
            Generate Insights
          </button>
        </div>
      )}

      {loading && (
        <div className="flex items-center gap-3 text-[#8b949e] text-sm">
          <Loader2 className="w-4 h-4 animate-spin" />
          Analyzing profile with Mistral AI...
        </div>
      )}

      {error && (
        <div className="text-[#f85149] text-sm bg-[#2d1215] border border-[#f85149]/30 rounded p-3">
          {error}
        </div>
      )}

      {loaded && insights.length > 0 && (
        <ul className="space-y-3">
          {insights.map((insight, i) => (
            <li key={i} className="flex gap-3 text-sm text-[#e6edf3]">
              <ChevronRight className="w-4 h-4 text-[#e3b341] flex-shrink-0 mt-0.5" />
              <span>{insight}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
