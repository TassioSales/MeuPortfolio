"use client";
import { useEffect } from "react";
import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { BarChart2, Clock, Activity, TrendingUp, Target, CheckCircle } from "lucide-react";
import { useCareerStore } from "@/lib/stores/careerStore";
import { PageTransition } from "@/components/layout/PageTransition";
import { SkeletonCard } from "@/components/ui/Skeleton";
import type { AnalyticsSummary } from "@/lib/api";

function CircleGauge({ pct }: { pct: number }) {
  const R = 52;
  const C = 2 * Math.PI * R;
  const offset = C - (pct / 100) * C;
  return (
    <svg width="148" height="148" viewBox="0 0 148 148">
      <defs>
        <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#00b85e" />
          <stop offset="100%" stopColor="#00e87a" />
        </linearGradient>
      </defs>
      {/* Track */}
      <circle cx="74" cy="74" r={R} fill="none" stroke="#1e2536" strokeWidth="13" />
      {/* Progress */}
      <motion.circle
        cx="74" cy="74" r={R}
        fill="none"
        stroke="url(#gaugeGrad)"
        strokeWidth="13"
        strokeLinecap="round"
        strokeDasharray={C}
        initial={{ strokeDashoffset: C }}
        animate={{ strokeDashoffset: offset }}
        transition={{ duration: 1.5, ease: "easeOut" }}
        style={{ transform: "rotate(-90deg)", transformOrigin: "74px 74px" }}
      />
      <text x="74" y="70" textAnchor="middle" fill="#f0f4ff" fontSize="24" fontWeight="700">
        {pct.toFixed(0)}%
      </text>
      <text x="74" y="88" textAnchor="middle" fill="#6b7594" fontSize="11">
        concluído
      </text>
    </svg>
  );
}

function MetricCard({
  icon: Icon, label, value, color, bg, index,
}: {
  icon: React.ElementType; label: string; value: string;
  color: string; bg: string; index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.07, duration: 0.3 }}
      className="bg-surface-card border border-border rounded-2xl p-5 shadow-card flex flex-col gap-4"
    >
      <div className={`w-10 h-10 rounded-xl border flex items-center justify-center ${bg}`}>
        <Icon size={17} className={color} />
      </div>
      <div>
        <p className="text-xs text-text-muted mb-1 leading-none">{label}</p>
        <p className={`text-2xl font-bold leading-tight ${color}`}>{value}</p>
      </div>
    </motion.div>
  );
}

function buildMetrics(a: AnalyticsSummary) {
  return [
    {
      icon: Clock,
      label: "Horas estudadas",
      value: `${a.total_hours_studied}h`,
      color: "text-accent",
      bg: "bg-accent/10 border-accent/20",
    },
    {
      icon: Activity,
      label: "Média por milestone",
      value: `${a.avg_hours_per_milestone}h`,
      color: "text-blue-400",
      bg: "bg-blue-400/10 border-blue-400/20",
    },
    {
      icon: TrendingUp,
      label: "Horas restantes",
      value: `~${a.estimated_hours_remaining}h`,
      color: "text-amber-400",
      bg: "bg-amber-400/10 border-amber-400/20",
    },
    {
      icon: Target,
      label: "Previsão de conclusão",
      value: a.estimated_completion_date
        ? new Date(a.estimated_completion_date).toLocaleDateString("pt-BR", { month: "short", year: "numeric" })
        : "—",
      color: "text-violet-400",
      bg: "bg-violet-400/10 border-violet-400/20",
    },
  ];
}

const BAR_DATA = (a: AnalyticsSummary) => [
  { name: "Concluídos", value: a.completed, color: "#00e87a" },
  { name: "Em progresso", value: a.in_progress, color: "#facc15" },
  { name: "Não iniciados", value: a.not_started, color: "#353c52" },
];

export default function AnalyticsPage() {
  const { analytics, fetchAnalytics } = useCareerStore();

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const barData = analytics ? BAR_DATA(analytics) : [];

  return (
    <PageTransition>
      <div className="h-screen overflow-y-auto">
        <div className="p-6 max-w-4xl">

          {/* Header */}
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
              <BarChart2 size={18} className="text-accent" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-text-primary">Analytics</h1>
              {analytics && (
                <p className="text-sm text-text-muted">
                  {analytics.current_role}
                  <span className="mx-1.5 text-text-dim">→</span>
                  {analytics.target_role}
                </p>
              )}
            </div>
          </div>

          {/* Skeleton */}
          {!analytics && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
            </div>
          )}

          {analytics && (
            <div className="space-y-4">

              {/* Metric cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {buildMetrics(analytics).map((m, i) => (
                  <MetricCard key={m.label} {...m} index={i} />
                ))}
              </div>

              {/* Charts row */}
              <div className="grid grid-cols-5 gap-4">

                {/* Circle gauge */}
                <motion.div
                  initial={{ opacity: 0, scale: 0.93 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.32 }}
                  className="col-span-2 bg-surface-card border border-border rounded-2xl p-6 shadow-card flex flex-col"
                >
                  <p className="text-sm font-semibold text-text-primary mb-4">Progresso geral</p>
                  <div className="flex flex-col items-center justify-center flex-1 gap-4">
                    <CircleGauge pct={analytics.progress_pct} />
                    <div className="flex gap-6 text-center">
                      <div>
                        <p className="text-xl font-bold text-accent">{analytics.completed}</p>
                        <p className="text-[11px] text-text-muted mt-0.5">concluídos</p>
                      </div>
                      <div className="w-px bg-border" />
                      <div>
                        <p className="text-xl font-bold text-yellow-400">{analytics.in_progress}</p>
                        <p className="text-[11px] text-text-muted mt-0.5">em progresso</p>
                      </div>
                      <div className="w-px bg-border" />
                      <div>
                        <p className="text-xl font-bold text-text-muted">{analytics.not_started}</p>
                        <p className="text-[11px] text-text-muted mt-0.5">restantes</p>
                      </div>
                    </div>
                  </div>
                </motion.div>

                {/* Bar chart */}
                <motion.div
                  initial={{ opacity: 0, scale: 0.93 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.4 }}
                  className="col-span-3 bg-surface-card border border-border rounded-2xl p-6 shadow-card"
                >
                  <p className="text-sm font-semibold text-text-primary mb-4">Milestones por status</p>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={barData} barSize={48}>
                      <XAxis
                        dataKey="name"
                        tick={{ fontSize: 11, fill: "#6b7594" }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis hide allowDecimals={false} />
                      <Tooltip
                        contentStyle={{
                          background: "#1a2030",
                          border: "1px solid #252d40",
                          borderRadius: 10,
                          boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
                        }}
                        labelStyle={{ color: "#f0f4ff", fontSize: 12, fontWeight: 600 }}
                        itemStyle={{ color: "#a0a8c0", fontSize: 12 }}
                        cursor={{ fill: "rgba(255,255,255,0.03)" }}
                      />
                      <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                        {barData.map((entry, i) => (
                          <Cell key={i} fill={entry.color} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </motion.div>
              </div>

              {/* Milestone strip */}
              <motion.div
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="bg-surface-card border border-border rounded-2xl p-5 shadow-card"
              >
                <div className="flex items-center justify-between mb-4">
                  <p className="text-sm font-semibold text-text-primary">Trilha de milestones</p>
                  <div className="flex items-center gap-5 text-[11px] text-text-muted">
                    <span className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-accent inline-block" />
                      Concluído
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-yellow-400 inline-block" />
                      Em progresso
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-sm bg-surface-high border border-border inline-block" />
                      Não iniciado
                    </span>
                  </div>
                </div>

                <div className="flex gap-2">
                  {Array.from({ length: analytics.total_milestones }).map((_, i) => {
                    const done = i < analytics.completed;
                    const active = i === analytics.completed;
                    return (
                      <div key={i} className="flex-1 flex flex-col items-center gap-1.5">
                        <div className="relative w-full">
                          <div
                            className={`h-2.5 w-full rounded-full transition-all ${
                              done ? "bg-accent" : active ? "bg-yellow-400" : "bg-surface-high border border-border"
                            }`}
                          />
                          {active && (
                            <motion.div
                              className="absolute inset-0 rounded-full bg-yellow-400/30"
                              animate={{ opacity: [0.3, 0.7, 0.3] }}
                              transition={{ repeat: Infinity, duration: 1.8 }}
                            />
                          )}
                          {done && (
                            <div className="absolute inset-0 flex items-center justify-center">
                              <CheckCircle size={8} className="text-surface" />
                            </div>
                          )}
                        </div>
                        <span className="text-[10px] font-medium text-text-dim">{i + 1}</span>
                      </div>
                    );
                  })}
                </div>
              </motion.div>

            </div>
          )}
        </div>
      </div>
    </PageTransition>
  );
}
