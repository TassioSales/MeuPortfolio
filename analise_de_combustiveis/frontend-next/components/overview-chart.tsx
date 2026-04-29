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
import { HistoryPoint } from "@/lib/types";

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-xl border border-accent/20 bg-panel/90 p-3 shadow-glow backdrop-blur-md">
        <p className="text-[10px] font-bold uppercase tracking-wider text-mist/60">{label}</p>
        <p className="mt-1 font-display text-lg font-bold text-accent">
          R$ {payload[0].value.toFixed(2)}
        </p>
      </div>
    );
  }
  return null;
};

export function OverviewChart({ data }: { data: HistoryPoint[] }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <Card className="h-[440px] overflow-hidden bg-[linear-gradient(180deg,rgba(107,184,255,0.08),rgba(255,255,255,0.02))]">
      <div className="flex h-full flex-col justify-between">
      <div className="flex items-start justify-between gap-4">
        <div>
        <p className="text-[10px] uppercase font-bold tracking-[0.4em] text-mist/50">Historical Radar</p>
        <h3 className="mt-3 font-display text-4xl leading-tight">Pulse of Price</h3>
        </div>
        <div className="rounded-full border border-sky/20 bg-sky/10 px-3 py-1 text-[10px] uppercase tracking-[0.24em] text-sky">Serie temporal</div>
      </div>
      
      <div className="mt-10 h-[300px] w-full relative">
        {mounted && (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#36d6a7" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#36d6a7" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(142,164,184,0.05)" vertical={false} />
              <XAxis dataKey="week" hide={true} />
              <YAxis 
                tick={{ fill: "#8ea4b8", fontSize: 10, fontWeight: 500 }} 
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="average_price"
                stroke="#36d6a7"
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#colorPrice)"
                dot={false}
                activeDot={{ r: 6, fill: "#36d6a7", stroke: "#0a131f", strokeWidth: 2 }}
                isAnimationActive={true}
                animationDuration={1500}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
      </div>
    </Card>
  );
}
