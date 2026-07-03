"use client";
import { Zap, Clock, ArrowRight } from "lucide-react";
import type { Milestone } from "@/lib/api";

interface Props {
  milestone: Milestone | null;
  progressPct: number;
  targetRole: string;
  onStart: () => void;
}

export function NextBestAction({ milestone, progressPct, targetRole, onStart }: Props) {
  if (!milestone) return null;

  return (
    <div className="rounded-xl border border-border bg-surface-card shadow-card overflow-hidden">
      {/* Accent header strip */}
      <div className="h-0.5 bg-accent-gradient" />

      <div className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-6 h-6 rounded-md bg-accent/15 border border-accent/25 flex items-center justify-center">
            <Zap size={12} className="text-accent" />
          </div>
          <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">Próxima ação</span>
        </div>

        <p className="text-sm font-semibold text-text-primary mb-1 leading-snug">{milestone.title}</p>
        <p className="text-xs text-text-muted mb-3">
          Rumo a <span className="text-text-primary font-medium">{targetRole}</span> — {progressPct.toFixed(0)}% concluído
        </p>

        {/* Skills chips */}
        {milestone.skills.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {milestone.skills.slice(0, 3).map((s) => (
              <span key={s} className="text-[10px] px-2 py-0.5 rounded-full bg-surface-high border border-border text-text-muted">
                {s}
              </span>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2 mb-3 text-xs text-text-muted">
          <Clock size={11} />
          <span>~{milestone.estimated_hours}h estimadas</span>
        </div>

        <button
          onClick={onStart}
          className="w-full py-2.5 rounded-lg text-surface text-xs font-semibold transition-all flex items-center justify-center gap-2 shadow-accent-sm hover:shadow-accent-md"
          style={{ background: "linear-gradient(135deg,#00e87a,#00b85e)" }}
          aria-label="Iniciar milestone recomendado"
        >
          Iniciar agora
          <ArrowRight size={13} />
        </button>
      </div>
    </div>
  );
}
