'use client'

import { useState } from 'react'
import { Sparkles, Loader2, RefreshCw, AlertCircle } from 'lucide-react'

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
      setError(err instanceof Error ? err.message : 'Erro ao gerar insights')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card card-accent p-6 animate-fade-in-4 flex flex-col">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
               style={{ background: 'rgba(227,179,65,0.15)' }}>
            <Sparkles className="w-4 h-4" style={{ color: 'var(--yellow)' }} />
          </div>
          <div>
            <h3 className="text-[15px] font-semibold" style={{ color: 'var(--text)' }}>
              Insights com IA
            </h3>
            <p className="text-[11px]" style={{ color: 'var(--muted)' }}>Mistral AI</p>
          </div>
        </div>
        {loaded && !loading && (
          <button onClick={handleLoad} className="btn-ghost text-[12px] py-1.5 px-2.5">
            <RefreshCw className="w-3.5 h-3.5" />
            Atualizar
          </button>
        )}
      </div>

      {!loaded && !loading && !error && (
        <div className="flex-1 flex flex-col justify-center">
          <p className="text-[13px] mb-5 leading-relaxed" style={{ color: 'var(--muted)' }}>
            Análise inteligente do perfil do desenvolvedor — pontos fortes, padrões de uso de linguagens e sugestões de melhoria.
          </p>
          <button onClick={handleLoad} className="btn-primary self-start">
            <Sparkles className="w-4 h-4" />
            Gerar Análise
          </button>
        </div>
      )}

      {loading && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3" style={{ color: 'var(--yellow)' }} />
            <p className="text-[13px]" style={{ color: 'var(--muted)' }}>
              Analisando perfil com Mistral AI...
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-lg p-4 flex gap-3" style={{ background: 'rgba(248,81,73,0.1)', border: '1px solid rgba(248,81,73,0.3)' }}>
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: 'var(--red)' }} />
          <div>
            <p className="text-[13px] font-medium mb-1" style={{ color: 'var(--red)' }}>Erro ao gerar insights</p>
            <p className="text-[12px]" style={{ color: 'var(--muted)' }}>{error}</p>
            <button onClick={handleLoad} className="text-[12px] mt-2 font-medium" style={{ color: 'var(--blue-light)' }}>
              Tentar novamente
            </button>
          </div>
        </div>
      )}

      {loaded && insights.length > 0 && (
        <ul className="space-y-3">
          {insights.map((insight, i) => (
            <li
              key={i}
              className="flex gap-3 p-3 rounded-lg text-[13px] leading-relaxed"
              style={{
                background: 'var(--surface2)',
                border: '1px solid var(--border)',
                animationDelay: `${i * 60}ms`,
              }}
            >
              <span
                className="w-5 h-5 rounded-full flex-shrink-0 flex items-center justify-center text-[10px] font-bold mt-0.5"
                style={{ background: 'rgba(227,179,65,0.2)', color: 'var(--yellow)' }}
              >
                {i + 1}
              </span>
              <span style={{ color: 'var(--text)' }}>{insight}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
