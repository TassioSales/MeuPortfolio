import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  hint,
  trend,
}: {
  label: string;
  value: string;
  hint: string;
  trend?: "up" | "down" | "flat";
}) {
  const Icon = trend === "up" ? ArrowUpRight : trend === "down" ? ArrowDownRight : Minus;
  const toneClass =
    trend === "up"
      ? "from-coral/18 via-coral/6 to-white/[0.02] text-coral"
      : trend === "down"
        ? "from-accent/18 via-accent/6 to-white/[0.02] text-accent"
        : "from-sky/14 via-sky/5 to-white/[0.02] text-sky";
  const trendLabel = trend === "up" ? "Pressao" : trend === "down" ? "Alivio" : "Estavel";

  return (
    <Card className="group relative overflow-hidden border-white/10 bg-[linear-gradient(155deg,rgba(255,255,255,0.08),rgba(255,255,255,0.02))]">
      <div className={cn("absolute inset-x-0 top-0 h-24 bg-gradient-to-r blur-2xl", toneClass)} />
      <div className="relative flex h-full flex-col justify-between gap-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[10px] uppercase font-bold tracking-[0.3em] text-mist/60">{label}</p>
            <p className="mt-3 text-xs font-medium text-mist/60">{hint}</p>
          </div>
          <div className={cn(
            "flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-black/20",
            trend === "up" ? "text-coral" : trend === "down" ? "text-accent" : "text-sky",
          )}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
        <div className="relative">
          <div className="flex items-end justify-between gap-3">
            <p className="font-display text-4xl font-bold tracking-tight text-white lg:text-[2.6rem]">{value}</p>
            <span className={cn("rounded-full border px-3 py-1 text-[10px] font-bold uppercase tracking-[0.24em]", trend === "up" ? "border-coral/25 bg-coral/10 text-coral" : trend === "down" ? "border-accent/25 bg-accent/10 text-accent" : "border-sky/25 bg-sky/10 text-sky")}>
              {trendLabel}
            </span>
          </div>
        </div>
        <div className={cn(
          "rounded-[1.25rem] border border-white/8 px-4 py-3 text-xs font-medium text-white/68",
          "bg-black/15"
        )}>
          {trend === "up" ? "Movimento de alta no recorte recente." : trend === "down" ? "Sinal de acomodacao no recorte recente." : "Sem ruptura material no ultimo ponto."}
        </div>
      </div>
    </Card>
  );
}
