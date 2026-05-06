"use client";

import React from "react";
import { usePortfolio } from "@/context/PortfolioContext";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip } from "recharts";
import { PieChart as PieChartIcon } from "lucide-react";

const COLORS = ["#8b5cf6", "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#ec4899", "#06b6d4"];

const AllocationTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;

  const value = Number(payload[0].value || 0);

  return (
    <div className="chart-tooltip">
      <span className="chart-tooltip-label">{payload[0].name}</span>
      <strong>R$ {value.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</strong>
    </div>
  );
};

const AllocationChart = () => {
  const { portfolio } = usePortfolio();

  const data = portfolio.map((pos) => ({
    name: pos.asset.ticker,
    value: pos.current_value,
  })).sort((a, b) => b.value - a.value);
  const totalValue = portfolio.reduce((acc, pos) => acc + pos.current_value, 0);

  return (
    <div className="glass rounded-2xl p-6 flex flex-col h-full">
      <div className="mb-6">
        <h3 className="text-xl font-bold flex items-center gap-2">
          <PieChartIcon className="text-orange-400" size={20} /> Allocation map
        </h3>
        <p className="text-xs text-neutral-500 mt-1">Peso por posicao e concentracao da carteira.</p>
      </div>
      <div className="flex-1 min-h-[300px] w-full">
        {data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={100}
                stroke="none"
                paddingAngle={4}
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <RechartsTooltip content={<AllocationTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-neutral-500 opacity-30">
            <PieChartIcon size={64} />
          </div>
        )}
      </div>
      <div className="mt-4 space-y-2">
        {data.slice(0, 5).map((item, idx) => (
          <div key={idx} className="flex justify-between items-center text-[11px]">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full allocation-color-${idx % COLORS.length}`}></div>
              <span className="font-bold text-neutral-300">{item.name}</span>
            </div>
            <span className="text-neutral-500">
              {totalValue > 0 ? ((item.value / totalValue) * 100).toFixed(1) : "0.0"}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AllocationChart;
