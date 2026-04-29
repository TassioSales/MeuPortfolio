"use client";

import { FuelName } from "@/lib/types";
import { useDashboardStore } from "@/lib/store";

export function Filters({
  fuels,
  states,
  cities,
  mode = "dashboard",
}: {
  fuels: FuelName[];
  states: string[];
  cities: string[];
  mode?: "dashboard" | "historico" | "previsoes" | "comparacoes" | "combustivel";
}) {
  const { fuel, state, city, compareWith, startDate, endDate, setFuel, setState, setCity, setCompareWith, setDateRange } =
    useDashboardStore();

  const applyMonthsBack = (months: number) => {
    const end = new Date();
    const start = new Date();
    start.setMonth(start.getMonth() - months);
    setDateRange(start.toISOString().split("T")[0], end.toISOString().split("T")[0]);
  };

  return (
    <div className="section-shell mesh-accent overflow-hidden">
      <div className="grid gap-5 xl:grid-cols-[0.92fr_1.08fr]">
        <div className="rounded-[1.8rem] border border-white/10 bg-black/15 p-5">
          <p className="text-[10px] uppercase tracking-[0.35em] text-white/45">Controlos Globais</p>
          <h3 className="mt-3 font-display text-3xl text-white">Filtros e periodo</h3>
          <p className="mt-3 text-sm leading-7 text-mist">
            Ajuste produto, estado, municipio, recorte temporal e combustivel de comparacao em um unico cockpit.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            <button type="button" className="rounded-full border border-accent/20 bg-accent/10 px-4 py-2 text-xs font-semibold text-accent" onClick={() => applyMonthsBack(12)}>
              Ultimos 12 meses
            </button>
            <button type="button" className="rounded-full border border-amber/20 bg-amber/10 px-4 py-2 text-xs font-semibold text-amber" onClick={() => applyMonthsBack(24)}>
              Ultimos 24 meses
            </button>
            <button type="button" className="rounded-full border border-sky/20 bg-sky/10 px-4 py-2 text-xs font-semibold text-sky" onClick={() => setDateRange("", "")}>
              Base completa
            </button>
          </div>
          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.05] p-4">
              <p className="text-[10px] uppercase tracking-[0.24em] text-white/45">Produto</p>
              <p className="mt-2 font-display text-2xl text-white">{fuel.toUpperCase()}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.05] p-4">
              <p className="text-[10px] uppercase tracking-[0.24em] text-white/45">Territorio</p>
              <p className="mt-2 font-display text-2xl text-white">{city || state}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.05] p-4">
              <p className="text-[10px] uppercase tracking-[0.24em] text-white/45">{mode === "comparacoes" ? "Comparativo" : "Modo"}</p>
              <p className="mt-2 font-display text-2xl text-white">{mode === "comparacoes" ? compareWith.toUpperCase() : "Individual"}</p>
            </div>
          </div>
        </div>
        <div className={`grid gap-4 md:grid-cols-2 ${mode === "comparacoes" ? "xl:grid-cols-5" : "xl:grid-cols-4"}`}>
      <label className="space-y-2 text-sm text-mist">
        <span className="text-[11px] uppercase tracking-[0.24em] text-white/50">Combustivel</span>
        <select
          className="w-full rounded-[1.4rem] border border-white/10 bg-panel/90 px-4 py-4 text-white shadow-inner"
          value={fuel}
          onChange={(event) => setFuel(event.target.value as FuelName)}
        >
          {fuels.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </label>
      <label className="space-y-2 text-sm text-mist">
        <span className="text-[11px] uppercase tracking-[0.24em] text-white/50">Estado</span>
        <select
          className="w-full rounded-[1.4rem] border border-white/10 bg-panel/90 px-4 py-4 text-white shadow-inner"
          value={state}
          onChange={(event) => setState(event.target.value)}
        >
          {states.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </label>
      <label className="space-y-2 text-sm text-mist">
        <span className="text-[11px] uppercase tracking-[0.24em] text-white/50">Cidade</span>
        <select
          className="w-full rounded-[1.4rem] border border-white/10 bg-panel/90 px-4 py-4 text-white shadow-inner"
          value={city}
          onChange={(event) => setCity(event.target.value)}
        >
          <option value="">Todas as cidades</option>
          {cities.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </label>
      <label className="space-y-2 text-sm text-mist">
        <span className="text-[11px] uppercase tracking-[0.24em] text-white/50">Periodo</span>
        <div className="grid gap-2">
          <input
            type="date"
            className="w-full rounded-[1.4rem] border border-white/10 bg-panel/90 px-3 py-4 text-sm text-white shadow-inner"
            value={startDate}
            onChange={(e) => setDateRange(e.target.value, endDate)}
          />
          <input
            type="date"
            className="w-full rounded-[1.4rem] border border-white/10 bg-panel/90 px-3 py-4 text-sm text-white shadow-inner"
            value={endDate}
            onChange={(e) => setDateRange(startDate, e.target.value)}
          />
        </div>
      </label>
      {mode === "comparacoes" ? (
        <label className="space-y-2 text-sm text-mist">
          <span className="text-[11px] uppercase tracking-[0.24em] text-white/50">Comparar com</span>
          <select
            className="w-full rounded-[1.4rem] border border-white/10 bg-panel/90 px-4 py-4 text-white shadow-inner"
            value={compareWith}
            onChange={(event) => setCompareWith(event.target.value as FuelName)}
          >
            {(fuels.filter((item) => item !== fuel).length > 0 ? fuels.filter((item) => item !== fuel) : fuels).map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      </div>
      </div>
    </div>
  );
}
