'use client'

import { useEffect, useState } from 'react'
import { Calendar } from 'lucide-react'
import { fetchContributions, type ContributionsResponse } from '@/lib/api'

interface ActivityHeatmapProps {
  username: string
}

function getColor(count: number): string {
  if (count === 0) return '#161b22'
  if (count <= 2) return '#0e4429'
  if (count <= 5) return '#006d32'
  if (count <= 9) return '#26a641'
  return '#39d353'
}

const MONTHS = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
const DAYS = ['', 'Seg', '', 'Qua', '', 'Sex', '']

export default function ActivityHeatmap({ username }: ActivityHeatmapProps) {
  const [data, setData] = useState<ContributionsResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchContributions(username)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [username])

  const weeks = data?.weeks || []
  const total = data?.total_contributions || 0
  const noToken = !!data?.error

  const monthLabels: { label: string; col: number }[] = []
  let lastMonth = -1
  weeks.forEach((week, i) => {
    if (week.days && week.days.length > 0) {
      const month = new Date(week.days[0].date + 'T00:00:00').getMonth()
      if (month !== lastMonth) {
        monthLabels.push({ label: MONTHS[month], col: i })
        lastMonth = month
      }
    }
  })

  return (
    <div className="card card-accent p-6 animate-fade-in-5">
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
               style={{ background: 'rgba(57,211,83,0.12)' }}>
            <Calendar className="w-4 h-4" style={{ color: '#39d353' }} />
          </div>
          <div>
            <h3 className="text-[15px] font-semibold" style={{ color: 'var(--text)' }}>
              Atividade de Contribuições
            </h3>
            {!loading && !noToken && total > 0 && (
              <p className="text-[11px]" style={{ color: 'var(--muted)' }}>
                {total.toLocaleString('pt-BR')} contribuições no último ano
              </p>
            )}
          </div>
        </div>
        {!noToken && (
          <div className="hidden sm:flex items-center gap-1.5 text-[10px]" style={{ color: 'var(--muted)' }}>
            Menos
            {['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353'].map((c) => (
              <div key={c} style={{ width: 11, height: 11, borderRadius: 2, background: c, border: '1px solid rgba(255,255,255,0.05)' }} />
            ))}
            Mais
          </div>
        )}
      </div>

      {loading && (
        <div className="flex gap-1">
          <div className="flex flex-col gap-1 mr-1">
            {DAYS.map((_, i) => (
              <div key={i} style={{ width: 20, height: 11 }} />
            ))}
          </div>
          {[...Array(26)].map((_, wi) => (
            <div key={wi} className="flex flex-col gap-1">
              {[...Array(7)].map((_, di) => (
                <div key={di} className="skeleton" style={{ width: 11, height: 11, borderRadius: 2 }} />
              ))}
            </div>
          ))}
        </div>
      )}

      {!loading && noToken && (
        <div className="rounded-lg p-4 text-[13px]"
             style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--muted)' }}>
          Heatmap requer{' '}
          <code className="px-1 rounded text-[12px]" style={{ background: 'var(--surface)', color: 'var(--blue-light)' }}>
            GITHUB_TOKEN
          </code>{' '}
          configurado no backend para acesso à API GraphQL do GitHub.
        </div>
      )}

      {!loading && !noToken && weeks.length > 0 && (
        <div className="overflow-x-auto">
          {/* Month labels */}
          <div className="flex mb-1" style={{ marginLeft: 28 }}>
            <div className="relative flex" style={{ flex: 1 }}>
              {monthLabels.map(({ label, col }) => (
                <span
                  key={`${label}-${col}`}
                  className="absolute text-[10px]"
                  style={{ color: 'var(--muted)', left: col * 13 }}
                >
                  {label}
                </span>
              ))}
            </div>
          </div>
          <div style={{ height: 14 }} />

          <div className="flex gap-1">
            {/* Day labels */}
            <div className="flex flex-col gap-1 mr-1 flex-shrink-0" style={{ paddingTop: 1 }}>
              {DAYS.map((d, i) => (
                <div
                  key={i}
                  className="text-[9px] flex items-center"
                  style={{ height: 11, color: 'var(--muted)', width: 20 }}
                >
                  {d}
                </div>
              ))}
            </div>

            {/* Contribution cells */}
            {weeks.map((week, wi) => (
              <div key={wi} className="flex flex-col gap-1">
                {Array.from({ length: 7 }).map((_, di) => {
                  const day = week.days?.[di]
                  const count = day?.count ?? 0
                  return (
                    <div
                      key={di}
                      title={day ? `${day.date}: ${count} contribuição${count !== 1 ? 'ões' : ''}` : ''}
                      style={{
                        width: 11,
                        height: 11,
                        borderRadius: 2,
                        background: day ? getColor(count) : 'transparent',
                        border: day ? '1px solid rgba(255,255,255,0.04)' : 'none',
                      }}
                    />
                  )
                })}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
