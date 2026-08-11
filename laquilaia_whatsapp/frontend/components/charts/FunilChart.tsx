"use client";

import { FUNNEL_RAMP } from "./theme";
import type { LeadDistribution } from "@/types";

interface FunilChartProps {
  distribuicao: LeadDistribution;
}

/** As etapas na ordem do funil — a ordem é o significado aqui. */
const ETAPAS: Array<{ chave: keyof LeadDistribution; rotulo: string }> = [
  { chave: "novo", rotulo: "Novo lead" },
  { chave: "em_qualificacao", rotulo: "Em qualificação" },
  { chave: "qualificado", rotulo: "Qualificado" },
  { chave: "agendado", rotulo: "Agendado" },
  { chave: "arquivado", rotulo: "Arquivado" },
];

/**
 * Distribuição dos leads pelo funil.
 *
 * Barras horizontais, e não pizza: os rótulos são longos e comparar
 * comprimentos é mais preciso que comparar ângulos. A cor é uma rampa ordinal
 * de um hue só — as etapas têm ordem, então mais adiante no funil é mais
 * escuro, em vez de cinco cores sem relação entre si.
 *
 * Cada barra é rotulada com o número, então a leitura nunca depende só da cor.
 */
export function FunilChart({ distribuicao }: FunilChartProps) {
  const rampa = FUNNEL_RAMP.light;
  const maior = Math.max(...ETAPAS.map((e) => distribuicao[e.chave] as number), 1);

  return (
    <figure className="rounded-xl border border-surface-border bg-white p-5">
      <figcaption className="mb-4">
        <h3 className="text-sm font-medium text-gray-900">Leads por etapa do funil</h3>
        <p className="mt-0.5 text-xs text-gray-500">
          Situação atual — {distribuicao.total}{" "}
          {distribuicao.total === 1 ? "lead" : "leads"} no total.
        </p>
      </figcaption>

      <ul className="flex flex-col gap-3">
        {ETAPAS.map((etapa, indice) => {
          const valor = distribuicao[etapa.chave] as number;
          const largura = (valor / maior) * 100;

          return (
            <li key={etapa.chave} className="flex items-center gap-3">
              <span className="w-32 shrink-0 text-xs text-gray-600">{etapa.rotulo}</span>

              <div className="h-6 flex-1 overflow-hidden rounded bg-surface-muted">
                <div
                  className="h-full rounded"
                  style={{
                    width: `${Math.max(largura, valor > 0 ? 2 : 0)}%`,
                    backgroundColor: rampa[indice],
                  }}
                  role="img"
                  aria-label={`${etapa.rotulo}: ${valor}`}
                />
              </div>

              <span className="w-10 shrink-0 text-right text-sm font-medium tabular-nums text-gray-900">
                {valor}
              </span>
            </li>
          );
        })}
      </ul>
    </figure>
  );
}

export default FunilChart;
