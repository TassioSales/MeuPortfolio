'use client'
import type { RegionalData } from '@/lib/types'

// Mapa simplificado usando posições relativas dos estados
const STATE_POSITIONS: Record<string, { x: number; y: number; label: string }> = {
  AC: { x: 8, y: 52, label: 'AC' },
  AM: { x: 18, y: 38, label: 'AM' },
  RR: { x: 20, y: 15, label: 'RR' },
  PA: { x: 38, y: 30, label: 'PA' },
  AP: { x: 42, y: 14, label: 'AP' },
  TO: { x: 45, y: 48, label: 'TO' },
  RO: { x: 22, y: 55, label: 'RO' },
  MT: { x: 35, y: 62, label: 'MT' },
  MA: { x: 52, y: 32, label: 'MA' },
  PI: { x: 57, y: 44, label: 'PI' },
  CE: { x: 63, y: 34, label: 'CE' },
  RN: { x: 69, y: 32, label: 'RN' },
  PB: { x: 68, y: 38, label: 'PB' },
  PE: { x: 64, y: 44, label: 'PE' },
  AL: { x: 67, y: 50, label: 'AL' },
  SE: { x: 65, y: 55, label: 'SE' },
  BA: { x: 58, y: 58, label: 'BA' },
  GO: { x: 46, y: 65, label: 'GO' },
  DF: { x: 49, y: 63, label: 'DF' },
  MG: { x: 54, y: 72, label: 'MG' },
  ES: { x: 62, y: 74, label: 'ES' },
  RJ: { x: 57, y: 80, label: 'RJ' },
  SP: { x: 48, y: 80, label: 'SP' },
  PR: { x: 44, y: 87, label: 'PR' },
  SC: { x: 45, y: 92, label: 'SC' },
  RS: { x: 42, y: 97, label: 'RS' },
  MS: { x: 38, y: 78, label: 'MS' },
}

type Metric = 'pib_per_capita' | 'desemprego' | 'pib'

interface Props {
  data: RegionalData[]
  metric?: Metric
}

export default function RegionalMap({ data, metric = 'pib_per_capita' }: Props) {
  const values = data.map((d) => d[metric] as number)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const normalize = (v: number) => (v - min) / (max - min)

  const getColor = (v: number) => {
    const t = normalize(v)
    if (metric === 'desemprego') {
      // High unemployment = red
      const r = Math.round(60 + t * 195)
      const g = Math.round(180 - t * 150)
      return `rgb(${r},${g},60)`
    }
    // High value = green
    const r = Math.round(20 + (1 - t) * 200)
    const g = Math.round(80 + t * 125)
    return `rgb(${r},${g},80)`
  }

  const byUF: Record<string, RegionalData> = {}
  data.forEach((d) => {
    byUF[d.uf] = d
  })

  const metricLabel = {
    pib_per_capita: 'PIB per capita',
    desemprego: 'Desemprego',
    pib: 'PIB Total',
  }[metric]

  return (
    <div className="relative w-full" style={{ paddingBottom: '110%' }}>
      <svg viewBox="0 0 100 110" className="absolute inset-0 w-full h-full">
        {Object.entries(STATE_POSITIONS).map(([uf, pos]) => {
          const d = byUF[uf]
          if (!d) return null
          const val = d[metric] as number
          return (
            <g key={uf}>
              <circle
                cx={pos.x}
                cy={pos.y}
                r={3.5}
                fill={getColor(val)}
                stroke="#0a0e1a"
                strokeWidth={0.3}
                opacity={0.9}
              >
                <title>
                  {d.state_name}:{' '}
                  {metric === 'pib_per_capita'
                    ? `R$ ${val.toLocaleString('pt-BR')}`
                    : `${val}${metric === 'desemprego' ? '%' : 'bi'}`}
                </title>
              </circle>
              <text
                x={pos.x}
                y={pos.y + 6}
                textAnchor="middle"
                fontSize={2.5}
                fill="#9ca3af"
              >
                {pos.label}
              </text>
            </g>
          )
        })}
      </svg>
      <div className="absolute bottom-0 right-0 text-xs text-muted">{metricLabel}</div>
    </div>
  )
}
