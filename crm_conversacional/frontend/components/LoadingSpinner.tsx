import { cn } from "@/lib/utils";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
  className?: string;
}

const SIZES = {
  sm: "h-4 w-4 border-2",
  md: "h-8 w-8 border-2",
  lg: "h-12 w-12 border-4",
};

export function LoadingSpinner({
  size = "md",
  label = "Carregando...",
  className,
}: LoadingSpinnerProps) {
  return (
    <div role="status" className={cn("flex flex-col items-center gap-3", className)}>
      <span
        aria-hidden="true"
        className={cn(
          "animate-spin rounded-full border-brand-500 border-t-transparent",
          SIZES[size],
        )}
      />
      <span className="sr-only">{label}</span>
    </div>
  );
}

/** Spinner centralizado ocupando a área toda — usado em telas de carregamento. */
export function FullPageLoader({ label }: { label?: string }) {
  return (
    <div className="flex min-h-[60vh] w-full items-center justify-center">
      <LoadingSpinner size="lg" label={label} />
    </div>
  );
}

export default LoadingSpinner;
