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
  const toneClasses = {
    teal: "from-[#0f2330] via-[#102f37] to-[#101a24] border-[#36d6a7]/20",
    amber: "from-[#35210f] via-[#251b18] to-[#17151d] border-[#f4b860]/20",
    coral: "from-[#30161a] via-[#221823] to-[#141920] border-[#ff7b72]/20",
    blue: "from-[#101c31] via-[#18284a] to-[#101721] border-[#6bb8ff]/20",
  }[tone];

  return (
    <section
      className={cn(
        "relative overflow-hidden rounded-[2.2rem] border bg-gradient-to-br p-6 shadow-float lg:p-8",
        toneClasses,
      )}
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.22),transparent_22%),radial-gradient(circle_at_bottom_left,rgba(255,255,255,0.12),transparent_24%),linear-gradient(120deg,transparent,rgba(255,255,255,0.03),transparent)]" />
      <div className="absolute -right-10 top-10 h-48 w-48 rounded-full bg-white/10 blur-3xl" />
      <div className="relative grid gap-8 xl:grid-cols-[1.25fr_0.75fr]">
        <div className="space-y-5">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/8 px-4 py-2 text-[11px] uppercase tracking-[0.3em] text-white/75">
            <Sparkles className="h-3.5 w-3.5" />
            {kicker}
          </div>
          <div>
            <h2 className="max-w-4xl font-display text-4xl leading-tight text-white lg:text-[3.8rem]">{title}</h2>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-white/70 lg:text-base">{description}</p>
          </div>
        </div>
        <div className="grid gap-3 rounded-[1.9rem] border border-white/10 bg-black/20 p-4 backdrop-blur">
          <div className="inline-flex items-center rounded-full bg-white/10 px-3 py-1 text-xs uppercase tracking-[0.28em] text-white/70">
            {badge}
          </div>
          <div className="grid gap-3">
            {stats.map((item) => {
              const Icon = iconMap[item.icon];
              return (
                <div key={item.label} className="rounded-[1.35rem] border border-white/10 bg-[linear-gradient(135deg,rgba(255,255,255,0.09),rgba(255,255,255,0.03))] p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-white/65">{item.label}</span>
                    <div className="rounded-xl border border-white/10 bg-white/10 p-2">
                      <Icon className="h-4 w-4 text-white/70" />
                    </div>
                  </div>
                  <p className="mt-3 font-display text-2xl text-white">{item.value}</p>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
