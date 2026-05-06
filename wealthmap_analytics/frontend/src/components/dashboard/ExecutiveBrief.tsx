"use client";

import React from "react";
import { usePortfolio } from "@/context/PortfolioContext";
import {
  AlertTriangle,
  ArrowUpRight,
  BadgeCheck,
  Gauge,
  Landmark,
  Layers3,
  ListChecks,
  Target,
} from "lucide-react";

const money = (value: number) =>
  `R$ ${value.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;

const pct = (value: number) => `${value.toFixed(1)}%`;

const ExecutiveBrief = () => {
  const { portfolio, riskData } = usePortfolio();

  const totalValue = portfolio.reduce((acc, pos) => acc + pos.current_value, 0);
  const totalInvested = portfolio.reduce((acc, pos) => acc + pos.total_invested, 0);
  const totalProfit = totalValue - totalInvested;
  const returnPct = totalInvested > 0 ? (totalProfit / totalInvested) * 100 : 0;
  const topHolding = [...portfolio].sort((a, b) => b.current_value - a.current_value)[0];
  const topWeight = topHolding && totalValue > 0 ? (topHolding.current_value / totalValue) * 100 : 0;
  const winner = [...portfolio].sort((a, b) => b.profit_loss_percentage - a.profit_loss_percentage)[0];
  const laggard = [...portfolio].sort((a, b) => a.profit_loss_percentage - b.profit_loss_percentage)[0];
  const volatility = (riskData?.portfolio_volatility || 0) * 100;
  const sharpe = riskData?.portfolio_sharpe || 0;
  const assetTypes = new Set(portfolio.map((pos) => pos.asset.asset_type || "OTHER"));
  const diversificationScore = Math.min(100, Math.round((portfolio.length * 11) + (assetTypes.size * 12) - Math.max(0, topWeight - 25)));
  const riskLabel = volatility > 35 ? "Elevado" : volatility > 18 ? "Moderado" : "Controlado";

  const actions = [
    {
      label: topWeight > 35 ? `Reduzir dependencia de ${topHolding?.asset.ticker}` : "Manter disciplina de rebalanceamento",
      detail: topWeight > 35 ? `${pct(topWeight)} do portfolio esta em uma unica posicao.` : "Nenhum ativo domina a carteira de forma critica.",
      tone: topWeight > 35 ? "warning" : "ok",
    },
    {
      label: sharpe < 0.5 ? "Revisar retorno ajustado ao risco" : "Risco remunerado acima do minimo",
      detail: `Sharpe atual em ${sharpe.toFixed(2)} com volatilidade anual de ${pct(volatility)}.`,
      tone: sharpe < 0.5 ? "warning" : "ok",
    },
    {
      label: portfolio.length < 5 ? "Ampliar universo de ativos" : "Carteira com base diversificada",
      detail: `${portfolio.length} ativos em ${assetTypes.size} classes cadastradas.`,
      tone: portfolio.length < 5 ? "warning" : "ok",
    },
  ];

  return (
    <section className="grid grid-cols-1 xl:grid-cols-[1.4fr_0.9fr] gap-6">
      <div className="glass rounded-2xl p-6 md:p-8">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.24em] text-neutral-500 mb-3">Executive brief</p>
            <h2 className="text-2xl md:text-3xl font-black tracking-tight text-white">Visao consolidada da carteira</h2>
            <p className="text-sm text-neutral-400 mt-3 max-w-2xl">
              Leitura inspirada em ferramentas como trackers de patrimonio, performance real e investment checkup:
              valor total, retorno, concentracao, risco e proximas acoes em uma unica tela.
            </p>
          </div>
          <div className={`professional-pill ${totalProfit >= 0 ? "professional-pill-positive" : "professional-pill-negative"}`}>
            <ArrowUpRight size={16} />
            {totalProfit >= 0 ? "+" : ""}{pct(returnPct)} total return
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-8">
          <article className="metric-tile">
            <Landmark size={18} className="text-violet-300" />
            <span>Patrimonio</span>
            <strong>{money(totalValue)}</strong>
          </article>
          <article className="metric-tile">
            <Target size={18} className="text-emerald-300" />
            <span>Resultado</span>
            <strong className={totalProfit >= 0 ? "text-emerald-300" : "text-red-300"}>{money(totalProfit)}</strong>
          </article>
          <article className="metric-tile">
            <Layers3 size={18} className="text-blue-300" />
            <span>Maior posicao</span>
            <strong>{topHolding ? `${topHolding.asset.ticker} ${pct(topWeight)}` : "N/A"}</strong>
          </article>
          <article className="metric-tile">
            <Gauge size={18} className="text-amber-300" />
            <span>Risco</span>
            <strong>{riskLabel}</strong>
          </article>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
          <div className="insight-strip">
            <span>Melhor contribuidor</span>
            <strong>{winner ? `${winner.asset.ticker} ${pct(winner.profit_loss_percentage)}` : "Sem dados"}</strong>
          </div>
          <div className="insight-strip">
            <span>Pior contribuidor</span>
            <strong>{laggard ? `${laggard.asset.ticker} ${pct(laggard.profit_loss_percentage)}` : "Sem dados"}</strong>
          </div>
          <div className="insight-strip">
            <span>Diversificacao</span>
            <strong>{diversificationScore}/100</strong>
          </div>
        </div>
      </div>

      <aside className="glass rounded-2xl p-6">
        <div className="flex items-center justify-between mb-5">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-neutral-500">Action list</p>
            <h3 className="text-xl font-black mt-1">Proximos movimentos</h3>
          </div>
          <ListChecks className="text-emerald-300" size={22} />
        </div>

        <div className="space-y-3">
          {actions.map((action) => (
            <article key={action.label} className="action-row">
              <div className={action.tone === "warning" ? "action-icon-warning" : "action-icon-ok"}>
                {action.tone === "warning" ? <AlertTriangle size={15} /> : <BadgeCheck size={15} />}
              </div>
              <div>
                <strong>{action.label}</strong>
                <p>{action.detail}</p>
              </div>
            </article>
          ))}
        </div>
      </aside>
    </section>
  );
};

export default ExecutiveBrief;
