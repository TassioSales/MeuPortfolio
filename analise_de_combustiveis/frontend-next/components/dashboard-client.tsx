"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  Bot,
  ChevronRight,
  Compass,
  DatabaseZap,
  Fuel,
  Radar,
  Scale,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

import { AIBriefing } from "@/components/ai-briefing";
import { ComparisonChart } from "@/components/comparison-chart";
import { Filters } from "@/components/filters";
import { ForecastChart } from "@/components/forecast-chart";
import { MarketChart } from "@/components/market-chart";
import { MarketPressure } from "@/components/market-pressure";
import { OverviewChart } from "@/components/overview-chart";
import { PageHero } from "@/components/page-hero";
import { PriceMap } from "@/components/price-map";
import { StatCard } from "@/components/stat-card";
import { Card } from "@/components/ui/card";
import {
  getCities,
  getComparison,
  getForecast,
  getFuels,
  getHistory,
  getInsights,
  getMap,
  getMarket,
  getOverview,
  getStats,
} from "@/lib/api";
import type {
  ComparisonPoint,
  ForecastPoint,
  FuelName,
  FuelSummary,
  HistoryPoint,
  InsightPayload,
  MarketSignal,
  NationalStats,
} from "@/lib/types";
import { useDashboardStore, useSettingsStore } from "@/lib/store";

const FALLBACK_FUELS: FuelName[] = ["gasolina", "etanol", "diesel", "glp", "gnv"];

type PageMode = "dashboard" | "historico" | "previsoes" | "comparacoes" | "combustivel";

function formatCurrency(value?: number) {
  return value === undefined ? "--" : `R$ ${value.toFixed(2)}`;
}

function formatPercent(value?: number) {
  return value === undefined ? "--" : `${value.toFixed(2)}%`;
}

function trendFromDelta(delta: number) {
  if (delta > 0.01) return "up" as const;
  if (delta < -0.01) return "down" as const;
  return "flat" as const;
}

function InfoPanel({
  kicker,
  title,
  children,
  className = "",
}: {
  kicker: string;
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Card className={className}>
      <p className="text-[10px] uppercase tracking-widest text-muted">{kicker}</p>
      <h3 className="mt-2 font-display text-xl font-bold text-text">{title}</h3>
      <div className="mt-4">{children}</div>
    </Card>
  );
}

function MetricStrip({
  items,
}: {
  items: Array<{ label: string; value: string; tone?: "teal" | "amber" | "coral" }>;
}) {
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {items.map((item) => (
        <div
          key={item.label}
          className="rounded-xl border border-line bg-surface2 p-4"
        >
          <p className="text-[10px] uppercase tracking-widest text-muted">{item.label}</p>
          <p className="mt-2 font-mono text-xl font-bold text-text">{item.value}</p>
        </div>
      ))}
    </div>
  );
}

function RankedList({
  title,
  subtitle,
  items,
  formatter,
}: {
  title: string;
  subtitle: string;
  items: Array<{ label: string; value: number }>;
  formatter: (value: number) => string;
}) {
  return (
    <InfoPanel kicker={subtitle} title={title}>
      <div className="space-y-3">
        {items.length === 0 ? (
          <div className="rounded-xl border border-line bg-surface2 px-4 py-3 text-sm text-muted">
            Sem dados suficientes para montar o ranking.
          </div>
        ) : (
          items.map((item, index) => (
            <div
              key={`${item.label}-${index}`}
              className="flex items-center justify-between rounded-xl border border-line bg-surface2 px-4 py-3 transition-colors hover:bg-surface"
            >
              <div>
                <p className="text-sm text-text">{item.label}</p>
                <p className="text-xs text-muted">#{index + 1}</p>
              </div>
              <p className="font-mono text-lg font-bold text-amber">{formatter(item.value)}</p>
            </div>
          ))
        )}
      </div>
    </InfoPanel>
  );
}

function FuelSwitchboard({
  fuels,
  activeFuel,
}: {
  fuels: FuelName[];
  activeFuel: FuelName;
}) {
  const fuelMeta: Record<FuelName, { gradient: string; accent: string; label: string }> = {
    gasolina: { gradient: "from-amber/15 to-amber/[0.03] border-amber/25",  accent: "text-amber",   label: "Gasolina" },
    etanol:   { gradient: "from-emerald/15 to-emerald/[0.03] border-emerald/25", accent: "text-emerald", label: "Etanol" },
    diesel:   { gradient: "from-blue/15 to-blue/[0.03] border-blue/25",     accent: "text-blue",    label: "Diesel" },
    glp:      { gradient: "from-rose/15 to-rose/[0.03] border-rose/25",     accent: "text-rose",    label: "GLP" },
    gnv:      { gradient: "from-purple/15 to-purple/[0.03] border-purple/25", accent: "text-purple", label: "GNV" },
  };

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5">
      {fuels.map((item) => {
        const meta = fuelMeta[item] ?? { gradient: "from-surface2 to-surface border-line", accent: "text-muted", label: item };
        return (
        <Link
          key={item}
          href={`/combustivel/${item}`}
          className={`group flex min-h-[160px] flex-col justify-between rounded-2xl border bg-gradient-to-br p-5 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card ${meta.gradient}`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[9px] uppercase tracking-widest text-muted">Análise</span>
            <Fuel className={`h-4 w-4 transition-colors ${item === activeFuel ? meta.accent : "text-muted"}`} />
          </div>
          <div>
            <p className={`font-display text-2xl font-bold leading-none ${meta.accent}`}>{meta.label}</p>
            <div className="mt-3 inline-flex items-center gap-1.5 text-xs text-muted group-hover:text-text">
              {item === activeFuel ? "Tela atual" : "Abrir análise"}
              <ChevronRight className="h-3 w-3" />
            </div>
          </div>
        </Link>
        );
      })}
    </div>
  );
}

export function DashboardClient({
  pageMode = "dashboard",
  initialFuel,
}: {
  pageMode?: PageMode;
  initialFuel?: FuelName;
}) {
  const { fuel, state, city, compareWith, startDate, endDate, setFuel } = useDashboardStore();
  const { mistralKey } = useSettingsStore();
  const [overview, setOverview] = useState<FuelSummary[]>([]);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [forecast, setForecast] = useState<ForecastPoint[]>([]);
  const [comparison, setComparison] = useState<ComparisonPoint[]>([]);
  const [mapData, setMapData] = useState<FuelSummary[]>([]);
  const [market, setMarket] = useState<MarketSignal[]>([]);
  const [insight, setInsight] = useState<InsightPayload | null>(null);
  const [availableFuels, setAvailableFuels] = useState<FuelName[]>([]);
  const [availableCities, setAvailableCities] = useState<string[]>([]);
  const [nationalStats, setNationalStats] = useState<NationalStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const pageConfig = {
    dashboard: {
      kicker: "Command Layer",
      title: "Visao geral do mercado",
      description: "Resumo executivo com preco, mapa, logistica e sinais recentes do recorte selecionado.",
      tone: "teal" as const,
      badge: "Visao de comando",
      heroStats: [
        { label: "Filtro", value: `${fuel.toUpperCase()} / ${state}`, icon: "radar" as const },
        { label: "Leitura", value: "Panorama + alerta", icon: "brain" as const },
        { label: "Frequencia", value: "Semanal + mensal", icon: "waypoints" as const },
      ],
    },
    historico: {
      kicker: "History Desk",
      title: "Historico de precos",
      description: "Serie temporal, extremos, cadencia semanal e cobertura territorial do periodo escolhido.",
      tone: "blue" as const,
      badge: "Serie temporal",
      heroStats: [
        { label: "Recorte", value: city || state, icon: "waypoints" as const },
        { label: "Pergunta", value: "De onde veio o preco", icon: "brain" as const },
        { label: "Base", value: "Historico semanal", icon: "radar" as const },
      ],
    },
    previsoes: {
      kicker: "Scenario Board",
      title: "Cenarios e previsoes",
      description: "Faixas projetadas, regime de mercado e sinais que sustentam os cenarios atuais.",
      tone: "amber" as const,
      badge: "Forecast studio",
      heroStats: [
        { label: "Horizonte", value: "3 cenarios", icon: "sparkles" as const },
        { label: "Lente", value: "Risco e faixa", icon: "brain" as const },
        { label: "Suporte", value: "Mercado fisico", icon: "radar" as const },
      ],
    },
    comparacoes: {
      kicker: "Decision Room",
      title: "Comparacao entre combustiveis",
      description: "Spread, vencedor recente e desempenho relativo entre os produtos selecionados.",
      tone: "coral" as const,
      badge: "Head to head",
      heroStats: [
        { label: "Duelo", value: `${fuel} vs ${compareWith}`, icon: "sparkles" as const },
        { label: "Foco", value: "Spread e recomendacao", icon: "brain" as const },
        { label: "Base", value: "Serie comparativa", icon: "radar" as const },
      ],
    },
    combustivel: {
      kicker: "Fuel Dossier",
      title: `Painel dedicado de ${(initialFuel ?? fuel).toUpperCase()}`,
      description: "Mapa, historico, previsao e mercado focados em um unico combustivel.",
      tone: "teal" as const,
      badge: "Dossie dedicado",
      heroStats: [
        { label: "Produto", value: (initialFuel ?? fuel).toUpperCase(), icon: "sparkles" as const },
        { label: "Modo", value: "Leitura vertical", icon: "brain" as const },
        { label: "Cobertura", value: "Mapa + mercado + forecast", icon: "waypoints" as const },
      ],
    },
  }[pageMode];

  const workspaceLinks = [
    { href: "/", label: "Overview", icon: Compass },
    { href: "/historico", label: "Historico", icon: Radar },
    { href: "/previsoes", label: "Previsoes", icon: TrendingUp },
    { href: "/comparacoes", label: "Comparar", icon: Scale },
    { href: "/explorer", label: "Explorer", icon: DatabaseZap },
  ];

  useEffect(() => {
    if (initialFuel && initialFuel !== fuel) {
      setFuel(initialFuel);
    }
  }, [initialFuel, fuel, setFuel]);

  useEffect(() => {
    let active = true;
    getFuels()
      .then((items) => {
        if (!active) return;
        setAvailableFuels(items);
        if (items.length > 0 && !items.includes(fuel)) {
          setFuel(items[0]);
        }
      })
      .catch(() => {
        if (!active) return;
        setAvailableFuels(FALLBACK_FUELS);
      });
    return () => {
      active = false;
    };
  }, [fuel, setFuel]);

  useEffect(() => {
    let active = true;
    setLoading(true);

    Promise.allSettled([
      getOverview(fuel, state, startDate, endDate),
      getHistory(fuel, state, city, startDate, endDate),
      getForecast(fuel, state, startDate, endDate),
      pageMode === "comparacoes" ? getComparison(fuel, compareWith, state, startDate, endDate) : Promise.resolve([]),
      getMap(fuel),
      getMarket(fuel, state, startDate, endDate),
      getInsights(fuel, state, pageMode, pageMode === "comparacoes" ? compareWith : "", city, startDate, endDate, mistralKey || undefined),
      getCities(fuel, state),
      getStats(fuel, startDate, endDate),
    ]).then((results) => {
      if (!active) return;
      const [overviewResult, historyResult, forecastResult, comparisonResult, mapResult, marketResult, insightResult, citiesResult, statsResult] = results;
      setOverview(overviewResult.status === "fulfilled" ? overviewResult.value : []);
      setHistory(historyResult.status === "fulfilled" ? historyResult.value : []);
      setForecast(forecastResult.status === "fulfilled" ? forecastResult.value : []);
      setComparison(comparisonResult.status === "fulfilled" ? comparisonResult.value : []);
      setMapData(mapResult.status === "fulfilled" ? mapResult.value : []);
      setMarket(marketResult.status === "fulfilled" ? marketResult.value : []);
      setInsight(insightResult.status === "fulfilled" ? insightResult.value : null);
      setAvailableCities(citiesResult.status === "fulfilled" ? citiesResult.value : []);
      setNationalStats(statsResult.status === "fulfilled" ? statsResult.value : null);
      const firstFailure = results.find((result) => result.status === "rejected");
      setError(firstFailure?.status === "rejected" ? firstFailure.reason?.message ?? "Falha parcial ao carregar dados" : null);
      setLoading(false);
    });

    return () => {
      active = false;
    };
  }, [fuel, state, city, compareWith, pageMode, startDate, endDate, mistralKey]);

  const current = overview[0];
  const availableStates = useMemo(() => Array.from(new Set(mapData.map((item) => item.state))).sort(), [mapData]);
  const recentHistory = useMemo(() => history.slice(-12), [history]);
  const latestHistory = recentHistory[recentHistory.length - 1];
  const previousHistory = recentHistory[recentHistory.length - 2];
  const latestForecast = forecast.filter((item) => item.scenario === "realista").slice(-1)[0];
  const latestMarket = market[market.length - 1];
  const latestComparison = comparison[comparison.length - 1];
  const visibleMapData = useMemo(
    () => mapData.filter((item) => item.product === fuel).sort((a, b) => a.state.localeCompare(b.state)),
    [fuel, mapData],
  );
  const visibleMarketData = useMemo(() => market.slice(-18), [market]);
  const priceDelta = latestHistory && previousHistory ? latestHistory.average_price - previousHistory.average_price : 0;
  const priceDeltaPct = previousHistory?.average_price > 0 ? (priceDelta / previousHistory.average_price) * 100 : undefined;
  const rangeLow = recentHistory.length > 0 ? Math.min(...recentHistory.map((item) => item.average_price)) : undefined;
  const rangeHigh = recentHistory.length > 0 ? Math.max(...recentHistory.map((item) => item.average_price)) : undefined;
  const averageRecent = recentHistory.length > 0 ? recentHistory.reduce((sum, item) => sum + item.average_price, 0) / recentHistory.length : undefined;
  const topStates = visibleMapData.slice().sort((a, b) => b.average_price - a.average_price).slice(0, 5).map((item) => ({ label: item.state, value: item.average_price }));
  const cheapestStates = visibleMapData.slice().sort((a, b) => a.average_price - b.average_price).slice(0, 5).map((item) => ({ label: item.state, value: item.average_price }));
  const scenarioCards = ["conservador", "realista", "agressivo"].map((scenario) => {
    const points = forecast.filter((item) => item.scenario === scenario);
    const last = points[points.length - 1];
    return {
      scenario,
      week: last?.week,
      predicted: last?.predicted,
      minimum: last?.minimum,
      maximum: last?.maximum,
    };
  });
  const aiContextLabel =
    pageMode === "previsoes"
      ? "Briefing de cenarios"
      : pageMode === "comparacoes"
        ? "Briefing comparativo"
        : pageMode === "historico"
          ? "Briefing temporal"
          : pageMode === "combustivel"
            ? "Briefing de dossie"
            : "Briefing executivo";
  const periodLabel = startDate && endDate ? `${startDate} ate ${endDate}` : "Base historica completa";

  useEffect(() => {
    if (availableStates.length > 0 && !availableStates.includes(state)) {
      useDashboardStore.setState({ state: availableStates[0], city: "" });
    }
  }, [availableStates, state]);

  useEffect(() => {
    if (city && availableCities.length > 0 && !availableCities.includes(city)) {
      useDashboardStore.setState({ city: "" });
    }
  }, [availableCities, city]);

  useEffect(() => {
    if (availableFuels.length > 1 && fuel === compareWith) {
      const nextCompare = availableFuels.find((item) => item !== fuel);
      if (nextCompare) {
        useDashboardStore.setState({ compareWith: nextCompare });
      }
    }
  }, [availableFuels, compareWith, fuel]);

  const nationalStatsBar = nationalStats && (
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {[
        {
          label: "Media nacional",
          value: formatCurrency(nationalStats.national_avg),
          sub: `${nationalStats.state_count} estados`,
          color: "border-blue/20 bg-blue/[0.04]",
          valColor: "text-blue font-mono",
        },
        {
          label: "Estado mais barato",
          value: nationalStats.min_state.toUpperCase(),
          sub: formatCurrency(nationalStats.min_price),
          color: "border-emerald/20 bg-emerald/[0.04]",
          valColor: "text-emerald",
        },
        {
          label: "Estado mais caro",
          value: nationalStats.max_state.toUpperCase(),
          sub: formatCurrency(nationalStats.max_price),
          color: "border-rose/20 bg-rose/[0.04]",
          valColor: "text-rose",
        },
        {
          label: "Var. semanal nacional",
          value: `${nationalStats.change_week_pct > 0 ? "+" : ""}${nationalStats.change_week_pct.toFixed(2)}%`,
          sub: nationalStats.change_week_pct > 0 ? "Alta nacional" : nationalStats.change_week_pct < 0 ? "Queda nacional" : "Estavel",
          color: nationalStats.change_week_pct > 0 ? "border-rose/20 bg-rose/[0.04]" : nationalStats.change_week_pct < 0 ? "border-emerald/20 bg-emerald/[0.04]" : "border-line bg-surface",
          valColor: nationalStats.change_week_pct > 0 ? "text-rose font-mono" : nationalStats.change_week_pct < 0 ? "text-emerald font-mono" : "text-muted font-mono",
        },
      ].map((item) => (
        <div key={item.label} className={`bg-surface rounded-2xl border px-5 py-4 ${item.color}`}>
          <p className="text-[9px] uppercase tracking-[0.3em] text-muted">{item.label}</p>
          <p className={`mt-2 font-display text-2xl font-bold ${item.valColor}`}>{item.value}</p>
          <p className="mt-1 text-[11px] text-muted">{item.sub}</p>
        </div>
      ))}
    </section>
  );

  const executiveStats = (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <StatCard
        label="Preco medio"
        value={formatCurrency(current?.average_price)}
        hint="Ultimo fechamento consolidado"
        trend={trendFromDelta(priceDelta)}
        delta={priceDeltaPct}
      />
      <StatCard
        label="Variacao recente"
        value={
          nationalStats
            ? `${nationalStats.change_week_pct > 0 ? "+" : ""}${nationalStats.change_week_pct.toFixed(2)}%`
            : priceDeltaPct !== undefined
              ? `${priceDeltaPct > 0 ? "+" : ""}${priceDeltaPct.toFixed(2)}%`
              : "--"
        }
        hint="Var. semanal nacional — fonte: /stats"
        trend={trendFromDelta(nationalStats?.change_week_pct ?? priceDelta)}
        delta={nationalStats?.change_week_pct ?? priceDeltaPct}
      />
      <StatCard
        label="Faixa recente"
        value={rangeLow !== undefined && rangeHigh !== undefined ? `${rangeLow.toFixed(2)} - ${rangeHigh.toFixed(2)}` : "--"}
        hint="Minimo e maximo do recorte"
        trend="flat"
      />
      <StatCard
        label="IA ativa"
        value={insight?.source === "mistral" ? "Mistral" : "Fallback"}
        hint="Origem atual do briefing"
        trend="flat"
      />
    </section>
  );

  const historicalStats = (
    <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
      <InfoPanel kicker="Janela temporal" title="Resumo do recorte historico">
        <MetricStrip
          items={[
            { label: "Ultima semana", value: latestHistory?.week ?? "--" },
            { label: "Media recente", value: formatCurrency(averageRecent) },
            { label: "Amplitude", value: rangeLow !== undefined && rangeHigh !== undefined ? formatCurrency(rangeHigh - rangeLow) : "--" },
          ]}
        />
      </InfoPanel>
      <InfoPanel kicker="Cobertura territorial" title="Profundidade do recorte">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-[1.35rem] border border-line bg-surface2 p-4">
            <p className="text-[10px] uppercase tracking-[0.24em] text-muted">Estado</p>
            <p className="mt-3 font-display text-2xl text-white">{state}</p>
          </div>
          <div className="rounded-[1.35rem] border border-line bg-surface2 p-4">
            <p className="text-[10px] uppercase tracking-[0.24em] text-muted">Cidade</p>
            <p className="mt-3 font-display text-2xl text-white">{city || "Todas"}</p>
          </div>
          <div className="rounded-[1.35rem] border border-line bg-surface2 p-4">
            <p className="text-[10px] uppercase tracking-[0.24em] text-muted">Municipios</p>
            <p className="mt-3 font-display text-2xl text-white">{String(availableCities.length || 0)}</p>
          </div>
        </div>
      </InfoPanel>
    </section>
  );

  const forecastStats = (
    <section className="grid gap-4 xl:grid-cols-4">
      {scenarioCards.map((scenario) => (
        <Card key={scenario.scenario} className="bg-[linear-gradient(160deg,rgba(255,255,255,0.08),rgba(255,255,255,0.02))]">
          <p className="text-[10px] uppercase tracking-[0.28em] text-muted">{scenario.scenario}</p>
          <p className="mt-4 font-display text-4xl text-white">{formatCurrency(scenario.predicted)}</p>
          <p className="mt-3 text-sm text-muted">
            {scenario.week ?? "--"} · {formatCurrency(scenario.minimum)} a {formatCurrency(scenario.maximum)}
          </p>
        </Card>
      ))}
      <Card className="bg-[linear-gradient(160deg,rgba(244,184,96,0.08),rgba(255,255,255,0.02))]">
        <p className="text-[10px] uppercase tracking-[0.28em] text-muted">Regime de mercado</p>
        <p className="mt-4 font-display text-4xl text-white">{latestMarket?.market_regime ?? "--"}</p>
        <p className="mt-3 text-sm text-muted">Oferta versus demanda no ultimo ponto do recorte.</p>
      </Card>
    </section>
  );

  const comparisonStats = (
    <section className="grid gap-4 xl:grid-cols-4">
      <Card className="bg-[linear-gradient(160deg,rgba(139,125,255,0.12),rgba(255,255,255,0.02))]">
        <p className="text-[10px] uppercase tracking-[0.24em] text-muted">Combustivel base</p>
        <p className="mt-4 font-display text-4xl text-white">{fuel.toUpperCase()}</p>
      </Card>
      <Card className="bg-[linear-gradient(160deg,rgba(107,184,255,0.12),rgba(255,255,255,0.02))]">
        <p className="text-[10px] uppercase tracking-[0.24em] text-muted">Combustivel comparado</p>
        <p className="mt-4 font-display text-4xl text-white">{compareWith.toUpperCase()}</p>
      </Card>
      <Card className="bg-[linear-gradient(160deg,rgba(54,214,167,0.12),rgba(255,255,255,0.02))]">
        <p className="text-[10px] uppercase tracking-[0.24em] text-muted">Spread final</p>
        <p className="mt-4 font-display text-4xl text-white">{formatPercent(latestComparison?.advantage_percent)}</p>
      </Card>
      <Card className="bg-[linear-gradient(160deg,rgba(255,123,114,0.12),rgba(255,255,255,0.02))]">
        <p className="text-[10px] uppercase tracking-[0.24em] text-muted">Vencedor</p>
        <p className="mt-4 font-display text-4xl text-white">{latestComparison?.recommended_fuel ?? "--"}</p>
      </Card>
    </section>
  );

  const fuelStats = (
    <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
      <InfoPanel kicker="Produto" title={`Panorama dedicado de ${(initialFuel ?? fuel).toUpperCase()}`}>
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-[1.35rem] border border-line bg-surface2 p-4">
            <p className="text-[10px] uppercase tracking-[0.24em] text-muted">Preco medio</p>
            <p className="mt-3 font-display text-3xl text-white">{formatCurrency(current?.average_price)}</p>
          </div>
          <div className="rounded-[1.35rem] border border-line bg-surface2 p-4">
            <p className="text-[10px] uppercase tracking-[0.24em] text-muted">Volatilidade</p>
            <p className="mt-3 font-display text-3xl text-white">{current ? current.volatility.toFixed(3) : "--"}</p>
          </div>
          <div className="rounded-[1.35rem] border border-line bg-surface2 p-4">
            <p className="text-[10px] uppercase tracking-[0.24em] text-muted">Regime</p>
            <p className="mt-3 font-display text-3xl text-white">{latestMarket?.market_regime ?? "--"}</p>
          </div>
        </div>
      </InfoPanel>
      <InfoPanel kicker="Troca rapida" title="Abrir outro combustivel">
        <FuelSwitchboard fuels={availableFuels.length > 0 ? availableFuels : FALLBACK_FUELS} activeFuel={initialFuel ?? fuel} />
      </InfoPanel>
    </section>
  );

  const footerCards = [
    {
      kicker: "Periodo",
      value: periodLabel,
      note: "Janela ativa de analise",
      tone: "rgba(54,214,167,0.12)",
    },
    {
      kicker: "UF mais cara",
      value: topStates[0] ? `${topStates[0].label} · ${formatCurrency(topStates[0].value)}` : "--",
      note: "Maior preco medio no mapa atual",
      tone: "rgba(244,184,96,0.12)",
    },
    {
      kicker: "UF mais barata",
      value: cheapestStates[0] ? `${cheapestStates[0].label} · ${formatCurrency(cheapestStates[0].value)}` : "--",
      note: "Menor preco medio no mapa atual",
      tone: "rgba(107,184,255,0.12)",
    },
  ];

  const dashboardLayout = (
    <>
      {nationalStatsBar}
      {executiveStats}
      <AIBriefing insight={insight} contextLabel={aiContextLabel} />
      <section className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
        <OverviewChart data={recentHistory} />
        <InfoPanel kicker="Radar" title="Leitura instantanea do filtro">
          <MetricStrip
            items={[
              { label: "Preco atual", value: formatCurrency(current?.average_price) },
              { label: "Volatilidade", value: current ? current.volatility.toFixed(3) : "--" },
              { label: "Regime", value: latestMarket?.market_regime ?? "--" },
            ]}
          />
          <div className="mt-4 rounded-[1.3rem] border border-line bg-surface p-4 text-sm leading-7 text-muted">
            O painel principal agora concentra contexto de mercado, leitura de IA e rankings por estado para servir como hub analitico, nao como uma repeticao das outras rotas.
          </div>
        </InfoPanel>
      </section>
      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <MarketChart data={visibleMarketData} />
        <MarketPressure data={visibleMarketData} />
      </section>
      <section className="grid gap-6 lg:grid-cols-2">
        <RankedList title="Estados mais caros" subtitle="Ranking de pressao" items={topStates} formatter={(value) => formatCurrency(value)} />
        <RankedList title="Estados mais baratos" subtitle="Ranking de alivio" items={cheapestStates} formatter={(value) => formatCurrency(value)} />
      </section>
      <section className="grid gap-6">
        <PriceMap data={visibleMapData} />
        <ForecastChart data={forecast} />
      </section>
      <section className="space-y-4">
        <FuelSwitchboard fuels={availableFuels.length > 0 ? availableFuels : FALLBACK_FUELS} activeFuel={fuel} />
      </section>
    </>
  );

  const historicalLayout = (
    <>
      {historicalStats}
      <AIBriefing insight={insight} contextLabel={aiContextLabel} />
      <section className="grid gap-6 xl:grid-cols-[1.45fr_0.55fr]">
        <OverviewChart data={history} />
        <InfoPanel kicker="Extremos" title="Faixa e reversao">
          <div className="space-y-3">
            <div className="rounded-2xl border border-line bg-surface2 p-4">
              <p className="text-sm text-muted">Minimo recente</p>
              <p className="mt-2 font-display text-3xl text-white">{formatCurrency(rangeLow)}</p>
            </div>
            <div className="rounded-2xl border border-line bg-surface2 p-4">
              <p className="text-sm text-muted">Maximo recente</p>
              <p className="mt-2 font-display text-3xl text-white">{formatCurrency(rangeHigh)}</p>
            </div>
            <div className="rounded-2xl border border-line bg-surface2 p-4">
              <p className="text-sm text-muted">Mudanca semanal</p>
              <p className="mt-2 font-display text-3xl text-white">{formatCurrency(priceDelta)}</p>
            </div>
          </div>
        </InfoPanel>
      </section>
      <section className="grid gap-6 lg:grid-cols-2">
        <InfoPanel kicker="Cadencia" title="Semanas recentes">
          <div className="space-y-3">
            {recentHistory.slice().reverse().map((point) => (
              <div key={`${point.week}-${point.city || "state"}`} className="flex items-center justify-between rounded-2xl border border-line bg-surface2 px-4 py-3">
                <div>
                  <p className="text-sm text-white">{point.week}</p>
                  <p className="text-xs text-muted">{point.city || state}</p>
                </div>
                <p className="font-display text-xl text-white">{formatCurrency(point.average_price)}</p>
              </div>
            ))}
          </div>
        </InfoPanel>
        <InfoPanel kicker="Cobertura" title="Recorte analisado">
          <MetricStrip
            items={[
              { label: "Estado", value: state },
              { label: "Cidade", value: city || "Todas" },
              { label: "Municipios", value: String(availableCities.length || 0) },
            ]}
          />
          <div className="mt-4 rounded-[1.25rem] border border-line bg-surface p-4 text-sm leading-7 text-muted">
            Selecione uma cidade para trocar a serie agregada do estado por uma trilha municipal. Agora a lista de cidades e carregada diretamente da API, sem depender da serie agregada.
          </div>
        </InfoPanel>
      </section>
      <section className="grid gap-6 lg:grid-cols-2">
        <RankedList title="Estados mais caros no recorte" subtitle="Contexto territorial" items={topStates} formatter={(value) => formatCurrency(value)} />
        <RankedList title="Estados com alivio" subtitle="Comparacao geografica" items={cheapestStates} formatter={(value) => formatCurrency(value)} />
      </section>
    </>
  );

  const forecastLayout = (
    <>
      {forecastStats}
      <AIBriefing insight={insight} contextLabel={aiContextLabel} />
      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <ForecastChart data={forecast} />
        <InfoPanel kicker="Risco" title="Leitura do range">
          <div className="space-y-3">
            <div className="flex items-center justify-between rounded-2xl border border-line bg-surface2 px-4 py-3">
              <span className="text-sm text-muted">Amplitude projetada</span>
              <span className="font-display text-xl text-white">
                {latestForecast ? formatCurrency(latestForecast.maximum - latestForecast.minimum) : "--"}
              </span>
            </div>
            <div className="flex items-center justify-between rounded-2xl border border-line bg-surface2 px-4 py-3">
              <span className="text-sm text-muted">Regime atual</span>
              <span className="font-display text-xl text-white">{latestMarket?.market_regime ?? "--"}</span>
            </div>
            <div className="flex items-center justify-between rounded-2xl border border-line bg-surface2 px-4 py-3">
              <span className="text-sm text-muted">Oferta / demanda</span>
              <span className="font-display text-xl text-white">{latestMarket ? latestMarket.supply_demand_ratio.toFixed(2) : "--"}</span>
            </div>
          </div>
        </InfoPanel>
      </section>
      <section className="grid gap-6 lg:grid-cols-2">
        <MarketChart data={visibleMarketData} />
        <MarketPressure data={visibleMarketData} />
      </section>
    </>
  );

  const comparisonLayout = (
    <>
      {comparisonStats}
      <AIBriefing insight={insight} contextLabel={aiContextLabel} />
      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <ComparisonChart data={comparison.slice(-16)} />
        <InfoPanel kicker="Escolha" title="Quadro de decisao">
          <MetricStrip
            items={[
              { label: "Combustivel base", value: fuel },
              { label: "Alternativa", value: compareWith },
              { label: "Recomendacao", value: latestComparison?.recommended_fuel ?? "--" },
            ]}
          />
          <div className="mt-4 rounded-[1.25rem] border border-line bg-surface p-4 text-sm leading-7 text-muted">
            Esta tela privilegia a resposta final: quem vence agora, qual e o spread recente e quando a troca parece fazer sentido no fim da serie.
          </div>
        </InfoPanel>
      </section>
      <section className="grid gap-6 lg:grid-cols-2">
        <InfoPanel kicker="Spread" title="Ultimos duelos">
          <div className="space-y-3">
            {comparison.slice(-8).reverse().map((point) => (
              <div key={`${point.week}-${point.primary_fuel}-${point.compared_fuel}`} className="flex items-center justify-between rounded-2xl border border-line bg-surface2 px-4 py-3">
                <div>
                  <p className="text-sm text-white">{point.week}</p>
                  <p className="text-xs text-muted">{point.primary_fuel} vs {point.compared_fuel}</p>
                </div>
                <div className="text-right">
                  <p className="font-display text-xl text-white">{formatPercent(point.advantage_percent)}</p>
                  <p className="text-xs text-muted">{point.recommended_fuel}</p>
                </div>
              </div>
            ))}
          </div>
        </InfoPanel>
        <InfoPanel kicker="Regra pratica" title="Leituras complementares">
          <div className="space-y-3">
            <div className="rounded-2xl border border-line bg-surface2 p-4">
              <p className="flex items-center gap-2 text-sm text-white"><TrendingUp className="h-4 w-4 text-accent" /> Melhor alternativa recente</p>
              <p className="mt-2 text-sm leading-7 text-muted">{latestComparison?.recommended_fuel ?? "--"} lidera no ultimo ponto comparado.</p>
            </div>
            <div className="rounded-2xl border border-line bg-surface2 p-4">
              <p className="flex items-center gap-2 text-sm text-white"><TrendingDown className="h-4 w-4 text-coral" /> Spread</p>
              <p className="mt-2 text-sm leading-7 text-muted">O diferencial mais recente esta em {formatPercent(latestComparison?.advantage_percent)}.</p>
            </div>
          </div>
        </InfoPanel>
      </section>
    </>
  );

  const fuelLayout = (
    <>
      {fuelStats}
      <AIBriefing insight={insight} contextLabel={aiContextLabel} />
      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <PriceMap data={visibleMapData} />
        <InfoPanel kicker="Mapa" title="Onde este combustivel pressiona mais">
          <div className="space-y-3">
            {topStates.slice(0, 4).map((item) => (
              <div key={item.label} className="flex items-center justify-between rounded-2xl border border-line bg-surface2 px-4 py-3">
                <span className="text-sm text-white">{item.label}</span>
                <span className="font-display text-xl text-white">{formatCurrency(item.value)}</span>
              </div>
            ))}
          </div>
        </InfoPanel>
      </section>
      <section className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <OverviewChart data={history} />
        <InfoPanel kicker="Trajetoria do produto" title="Leitura executiva do combustivel">
          <div className="space-y-3">
            <div className="rounded-[1.35rem] border border-line bg-surface2 p-4">
              <p className="text-sm text-muted">Ultimo fechamento</p>
              <p className="mt-2 font-display text-3xl text-white">{latestHistory?.week ?? "--"}</p>
            </div>
            <div className="rounded-[1.35rem] border border-line bg-surface2 p-4">
              <p className="text-sm text-muted">Faixa do recorte</p>
              <p className="mt-2 font-display text-3xl text-white">{rangeLow !== undefined && rangeHigh !== undefined ? `${rangeLow.toFixed(2)} - ${rangeHigh.toFixed(2)}` : "--"}</p>
            </div>
            <div className="rounded-[1.35rem] border border-line bg-surface2 p-4">
              <p className="text-sm text-muted">Direcao recente</p>
              <p className="mt-2 font-display text-3xl text-white">{priceDelta > 0 ? "Alta" : priceDelta < 0 ? "Queda" : "Estavel"}</p>
            </div>
          </div>
        </InfoPanel>
      </section>
      <section className="grid gap-6">
        <ForecastChart data={forecast} />
        <RankedList title="Estados mais pressionados" subtitle="Mapa do produto" items={topStates} formatter={(value) => formatCurrency(value)} />
      </section>
      <section className="grid gap-6 lg:grid-cols-2">
        <MarketChart data={visibleMarketData} />
        <MarketPressure data={visibleMarketData} />
      </section>
    </>
  );

  return (
    <main className="space-y-6 pb-10">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
        <PageHero
          kicker={pageConfig.kicker}
          title={pageConfig.title}
          description={pageConfig.description}
          tone={pageConfig.tone}
          badge={pageConfig.badge}
          stats={pageConfig.heroStats}
        />
        <div className="section-shell overflow-hidden">
          <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
            <div className="flex flex-wrap gap-2">
          {workspaceLinks.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className="inline-flex items-center gap-2 rounded-full border border-line bg-white/[0.03] px-4 py-2 text-sm text-white/78 transition hover:bg-white/[0.08]"
              >
                <Icon className="h-4 w-4 text-accent" />
                {item.label}
              </Link>
            );
          })}
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-[1.4rem] border border-line bg-surface p-4">
                <p className="text-[10px] uppercase tracking-[0.24em] text-muted">Periodo</p>
                <p className="mt-2 text-sm leading-6 text-white">{periodLabel}</p>
              </div>
              <div className="rounded-[1.4rem] border border-line bg-surface p-4">
                <p className="text-[10px] uppercase tracking-[0.24em] text-muted">Foco</p>
                <p className="mt-2 text-sm leading-6 text-white">{city || state}</p>
              </div>
              <div className="rounded-[1.4rem] border border-line bg-surface p-4">
                <p className="text-[10px] uppercase tracking-[0.24em] text-muted">IA</p>
                <div className="mt-2 inline-flex items-center gap-2 text-sm text-white/80">
                  <Bot className="h-4 w-4 text-amber" />
                  {insight?.source === "mistral" ? "Mistral contextual" : "Fallback local"}
                </div>
              </div>
            </div>
          </div>
        </div>
        <Filters
          fuels={availableFuels.length > 0 ? availableFuels : FALLBACK_FUELS}
          states={availableStates.length > 0 ? availableStates : [state]}
          cities={availableCities}
          mode={pageMode}
        />
      </motion.div>

      {error ? <Card className="border-coral/50 text-coral">Falha ao carregar dados: {error}</Card> : null}
      {loading ? <Card className="text-muted">Atualizando painéis, rankings e briefings inteligentes...</Card> : null}

      {pageMode === "dashboard" && dashboardLayout}
      {pageMode === "historico" && historicalLayout}
      {pageMode === "previsoes" && forecastLayout}
      {pageMode === "comparacoes" && comparisonLayout}
      {pageMode === "combustivel" && fuelLayout}

      <section className="grid gap-4 lg:grid-cols-3">
        {footerCards.map((card) => (
          <Card
            key={card.kicker}
            className="bg-[linear-gradient(135deg,rgba(255,255,255,0.04),rgba(255,255,255,0.03))]"
            style={{ backgroundImage: `linear-gradient(135deg, ${card.tone}, rgba(255,255,255,0.03))` }}
          >
            <p className="text-xs uppercase tracking-[0.28em] text-muted">{card.kicker}</p>
            <p className="mt-4 font-display text-2xl text-white">{card.value}</p>
            <p className="mt-3 text-sm leading-7 text-muted">{card.note}</p>
          </Card>
        ))}
      </section>
    </main>
  );
}
