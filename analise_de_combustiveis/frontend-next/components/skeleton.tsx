import type { CSSProperties } from "react";

import { cn } from "@/lib/utils";

export function Skeleton({ className, style }: { className?: string; style?: CSSProperties }) {
  return (
    <div className={cn("animate-pulse rounded-lg bg-surface", className)} style={style} />
  );
}

export function StatCardSkeleton() {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-line bg-surface p-5 pl-7">
      {/* Left accent placeholder */}
      <div className="absolute inset-y-0 left-0 w-[2px] animate-pulse bg-line" />

      {/* Label row */}
      <div className="mb-1 flex items-center gap-2">
        <Skeleton className="h-2.5 w-20" />
        <Skeleton className="h-4 w-16 rounded" />
      </div>

      {/* Hint */}
      <Skeleton className="mb-3 h-3 w-28" />

      {/* Value */}
      <Skeleton className="h-10 w-36" />
    </div>
  );
}

export function ChartSkeleton({ height = "h-64", className }: { height?: string; className?: string }) {
  return (
    <div className={cn("relative overflow-hidden rounded-2xl border border-line bg-surface p-5", height, className)}>
      {/* Title area */}
      <Skeleton className="mb-1 h-3 w-32" />
      <Skeleton className="mb-6 h-3 w-20" />

      {/* Bar chart skeleton */}
      <div className="flex h-32 items-end gap-2">
        {[40, 70, 55, 85, 60, 75, 90, 65, 80, 50, 70, 60].map((h, i) => (
          <Skeleton
            key={i}
            className="flex-1 rounded-t-sm rounded-b-none"
            style={{ height: `${h}%` }}
          />
        ))}
      </div>
    </div>
  );
}
