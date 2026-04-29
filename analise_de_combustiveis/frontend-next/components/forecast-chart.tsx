"use client";

import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card } from "@/components/ui/card";
import { ForecastPoint } from "@/lib/types";

function formatDateLabel(value: string) {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-xl border border-white/10 bg-panel/95 p-4 shadow-panel backdrop-blur-xl">
        <p className="mb-3 text-[10px] font-bold uppercase tracking-widest text-mist/60">{formatDateLabel(label)}</p>
        <div className="space-y-2">
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center justify-between gap-6">
              <span className="text-[10px] uppercase font-bold" style={{ color: entry.color }}>
                {entry.name}
              </span>
              <span className="font-display font-bold text-white">
                R$ {entry.value.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

export function ForecastChart({ data }: { data: ForecastPoint[] }) {
  const [mounted, setMounted] = useState(false);
  const grouped = data.reduce<Record<string, { week: string; realista?: number; otimista?: number; pessimista?: number }>>(
    (acc, item) => {
      if (!acc[item.week]) {
        acc[item.week] = { week: item.week };
      }
      if (item.scenario === "realista") {
        acc[item.week].realista = item.predicted;
      } else if (item.scenario === "agressivo") {
        acc[item.week].otimista = item.predicted;
      } else if (item.scenario === "conservador") {
        acc[item.week].pessimista = item.predicted;
      }
      return acc;
    },
    {},
  );
  const chartData = Object.values(grouped).sort((a, b) => a.week.localeCompare(b.week));
  const forecastStart = chartData[0]?.week;
  const forecastEnd = chartData[chartData.length - 1]?.week;

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <Card className="h-[440px] overflow-hidden bg-[linear-gradient(180deg,rgba(244,184,96,0.09),rgba(255,255,255,0.02))]">
      <div className="flex h-full flex-col justify-between">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase font-bold tracking-[0.4em] text-mist/50">Predictive Engine</p>
          <h3 className="mt-3 font-display text-4xl leading-tight">Scenario Modeler</h3>
          <p className="mt-3 text-sm text-mist">
            {forecastStart && forecastEnd
              ? `Projecao diaria de ${formatDateLabel(forecastStart)} ate ${formatDateLabel(forecastEnd)}`
              : "Projecao diaria para os proximos 15 dias"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full border border-accent/20 bg-accent/10 px-3 py-1 text-[10px] uppercase tracking-[0.22em] text-accent">Realista</span>
          <span className="rounded-full border border-amber/20 bg-amber/10 px-3 py-1 text-[10px] uppercase tracking-[0.22em] text-amber">Agressivo</span>
          <span className="rounded-full border border-coral/20 bg-coral/10 px-3 py-1 text-[10px] uppercase tracking-[0.22em] text-coral">Conservador</span>
        </div>
      </div>

      <div className="mt-10 h-[300px] w-full relative">
        {mounted && (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorRealista" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#36d6a7" stopOpacity={0.1}/>
                  <stop offset="95%" stopColor="#36d6a7" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(142,164,184,0.05)" vertical={false} />
              <XAxis
                dataKey="week"
                tickFormatter={formatDateLabel}
                tick={{ fill: "#8ea4b8", fontSize: 10, fontWeight: 500 }}
                axisLine={false}
                tickLine={false}
                minTickGap={24}
              />
              <YAxis 
                tick={{ fill: "#8ea4b8", fontSize: 10, fontWeight: 500 }} 
                axisLine={false} 
                tickLine={false} 
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                name="Realista"
                type="monotone"
                dataKey="realista"
                stroke="#36d6a7"
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#colorRealista)"
                dot={false}
                activeDot={{ r: 6, fill: "#36d6a7", stroke: "#0a131f", strokeWidth: 2 }}
              />
              <Area
                name="Otimista"
                type="monotone"
                dataKey="otimista"
                stroke="#f4b860"
                strokeWidth={2}
                strokeDasharray="5 5"
                fill="none"
                dot={false}
              />
              <Area
                name="Pessimista"
                type="monotone"
                dataKey="pessimista"
                stroke="#ff7b72"
                strokeWidth={2}
                strokeDasharray="5 5"
                fill="none"
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
      </div>
    </Card>
  );
}
