"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { INK, SERIES, formatDayShort } from "./theme";
import type { TimeseriesPoint } from "@/types";

interface AtendimentosChartProps {
  pontos: TimeseriesPoint[];
}

/** Tooltip próprio: o padrão do Recharts pinta o texto com a cor da série. */
function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-lg border border-surface-border bg-white px-3 py-2 text-xs shadow-sm">
      <p className="font-medium text-gray-900">{formatDayShort(String(label))}</p>
      {payload.map((entry: any) => (
        <p key={entry.dataKey} className="mt-1 flex items-center gap-2 text-gray-600">
          <span
            aria-hidden="true"
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          {entry.name}
          <span className="ml-auto font-medium tabular-nums text-gray-900">
            {entry.value}
          </span>
        </p>
      ))}
    </div>
  );
}

/**
 * Duas séries ao longo do tempo — atendimentos e leads qualificados.
 *
 * Ambas contam a mesma coisa (leads), então dividem um eixo Y. Nunca um
 * segundo eixo: escalas diferentes no mesmo gráfico deixam a comparação
 * visual mentirosa.
 */
export function AtendimentosChart({ pontos }: AtendimentosChartProps) {
  const ink = INK.light;
  const [corAtendimentos, corQualificados] = SERIES.light;

  return (
    <figure className="rounded-xl border border-surface-border bg-white p-5">
      <figcaption className="mb-4">
        <h3 className="text-sm font-medium text-gray-900">Atendimentos por dia</h3>
        <p className="mt-0.5 text-xs text-gray-500">
          Conversas iniciadas e leads que chegaram a qualificado.
        </p>
      </figcaption>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={pontos} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
            <CartesianGrid stroke={ink.grid} vertical={false} />
            <XAxis
              dataKey="data"
              tickFormatter={formatDayShort}
              tick={{ fill: ink.secondary, fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: ink.grid }}
              minTickGap={16}
            />
            <YAxis
              allowDecimals={false}
              // Contagem começa em zero. Sem travar o domínio, o Recharts
              // pode estender o eixo para valores negativos e desenhar a
              // linha abaixo da base — sugerindo atendimentos negativos.
              domain={[0, "auto"]}
              tick={{ fill: ink.secondary, fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              width={48}
            />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: ink.grid }} />
            <Legend
              verticalAlign="top"
              align="left"
              height={28}
              iconType="plainline"
              wrapperStyle={{ fontSize: 12, color: ink.secondary }}
            />
            <Line
              type="monotone"
              dataKey="atendimentos"
              name="Atendimentos"
              stroke={corAtendimentos}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, stroke: ink.surface }}
            />
            <Line
              type="monotone"
              dataKey="leads_qualificados"
              name="Qualificados"
              stroke={corQualificados}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, stroke: ink.surface }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}

export default AtendimentosChart;
