"use client";

import React, { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { analyticsService } from "@/services/api";
import { usePortfolio } from "@/context/PortfolioContext";
import { 
  Activity, Cpu, Newspaper, Search, Radar, TrendingUp, 
  ChevronRight, Calendar, BarChart3, AlertCircle 
} from "lucide-react";
import { 
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, 
  CartesianGrid, Tooltip as RechartsTooltip, Legend 
} from "recharts";

const ReactApexChart = dynamic(() => import("react-apexcharts"), { ssr: false });

const ForecastTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;

  return (
    <div className="chart-tooltip">
      <span className="chart-tooltip-label">{label}</span>
      {payload.map((item: any) => (
        <div key={item.dataKey} className="chart-tooltip-row">
          <span>{item.dataKey}</span>
          <strong>{Number(item.value || 0).toFixed(2)}</strong>
        </div>
      ))}
    </div>
  );
};

interface MarketRadarProps {
  initialTicker?: string | null;
}

const MarketRadar: React.FC<MarketRadarProps> = ({ initialTicker }) => {
  const { portfolio, showToast } = usePortfolio();
  const [ticker, setTicker] = useState(initialTicker || "");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  const [sentiment, setSentiment] = useState<any>(null);

  const fetchData = async (targetTicker: string) => {
    if (!targetTicker) return;
    setLoading(true);
    try {
      const [forecastRes, sentimentRes] = await Promise.all([
        analyticsService.getForecast(targetTicker),
        analyticsService.getSentiment(targetTicker)
      ]);
      setData(forecastRes.data);
      setSentiment(sentimentRes.data);
    } catch (error) {
      console.error("Error fetching radar data:", error);
      showToast("Erro ao carregar dados do radar", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialTicker) {
      setTicker(initialTicker);
      fetchData(initialTicker);
    }
  }, [initialTicker]);

  const apexOptions: any = {
    chart: { type: 'candlestick', background: 'transparent', toolbar: { show: false } },
    theme: { mode: 'dark' },
    plotOptions: { candlestick: { colors: { upward: '#10b981', downward: '#ef4444' } } },
    xaxis: { type: 'datetime', labels: { style: { colors: '#737373', fontSize: '10px' } } },
    yaxis: { tooltip: { enabled: true }, labels: { style: { colors: '#737373', fontSize: '10px' }, formatter: (v:number) => v.toFixed(2) } },
    grid: { borderColor: 'rgba(255,255,255,0.05)', strokeDashArray: 3 }
  };

  const candlestickSeries = data?.historical ? [{
    name: "Candlestick",
    data: data.historical.map((d: any) => ({
      x: new Date(d.date).getTime(),
      y: [d.open, d.high, d.low, d.close]
    }))
  }] : [];

  const forecastChartData = data ? [
    ...data.historical.slice(-30).map((d: any) => ({ date: d.date, Historical: d.close })),
    ...data.forecast.map((d: any) => ({ date: d.date, Forecast: d.value }))
  ] : [];
  const gaugeValue = Math.max(0, Math.min(100, Number(sentiment?.gauge_value ?? 50)));
  const gaugeTone = gaugeValue > 60 ? "positive" : gaugeValue < 40 ? "negative" : "neutral";
  const gaugeStep = Math.round(gaugeValue / 10);

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Search Bar */}
      <div className="glass p-4 rounded-2xl flex flex-col md:flex-row gap-4 items-center">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-500" size={18} />
          <input 
            type="text" 
            placeholder="Search asset (e.g. PETR4.SA, AAPL, BTC)..." 
            value={ticker} 
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && fetchData(ticker)}
            className="w-full bg-neutral-900/50 border border-white/5 rounded-xl pl-12 pr-4 py-3 focus:outline-none focus:border-purple-500/50 transition font-bold"
          />
        </div>
        <button 
          onClick={() => fetchData(ticker)}
          disabled={loading}
          className="w-full md:w-auto bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-black px-8 py-3 rounded-xl transition shadow-lg shadow-purple-500/20 flex items-center justify-center gap-2"
        >
          {loading ? <Cpu className="animate-spin" size={18} /> : <Radar size={18} />}
          ANALYZE
        </button>
      </div>

      {data ? (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 space-y-6">
            {/* Main Chart */}
            <div className="glass p-6 rounded-2xl">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-black flex items-center gap-2">
                  <Activity className="text-blue-500" /> Market Execution
                </h3>
                <div className="flex gap-2">
                  <span className="text-[10px] font-black px-2 py-1 bg-white/5 rounded border border-white/5 text-neutral-400">OHLC</span>
                  <span className="text-[10px] font-black px-2 py-1 bg-white/5 rounded border border-white/5 text-neutral-400">SMA 50/200</span>
                </div>
              </div>
              <div className="h-[400px] w-full">
                <ReactApexChart options={apexOptions} series={candlestickSeries} type="candlestick" height={400} />
              </div>
            </div>

            {/* Forecast Chart */}
            <div className="glass p-6 rounded-2xl">
              <h3 className="text-xl font-black mb-6 flex items-center gap-2">
                <Cpu className="text-purple-500" /> ML Predictive Forecast (15 Days)
              </h3>
              <div className="h-[250px] w-full">
                <ResponsiveContainer>
                  <LineChart data={forecastChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis dataKey="date" stroke="#404040" tick={{fontSize: 10}} tickLine={false} axisLine={false} />
                    <YAxis stroke="#404040" tick={{fontSize: 10}} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                    <RechartsTooltip content={<ForecastTooltip />} />
                    <Line type="monotone" dataKey="Historical" stroke="#8b5cf6" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="Forecast" stroke="#10b981" strokeWidth={3} strokeDasharray="5 5" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Sentiment Sidebar */}
          <div className="glass p-6 rounded-2xl flex flex-col h-full">
            <h3 className="text-xl font-black mb-8 flex items-center gap-2">
              <Newspaper className="text-orange-500" /> News Sentiment
            </h3>
            
            {sentiment && (
              <>
                <div className="flex flex-col items-center mb-10">
                  <div className="relative w-48 h-24 overflow-hidden mb-4">
                    <div className="w-48 h-48 rounded-full border-[12px] border-white/5 absolute top-0"></div>
                    <div 
                      className={`sentiment-gauge sentiment-gauge-${gaugeTone} sentiment-gauge-step-${gaugeStep}`}
                    ></div>
                  </div>
                  <div className="text-3xl font-black text-white">{sentiment.sentiment.split(' ')[0]}</div>
                  <div className="text-[10px] text-neutral-500 uppercase tracking-widest mt-2 font-black">Score: {sentiment.score_raw}</div>
                </div>

                <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
                  <p className="text-[10px] font-black text-neutral-500 uppercase tracking-[0.2em] mb-4">Recent Headlines</p>
                  {sentiment.headlines.map((news: any, idx: number) => (
                    <a key={idx} href={news.link} target="_blank" rel="noreferrer" className="block p-4 rounded-xl bg-white/[0.02] border border-white/5 hover:border-purple-500/30 transition group">
                      <p className="text-xs text-neutral-300 group-hover:text-white leading-relaxed line-clamp-2 mb-3">{news.title}</p>
                      <div className="flex justify-between items-center">
                        <span className={`text-[9px] font-black px-2 py-0.5 rounded uppercase tracking-wider ${
                          news.score > 0 ? 'bg-emerald-500/10 text-emerald-400' : 
                          news.score < 0 ? 'bg-red-500/10 text-red-400' : 'bg-neutral-800 text-neutral-500'
                        }`}>
                          {news.score > 0 ? 'Positive' : news.score < 0 ? 'Negative' : 'Neutral'}
                        </span>
                        <ChevronRight size={14} className="text-neutral-600 group-hover:text-purple-400 transition" />
                      </div>
                    </a>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="h-[500px] glass rounded-3xl flex flex-col items-center justify-center text-neutral-500">
          <Radar size={64} className="mb-6 opacity-20 animate-pulse" />
          <h3 className="text-2xl font-black text-white/50">Radar Standby</h3>
          <p className="text-sm mt-2 font-medium">Search for an asset to initiate institutional grade analysis.</p>
        </div>
      )}
    </div>
  );
};

export default MarketRadar;
