"use client";

import React, { useEffect, useState } from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { WS_URL } from "@/services/api";

interface TickerUpdate {
  symbol: string;
  price: number;
  change_pct: number;
}

const TickerTape = () => {
  const [mounted, setMounted] = useState(false);
  const [updates, setUpdates] = useState<TickerUpdate[]>([
    { symbol: "IBOV", price: 130400, change_pct: 0.5 },
    { symbol: "S&P500", price: 5100, change_pct: 1.2 },
    { symbol: "BTC/USD", price: 64000, change_pct: 2.1 },
    { symbol: "USD/BRL", price: 5.05, change_pct: 0.0 },
    { symbol: "PETR4", price: 38.50, change_pct: -1.5 },
    { symbol: "AAPL", price: 172.00, change_pct: 0.8 },
  ]);

  useEffect(() => {
    setMounted(true);
    const ws = new WebSocket(`${WS_URL}/ai/ws/ticker`);
    
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === "ticker_update") {
        setUpdates(message.data);
      }
    };

    return () => ws.close();
  }, []);

  return (
    <div className="bg-neutral-900/80 backdrop-blur-md border-b border-white/5 flex overflow-hidden h-10 items-center text-[11px] text-neutral-400 whitespace-nowrap z-50 sticky top-0">
      <div className="animate-marquee flex gap-12 px-6 font-mono items-center">
        {[...updates, ...updates].map((item, idx) => (
          <div key={idx} className="flex items-center gap-2 group cursor-default">
            <span className="text-neutral-500 font-bold group-hover:text-neutral-300 transition-colors">{item.symbol}</span>
            <span className="text-white font-medium">
              {item.symbol.includes("USD") || item.symbol.includes("BRL") || item.symbol === "AAPL" ? "$" : ""}
              {mounted ? item.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : item.price.toFixed(2)}
            </span>
            <span className={`flex items-center gap-0.5 font-bold ${item.change_pct > 0 ? "text-emerald-400" : item.change_pct < 0 ? "text-red-400" : "text-neutral-500"}`}>
              {item.change_pct > 0 ? <TrendingUp size={10} /> : item.change_pct < 0 ? <TrendingDown size={10} /> : <Minus size={10} />}
              {Math.abs(item.change_pct).toFixed(2)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TickerTape;
