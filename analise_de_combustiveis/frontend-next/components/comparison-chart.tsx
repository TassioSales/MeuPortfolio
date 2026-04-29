"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card } from "@/components/ui/card";
import { ComparisonPoint } from "@/lib/types";

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload as ComparisonPoint;
    return (
      <div className="rounded-xl border border-white/10 bg-panel/95 p-4 shadow-panel backdrop-blur-xl">
        <p className="mb-3 text-[10px] font-bold uppercase tracking-widest text-mist/60">{label}</p>
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-6">
            <span className="text-[10px] uppercase font-bold text-accent">Gasolina</span>
            <span className="font-display font-bold text-white">R$ {data.primary_price.toFixed(2)}</span>
          </div>
          <div className="flex items-center justify-between gap-6">
            <span className="text-[10px] uppercase font-bold text-amber">Etanol</span>
            <span className="font-display font-bold text-white">R$ {data.compared_price.toFixed(2)}</span>
          </div>
          <div className="mt-3 border-t border-white/5 pt-2">
            <span className="text-[10px] uppercase font-bold text-mist/40">Vantagem</span>
            <p className="font-display text-lg font-bold text-accent">
               {data.advantage_percent > 0 ? `+${data.advantage_percent.toFixed(1)}%` : `${data.advantage_percent.toFixed(1)}%`}
            </p>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

export function ComparisonChart({ data }: { data: ComparisonPoint[] }) {
  const [mounted, setMounted] = useState(false);
  const chartData = data.slice(-12);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <Card className="h-[440px] overflow-hidden bg-[linear-gradient(180deg,rgba(139,125,255,0.09),rgba(255,255,255,0.02))]">
      <div className="flex h-full flex-col justify-between">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase font-bold tracking-[0.4em] text-mist/50">Market Parity</p>
          <h3 className="mt-3 font-display text-4xl leading-tight">Spread Analysis</h3>
        </div>
        <div className="rounded-full border border-iris/20 bg-iris/10 px-3 py-1 text-[10px] uppercase tracking-[0.24em] text-iris">Head to head</div>
      </div>

      <div className="mt-10 h-[300px] w-full relative">
        {mounted && (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(142,164,184,0.05)" vertical={false} />
              <XAxis dataKey="week" hide={true} />
              <YAxis 
                tick={{ fill: "#8ea4b8", fontSize: 10, fontWeight: 500 }} 
                axisLine={false} 
                tickLine={false} 
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
              <Bar
                dataKey="advantage_percent"
                radius={[4, 4, 0, 0]}
                animationDuration={1500}
              >
                {chartData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={entry.advantage_percent > 0 ? "#36d6a7" : "#ff7b72"} 
                    fillOpacity={0.8}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
      </div>
    </Card>
  );
}
