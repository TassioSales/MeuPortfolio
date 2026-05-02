"use client";

import React, { useEffect, useState } from "react";
import axios from "axios";
import { 
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, LineChart, Line, Legend
} from "recharts";
import { TrendingUp, TrendingDown, DollarSign, Briefcase, Activity, Search, Filter, ShieldAlert, Cpu } from "lucide-react";

interface Asset {
  id: number;
  ticker: string;
  name: string;
  asset_type: string;
  currency: string;
}

interface PortfolioPosition {
  asset: Asset;
  total_quantity: number;
  average_price: number;
  current_price: number;
  current_value: number;
  total_invested: number;
  profit_loss: number;
  profit_loss_percentage: number;
}

interface RiskAnalytics {
  portfolio_volatility: number;
  portfolio_sharpe: number;
  asset_volatility: Record<string, number>;
  asset_sharpe: Record<string, number>;
  correlation: Record<string, Record<string, number>>;
}

interface ForecastData {
  historical: { date: string, value: number }[];
  forecast: { date: string, value: number }[];
}

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8b5cf6", "#ec4899"];

export default function Home() {
  const [portfolio, setPortfolio] = useState<PortfolioPosition[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"portfolio" | "risk">("portfolio");
  
  // Search & Filters
  const [localSearch, setLocalSearch] = useState("");
  const [globalSearch, setGlobalSearch] = useState("");
  const [filterType, setFilterType] = useState("ALL");
  
  // ML States
  const [riskData, setRiskData] = useState<RiskAnalytics | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<string | null>(null);
  const [forecastData, setForecastData] = useState<any[]>([]);
  const [loadingForecast, setLoadingForecast] = useState(false);
  const [forecastError, setForecastError] = useState<string | null>(null);

  useEffect(() => {
    fetchPortfolio();
    fetchRiskData();
  }, []);

  const fetchPortfolio = () => {
    axios.get("http://localhost:8000/portfolio/")
      .then((res) => {
        setPortfolio(res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching portfolio:", err);
        setLoading(false);
      });
  };

  const fetchRiskData = () => {
    axios.get("http://localhost:8000/analytics/risk")
      .then((res) => {
        setRiskData(res.data);
      })
      .catch((err) => console.error("Error fetching risk analytics", err));
  };

  const handleGlobalForecast = (tickerToSearch?: string) => {
    let ticker = (tickerToSearch || globalSearch).trim().toUpperCase();
    if (!ticker) return;
    
    // Heuristica basica: Se parece com codigo B3 e nao tem .SA, adicionamos automaticamente.
    if (!ticker.includes('.') && ticker !== "BTC" && ticker !== "ETH") {
      if (/^[A-Z]{4}\d{1,2}$/.test(ticker)) {
        ticker = ticker + ".SA";
      }
    }
    
    fetchForecast(ticker);
  };

  const fetchForecast = (ticker: string) => {
    setSelectedAsset(ticker);
    setLoadingForecast(true);
    setForecastError(null);
    axios.get(`http://localhost:8000/forecast/${ticker}?days=30`)
      .then((res) => {
        const data = res.data;
        if (!data.historical || data.historical.length === 0) {
          setForecastError("Ativo não encontrado ou sem dados históricos.");
          setLoadingForecast(false);
          return;
        }
        const merged = [
          ...data.historical.map((d: any) => ({ date: d.date, Historical: d.value })),
          ...data.forecast.map((d: any) => ({ date: d.date, Forecast: d.value }))
        ];
        setForecastData(merged);
        setLoadingForecast(false);
      })
      .catch((err) => {
        console.error("Error fetching forecast:", err);
        setForecastError("Falha ao comunicar com o servidor ML.");
        setLoadingForecast(false);
      });
  };

  const filteredPortfolio = portfolio.filter(p => {
    const matchesSearch = p.asset.ticker.toLowerCase().includes(localSearch.toLowerCase()) || 
                          p.asset.name.toLowerCase().includes(localSearch.toLowerCase());
    const matchesType = filterType === "ALL" || p.asset.asset_type === filterType;
    return matchesSearch && matchesType;
  });

  const totalValue = filteredPortfolio.reduce((acc, pos) => acc + pos.current_value, 0);
  const totalInvested = filteredPortfolio.reduce((acc, pos) => acc + pos.total_invested, 0);
  const totalProfit = totalValue - totalInvested;
  const totalProfitPercentage = totalInvested > 0 ? (totalProfit / totalInvested) * 100 : 0;

  const pieData = filteredPortfolio.map((pos) => ({
    name: pos.asset.ticker,
    value: pos.current_value
  }));

  return (
    <div className="min-h-screen bg-neutral-950 text-white p-4 md:p-8 font-sans selection:bg-purple-500/30">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-4xl font-extrabold bg-gradient-to-r from-purple-400 to-blue-500 bg-clip-text text-transparent flex items-center gap-3">
              WealthMap PRO <Cpu size={28} className="text-purple-500" />
            </h1>
            <p className="text-neutral-400 mt-2 flex items-center gap-2">
              <Activity size={16} className="text-blue-400" />
              AI-Powered Asset Tracking & Risk Analytics
            </p>
          </div>
          
          <div className="flex bg-neutral-900 border border-neutral-800 rounded-lg p-1">
            <button 
              onClick={() => setActiveTab("portfolio")}
              className={`px-6 py-2 rounded-md font-medium transition ${activeTab === "portfolio" ? "bg-purple-600 text-white shadow-lg" : "text-neutral-400 hover:text-white"}`}
            >
              Portfolio
            </button>
            <button 
              onClick={() => setActiveTab("risk")}
              className={`px-6 py-2 rounded-md font-medium transition flex items-center gap-2 ${activeTab === "risk" ? "bg-purple-600 text-white shadow-lg" : "text-neutral-400 hover:text-white"}`}
            >
              <ShieldAlert size={16} /> Risk Analysis
            </button>
          </div>
        </header>

        {activeTab === "portfolio" && (
          <div className="space-y-6 transform transition-all animate-in fade-in slide-in-from-bottom-4">
            {/* Top Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-neutral-900/50 border border-neutral-800 p-6 rounded-2xl backdrop-blur-sm">
                <div className="flex items-center gap-3 text-neutral-400 mb-2">
                  <DollarSign size={20} className="text-emerald-400" />
                  <h3 className="font-semibold">Filtered Balance</h3>
                </div>
                <p className="text-4xl font-bold">R$ {totalValue.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</p>
              </div>

              <div className="bg-neutral-900/50 border border-neutral-800 p-6 rounded-2xl backdrop-blur-sm">
                <div className="flex items-center gap-3 text-neutral-400 mb-2">
                  <Briefcase size={20} className="text-purple-400" />
                  <h3 className="font-semibold">Filtered Invested</h3>
                </div>
                <p className="text-3xl font-bold">R$ {totalInvested.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</p>
              </div>

              <div className="bg-neutral-900/50 border border-neutral-800 p-6 rounded-2xl backdrop-blur-sm">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-neutral-400">Profit / Loss</h3>
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

            {/* Controls Bar: ML Forecast Global Search */}
            <div className="flex flex-col lg:flex-row gap-4 bg-neutral-900/40 p-4 rounded-xl border border-neutral-800">
              
              {/* Type to search */}
              <div className="flex flex-1 gap-2">
                <div className="relative w-full">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" size={18} />
                  <input 
                    type="text" 
                    placeholder="Forecast qualquer ativo (ex: MXRF11, AAPL, BTC)..." 
                    value={globalSearch}
                    onChange={(e) => setGlobalSearch(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') handleGlobalForecast(); }}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition"
                  />
                </div>
                <button 
                  onClick={() => handleGlobalForecast()} 
                  className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
                >
                  Analisar
                </button>
              </div>

              {/* Or Select from Dropdown */}
              <div className="flex-1 flex items-center gap-3 border-t lg:border-t-0 lg:border-l border-neutral-800 pt-4 lg:pt-0 lg:pl-4">
                <span className="text-sm text-neutral-400 whitespace-nowrap">Ou selecione:</span>
                <select 
                  onChange={(e) => {
                    if (e.target.value) handleGlobalForecast(e.target.value);
                  }}
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-purple-500 transition cursor-pointer"
                >
                  <option value="">(Ativos Populares)</option>
                  <option value="MXRF11.SA">MXRF11 (Maxi Renda FII)</option>
                  <option value="PETR4.SA">PETR4 (Petrobras)</option>
                  <option value="VALE3.SA">VALE3 (Vale)</option>
                  <option value="BOVA11.SA">BOVA11 (Ibovespa ETF)</option>
                  <option value="BTC">BTC (Bitcoin)</option>
                  <option value="AAPL">AAPL (Apple - US)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Asset Details & Forecast */}
              <div className="lg:col-span-2 bg-neutral-900/50 border border-neutral-800 p-6 rounded-2xl backdrop-blur-sm relative overflow-hidden">
                <div className="absolute top-0 right-0 bg-purple-600/20 px-4 py-1 rounded-bl-xl border-l border-b border-purple-500/30 text-xs font-semibold text-purple-400 flex items-center gap-2">
                  <Cpu size={12} /> ML FORECAST ENGINE
                </div>
                
                <h3 className="text-xl font-bold mb-2">
                  {selectedAsset ? `${selectedAsset} AI Forecast` : "Nenhum ativo em análise"}
                </h3>
                
                {!selectedAsset ? (
                  <div className="h-[300px] flex flex-col items-center justify-center border-2 border-dashed border-neutral-800 rounded-xl text-neutral-500 p-6 text-center">
                    <Search size={32} className="mb-2 opacity-50" />
                    Pesquise por um ativo na barra acima ou clique na sua carteira abaixo para projetar o futuro com Inteligência Artificial.
                  </div>
                ) : loadingForecast ? (
                  <div className="h-[300px] flex flex-col items-center justify-center border-2 border-dashed border-neutral-800 rounded-xl text-neutral-400 animate-pulse">
                    <Cpu size={32} className="mb-4 animate-spin text-purple-500" /> 
                    <p className="font-medium">Treinando Modelo de Machine Learning...</p>
                    <p className="text-xs mt-2 opacity-70">Calculando regressão polinomial histórica de {selectedAsset}</p>
                  </div>
                ) : forecastError ? (
                  <div className="h-[300px] flex items-center justify-center border-2 border-dashed border-red-900/50 rounded-xl text-red-400">
                    <ShieldAlert size={24} className="mr-2" /> {forecastError}
                  </div>
                ) : (
                  <div className="h-[300px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={forecastData} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                        <XAxis dataKey="date" stroke="#666" tick={{fill: '#888'}} axisLine={false} tickLine={false} minTickGap={30} />
                        <YAxis stroke="#666" tick={{fill: '#888'}} axisLine={false} tickLine={false} domain={['auto', 'auto']} />
                        <RechartsTooltip 
                          contentStyle={{ backgroundColor: '#171717', borderColor: '#333', borderRadius: '8px' }}
                          itemStyle={{ color: '#fff' }}
                        />
                        <Legend />
                        <Line type="monotone" dataKey="Historical" stroke="#8b5cf6" strokeWidth={2} dot={false} />
                        <Line type="monotone" dataKey="Forecast" stroke="#00C49F" strokeWidth={2} strokeDasharray="5 5" dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
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
                </div>
              </div>
            </div>

            {/* Positions Table */}
            <div className="bg-neutral-900/50 border border-neutral-800 rounded-2xl backdrop-blur-sm overflow-hidden mt-6">
              <div className="p-4 border-b border-neutral-800 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-neutral-900/80">
                <h3 className="text-xl font-bold">Minha Carteira</h3>
                
                {/* Local Portfolio Filters */}
                <div className="flex items-center gap-3 w-full md:w-auto">
                  <div className="relative flex-1 md:w-64">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" size={16} />
                    <input 
                      type="text" 
                      placeholder="Filtrar carteira..." 
                      value={localSearch}
                      onChange={(e) => setLocalSearch(e.target.value)}
                      className="w-full bg-neutral-950 border border-neutral-800 rounded-lg pl-9 pr-4 py-1.5 text-sm focus:outline-none focus:border-purple-500 transition"
                    />
                  </div>
                  <select 
                    value={filterType}
                    onChange={(e) => setFilterType(e.target.value)}
                    className="bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-purple-500 transition cursor-pointer"
                  >
                    <option value="ALL">Todos os Tipos</option>
                    <option value="STOCK">Ações</option>
                    <option value="FII">FIIs</option>
                    <option value="CRYPTO">Cripto</option>
                  </select>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-neutral-900/80 text-neutral-400 text-sm border-b border-neutral-800">
                      <th className="p-4 font-medium">Asset</th>
                      <th className="p-4 font-medium">Quantity</th>
                      <th className="p-4 font-medium">Avg Price</th>
                      <th className="p-4 font-medium">Current Price</th>
                      <th className="p-4 font-medium">Total Value</th>
                      <th className="p-4 font-medium">P&L</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-800/50">
                    {filteredPortfolio.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="p-8 text-center text-neutral-500">
                          {loading ? "Loading portfolio..." : "No assets match your search/filters."}
                        </td>
                      </tr>
                    ) : (
                      filteredPortfolio.map((pos) => (
                        <tr 
                          key={pos.asset.id} 
                          onClick={() => fetchForecast(pos.asset.ticker)}
                          className={`hover:bg-neutral-800/50 transition cursor-pointer ${selectedAsset === pos.asset.ticker ? 'bg-purple-900/20 border-l-2 border-purple-500' : 'border-l-2 border-transparent'}`}
                        >
                          <td className="p-4">
                            <div className="font-bold text-lg flex items-center gap-2">
                              {pos.asset.ticker} 
                              {pos.asset.asset_type === "CRYPTO" && <span className="text-[10px] bg-orange-500/20 text-orange-400 px-2 py-0.5 rounded uppercase">Crypto</span>}
                            </div>
                            <div className="text-sm text-neutral-400">{pos.asset.name}</div>
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
        )}

        {activeTab === "risk" && (
          <div className="space-y-6 transform transition-all animate-in fade-in slide-in-from-bottom-4">
            {!riskData ? (
              <div className="p-12 text-center text-neutral-500 bg-neutral-900/50 rounded-2xl border border-neutral-800">
                <ShieldAlert size={48} className="mx-auto mb-4 text-neutral-600" />
                <p>Loading Risk Analytics...</p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Sharpe Ratio */}
                  <div className="bg-neutral-900/50 border border-neutral-800 p-6 rounded-2xl backdrop-blur-sm">
                    <h3 className="text-xl font-bold mb-2 flex items-center gap-2">
                      Sharpe Ratio <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded">Risk-Adjusted Return</span>
                    </h3>
                    <p className="text-neutral-400 text-sm mb-6">Compares your portfolio return to the risk-free rate.</p>
                    <div className="flex items-end gap-4">
                      <div className="text-5xl font-black text-blue-400">
                        {riskData.portfolio_sharpe.toFixed(2)}
                      </div>
                      <div className="pb-1 text-sm text-neutral-500">
                        {riskData.portfolio_sharpe > 1 ? "Excellent. The return justifies the risk taken." : "Poor. Too much risk for the given return."}
                      </div>
                    </div>
                  </div>

                  {/* Volatility */}
                  <div className="bg-neutral-900/50 border border-neutral-800 p-6 rounded-2xl backdrop-blur-sm">
                    <h3 className="text-xl font-bold mb-2 flex items-center gap-2">
                      Annualized Volatility <span className="text-xs bg-orange-500/20 text-orange-400 px-2 py-1 rounded">Price Fluctuation</span>
                    </h3>
                    <p className="text-neutral-400 text-sm mb-6">Measures the variance of your portfolio over a year.</p>
                    <div className="flex items-end gap-4">
                      <div className="text-5xl font-black text-orange-400">
                        {(riskData.portfolio_volatility * 100).toFixed(1)}%
                      </div>
                      <div className="pb-1 text-sm text-neutral-500">
                        {riskData.portfolio_volatility > 0.3 ? "High volatility (crypto/tech heavy)" : "Moderate/Low volatility"}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Correlation Matrix */}
                <div className="bg-neutral-900/50 border border-neutral-800 p-6 rounded-2xl backdrop-blur-sm">
                  <h3 className="text-xl font-bold mb-6">Asset Correlation Matrix</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-center border-collapse">
                      <thead>
                        <tr>
                          <th className="p-3 border border-neutral-800"></th>
                          {Object.keys(riskData.correlation).map(ticker => (
                            <th key={ticker} className="p-3 border border-neutral-800 text-sm font-medium text-neutral-400">{ticker}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {Object.keys(riskData.correlation).map(rowTicker => (
                          <tr key={rowTicker}>
                            <th className="p-3 border border-neutral-800 text-sm font-medium text-neutral-400 text-left">{rowTicker}</th>
                            {Object.values(riskData.correlation[rowTicker]).map((val, idx) => {
                              // Color gradient based on correlation value (-1 to 1)
                              const colorStr = val > 0.7 ? "bg-emerald-500/20 text-emerald-400" : 
                                               val < -0.3 ? "bg-red-500/20 text-red-400" : 
                                               "text-neutral-400";
                              return (
                                <td key={idx} className={`p-3 border border-neutral-800 text-sm font-bold ${colorStr}`}>
                                  {val.toFixed(2)}
                                </td>
                              )
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
