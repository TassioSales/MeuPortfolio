"use client";

import { Sparkles, Radar, Waypoints, BrainCircuit } from "lucide-react";

import { cn } from "@/lib/utils";

const iconMap = {
  radar: Radar,
  waypoints: Waypoints,
  sparkles: Sparkles,
  brain: BrainCircuit,
};

export function PageHero({
  kicker,
  title,
  description,
  tone,
  badge,
  stats,
}: {
  kicker: string;
  title: string;
  description: string;
  tone: "teal" | "amber" | "coral" | "blue";
  badge: string;
  stats: Array<{ label: string; value: string; icon: keyof typeof iconMap }>;
}) {
  const toneMap = {
    teal:  { border: "border-emerald/20", accent: "bg-emerald/10 text-emerald border-emerald/20" },
    amber: { border: "border-amber/20",   accent: "bg-amber/10 text-amber border-amber/20" },
    coral: { border: "border-rose/20",    accent: "bg-rose/10 text-rose border-rose/20" },
    blue:  { border: "border-blue/20",    accent: "bg-blue/10 text-blue border-blue/20" },
  }[tone];

  return (
    <section
      className={cn(
        "relative overflow-hidden rounded-2xl border bg-surface p-6 lg:p-8",
        toneMap.border,
      )}
    >
      {/* Subtle ambient glow */}
      <div className="pointer-events-none absolute inset-0 rounded-2xl bg-[radial-gradient(ellipse_60%_50%_at_top_left,rgba(245,158,11,0.06),transparent)]" />

      <div className="relative grid gap-8 xl:grid-cols-[1.4fr_0.6fr]">
        {/* Left: title + description */}
        <div className="space-y-4">
          <div className={cn("inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest", toneMap.accent)}>
            <Sparkles className="h-3 w-3" />
            {kicker}
          </div>
          <div>
            <h2 className="font-display text-3xl font-bold leading-tight text-text lg:text-4xl">{title}</h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-muted">{description}</p>
          </div>
        </div>

        {/* Right: badge + stats */}
        <div className="flex flex-col gap-2.5 rounded-xl border border-line bg-surface2 p-4">
          <div className={cn("inline-flex w-fit items-center rounded-full border px-2.5 py-1 text-[9px] font-semibold uppercase tracking-widest", toneMap.accent)}>
            {badge}
          </div>
          <div className="grid gap-2">
            {stats.map((item) => {
              const Icon = iconMap[item.icon];
              return (
                <div key={item.label} className="flex items-center justify-between rounded-lg border border-line bg-surface p-3">
                  <div className="flex items-center gap-2.5">
                    <div className="rounded-lg border border-line bg-surface2 p-1.5">
                      <Icon className="h-3.5 w-3.5 text-muted" />
                    </div>
                    <span className="text-xs text-muted">{item.label}</span>
                  </div>
                  <p className="font-mono text-sm font-semibold text-text">{item.value}</p>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
