import { ArrowDown, ArrowUp, Minus } from "lucide-react";

import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string;
  hint: string;
  trend?: "up" | "down" | "flat";
  delta?: number;
  size?: "default" | "sm";
}

export function StatCard({ label, value, hint, trend = "flat", delta, size = "default" }: StatCardProps) {
  const isUp = trend === "up";
  const isDown = trend === "down";

  const accentBar = isUp ? "bg-rose" : isDown ? "bg-emerald" : "bg-muted";
  const valueColor = isUp ? "text-rose" : isDown ? "text-emerald" : "text-white";
  const valueSize = size === "sm" ? "text-2xl" : "text-[2.4rem]";

  const deltaPositive = delta !== undefined && delta > 0;
  const deltaNegative = delta !== undefined && delta < 0;
  const deltaBadgeClass = deltaPositive
    ? "text-rose bg-rose/10 border-rose/20"
    : deltaNegative
      ? "text-emerald bg-emerald/10 border-emerald/20"
      : "text-muted bg-muted/10 border-muted/20";

  const TrendIcon = isUp ? ArrowUp : isDown ? ArrowDown : Minus;
  const trendIconColor = isUp ? "text-rose" : isDown ? "text-emerald" : "text-muted";

  return (
    <div className="relative overflow-hidden rounded-2xl border border-line bg-surface p-5 pl-7">
      {/* Left accent bar */}
      <div className={cn("absolute inset-y-0 left-0 w-[2px]", accentBar)} />

      {/* Trend icon — top right */}
      <div className={cn("absolute right-4 top-4", trendIconColor)}>
        <TrendIcon size={16} strokeWidth={2.5} />
      </div>

      {/* Label + delta badge */}
      <div className="mb-1 flex items-center gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-muted">
          {label}
        </span>
        {delta !== undefined && (
          <span className={cn("rounded border px-1.5 py-0.5 text-[9px] font-semibold tabular-nums", deltaBadgeClass)}>
            {deltaPositive ? "+" : ""}{delta.toFixed(1)}% semana
          </span>
        )}
      </div>

      {/* Hint */}
      <p className="mb-3 text-xs text-muted">{hint}</p>

      {/* Value — DM Mono, trading-terminal style */}
      <p className={cn("font-mono font-medium leading-none tabular-nums", valueSize, valueColor)}>
        {value}
      </p>
    </div>
  );
}
