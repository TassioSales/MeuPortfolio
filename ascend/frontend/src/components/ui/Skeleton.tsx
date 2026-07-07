import { clsx } from "clsx";

interface Props {
  className?: string;
  lines?: number;
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={clsx(
        "animate-pulse rounded-lg bg-surface-high",
        className
      )}
    />
  );
}

export function SkeletonCard({ lines = 3 }: Props) {
  return (
    <div className="bg-surface-raised border border-border rounded-xl p-4 space-y-2">
      <Skeleton className="h-4 w-1/3" />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className={clsx("h-3", i === lines - 1 ? "w-2/3" : "w-full")} />
      ))}
    </div>
  );
}
