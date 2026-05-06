"use client";

import React from "react";
import { usePortfolio } from "@/context/PortfolioContext";
import { Activity, TrendingUp, TrendingDown, DollarSign, ShieldCheck, PieChart, WalletCards } from "lucide-react";

const DashboardStats = () => {
  const { portfolio, riskData } = usePortfolio();

  const totalValue = portfolio.reduce((acc, pos) => acc + pos.current_value, 0);
  const totalInvested = portfolio.reduce((acc, pos) => acc + pos.total_invested, 0);
  const totalProfit = totalValue - totalInvested;
  const profitPercentage = totalInvested > 0 ? (totalProfit / totalInvested) * 100 : 0;
  const topHolding = [...portfolio].sort((a, b) => b.current_value - a.current_value)[0];
  const topWeight = topHolding && totalValue > 0 ? (topHolding.current_value / totalValue) * 100 : 0;

  const stats = [
    {
      label: "Total Balance",
      value: `R$ ${totalValue.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`,
      icon: <DollarSign className="text-purple-400" size={20} />,
      sub: "Net Liquidation Value",
      trend: null
    },
    {
      label: "Total P/L",
      value: `R$ ${totalProfit.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`,
      icon: totalProfit >= 0 ? <TrendingUp className="text-emerald-400" size={20} /> : <TrendingDown className="text-red-400" size={20} />,
      sub: `${profitPercentage.toFixed(2)}% total return`,
      trend: totalProfit >= 0 ? "positive" : "negative"
    },
    {
      label: "Top Exposure",
      value: topHolding ? `${topHolding.asset.ticker} ${topWeight.toFixed(1)}%` : "N/A",
      icon: <PieChart className="text-cyan-300" size={20} />,
      sub: "Largest allocation weight",
      trend: topWeight > 35 ? "negative" : "positive"
    },
    {
      label: "Asset Classes",
      value: `${new Set(portfolio.map((pos) => pos.asset.asset_type || "OTHER")).size}`,
      icon: <WalletCards className="text-violet-300" size={20} />,
      sub: `${portfolio.length} live positions`,
      trend: portfolio.length >= 5 ? "positive" : null
    },
    {
      label: "Portfolio Sharpe",
      value: riskData?.portfolio_sharpe?.toFixed(2) || "0.00",
      icon: <ShieldCheck className="text-blue-400" size={20} />,
      sub: "Risk-adjusted performance",
      trend: riskData?.portfolio_sharpe > 1 ? "positive" : null
    },
    {
      label: "Annual Volatility",
      value: `${((riskData?.portfolio_volatility || 0) * 100).toFixed(1)}%`,
      icon: <Activity className="text-orange-400" size={20} />,
      sub: "Expected price variance",
      trend: riskData?.portfolio_volatility < 0.2 ? "positive" : "negative"
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-6 gap-4">
      {stats.map((stat, idx) => (
        <div key={idx} className="glass glass-hover p-5 rounded-2xl relative overflow-hidden group">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 bg-white/5 rounded-lg">
              {stat.icon}
            </div>
          </div>
          <div>
            <div className="text-neutral-400 text-sm font-medium mb-1">{stat.label}</div>
            <p className={`text-xl font-black tracking-tight ${
              stat.trend === "positive" ? "text-emerald-400" : 
              stat.trend === "negative" ? "text-red-400" : ""
            }`}>
              {stat.value}
            </p>
            <p className="text-[10px] text-neutral-500 mt-2 uppercase tracking-widest font-bold">
              {stat.sub}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
};

export default DashboardStats;
