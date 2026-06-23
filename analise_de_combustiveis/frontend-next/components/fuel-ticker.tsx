"use client";

import { useEffect, useState } from "react";
import { TrendingDown, TrendingUp } from "lucide-react";

import { getStats } from "@/lib/api";
import type { FuelName, NationalStats } from "@/lib/types";
import { cn } from "@/lib/utils";

const ALL_FUELS: FuelName[] = ["gasolina", "etanol", "diesel", "glp", "gnv"];
const FUEL_LABELS: Record<FuelName, string> = {
  gasolina: "GASOLINA",
  etanol: "ETANOL",
  diesel: "DIESEL",
  glp: "GLP",
  gnv: "GNV",
};

interface TickerItem {
  fuel: FuelName;
  avg: number;
  changePct: number;
}

export function FuelTicker() {
  const [items, setItems] = useState<TickerItem[]>([]);

  useEffect(() => {
    Promise.allSettled(ALL_FUELS.map((fuel) => getStats(fuel))).then((results) => {
      const loaded: TickerItem[] = [];
      results.forEach((r, i) => {
        if (r.status === "fulfilled" && r.value) {
          const s: NationalStats = r.value;
          if (s.national_avg > 0) {
            loaded.push({ fuel: ALL_FUELS[i], avg: s.national_avg, changePct: s.change_week_pct });
          }
        }
      });
      if (loaded.length > 0) setItems(loaded);
    });
  }, []);

  if (items.length === 0) return null;

  // Duplicate items so the marquee loops seamlessly
  const repeated = [...items, ...items, ...items];

  return (
    <div className="relative overflow-hidden border-b border-line bg-surface/80 backdrop-blur">
      <div className="flex items-center gap-0">
        {/* LIVE badge */}
        <div className="shrink-0 border-r border-line bg-amber/10 px-4 py-2">
          <p className="text-[9px] font-bold uppercase tracking-[0.4em] text-amber">Live</p>
        </div>

        {/* Scrolling strip — pauses on hover */}
        <div className="ticker-wrap min-w-0 flex-1 overflow-hidden">
          <div
            className="flex items-center gap-0 will-change-transform"
            style={{ animation: "ticker-scroll 28s linear infinite" }}
          >
            {repeated.map((item, idx) => {
              const up = item.changePct > 0.05;
              const down = item.changePct < -0.05;
              return (
                <div
                  key={`${item.fuel}-${idx}`}
                  className="flex shrink-0 items-center gap-3 border-r border-line px-5 py-2"
                >
                  <span className="text-[10px] font-semibold uppercase tracking-[0.28em] text-muted">
                    {FUEL_LABELS[item.fuel]}
                  </span>
                  <span className="font-mono text-sm font-medium tabular-nums text-text">
                    R$ {item.avg.toFixed(2)}
                  </span>
                  <span
                    className={cn(
                      "flex items-center gap-0.5 text-[11px] font-semibold tabular-nums",
                      up ? "text-rose" : down ? "text-emerald" : "text-muted",
                    )}
                  >
                    {up ? <TrendingUp className="h-3 w-3" /> : down ? <TrendingDown className="h-3 w-3" /> : null}
                    {item.changePct > 0 ? "+" : ""}{item.changePct.toFixed(2)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes ticker-scroll {
          0%   { transform: translateX(0); }
          100% { transform: translateX(-33.333%); }
        }
      `}</style>
    </div>
  );
}
