'use client'

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

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
  const data = languages.map((l) => ({
    name: l.language,
    value: Math.round(l.percentage * 10) / 10,
  }))

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Language Distribution</h3>
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={90}
            paddingAngle={2}
            dataKey="value"
          >
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: '#21262d',
              border: '1px solid #30363d',
              borderRadius: '6px',
            }}
            itemStyle={{ color: '#e6edf3' }}
            formatter={(value: number) => [`${value}%`, '']}
          />
          <Legend
            formatter={(value) => (
              <span style={{ color: '#8b949e', fontSize: '12px' }}>{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
