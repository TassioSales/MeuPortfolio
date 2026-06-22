'use client'

interface Props {
  label: string
  value: string
  sub?: string
  trend?: 'up' | 'down' | 'neutral'
  unit?: string
}

export default function MetricCard({ label, value, sub, trend, unit }: Props) {
  const trendIcon = trend === 'up' ? '▲' : trend === 'down' ? '▼' : '●'
  const trendColor =
    trend === 'up' ? 'text-positive' : trend === 'down' ? 'text-negative' : 'text-muted'

  return (
    <div className="bg-panel border border-border rounded-xl p-5 flex flex-col gap-2">
      <span className="text-muted text-sm">{label}</span>
      <div className="flex items-end gap-2">
        <span className="text-3xl font-bold text-text">{value}</span>
        {unit && <span className="text-muted text-sm mb-1">{unit}</span>}
      </div>
      {sub && (
        <div className={`text-sm ${trendColor} flex items-center gap-1`}>
          <span>{trendIcon}</span>
          <span>{sub}</span>
        </div>
      )}
    </div>
  )
}
