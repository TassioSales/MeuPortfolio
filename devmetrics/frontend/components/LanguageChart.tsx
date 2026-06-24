'use client'

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

interface LanguageStat {
  language: string
  bytes: number
  percentage: number
}

interface LanguageChartProps {
  languages: LanguageStat[]
}

const COLORS = [
  '#388bfd', '#3fb950', '#e3b341', '#a371f7', '#f78166',
  '#39d353', '#ffa657', '#79c0ff', '#d2a8ff', '#ff7b72',
]

export default function LanguageChart({ languages }: LanguageChartProps) {
  const data = languages.slice(0, 8).map((l) => ({
    name: l.language,
    value: Math.round(l.percentage * 10) / 10,
  }))

  return (
    <div className="card card-accent p-6 animate-fade-in-3">
      <h3 className="text-[15px] font-semibold mb-5" style={{ color: 'var(--text)' }}>
        Distribuição de Linguagens
      </h3>

      <div className="flex items-center gap-6">
        <div className="flex-shrink-0" style={{ width: 140, height: 140 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={42}
                outerRadius={64}
                paddingAngle={2}
                dataKey="value"
                strokeWidth={0}
              >
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#21262d',
                  border: '1px solid #30363d',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
                itemStyle={{ color: '#e6edf3' }}
                formatter={(value: number) => [`${value}%`, '']}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="flex-1 space-y-2.5">
          {data.map((item, index) => (
            <div key={item.name} className="flex items-center gap-2.5">
              <div
                className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                style={{ background: COLORS[index % COLORS.length] }}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[12px] font-medium truncate" style={{ color: 'var(--text)' }}>
                    {item.name}
                  </span>
                  <span className="text-[11px] ml-2 flex-shrink-0" style={{ color: 'var(--muted)' }}>
                    {item.value}%
                  </span>
                </div>
                <div className="h-1 rounded-full" style={{ background: 'var(--surface2)' }}>
                  <div
                    className="h-1 rounded-full transition-all"
                    style={{
                      width: `${item.value}%`,
                      background: COLORS[index % COLORS.length],
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
