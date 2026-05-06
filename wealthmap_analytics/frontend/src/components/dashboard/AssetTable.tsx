"use client";

import React from "react";
import { usePortfolio } from "@/context/PortfolioContext";
import { Briefcase, ArrowUpRight, ArrowDownRight, Radar } from "lucide-react";

interface AssetTableProps {
  onSelectAsset: (ticker: string) => void;
}

const AssetTable: React.FC<AssetTableProps> = ({ onSelectAsset }) => {
  const { portfolio, loading, riskData } = usePortfolio();
  const totalValue = portfolio.reduce((acc, pos) => acc + pos.current_value, 0);

  if (loading) {
    return (
      <div className="glass p-6 rounded-2xl h-[400px] flex items-center justify-center">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="w-12 h-12 bg-neutral-800 rounded-full"></div>
          <div className="h-4 w-32 bg-neutral-800 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="glass rounded-2xl overflow-hidden">
      <div className="p-6 border-b border-white/5 flex justify-between items-center">
        <div>
          <h3 className="text-xl font-bold flex items-center gap-2">
            <Briefcase size={20} className="text-purple-400" /> Holdings ledger
          </h3>
          <p className="text-xs text-neutral-500 mt-1">Clique em um ativo para abrir o radar de mercado.</p>
        </div>
        <span className="text-xs bg-purple-500/10 text-purple-400 px-3 py-1 rounded-full font-bold">
          {portfolio.length} Assets
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="text-neutral-500 border-b border-white/5 text-[10px] uppercase tracking-[0.2em] font-black">
              <th className="px-6 py-4">Asset</th>
              <th className="px-6 py-4">Quantity</th>
              <th className="px-6 py-4">Price / Avg</th>
              <th className="px-6 py-4">Weight</th>
              <th className="px-6 py-4">Market Value</th>
              <th className="px-6 py-4">P/L</th>
              <th className="px-6 py-4">Risk</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {portfolio.map((pos) => {
              const weight = totalValue > 0 ? (pos.current_value / totalValue) * 100 : 0;
              const assetVolatility = ((riskData?.asset_volatility?.[pos.asset.ticker] || 0) * 100);
              const riskTone = assetVolatility > 35 ? "High" : assetVolatility > 18 ? "Medium" : "Low";

              return (
              <tr
                key={pos.asset.id}
                className="hover:bg-white/[0.02] cursor-pointer transition group"
                onClick={() => onSelectAsset(pos.asset.ticker)}
              >
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-neutral-800 to-neutral-900 flex items-center justify-center font-bold text-sm border border-white/5 group-hover:border-purple-500/50 transition">
                      {pos.asset.ticker.slice(0, 2)}
                    </div>
                    <div>
                      <div className="font-black text-white group-hover:text-purple-400 transition">{pos.asset.ticker}</div>
                      <div className="text-[10px] text-neutral-500 uppercase tracking-tighter">{pos.asset.name}</div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 font-mono font-bold text-sm">
                  {pos.total_quantity.toLocaleString(undefined, { maximumFractionDigits: 4 })}
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm font-bold text-white">R$ {pos.current_price.toFixed(2)}</div>
                  <div className="text-[10px] text-neutral-500">Avg: R$ {pos.average_price.toFixed(2)}</div>
                </td>
                <td className="px-6 py-4">
                  <div className="allocation-track">
                    <span className={`allocation-fill allocation-width-${Math.min(10, Math.round(weight / 10))}`}></span>
                  </div>
                  <div className="text-[10px] text-neutral-500 mt-1 font-bold">{weight.toFixed(1)}%</div>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm font-black text-white">R$ {pos.current_value.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</div>
                </td>
                <td className="px-6 py-4">
                  <div className={`flex items-center gap-1 font-black text-sm ${pos.profit_loss >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                    {pos.profit_loss >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                    {pos.profit_loss_percentage.toFixed(2)}%
                  </div>
                  <div className={`text-[10px] font-bold ${pos.profit_loss >= 0 ? "text-emerald-500/60" : "text-red-500/60"}`}>
                    {pos.profit_loss >= 0 ? "+" : ""}R$ {Math.abs(pos.profit_loss).toFixed(2)}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onSelectAsset(pos.asset.ticker);
                    }}
                    className={`risk-chip ${riskTone === "High" ? "risk-chip-high" : riskTone === "Medium" ? "risk-chip-medium" : "risk-chip-low"}`}
                    title={`Open ${pos.asset.ticker} market radar`}
                    aria-label={`Open ${pos.asset.ticker} market radar`}
                  >
                    <Radar size={12} />
                    {riskTone}
                  </button>
                </td>
              </tr>
            )})}
            {portfolio.length === 0 && (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center">
                  <div className="flex flex-col items-center gap-2 opacity-30">
                    <Briefcase size={48} />
                    <p className="text-sm font-medium">Your portfolio is currently empty.</p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AssetTable;
