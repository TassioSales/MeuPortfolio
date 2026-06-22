'use client'
import {
  LineChart as ReLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface Props {
  data: { date: string; value: number }[]
  color?: string
  label?: string
}

export default function LineChart({ data, color = '#3b82f6', label = 'Valor' }: Props) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <ReLineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis
          dataKey="date"
          tick={{ fill: '#6b7280', fontSize: 11 }}
          tickLine={false}
          tickFormatter={(v: string) => v.slice(5)}
        />
        <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} tickLine={false} width={50} />
        <Tooltip
          contentStyle={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 8 }}
          labelStyle={{ color: '#9ca3af' }}
          itemStyle={{ color: color }}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          dot={false}
          name={label}
        />
      </ReLineChart>
    </ResponsiveContainer>
  )
}
