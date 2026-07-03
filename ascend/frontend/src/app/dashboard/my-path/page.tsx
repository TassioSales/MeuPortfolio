"use client";
import { useEffect } from "react";
import { motion } from "framer-motion";
import { CheckCircle, Circle, Clock, ChevronRight, ExternalLink, Map } from "lucide-react";
import { clsx } from "clsx";
import { useCareerStore } from "@/lib/stores/careerStore";
import { toast } from "@/lib/toast";
import { PageTransition } from "@/components/layout/PageTransition";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonCard } from "@/components/ui/Skeleton";

const STATUS_ICONS = {
  done: <CheckCircle size={18} className="text-accent" />,
  in_progress: <Clock size={18} className="text-yellow-400" />,
  not_started: <Circle size={18} className="text-text-muted" />,
};

const STATUS_LABELS = { done: "Concluído", in_progress: "Em progresso", not_started: "Não iniciado" };

export default function MyPathPage() {
  const { roadmap, loading, fetchRoadmap, updateMilestone } = useCareerStore();

  useEffect(() => { fetchRoadmap(); }, []);

  async function handleUpdate(index: number, status: string) {
    try {
      await updateMilestone(index, status);
      toast.success(status === "done" ? "Milestone concluído!" : "Milestone iniciado!");
    } catch {
      toast.error("Erro ao atualizar milestone.");
    }
  }

  return (
    <PageTransition>
      <div className="p-6 max-w-3xl">
        <h1 className="text-xl font-bold text-text-primary mb-1">Meu Caminho</h1>
        <p className="text-text-muted text-sm mb-6">Seu roadmap personalizado gerado pela IA</p>

        {loading && (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} lines={3} />)}
          </div>
        )}

        {!loading && !roadmap?.milestones?.length && (
          <EmptyState
            icon={<Map size={20} />}
            title="Roadmap ainda sendo gerado"
            description="Sua trilha de carreira está sendo personalizada pela IA. Aguarde alguns instantes e atualize a página."
            action={
              <button
                onClick={() => fetchRoadmap()}
                className="px-4 py-2 bg-accent text-surface text-sm font-semibold rounded-lg hover:bg-accent-dim transition-colors"
              >
                Atualizar
              </button>
            }
          />
        )}

        <div className="space-y-3">
          {roadmap?.milestones.map((ms, i) => {
            const status =
              i < roadmap.current_milestone_index
                ? "done"
                : i === roadmap.current_milestone_index
                ? "in_progress"
                : "not_started";

            return (
              <motion.div
                key={ms.index}
                initial={{ opacity: 0, x: -16 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.07 }}
                className={clsx(
                  "bg-surface-raised border rounded-xl p-4 transition-all",
                  status === "in_progress" ? "border-accent/40" : "border-border"
                )}
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5">{STATUS_ICONS[status]}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs text-text-muted">Passo {i + 1}</span>
                      <span className={clsx(
                        "text-xs px-2 py-0.5 rounded-full",
                        status === "done" ? "bg-accent/10 text-accent" :
                        status === "in_progress" ? "bg-yellow-400/10 text-yellow-400" :
                        "bg-surface-high text-text-muted"
                      )}>
                        {STATUS_LABELS[status]}
                      </span>
                    </div>
                    <h3 className="font-semibold text-text-primary">{ms.title}</h3>
                    <p className="text-sm text-text-muted mt-0.5 mb-2">{ms.description}</p>

                    <div className="flex flex-wrap gap-1.5 mb-3">
                      {ms.skills.map((s) => (
                        <span key={s} className="text-xs px-2 py-0.5 bg-surface-high border border-border rounded-full text-text-muted">
                          {s}
                        </span>
                      ))}
                    </div>

                    <div className="flex items-center gap-4">
                      <span className="text-xs text-text-muted flex items-center gap-1">
                        <Clock size={11} /> ~{ms.estimated_hours}h estimadas
                      </span>
                      {ms.resources?.slice(0, 2).map((r) => (
                        <span key={r} className="text-xs text-accent flex items-center gap-1">
                          <ExternalLink size={10} /> {r}
                        </span>
                      ))}
                    </div>
                  </div>

                  {status !== "done" && (
                    <button
                      onClick={() => handleUpdate(ms.index, status === "in_progress" ? "done" : "in_progress")}
                      aria-label={status === "in_progress" ? "Marcar como concluído" : "Iniciar milestone"}
                      className="shrink-0 px-3 py-1.5 bg-accent text-surface text-xs font-semibold rounded-lg hover:bg-accent-dim transition-colors flex items-center gap-1"
                    >
                      {status === "in_progress" ? "Marcar concluído" : "Iniciar"}
                      <ChevronRight size={12} />
                    </button>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </PageTransition>
  );
}
