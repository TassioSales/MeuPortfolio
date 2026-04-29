"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BarChart3, Database, Gauge, LineChart, Sparkles, BrainCircuit } from "lucide-react";

import { cn } from "@/lib/utils";

const links = [
  { href: "/", label: "Dashboard", subtitle: "Visao executiva", icon: Gauge },
  { href: "/historico", label: "Historico", subtitle: "Serie e contexto", icon: Activity },
  { href: "/previsoes", label: "Previsoes", subtitle: "Cenarios e faixa", icon: LineChart },
  { href: "/comparacoes", label: "Comparacoes", subtitle: "Escolha relativa", icon: BarChart3 },
  { href: "/explorer", label: "Explorer", subtitle: "Base local", icon: Database },
  { href: "/combustivel/gasolina", label: "Combustivel", subtitle: "Painel dedicado", icon: Sparkles },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="grid-bg min-h-screen">
      <div className="mx-auto flex min-h-screen w-full max-w-[1600px] gap-8 px-4 py-8 lg:px-8">
        <aside className="glass-panel sticky top-8 hidden h-[calc(100vh-4rem)] w-[21rem] shrink-0 flex-col overflow-hidden rounded-[2.75rem] lg:flex">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(54,214,167,0.15),transparent_24%),radial-gradient(circle_at_top_right,rgba(244,184,96,0.14),transparent_22%),radial-gradient(circle_at_bottom_center,rgba(107,184,255,0.15),transparent_24%)]" />
          <div className="relative flex h-full flex-col p-8">
          <div className="mb-10">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-accent to-sky shadow-glow">
                <Activity className="h-6 w-6 text-ink" />
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.4em] text-accent">Fuel Intel</p>
                <p className="mt-1 text-[11px] uppercase tracking-[0.28em] text-white/35">Intelligence Studio</p>
              </div>
            </div>
            <h1 className="mt-6 font-display text-4xl leading-tight">Market Operating System</h1>
            <p className="mt-4 text-sm leading-7 text-mist/80">
              Uma mesa visual para navegar historico, previsao, spread, logistica e leitura contextual da Mistral sem parecer a mesma tela o tempo todo.
            </p>
          </div>

          <div className="mb-8 rounded-[2rem] border border-white/10 bg-black/20 p-5">
            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.3em] text-white/40">
              <BrainCircuit className="h-3 w-3 text-accent/60" />
              Intelligence Desk
            </div>
            <p className="mt-4 font-display text-2xl text-white">Mistral em contexto</p>
            <p className="mt-3 text-xs leading-6 text-mist">
              Cada rota ganhou um modo proprio de leitura: executivo, temporal, cenarios, decisao e dossie.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {["Historico", "Forecast", "Spread"].map((item) => (
                <span key={item} className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-[10px] uppercase tracking-[0.24em] text-white/65">
                  {item}
                </span>
              ))}
            </div>
          </div>

          <nav className="flex-1 space-y-1.5 overflow-y-auto pr-2 custom-scrollbar">
            {links.map((link) => {
              const Icon = link.icon;
              const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "group flex items-center gap-4 rounded-[1.65rem] px-5 py-4 transition-all duration-300",
                    active
                      ? "border-white/10 bg-[linear-gradient(135deg,rgba(54,214,167,0.18),rgba(107,184,255,0.12),rgba(255,255,255,0.04))] text-white shadow-glow"
                      : "border border-transparent text-mist hover:bg-white/[0.05] hover:text-white",
                  )}
                >
                  <div className={cn("flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-black/20", active ? "text-accent" : "group-hover:text-white")}>
                    <Icon className="h-5 w-5 transition-colors" />
                  </div>
                  <div>
                    <div className="font-semibold tracking-wide">{link.label}</div>
                    <div className={cn("text-[10px] uppercase tracking-widest transition-opacity", active ? "text-white/55 opacity-100" : "text-white/30 opacity-60 group-hover:opacity-100")}>
                      {link.subtitle}
                    </div>
                  </div>
                </Link>
              );
            })}
          </nav>

          <div className="mt-8 rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-4">
            <p className="text-[10px] uppercase tracking-[0.4em] text-white/25">System Phase 4.2</p>
            <p className="mt-3 text-sm leading-6 text-mist">Filtros globais, briefings assistidos e leitura multi-camada da serie historica da ANP.</p>
          </div>
          </div>
        </aside>

        <div className="min-w-0 flex-1">
          <div className="mb-6 space-y-3 lg:hidden">
            <div className="rounded-[1.8rem] border border-white/10 bg-[linear-gradient(135deg,rgba(54,214,167,0.14),rgba(107,184,255,0.14),rgba(255,255,255,0.04))] p-4">
              <p className="text-[10px] uppercase tracking-[0.35em] text-white/55">Fuel Intel</p>
              <p className="mt-2 font-display text-2xl text-white">Market Operating System</p>
            </div>
            <div className="flex gap-3 overflow-x-auto pb-2 no-scrollbar">
            {links.map((link) => {
              const Icon = link.icon;
              const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "inline-flex min-w-max items-center gap-3 rounded-2xl border px-5 py-3 text-sm font-medium transition-all",
                    active
                      ? "border-accent/30 bg-[linear-gradient(135deg,rgba(54,214,167,0.18),rgba(107,184,255,0.12))] text-white shadow-glow"
                      : "border-white/10 bg-white/[0.03] text-mist",
                  )}
                >
                  <Icon className={cn("h-4 w-4", active ? "text-accent" : "")} />
                  {link.label}
                </Link>
              );
            })}
          </div>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
