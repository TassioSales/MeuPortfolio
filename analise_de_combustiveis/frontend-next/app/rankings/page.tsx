"use client";

import { useEffect, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, Flame, Snowflake, TrendingDown, TrendingUp } from "lucide-react";

import { Card } from "@/components/ui/card";
import { getRanking } from "@/lib/api";
import type { FuelName, RankingEntry } from "@/lib/types";
import { cn } from "@/lib/utils";

const FUELS: { value: FuelName; label: string }[] = [
  { value: "gasolina", label: "Gasolina" },
  { value: "etanol", label: "Etanol" },
  { value: "diesel", label: "Diesel" },
  { value: "glp", label: "GLP" },
  { value: "gnv", label: "GNV" },
];

function DeltaBadge({ pct }: { pct: number }) {
  const up = pct > 0.05;
  const down = pct < -0.05;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold font-mono tabular-nums",
        up
          ? "bg-rose/10 text-rose border border-rose/20"
          : down
            ? "bg-emerald/10 text-emerald border border-emerald/20"
            : "bg-white/[0.06] text-muted border border-line",
      )}
    >
      {up ? <TrendingUp className="h-3 w-3" /> : down ? <TrendingDown className="h-3 w-3" /> : null}
      {pct > 0 ? "+" : ""}{pct.toFixed(2)}%
    </span>
  );
}

function VolatilityBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  const color =
    pct > 66
      ? "bg-rose/70"
      : pct > 33
        ? "bg-amber/70"
        : "bg-emerald/70";
  return (
    <div className="flex items-center gap-2 min-w-[80px]">
      <div className="h-1.5 flex-1 rounded-full bg-white/[0.07]">
        <div className={cn("h-full rounded-full transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-muted font-mono w-8 text-right">{value.toFixed(3)}</span>
    </div>
  );
}

export default function RankingsPage() {
  const [fuel, setFuel] = useState<FuelName>("gasolina");
  const [order, setOrder] = useState<"desc" | "asc">("desc");
  const [entries, setEntries] = useState<RankingEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getRanking(fuel, order)
      .then(setEntries)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [fuel, order]);

  const maxVol = entries.reduce((m, e) => Math.max(m, e.volatility), 0);
  const minPrice = entries.reduce((m, e) => Math.min(m, e.price === 0 ? Infinity : e.price), Infinity);
  const maxPrice = entries.reduce((m, e) => Math.max(m, e.price), 0);
  const priceRange = maxPrice - minPrice;

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <section className="space-y-1">
        <h1 className="font-display text-3xl font-bold text-text lg:text-4xl">Rankings por Estado</h1>
        <p className="text-sm text-muted">
          Classificacao de todos os estados brasileiros por preco medio de combustivel, com variacao semanal e nivel de volatilidade.
        </p>
      </section>

      {/* Controls */}
      <div className="flex flex-wrap gap-3">
        <div className="flex gap-1.5 rounded-2xl border border-line bg-surface p-1.5">
          {FUELS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFuel(f.value)}
              className={cn(
                "rounded-xl px-4 py-2 text-[11px] font-bold uppercase tracking-[0.2em] transition-all",
                fuel === f.value
                  ? "bg-amber/15 text-amber border border-amber/30"
                  : "text-muted hover:text-text",
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="flex gap-1.5 rounded-2xl border border-line bg-surface p-1.5">
          <button
            onClick={() => setOrder("desc")}
            className={cn(
              "flex items-center gap-2 rounded-xl px-4 py-2 text-[11px] font-bold uppercase tracking-[0.2em] transition-all",
              order === "desc"
                ? "bg-rose/15 text-rose border border-rose/30"
                : "text-muted hover:text-text",
            )}
          >
            <Flame className="h-3.5 w-3.5" />
            Mais caros
          </button>
          <button
            onClick={() => setOrder("asc")}
            className={cn(
              "flex items-center gap-2 rounded-xl px-4 py-2 text-[11px] font-bold uppercase tracking-[0.2em] transition-all",
              order === "asc"
                ? "bg-emerald/15 text-emerald border border-emerald/30"
                : "text-muted hover:text-text",
            )}
          >
            <Snowflake className="h-3.5 w-3.5" />
            Mais baratos
          </button>
        </div>
      </div>

      {/* Summary pills */}
      {!loading && entries.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {[
            { label: "Estados rankeados", value: entries.length.toString(), color: "text-text" },
            {
              label: "Preco mais alto",
              value: `R$ ${maxPrice.toFixed(2)}`,
              color: "text-rose",
            },
            {
              label: "Preco mais baixo",
              value: `R$ ${minPrice.toFixed(2)}`,
              color: "text-emerald",
            },
            {
              label: "Spread max-min",
              value: `R$ ${priceRange.toFixed(2)}`,
              color: "text-blue",
            },
          ].map((pill) => (
            <div
              key={pill.label}
              className="rounded-2xl border border-line bg-surface px-5 py-3"
            >
              <p className="text-[9px] uppercase tracking-[0.3em] text-muted">{pill.label}</p>
              <p className={cn("mt-1 font-display text-xl font-bold font-mono", pill.color)}>{pill.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Table */}
      <Card className="overflow-hidden border-line bg-surface p-0">
        {/* Header */}
        <div className="grid grid-cols-[2.5rem_1fr_8rem_8rem_8rem_9rem] gap-4 border-b border-line px-6 py-4 text-[9px] font-bold uppercase tracking-[0.28em] text-muted">
          <span>#</span>
          <span>Estado</span>
          <button
            onClick={() => setOrder(order === "desc" ? "asc" : "desc")}
            className="flex items-center gap-1 hover:text-text transition-colors text-left"
          >
            Preco <ArrowUpDown className="h-3 w-3" />
          </button>
          <span>Var. Semana</span>
          <span>Tendencia</span>
          <span>Volatilidade</span>
        </div>

        {loading && (
          <div className="space-y-px">
            {Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="grid grid-cols-[2.5rem_1fr_8rem_8rem_8rem_9rem] gap-4 px-6 py-4 border-b border-line">
                <div className="h-5 w-6 animate-pulse rounded bg-surface2" />
                <div className="h-5 w-24 animate-pulse rounded bg-surface2" />
                <div className="h-5 w-20 animate-pulse rounded bg-surface2" />
                <div className="h-5 w-16 animate-pulse rounded bg-surface2" />
                <div className="h-5 w-16 animate-pulse rounded bg-surface2" />
                <div className="h-5 w-24 animate-pulse rounded bg-surface2" />
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="px-6 py-12 text-center text-sm text-muted">
            {error === "API offline" ? "Backend offline. Inicie via run.bat." : error}
          </div>
        )}

        {!loading && !error && entries.length === 0 && (
          <div className="px-6 py-12 text-center text-sm text-muted">
            Nenhum dado disponivel para {fuel}.
          </div>
        )}

        {!loading && !error && entries.length > 0 && (
          <div>
            {entries.map((entry, idx) => {
              const relativeBar = priceRange > 0 ? ((entry.price - minPrice) / priceRange) * 100 : 50;
              const isTop3 = idx < 3;
              const isBottom3 = idx >= entries.length - 3;
              return (
                <div
                  key={entry.state}
                  style={{ animationDelay: `${idx * 30}ms` }}
                  className={cn(
                    "row-in group grid grid-cols-[2.5rem_1fr_8rem_8rem_8rem_9rem] gap-4 items-center border-b border-line px-6 py-4 transition-colors hover:bg-surface2",
                    isTop3 && order === "desc" && "bg-rose/[0.03]",
                    isBottom3 && order === "asc" && "bg-emerald/[0.03]",
                  )}
                >
                  {/* Position */}
                  <span
                    className={cn(
                      "text-center font-display text-lg font-bold font-mono tabular-nums",
                      entry.position <= 3
                        ? order === "desc"
                          ? "text-rose/80"
                          : "text-emerald/80"
                        : "text-dim",
                    )}
                  >
                    {entry.position}
                  </span>

                  {/* State + price bar */}
                  <div>
                    <p className="font-semibold text-sm text-text">{entry.state.toUpperCase()}</p>
                    <div className="mt-1.5 h-1 w-full max-w-[8rem] rounded-full bg-white/[0.07]">
                      <div
                        className={cn("h-full rounded-full transition-all", order === "desc" ? "bg-rose/50" : "bg-emerald/50")}
                        style={{ width: `${relativeBar}%` }}
                      />
                    </div>
                  </div>

                  {/* Price */}
                  <span className="font-display text-lg font-bold font-mono text-text tabular-nums">
                    R$ {entry.price.toFixed(2)}
                  </span>

                  {/* Weekly change */}
                  <DeltaBadge pct={entry.change_week_pct} />

                  {/* Trend arrow */}
                  <span>
                    {entry.change_week_pct > 0.05 ? (
                      <ArrowUp className="h-4 w-4 text-rose" />
                    ) : entry.change_week_pct < -0.05 ? (
                      <ArrowDown className="h-4 w-4 text-emerald" />
                    ) : (
                      <span className="text-[10px] text-dim">—</span>
                    )}
                  </span>

                  {/* Volatility bar */}
                  <VolatilityBar value={entry.volatility} max={maxVol} />
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
