"use client";
import { useEffect } from "react";
import { motion } from "framer-motion";
import { RefreshCw, Play, BookOpen, Users, BarChart2, ArrowRight } from "lucide-react";
import Link from "next/link";
import { CareerPath } from "@/components/roadmap/CareerPath";
import { AIChatPanel } from "@/components/coach/AIChatPanel";
import { NextBestAction } from "@/components/coach/NextBestAction";
import { useCareerStore } from "@/lib/stores/careerStore";
import { useAuthStore } from "@/lib/stores/authStore";
import { SkeletonCard } from "@/components/ui/Skeleton";

const QUICK_ACTIONS = [
  { label: "Meu Caminho", desc: "Ver roadmap", icon: BookOpen, href: "/dashboard/my-path", color: "text-violet-400", bg: "bg-violet-400/10 border-violet-400/20" },
  { label: "Simulação", desc: "Praticar cenários", icon: Play, href: "/dashboard/simulation", color: "text-blue-400", bg: "bg-blue-400/10 border-blue-400/20" },
  { label: "Mentoria", desc: "Agendar sessão", icon: Users, href: "/dashboard/mentorship", color: "text-amber-400", bg: "bg-amber-400/10 border-amber-400/20" },
  { label: "Analytics", desc: "Ver progresso", icon: BarChart2, href: "/dashboard/analytics", color: "text-accent", bg: "bg-accent/10 border-accent/20" },
];

export default function HomePage() {
  const { roadmap, loading, fetchRoadmap, updateMilestone } = useCareerStore();
  const { user } = useAuthStore();

  useEffect(() => { fetchRoadmap(); }, []);

  const currentMs = roadmap?.milestones[roadmap.current_milestone_index] ?? null;
  const pct = roadmap?.progress_pct ?? 0;

  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-y-auto p-6 gap-5 min-w-0">

        {/* Hero card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          className="relative overflow-hidden rounded-2xl border border-border shadow-card bg-surface-card"
        >
          {/* Decorative glow */}
          <div className="absolute top-0 left-0 w-64 h-64 bg-accent/5 rounded-full blur-3xl pointer-events-none -translate-x-1/2 -translate-y-1/2" />
          <div className="absolute top-0 right-0 w-96 h-48 bg-violet-500/5 rounded-full blur-3xl pointer-events-none" />

          <div className="relative p-6">
            <div className="flex items-start justify-between mb-5">
              <div>
                <p className="text-xs font-semibold text-accent uppercase tracking-[0.12em] mb-2 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse inline-block" />
                  AI-Powered Career Acceleration
                </p>
                <h1 className="text-2xl font-bold text-text-primary leading-tight mb-1">
                  Roadmap para{" "}
                  <span className="text-accent">{user?.target_role ?? "..."}</span>
                </h1>
                <p className="text-text-muted text-sm max-w-md">
                  De <span className="text-text-primary font-medium">{user?.current_role ?? "..."}</span> à sua meta — cada milestone é um passo validado pela IA.
                </p>
              </div>
              <button
                onClick={() => fetchRoadmap()}
                disabled={loading}
                aria-label="Recarregar roadmap"
                className="p-2 rounded-lg border border-border hover:border-border-bright text-text-muted hover:text-text-primary transition-all shrink-0"
              >
                <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
              </button>
            </div>

            {/* Progress */}
            <div className="mb-5">
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-text-muted">Progresso geral</span>
                <span className="text-accent font-semibold">{pct.toFixed(0)}%</span>
              </div>
              <div className="h-2 bg-surface-high rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: "linear-gradient(90deg, #00e87a, #00b85e)" }}
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 1.2, ease: "easeOut" }}
                />
              </div>
              <div className="flex justify-between text-xs mt-1 text-text-dim">
                <span>{roadmap?.current_milestone_index ?? 0} de {roadmap?.milestones.length ?? 0} concluídos</span>
                <span>{roadmap ? 100 - pct : 0}% restante</span>
              </div>
            </div>

            {/* Career path SVG */}
            <div className="h-64 rounded-xl overflow-visible">
              {loading ? (
                <div className="h-full flex items-center justify-center">
                  <div className="space-y-2 w-full px-4">
                    <SkeletonCard lines={2} />
                  </div>
                </div>
              ) : roadmap ? (
                <CareerPath
                  milestones={roadmap.milestones}
                  currentIndex={roadmap.current_milestone_index}
                  progressPct={pct}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-text-muted text-sm">
                  Roadmap sendo gerado pela IA...
                </div>
              )}
            </div>

            {/* CTA */}
            <div className="flex gap-3 mt-5">
              <button
                onClick={() => currentMs && updateMilestone(currentMs.index, "in_progress")}
                disabled={!currentMs}
                className="px-5 py-2.5 rounded-xl text-sm font-semibold text-surface transition-all disabled:opacity-40 shadow-accent-sm hover:shadow-accent-md"
                style={{ background: "linear-gradient(135deg, #00e87a, #00b85e)" }}
              >
                Continuar jornada
              </button>
              <Link
                href="/dashboard/simulation"
                className="px-5 py-2.5 bg-surface-high border border-border text-sm text-text-primary rounded-xl hover:border-border-bright transition-all flex items-center gap-2"
              >
                Iniciar simulação
                <ArrowRight size={14} className="text-text-muted" />
              </Link>
            </div>
          </div>
        </motion.div>

        {/* Quick actions */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {QUICK_ACTIONS.map(({ label, desc, icon: Icon, href, color, bg }, i) => (
            <motion.div
              key={href}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.05 }}
            >
              <Link
                href={href}
                className="group flex flex-col gap-3 p-4 rounded-xl border border-border bg-surface-card shadow-card hover:shadow-card-hover hover:border-border-bright transition-all"
              >
                <div className={`w-9 h-9 rounded-lg border flex items-center justify-center ${bg}`}>
                  <Icon size={16} className={color} />
                </div>
                <div>
                  <p className="text-sm font-semibold text-text-primary group-hover:text-white transition-colors">{label}</p>
                  <p className="text-xs text-text-muted mt-0.5">{desc}</p>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Right panel */}
      <div className="w-80 flex flex-col gap-4 p-4 border-l border-border shrink-0 overflow-y-auto">
        <NextBestAction
          milestone={currentMs}
          progressPct={pct}
          targetRole={user?.target_role ?? ""}
          onStart={() => currentMs && updateMilestone(currentMs.index, "in_progress")}
        />
        <div className="flex-1 min-h-0" style={{ minHeight: 360 }}>
          <AIChatPanel />
        </div>
      </div>
    </div>
  );
}
