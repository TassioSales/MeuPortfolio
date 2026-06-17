"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { DailyStat } from "@/lib/api";

interface Props {
  data: DailyStat[];
}

export default function ClicksChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-6 text-center text-[#8b949e] text-sm">
        Nenhum clique registrado nos últimos 30 dias.
      </div>
    );
  }

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-6">
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
          <XAxis
            dataKey="date"
            tick={{ fill: "#8b949e", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#30363d" }}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: "#8b949e", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#161b22",
              border: "1px solid #30363d",
              borderRadius: "6px",
              color: "#c9d1d9",
              fontSize: 12,
            }}
            cursor={{ fill: "rgba(88, 166, 255, 0.08)" }}
          />
          <Bar dataKey="count" name="Cliques" fill="#58a6ff" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
