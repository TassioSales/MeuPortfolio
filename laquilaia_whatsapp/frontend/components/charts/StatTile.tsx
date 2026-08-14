import { cn } from "@/lib/utils";

interface StatTileProps {
  label: string;
  value: string;
  /** Contexto curto abaixo do número (período, base de cálculo). */
  hint?: string;
  /** Variação vs período anterior, em pontos percentuais ou %. */
  delta?: number | null;
  /** Para métricas onde cair é bom (tempo de resposta). */
  lowerIsBetter?: boolean;
}

/**
 * Um número de destaque.
 *
 * Um valor isolado é um stat tile, não um gráfico de uma barra só — o número
 * lido direto é mais rápido que uma barra sem nada para comparar.
 */
export function StatTile({
  label,
  value,
  hint,
  delta = null,
  lowerIsBetter = false,
}: StatTileProps) {
  const hasDelta = delta !== null && Number.isFinite(delta) && delta !== 0;
  const isGood = hasDelta ? (lowerIsBetter ? delta! < 0 : delta! > 0) : false;

  return (
    <div className="rounded-xl border border-surface-border bg-surface p-5">
      <p className="text-sm text-fg-muted">{label}</p>
      <p className="mt-1 text-3xl font-semibold tabular-nums text-fg">{value}</p>

      <div className="mt-1 flex items-center gap-2">
        {hasDelta && (
          <span
            className={cn(
              "inline-flex items-center gap-1 text-xs font-medium",
              // Ícone + sinal junto da cor: a variação nunca é só cor.
              isGood ? "text-green-700 dark:text-green-200" : "text-red-700 dark:text-red-200",
            )}
          >
            <span aria-hidden="true">{delta! > 0 ? "▲" : "▼"}</span>
            {Math.abs(delta!).toFixed(1)}%
          </span>
        )}
        {hint && <span className="text-xs text-fg-muted">{hint}</span>}
      </div>
    </div>
  );
}

export default StatTile;
