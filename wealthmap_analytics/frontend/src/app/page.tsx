"use client";

import React, { useEffect, useState } from "react";
import axios from "axios";
import dynamic from "next/dynamic";
import { 
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, 
  CartesianGrid, LineChart, Line, XAxis, YAxis, Legend
} from "recharts";
import { 
  TrendingUp, TrendingDown, DollarSign, Briefcase, Activity, Search, 
  ShieldAlert, Cpu, Radar, Wallet, Plus, Trash2, Newspaper, CheckCircle2
} from "lucide-react";

const ReactApexChart = dynamic(() => import("react-apexcharts"), { ssr: false });

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8b5cf6", "#ec4899"];

export default function Home() {
  const [portfolio, setPortfolio] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"portfolio" | "radar" | "wallet">("portfolio");
  
  const [riskData, setRiskData] = useState<any>(null);
  const [globalSearch, setGlobalSearch] = useState("");
  const [selectedAsset, setSelectedAsset] = useState<string | null>(null);
  
  // Forecast & Candlestick Data
  const [forecastData, setForecastData] = useState<any[]>([]);
  const [candlestickData, setCandlestickData] = useState<any[]>([]);
  const [sma50Data, setSma50Data] = useState<any[]>([]);
  const [sma200Data, setSma200Data] = useState<any[]>([]);
  const [loadingForecast, setLoadingForecast] = useState(false);
  
  // Sentiment Data
  const [sentimentData, setSentimentData] = useState<any>(null);

  // Wallet Form State
  const [formTicker, setFormTicker] = useState("");
  const [formName, setFormName] = useState("");
  const [formType, setFormType] = useState("STOCK");
  const [formCurrency, setFormCurrency] = useState("BRL");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  
  const [txTicker, setTxTicker] = useState("");
  const [txType, setTxType] = useState("BUY");
  const [txQuantity, setTxQuantity] = useState("");
  const [txPrice, setTxPrice] = useState("");
  const [txDate, setTxDate] = useState(new Date().toISOString().split("T")[0]);

  const [toast, setToast] = useState<{msg: string, type: "success"|"error"} | null>(null);
  const [registeredAssets, setRegisteredAssets] = useState<any[]>([]);

  useEffect(() => {
    fetchPortfolio();
    fetchRiskData();
    fetchRegisteredAssets();
  }, []);

  // Debounced search for Add Asset
  useEffect(() => {
    if (formTicker.length > 1 && document.activeElement?.id === "assetSearchInput") {
      setIsSearching(true);
      const delay = setTimeout(() => {
        axios.get(`http://localhost:8000/search/?q=${formTicker}`)
          .then(res => setSearchResults(res.data))
          .catch(() => setSearchResults([]))
          .finally(() => setIsSearching(false));
      }, 500);
      return () => clearTimeout(delay);
    } else {
      setSearchResults([]);
    }
  }, [formTicker]);

  const showToast = (msg: string, type: "success"|"error") => {
    setToast({msg, type});
    setTimeout(() => setToast(null), 3000);
  }

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

  const fetchRegisteredAssets = () => {
    axios.get("http://localhost:8000/assets/")
      .then(res => setRegisteredAssets(res.data))
      .catch(err => console.error(err));
  };

  const fetchRiskData = () => {
    axios.get("http://localhost:8000/analytics/risk")
      .then((res) => setRiskData(res.data))
      .catch((err) => console.error("Error fetching risk analytics", err));
  };

  const handleGlobalForecast = (tickerToSearch?: string) => {
    let ticker = (tickerToSearch || globalSearch).trim().toUpperCase();
    if (!ticker) return;
    
    if (!ticker.includes('.') && ticker !== "BTC" && ticker !== "ETH") {
      if (/^[A-Z]{4}\d{1,2}$/.test(ticker)) ticker += ".SA";
    }
    
    setActiveTab("radar");
    setSelectedAsset(ticker);
    setLoadingForecast(true);
    setForecastData([]);
    setCandlestickData([]);
    setSentimentData(null);

    // Fetch Forecast & OHLC
    axios.get(`http://localhost:8000/forecast/${ticker}?days=15`)
      .then((res) => {
        const data = res.data;
        if (data.historical && data.historical.length > 0) {
          const ohlc = data.historical.map((d: any) => ({
            x: new Date(d.date).getTime(),
            y: [d.open, d.high, d.low, d.close]
          }));
          const sma50 = data.historical.map((d: any) => ({ x: new Date(d.date).getTime(), y: d.sma50 }));
          const sma200 = data.historical.map((d: any) => ({ x: new Date(d.date).getTime(), y: d.sma200 }));

          setCandlestickData(ohlc);
          setSma50Data(sma50);
          setSma200Data(sma200);

          const merged = [
            ...data.historical.map((d: any) => ({ date: d.date, Historical: d.close })),
            ...data.forecast.map((d: any) => ({ date: d.date, Forecast: d.value }))
          ];
          setForecastData(merged);
        }
        setLoadingForecast(false);
      })
      .catch((err) => {
        console.error("Forecast Error:", err);
        setLoadingForecast(false);
      });

    // Fetch Sentiment
    axios.get(`http://localhost:8000/sentiment/${ticker}`)
      .then((res) => setSentimentData(res.data))
      .catch((err) => console.error("Sentiment Error:", err));
  };

  const selectSearchResult = (asset: any) => {
    setFormTicker(asset.ticker);
    setFormName(asset.name);
    setFormType(asset.asset_type);
    // Currency heuristica (se acabar com .SA é BRL, cripto é USD, etc)
    setFormCurrency(asset.ticker.endsWith('.SA') ? "BRL" : "USD");
    setSearchResults([]);
  };

  const handleAddAsset = (e: React.FormEvent) => {
    e.preventDefault();
    axios.post("http://localhost:8000/assets/", {
      ticker: formTicker.toUpperCase(),
      name: formName,
      asset_type: formType,
      currency: formCurrency
    }).then(() => {
      showToast(`${formTicker} cadastrado com sucesso!`, "success");
      setFormTicker(""); setFormName("");
      fetchRegisteredAssets();
    }).catch((err) => showToast(err.response?.data?.detail || "Erro ao cadastrar", "error"));
  };

  const handleAddTransaction = (e: React.FormEvent) => {
    e.preventDefault();
    axios.post("http://localhost:8000/transactions/", {
      ticker: txTicker.toUpperCase(),
      transaction_type: txType,
      quantity: parseFloat(txQuantity),
      price: parseFloat(txPrice),
      date: txDate
    }).then(() => {
      showToast("Transação salva com sucesso!", "success");
      setTxQuantity(""); setTxPrice("");
      fetchPortfolio();
      fetchRiskData();
    }).catch((err) => showToast(err.response?.data?.detail || "Erro na transação", "error"));
  };

  const totalValue = portfolio.reduce((acc, pos) => acc + pos.current_value, 0);
  const totalInvested = portfolio.reduce((acc, pos) => acc + pos.total_invested, 0);
  const totalProfit = totalValue - totalInvested;

  const pieData = portfolio.map((pos) => ({
    name: pos.asset.ticker,
    value: pos.current_value
  }));

  const apexOptions: any = {
    chart: { type: 'candlestick', background: 'transparent', toolbar: { show: false } },
    theme: { mode: 'dark' },
    plotOptions: { candlestick: { colors: { upward: '#00C49F', downward: '#ef4444' } } },
    xaxis: { type: 'datetime', labels: { style: { colors: '#9ca3af' } } },
    yaxis: { tooltip: { enabled: true }, labels: { style: { colors: '#9ca3af' }, formatter: (v:number) => v.toFixed(2) } },
    grid: { borderColor: '#333', strokeDashArray: 3 }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-white font-sans selection:bg-purple-500/30">
      
      {/* Ticker Tape */}
      <div className="bg-neutral-900 border-b border-neutral-800 flex overflow-hidden h-8 items-center text-xs text-neutral-400 whitespace-nowrap">
        <div className="animate-[marquee_20s_linear_infinite] flex gap-8 px-4 font-mono">
          <span>IBOV: 130,400 <span className="text-emerald-400">▲ +0.5%</span></span>
          <span>S&P500: 5,100 <span className="text-emerald-400">▲ +1.2%</span></span>
          <span>BTC: $64,000 <span className="text-emerald-400">▲ +2.1%</span></span>
          <span>USD/BRL: R$ 5.05 <span className="text-neutral-400">- 0.0%</span></span>
          <span>AAPL: $172.00 <span className="text-emerald-400">▲ +0.8%</span></span>
          <span>PETR4: R$ 38.50 <span className="text-red-400">▼ -1.5%</span></span>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-4 md:p-8 space-y-8">
        {toast && (
          <div className={`fixed top-12 right-4 p-4 rounded-lg shadow-xl z-50 transition-all font-medium flex items-center gap-2 ${toast.type === 'success' ? 'bg-emerald-600' : 'bg-red-600'}`}>
            {toast.type === 'success' && <CheckCircle2 size={20} />} {toast.msg}
          </div>
        )}

        {/* Header */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-4xl font-extrabold bg-gradient-to-r from-purple-400 to-blue-500 bg-clip-text text-transparent flex items-center gap-3">
              WealthMap <span className="px-2 py-1 bg-gradient-to-r from-purple-600 to-blue-600 text-white text-sm rounded-lg uppercase tracking-wider shadow-lg shadow-purple-500/20">Enterprise</span>
            </h1>
            <p className="text-neutral-400 mt-2 flex items-center gap-2">
              <Activity size={16} className="text-blue-400" />
              Institutional Asset Tracking & ML Analytics
            </p>
          </div>
          
          <div className="flex bg-neutral-900 border border-neutral-800 rounded-lg p-1">
            <button onClick={() => setActiveTab("portfolio")} className={`px-4 py-2 rounded-md font-medium transition flex items-center gap-2 ${activeTab === "portfolio" ? "bg-purple-600 text-white shadow-lg" : "text-neutral-400 hover:text-white"}`}>
              <Briefcase size={16} /> Portfolio & Risk
            </button>
            <button onClick={() => setActiveTab("radar")} className={`px-4 py-2 rounded-md font-medium transition flex items-center gap-2 ${activeTab === "radar" ? "bg-purple-600 text-white shadow-lg" : "text-neutral-400 hover:text-white"}`}>
              <Radar size={16} /> Market Radar
            </button>
            <button onClick={() => setActiveTab("wallet")} className={`px-4 py-2 rounded-md font-medium transition flex items-center gap-2 ${activeTab === "wallet" ? "bg-emerald-600 text-white shadow-lg" : "text-neutral-400 hover:text-white"}`}>
              <Wallet size={16} /> Wallet Builder
            </button>
          </div>
        </header>

        {/* --- TAB 1: PORTFOLIO & RISK --- */}
        {activeTab === "portfolio" && (
          <div className="space-y-6 animate-in fade-in">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="bg-neutral-900/50 border border-neutral-800 p-6 rounded-2xl relative overflow-hidden group hover:border-purple-500/50 transition">
                <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition"></div>
                <div className="text-neutral-400 mb-2 font-medium">Total Balance</div>
                <p className="text-3xl font-black tracking-tight">R$ {totalValue.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</p>
              </div>
              <div className="bg-neutral-900/50 border border-neutral-800 p-6 rounded-2xl relative overflow-hidden group hover:border-emerald-500/50 transition">
                <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition"></div>
                <div className="text-neutral-400 mb-2 font-medium">Total Profit / Loss</div>
                <p className={`text-3xl font-black tracking-tight ${totalProfit >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {totalProfit >= 0 ? "+" : ""}R$ {totalProfit.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                </p>
              </div>
              <div className="bg-neutral-900/50 border border-neutral-800 p-6 rounded-2xl">
                <div className="text-neutral-400 mb-2 font-medium">Portfolio Sharpe</div>
                <p className="text-3xl font-black tracking-tight text-blue-400">{riskData?.portfolio_sharpe?.toFixed(2) || "0.0"}</p>
              </div>
              <div className="bg-neutral-900/50 border border-neutral-800 p-6 rounded-2xl">
                <div className="text-neutral-400 mb-2 font-medium">Annual Volatility</div>
                <p className="text-3xl font-black tracking-tight text-orange-400">{((riskData?.portfolio_volatility || 0) * 100).toFixed(1)}%</p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6">
                <h3 className="text-xl font-bold mb-4 flex items-center gap-2"><Briefcase size={20} className="text-purple-400" /> My Positions</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="text-neutral-400 border-b border-neutral-800 text-sm uppercase tracking-wider">
                        <th className="pb-3 font-medium">Asset</th>
                        <th className="pb-3 font-medium">Qty</th>
                        <th className="pb-3 font-medium">Avg Price</th>
                        <th className="pb-3 font-medium">Current Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-800/50">
                      {portfolio.map(pos => (
                        <tr key={pos.asset.id} className="hover:bg-neutral-800/50 cursor-pointer transition group" onClick={() => handleGlobalForecast(pos.asset.ticker)}>
                          <td className="py-4">
                            <div className="font-bold text-lg group-hover:text-purple-400 transition">{pos.asset.ticker}</div>
                            <div className="text-xs text-neutral-500">{pos.asset.name}</div>
                          </td>
                          <td className="py-4 font-medium">{pos.total_quantity}</td>
                          <td className="py-4 text-neutral-400">R$ {pos.average_price.toFixed(2)}</td>
                          <td className="py-4">
                            <div className="font-bold">R$ {pos.current_value.toFixed(2)}</div>
                            <div className={`text-xs ${pos.profit_loss >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                              {pos.profit_loss >= 0 ? '+' : ''}{pos.profit_loss_percentage.toFixed(2)}%
                            </div>
                          </td>
                        </tr>
                      ))}
                      {portfolio.length === 0 && (
                        <tr><td colSpan={4} className="py-8 text-center text-neutral-500">Nenhum ativo. Acesse o Wallet Builder para adicionar.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
              <div className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6">
                <h3 className="text-xl font-bold mb-4 flex items-center gap-2"><PieChart className="text-orange-400" size={20} /> Allocation</h3>
                <div className="h-[300px] w-full">
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie data={pieData} dataKey="value" cx="50%" cy="50%" innerRadius={70} outerRadius={90} stroke="none" paddingAngle={5}>
                        {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <RechartsTooltip contentStyle={{backgroundColor:'#171717', borderColor:'#333', borderRadius:'8px'}} formatter={(val:number)=>`R$ ${val.toFixed(2)}`} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* --- TAB 2: MARKET RADAR --- */}
        {activeTab === "radar" && (
          <div className="space-y-6 animate-in fade-in">
            <div className="flex flex-col md:flex-row gap-4 bg-neutral-900/50 p-4 rounded-xl border border-neutral-800">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" size={18} />
                <input 
                  type="text" placeholder="Pesquisa livre (Opcional)..." 
                  value={globalSearch} onChange={e => setGlobalSearch(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleGlobalForecast()}
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg pl-10 pr-4 py-3 focus:outline-none focus:border-purple-500 transition shadow-inner"
                />
              </div>
              
              <div className="flex-1 flex items-center gap-3 border-t md:border-t-0 md:border-l border-neutral-800 pt-4 md:pt-0 md:pl-4">
                <select 
                  onChange={(e) => {
                    if (e.target.value) handleGlobalForecast(e.target.value);
                  }}
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-3 font-bold focus:outline-none focus:border-purple-500 transition cursor-pointer text-purple-400"
                >
                  <option value="">Selecione um Ativo Rápido...</option>
                  <optgroup label="Meus Ativos (Carteira)">
                    {portfolio.map(p => <option key={p.asset.id} value={p.asset.ticker}>{p.asset.ticker} - {p.asset.name}</option>)}
                  </optgroup>
                  <optgroup label="Ações Brasileiras">
                    <option value="PETR4.SA">PETR4 (Petrobras)</option>
                    <option value="VALE3.SA">VALE3 (Vale)</option>
                    <option value="ITUB4.SA">ITUB4 (Itaú)</option>
                    <option value="WEGE3.SA">WEGE3 (WEG)</option>
                  </optgroup>
                  <optgroup label="FIIs & ETFs">
                    <option value="MXRF11.SA">MXRF11 (Maxi Renda)</option>
                    <option value="HGLG11.SA">HGLG11 (CSHG Logística)</option>
                    <option value="BOVA11.SA">BOVA11 (Ibovespa)</option>
                    <option value="IVVB11.SA">IVVB11 (S&P 500)</option>
                  </optgroup>
                  <optgroup label="Global & Cripto">
                    <option value="BTC">BTC (Bitcoin)</option>
                    <option value="ETH">ETH (Ethereum)</option>
                    <option value="AAPL">AAPL (Apple)</option>
                    <option value="MSFT">MSFT (Microsoft)</option>
                  </optgroup>
                </select>
              </div>

              <button onClick={() => handleGlobalForecast()} className="bg-purple-600 hover:bg-purple-700 px-8 py-3 rounded-lg font-bold transition shadow-lg shadow-purple-500/20">
                Analisar
              </button>
            </div>

            {selectedAsset ? (
              <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                <div className="xl:col-span-2 space-y-6">
                  {/* Candlestick */}
                  <div className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6 relative shadow-lg">
                    <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                      <Activity className="text-blue-500" /> {selectedAsset} - Preço Histórico e Médias Móveis
                    </h3>
                    <div className="h-[400px] w-full">
                      {candlestickData.length > 0 ? (
                        <ReactApexChart options={apexOptions} series={[
                            { name: "Candlestick", type: "candlestick", data: candlestickData },
                            { name: "SMA 50", type: "line", data: sma50Data, color: "#eab308" },
                            { name: "SMA 200", type: "line", data: sma200Data, color: "#8b5cf6" }
                          ]} type="candlestick" height={400} 
                        />
                      ) : (
                        <div className="h-full flex items-center justify-center text-neutral-500">
                          {loadingForecast ? <Cpu className="animate-spin text-purple-500" /> : "Gráfico indisponível"}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* ML Forecast */}
                  <div className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6 shadow-lg">
                    <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                      <Cpu className="text-purple-500" /> Projeção Machine Learning (15 Dias)
                    </h3>
                    <div className="h-[250px] w-full">
                      <ResponsiveContainer>
                        <LineChart data={forecastData} margin={{ top: 5, right: 0, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                          <XAxis dataKey="date" stroke="#666" tickLine={false} axisLine={false} minTickGap={30} />
                          <YAxis stroke="#666" tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                          <RechartsTooltip contentStyle={{ backgroundColor: '#171717', borderColor: '#333', borderRadius: '8px' }} />
                          <Legend />
                          <Line type="monotone" dataKey="Historical" stroke="#8b5cf6" strokeWidth={2} dot={false} />
                          <Line type="monotone" dataKey="Forecast" stroke="#00C49F" strokeWidth={3} strokeDasharray="5 5" dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>

                {/* Sentiment */}
                <div className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6 flex flex-col shadow-lg">
                  <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                    <Newspaper className="text-orange-500" /> News Sentiment Radar
                  </h3>
                  {!sentimentData ? (
                    <div className="flex-1 flex flex-col items-center justify-center text-neutral-500">
                      {loadingForecast ? <Cpu className="animate-spin text-purple-500 mb-2" /> : "Analisando RSS..."}
                      <p className="text-sm">Processando linguagem natural</p>
                    </div>
                  ) : (
                    <div className="flex-1 flex flex-col">
                      <div className="flex flex-col items-center mb-8">
                        <div className="relative w-48 h-24 overflow-hidden mb-2">
                          <div className="w-48 h-48 rounded-full border-[16px] border-neutral-800 absolute top-0"></div>
                          <div className="w-48 h-48 rounded-full border-[16px] absolute top-0 shadow-lg"
                            style={{ 
                              borderColor: sentimentData.gauge_value > 60 ? '#10b981 transparent transparent #10b981' : 
                                           sentimentData.gauge_value < 40 ? '#ef4444 transparent transparent #ef4444' : 
                                           '#f59e0b transparent transparent #f59e0b',
                              transform: `rotate(${ -135 + (sentimentData.gauge_value / 100) * 180 }deg)`,
                              transition: 'transform 1.5s cubic-bezier(0.4, 0, 0.2, 1)'
                            }}></div>
                        </div>
                        <div className="text-3xl font-black tracking-tight">{sentimentData.sentiment}</div>
                        <div className="text-sm text-neutral-400 mt-1">Score Léxico: {sentimentData.score_raw}</div>
                      </div>
                      <div className="flex-1 overflow-y-auto pr-2 space-y-3 custom-scrollbar">
                        <h4 className="text-sm font-bold text-neutral-500 uppercase tracking-wider mb-2">Notícias Analisadas</h4>
                        {sentimentData.headlines.length === 0 && <p className="text-sm text-neutral-500">Sem notícias.</p>}
                        {sentimentData.headlines.map((news: any, idx: number) => (
                          <a key={idx} href={news.link} target="_blank" rel="noreferrer" className="block p-3 rounded-lg bg-neutral-900 border border-neutral-800 hover:border-purple-500 transition group">
                            <p className="text-sm text-neutral-300 group-hover:text-white line-clamp-2 leading-relaxed">{news.title}</p>
                            <div className="mt-2">
                              <span className={`text-[10px] uppercase tracking-wider px-2 py-1 rounded font-bold ${news.score > 0 ? 'bg-emerald-500/10 text-emerald-400' : news.score < 0 ? 'bg-red-500/10 text-red-400' : 'bg-neutral-800 text-neutral-400'}`}>
                                {news.score > 0 ? 'Otimista' : news.score < 0 ? 'Pessimista' : 'Neutro'}
                              </span>
                            </div>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="h-[500px] flex flex-col items-center justify-center border-2 border-dashed border-neutral-800 rounded-2xl text-neutral-500">
                <Radar size={64} className="mb-4 opacity-30" />
                <h3 className="text-2xl font-bold mb-2">Market Radar Idle</h3>
                <p>Pesquise um ativo para ativar a Inteligência Artificial.</p>
              </div>
            )}
          </div>
        )}

        {/* --- TAB 3: WALLET BUILDER --- */}
        {activeTab === "wallet" && (
          <div className="space-y-8 animate-in fade-in">
            <div className="bg-emerald-900/10 border border-emerald-500/20 p-8 rounded-2xl flex items-center justify-between">
              <div>
                <h2 className="text-3xl font-extrabold text-emerald-400 flex items-center gap-3 mb-2">
                  <Wallet size={32} /> Wallet Builder
                </h2>
                <p className="text-emerald-400/80 text-lg">Pesquise, cadastre e gerencie suas posições para a análise de risco da IA.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Registration */}
              <div className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6 shadow-lg relative">
                <h3 className="text-xl font-bold mb-6 flex items-center gap-2 border-b border-neutral-800 pb-4">
                  <Plus className="text-emerald-500" /> 1. Pesquisar e Cadastrar Ativo
                </h3>
                <form onSubmit={handleAddAsset} className="space-y-5">
                  <div className="relative">
                    <label className="block text-sm text-neutral-400 mb-1 font-medium">Busca Inteligente (Nome ou Ticker)</label>
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" size={16} />
                      <input 
                        id="assetSearchInput"
                        required value={formTicker} onChange={e=>setFormTicker(e.target.value)} 
                        type="text" placeholder="Digite para buscar no Yahoo..."
                        className="w-full bg-neutral-950 border border-neutral-800 rounded-lg pl-9 pr-4 py-3 focus:border-emerald-500 focus:outline-none uppercase transition" 
                      />
                      {isSearching && <Cpu size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-emerald-500 animate-spin" />}
                    </div>
                    {/* Autocomplete Dropdown */}
                    {searchResults.length > 0 && (
                      <div className="absolute z-10 w-full mt-1 bg-neutral-900 border border-neutral-800 rounded-lg shadow-xl overflow-hidden">
                        {searchResults.map((res, i) => (
                          <div key={i} onClick={() => selectSearchResult(res)} className="px-4 py-3 hover:bg-neutral-800 cursor-pointer border-b border-neutral-800/50 last:border-0 flex justify-between items-center group">
                            <div>
                              <div className="font-bold text-white group-hover:text-emerald-400 transition">{res.ticker}</div>
                              <div className="text-xs text-neutral-400">{res.name}</div>
                            </div>
                            <span className="text-[10px] bg-neutral-800 px-2 py-1 rounded text-neutral-300">{res.asset_type}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm text-neutral-400 mb-1 font-medium">Nome do Ativo</label>
                    <input required value={formName} onChange={e=>setFormName(e.target.value)} type="text" className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-3 focus:border-emerald-500 focus:outline-none transition" />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-neutral-400 mb-1 font-medium">Tipo</label>
                      <select value={formType} onChange={e=>setFormType(e.target.value)} className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-3 focus:border-emerald-500 focus:outline-none">
                        <option value="STOCK">Ação / Stock</option>
                        <option value="FII">FII / REIT</option>
                        <option value="CRYPTO">Criptomoeda</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm text-neutral-400 mb-1 font-medium">Moeda</label>
                      <select value={formCurrency} onChange={e=>setFormCurrency(e.target.value)} className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-3 focus:border-emerald-500 focus:outline-none">
                        <option value="BRL">BRL (Real)</option>
                        <option value="USD">USD (Dólar)</option>
                      </select>
                    </div>
                  </div>
                  <button type="submit" className="w-full bg-neutral-800 hover:bg-emerald-600 text-white font-bold py-3.5 rounded-lg transition mt-2 shadow-lg hover:shadow-emerald-500/20">
                    Salvar na Base de Dados
                  </button>
                </form>
              </div>

              {/* Transactions */}
              <div className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6 shadow-lg">
                <h3 className="text-xl font-bold mb-6 flex items-center gap-2 border-b border-neutral-800 pb-4">
                  <DollarSign className="text-purple-500" /> 2. Registrar Transação
                </h3>
                <form onSubmit={handleAddTransaction} className="space-y-5">
                  <div>
                    <label className="block text-sm text-neutral-400 mb-1 font-medium">Ticker Cadastrado</label>
                    <select required value={txTicker} onChange={e=>setTxTicker(e.target.value)} className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-3 focus:border-purple-500 focus:outline-none">
                      <option value="">Selecione um ativo...</option>
                      {registeredAssets.map(a => <option key={a.id} value={a.ticker}>{a.ticker} - {a.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-neutral-400 mb-2 font-medium">Operação</label>
                    <div className="flex gap-4">
                      <label className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg border cursor-pointer transition ${txType === 'BUY' ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400 font-bold' : 'bg-neutral-950 border-neutral-800 text-neutral-500 hover:bg-neutral-800'}`}>
                        <input type="radio" className="hidden" name="type" value="BUY" checked={txType==="BUY"} onChange={()=>setTxType("BUY")} /> Compra
                      </label>
                      <label className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg border cursor-pointer transition ${txType === 'SELL' ? 'bg-red-500/20 border-red-500 text-red-400 font-bold' : 'bg-neutral-950 border-neutral-800 text-neutral-500 hover:bg-neutral-800'}`}>
                        <input type="radio" className="hidden" name="type" value="SELL" checked={txType==="SELL"} onChange={()=>setTxType("SELL")} /> Venda
                      </label>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-neutral-400 mb-1 font-medium">Quantidade</label>
                      <input required value={txQuantity} onChange={e=>setTxQuantity(e.target.value)} type="number" step="0.00001" className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-3 focus:border-purple-500 focus:outline-none" />
                    </div>
                    <div>
                      <label className="block text-sm text-neutral-400 mb-1 font-medium">Preço Unitário</label>
                      <input required value={txPrice} onChange={e=>setTxPrice(e.target.value)} type="number" step="0.01" className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-3 focus:border-purple-500 focus:outline-none" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm text-neutral-400 mb-1 font-medium">Data</label>
                    <input required value={txDate} onChange={e=>setTxDate(e.target.value)} type="date" className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-3 focus:border-purple-500 focus:outline-none" />
                  </div>
                  <button type="submit" className="w-full bg-purple-600 hover:bg-purple-700 text-white font-bold py-3.5 rounded-lg transition mt-2 shadow-lg hover:shadow-purple-500/20">
                    Executar Transação
                  </button>
                </form>
              </div>
            </div>

            {/* Registered Assets List */}
            <div className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6 mt-8">
              <h3 className="text-xl font-bold mb-4 flex items-center gap-2 border-b border-neutral-800 pb-4">
                <Briefcase className="text-blue-500" /> Ativos Guardados na Base de Dados (SQLite)
              </h3>
              <div className="flex flex-wrap gap-3">
                {registeredAssets.length === 0 && <span className="text-neutral-500 text-sm">Nenhum ativo guardado. Comece buscando acima!</span>}
                {registeredAssets.map(a => (
                  <div key={a.id} className="bg-neutral-950 border border-neutral-800 px-4 py-2 rounded-lg flex items-center gap-3">
                    <span className="font-bold text-white">{a.ticker}</span>
                    <span className="text-xs text-neutral-500">{a.name}</span>
                    <span className="text-[10px] bg-neutral-800 text-neutral-400 px-2 py-0.5 rounded">{a.asset_type}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
