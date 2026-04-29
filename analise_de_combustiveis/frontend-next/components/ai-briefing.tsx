"use client";

import { Bot, Sparkles, ShieldCheck, Workflow } from "lucide-react";

import { Card } from "@/components/ui/card";
import { InsightPayload } from "@/lib/types";

export function AIBriefing({
  insight,
  contextLabel,
}: {
  insight: InsightPayload | null;
  contextLabel: string;
}) {
  const source = insight?.source === "mistral" ? "Mistral ativo" : "Fallback analitico";

  return (
    <Card className="relative overflow-hidden border-accent/20 bg-[linear-gradient(135deg,rgba(54,214,167,0.11),rgba(107,184,255,0.09),rgba(255,255,255,0.03))]">
      <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-accent/10 blur-[80px]" />
      <div className="absolute bottom-0 left-0 h-48 w-48 rounded-full bg-amber/10 blur-[80px]" />
      <div className="grid gap-10 xl:grid-cols-[1.2fr_0.8fr] relative z-10">
        <div className="space-y-8">
          <div className="flex flex-wrap items-center gap-4">
            <span className="inline-flex items-center gap-2.5 rounded-full border border-accent/20 bg-accent/10 px-4 py-1.5 text-[10px] font-bold uppercase tracking-[0.2em] text-accent">
              <Bot className="h-3.5 w-3.5" />
              Intelligence Briefing
            </span>
            <span className="inline-flex items-center gap-2.5 rounded-full border border-white/5 bg-white/5 px-4 py-1.5 text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">
              <ShieldCheck className="h-3.5 w-3.5 text-mist/60" />
              {source}
            </span>
          </div>

          <div>
            <h3 className="font-display text-4xl leading-tight font-bold text-white">
              {insight?.title ?? "Analyzing live telemetry signals..."}
            </h3>
            <p className="mt-5 text-base leading-8 text-mist/90">
              {insight?.summary ??
                "A narrativa analitica entra aqui assim que o backend consolidar os sinais para o recorte selecionado."}
            </p>
          </div>

          <div className="grid gap-4">
            {(insight?.bullets ?? []).slice(0, 3).map((bullet) => (
              <div key={bullet} className="flex items-start gap-3 rounded-[1.6rem] border border-white/10 bg-black/15 p-5 shadow-sm group hover:border-accent/30 transition-all duration-300">
                <div className="mt-1 flex h-2 w-2 shrink-0 rounded-full bg-accent shadow-glow" />
                <p className="text-sm leading-relaxed text-mist font-medium group-hover:text-white transition-colors">{bullet}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="grid gap-4">
          <div className="rounded-[1.8rem] border border-white/10 bg-black/20 p-7 group hover:bg-white/[0.04] transition-all">
            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.3em] text-white/30 mb-4">
              <Sparkles className="h-4 w-4 text-amber/60" />
              Analytic Context
            </div>
            <p className="font-display text-3xl font-bold text-white mb-3">{contextLabel}</p>
            <p className="text-sm leading-7 text-mist/60">
              O briefing cruza snapshot executivo, historico recente e sinais de mercado para resumir o que realmente importa.
            </p>
          </div>
          <div className="rounded-[1.8rem] border border-white/10 bg-black/20 p-7 group hover:bg-white/[0.04] transition-all">
            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.3em] text-white/30 mb-4">
              <Workflow className="h-4 w-4 text-accent/60" />
              Optimization Logic
            </div>
            <ul className="space-y-3">
              {[ 
                "Prioriza anomalias de preco e vetores de volatilidade.",
                "Sintetiza tendencias sazonais e pressoes regionais.",
                "Processamento resiliente com fallback nativo."
              ].map((item, i) => (
                <li key={i} className="flex items-center gap-3 text-sm text-mist/80">
                  <div className="h-1 w-1 rounded-full bg-accent/40" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </Card>
  );
}
