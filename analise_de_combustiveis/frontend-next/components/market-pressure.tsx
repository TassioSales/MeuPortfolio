"use client";

import { Activity, Factory, Truck } from "lucide-react";

import { Card } from "@/components/ui/card";
import { MarketSignal } from "@/lib/types";

function regimeClassName(regime: string) {
  if (regime === "balanced") return "text-accent";
  if (regime === "tight") return "text-amber";
  return "text-coral";
}

export function MarketPressure({ data }: { data: MarketSignal[] }) {
  const latest = data[data.length - 1];

  return (
    <Card className="space-y-5 overflow-hidden bg-[linear-gradient(180deg,rgba(244,184,96,0.08),rgba(255,255,255,0.02))]">
      <div>
        <p className="text-xs uppercase tracking-[0.35em] text-mist">Supply / Demand</p>
        <h3 className="mt-3 font-display text-3xl">Pressao de mercado</h3>
        <p className="mt-2 text-sm text-mist">
          Relacao entre demanda de vendas, processamento e oferta refinada para robustecer a leitura
          de precos.
        </p>
      </div>
      <div className="grid gap-3">
        <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-black/10 px-4 py-3">
          <span className="flex items-center gap-3 text-sm text-mist">
            <Truck className="h-4 w-4 text-accent" />
            Vendas
          </span>
          <strong>{latest ? `${Math.round(latest.sales_volume_m3).toLocaleString("pt-BR")} m3` : "--"}</strong>
        </div>
        <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-black/10 px-4 py-3">
          <span className="flex items-center gap-3 text-sm text-mist">
            <Factory className="h-4 w-4 text-amber" />
            Produzido
          </span>
          <strong>{latest ? `${Math.round(latest.produced_m3).toLocaleString("pt-BR")} m3` : "--"}</strong>
        </div>
        <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-black/10 px-4 py-3">
          <span className="flex items-center gap-3 text-sm text-mist">
            <Activity className="h-4 w-4 text-coral" />
            Regime
          </span>
          <strong className={regimeClassName(latest?.market_regime ?? "")}>{latest?.market_regime ?? "--"}</strong>
        </div>
      </div>
    </Card>
  );
}
