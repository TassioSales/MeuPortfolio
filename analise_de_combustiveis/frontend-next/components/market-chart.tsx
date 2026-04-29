"use client";

import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card } from "@/components/ui/card";
import { MarketSignal } from "@/lib/types";

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-xl border border-white/10 bg-panel/95 p-4 shadow-panel backdrop-blur-xl">
        <p className="mb-3 text-[10px] font-bold uppercase tracking-widest text-mist/60">{label}</p>
        <div className="space-y-2">
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center justify-between gap-6">
              <span className="text-[10px] uppercase font-bold" style={{ color: entry.color }}>
                {entry.name}
              </span>
              <span className="font-display font-bold text-white">
                {entry.value.toLocaleString()} m³
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

export function MarketChart({ data }: { data: MarketSignal[] }) {
  const [mounted, setMounted] = useState(false);
  const chartData = data.slice(-24).map((item) => ({
    ...item,
    month_label: item.month.slice(0, 7),
  }));

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <Card className="h-[440px] overflow-hidden bg-[linear-gradient(180deg,rgba(255,123,114,0.09),rgba(255,255,255,0.02))]">
      <div className="flex h-full flex-col justify-between">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase font-bold tracking-[0.4em] text-mist/50">Structural Balance</p>
          <h3 className="mt-3 font-display text-4xl leading-tight">Market Logistics</h3>
        </div>
        <div className="rounded-full border border-coral/20 bg-coral/10 px-3 py-1 text-[10px] uppercase tracking-[0.24em] text-coral">Fluxo fisico</div>
      </div>

      <div className="mt-10 h-[300px] w-full relative">
        {mounted && (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="salesFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#36d6a7" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#36d6a7" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(142,164,184,0.05)" vertical={false} />
              <XAxis dataKey="month_label" hide={true} />
              <YAxis 
                tick={{ fill: "#8ea4b8", fontSize: 10, fontWeight: 500 }} 
                axisLine={false} 
                tickLine={false} 
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                name="Vendas"
                type="monotone"
                dataKey="sales_volume_m3"
                stroke="#36d6a7"
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#salesFill)"
                dot={false}
                activeDot={{ r: 6, fill: "#36d6a7", stroke: "#0a131f", strokeWidth: 2 }}
              />
              <Area
                name="Produzido"
                type="monotone"
                dataKey="produced_m3"
                stroke="#f4b860"
                strokeWidth={2}
                fill="none"
                dot={false}
              />
              <Area
                name="Processado"
                type="monotone"
                dataKey="processed_m3"
                stroke="#ff7b72"
                strokeWidth={2}
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
