"use client";

import React, { useEffect, useState } from "react";
import axios from "axios";
import { 
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, 
  AreaChart, Area, XAxis, YAxis, CartesianGrid
} from "recharts";
import { TrendingUp, TrendingDown, DollarSign, Briefcase, Activity, PlusCircle } from "lucide-react";

interface PortfolioPosition {
  asset: {
    id: number;
    ticker: str;
    name: str;
    asset_type: str;
    currency: str;
  };
  total_quantity: number;
  average_price: number;
  current_price: number;
  current_value: number;
  total_invested: number;
  profit_loss: number;
  profit_loss_percentage: number;
}

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8b5cf6", "#ec4899"];

export default function Home() {
  const [portfolio, setPortfolio] = useState<PortfolioPosition[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch data from FastAPI backend
    axios.get("http://localhost:8000/portfolio/")
      .then((res) => {
        setPortfolio(res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching portfolio:", err);
        setLoading(false);
      });
  }, []);

  // Mock data for the area chart (Evolution)
  const evolutionData = [
    { name: "Jan", value: 4000 },
    { name: "Feb", value: 3000 },
    { name: "Mar", value: 5000 },
    { name: "Apr", value: 4500 },
    { name: "May", value: 6000 },
    { name: "Jun", value: 7000 },
  ];

  const totalValue = portfolio.reduce((acc, pos) => acc + pos.current_value, 0);
  const totalInvested = portfolio.reduce((acc, pos) => acc + pos.total_invested, 0);
  const totalProfit = totalValue - totalInvested;
  const totalProfitPercentage = totalInvested > 0 ? (totalProfit / totalInvested) * 100 : 0;

  const pieData = portfolio.map((pos) => ({
    name: pos.asset.ticker,
    value: pos.current_value
  }));

  return (
    <div className="min-h-screen bg-neutral-950 text-white p-8 font-sans selection:bg-purple-500/30">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <header className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-extrabold bg-gradient-to-r from-purple-400 to-blue-500 bg-clip-text text-transparent">
              WealthMap Analytics
            </h1>
            <p className="text-neutral-400 mt-2 flex items-center gap-2">
              <Activity size={16} className="text-blue-400" />
              Real-time portfolio tracking & AI insights
            </p>
          </div>
          <button className="bg-white/10 hover:bg-white/20 transition px-4 py-2 rounded-xl flex items-center gap-2 font-medium backdrop-blur-md border border-white/5 shadow-xl">
            <PlusCircle size={18} />
            Add Transaction
          </button>
        </header>

        {/* Top Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-neutral-900/50 border border-neutral-800 p-6 rounded-2xl backdrop-blur-sm">
            <div className="flex items-center gap-3 text-neutral-400 mb-2">
              <DollarSign size={20} className="text-emerald-400" />
              <h3 className="font-semibold">Total Balance</h3>
            </div>
            <p className="text-4xl font-bold">R$ {totalValue.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</p>
          </div>

          <div className="bg-neutral-900/50 border border-neutral-800 p-6 rounded-2xl backdrop-blur-sm">
            <div className="flex items-center gap-3 text-neutral-400 mb-2">
              <Briefcase size={20} className="text-purple-400" />
              <h3 className="font-semibold">Total Invested</h3>
            </div>
            <p className="text-3xl font-bold">R$ {totalInvested.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</p>
          </div>

          <div className="bg-neutral-900/50 border border-neutral-800 p-6 rounded-2xl backdrop-blur-sm">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-neutral-400">Total Profit / Loss</h3>
              {totalProfit >= 0 ? <TrendingUp size={20} className="text-emerald-400" /> : <TrendingDown size={20} className="text-red-400" />}
            </div>
            <p className={`text-3xl font-bold ${totalProfit >= 0 ? "text-emerald-400" : "text-red-400"}`}>
              {totalProfit >= 0 ? "+" : ""}R$ {totalProfit.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
            </p>
            <p className={`text-sm mt-1 ${totalProfit >= 0 ? "text-emerald-400/80" : "text-red-400/80"}`}>
              {totalProfitPercentage >= 0 ? "+" : ""}{totalProfitPercentage.toFixed(2)}% All time
            </p>
          </div>
        </div>

        {/* Charts & Table Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Main Chart */}
          <div className="lg:col-span-2 bg-neutral-900/50 border border-neutral-800 p-6 rounded-2xl backdrop-blur-sm">
            <h3 className="text-xl font-bold mb-6">Portfolio Evolution</h3>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={evolutionData} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                  <XAxis dataKey="name" stroke="#666" tick={{fill: '#888'}} axisLine={false} tickLine={false} />
                  <YAxis stroke="#666" tick={{fill: '#888'}} axisLine={false} tickLine={false} tickFormatter={(value) => `R$${value}`} />
                  <RechartsTooltip 
                    contentStyle={{ backgroundColor: '#171717', borderColor: '#333', borderRadius: '8px' }}
                    itemStyle={{ color: '#fff' }}
                  />
                  <Area type="monotone" dataKey="value" stroke="#8b5cf6" strokeWidth={3} fillOpacity={1} fill="url(#colorValue)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Allocation Pie */}
          <div className="bg-neutral-900/50 border border-neutral-800 p-6 rounded-2xl backdrop-blur-sm">
            <h3 className="text-xl font-bold mb-6">Asset Allocation</h3>
            <div className="h-[250px] w-full relative">
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                      stroke="none"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <RechartsTooltip 
                      contentStyle={{ backgroundColor: '#171717', borderColor: '#333', borderRadius: '8px' }}
                      itemStyle={{ color: '#fff' }}
                      formatter={(value: number) => `R$ ${value.toFixed(2)}`}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-neutral-500">
                  No assets found
                </div>
              )}
              {/* Center text for Donut */}
              {pieData.length > 0 && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <span className="text-xl font-bold text-white">{pieData.length}</span>
                  <span className="text-xs text-neutral-400 absolute mt-6">Assets</span>
                </div>
              )}
            </div>
          </div>

        </div>

        {/* Positions Table */}
        <div className="bg-neutral-900/50 border border-neutral-800 rounded-2xl backdrop-blur-sm overflow-hidden">
          <div className="p-6 border-b border-neutral-800">
            <h3 className="text-xl font-bold">Your Positions</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-neutral-900/80 text-neutral-400 text-sm">
                  <th className="p-4 font-medium">Asset</th>
                  <th className="p-4 font-medium">Quantity</th>
                  <th className="p-4 font-medium">Avg Price</th>
                  <th className="p-4 font-medium">Current Price</th>
                  <th className="p-4 font-medium">Total Value</th>
                  <th className="p-4 font-medium">P&L</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800">
                {portfolio.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-neutral-500">
                      {loading ? "Loading portfolio..." : "No assets in your portfolio yet. Add a transaction."}
                    </td>
                  </tr>
                ) : (
                  portfolio.map((pos) => (
                    <tr key={pos.asset.id} className="hover:bg-neutral-800/30 transition">
                      <td className="p-4">
                        <div className="font-bold text-lg">{pos.asset.ticker}</div>
                        <div className="text-sm text-neutral-400">{pos.asset.name} • {pos.asset.asset_type}</div>
                      </td>
                      <td className="p-4 font-medium">{pos.total_quantity}</td>
                      <td className="p-4 text-neutral-300">R$ {pos.average_price.toFixed(2)}</td>
                      <td className="p-4 text-neutral-300">R$ {pos.current_price.toFixed(2)}</td>
                      <td className="p-4 font-bold">R$ {pos.current_value.toFixed(2)}</td>
                      <td className="p-4">
                        <div className={`font-bold flex items-center gap-1 ${pos.profit_loss >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                          {pos.profit_loss >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                          R$ {Math.abs(pos.profit_loss).toFixed(2)}
                        </div>
                        <div className={`text-xs ${pos.profit_loss >= 0 ? "text-emerald-400/80" : "text-red-400/80"}`}>
                          {pos.profit_loss_percentage > 0 ? "+" : ""}{pos.profit_loss_percentage.toFixed(2)}%
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}
