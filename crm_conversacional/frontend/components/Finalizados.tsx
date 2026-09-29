"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/Button";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { messageFrom } from "@/hooks/useAgents";
import { buscarFinalizados } from "@/lib/finalizados";
import { formatarTelefone } from "@/lib/telefone";
import { cn } from "@/lib/utils";
import type { FinalizadosResponse, GrupoFinalizado, MotivoDeFim } from "@/types";

const PERIODOS = [
  { dias: 30, rotulo: "30 dias" },
  { dias: 90, rotulo: "90 dias" },
  { dias: 365, rotulo: "1 ano" },
];

/**
 * O que cada motivo diz ao escritório.
 *
 * A explicação fica na tela, e não só no código, porque cada coluna aqui pede
 * uma ação diferente — e uma coluna cujo nome não diz o que fazer com ela
 * acaba virando só um lugar onde caso morre.
 */
const EXPLICACAO: Record<MotivoDeFim, string> = {
  abaixo_do_piso: "O piso comercial funcionando. Nada a corrigir.",
  fora_da_area: "Gente chegando pelo anúncio errado — é sinal de marketing, não de atendimento.",
  sem_retorno: "Pararam de responder antes de a triagem terminar. É aqui que se perde quem tinha caso.",
  outro: "O parecer não conseguiu dimensionar. Vale um olho humano.",
};

const TOM: Record<MotivoDeFim, string> = {
  abaixo_do_piso: "bg-surface-muted text-fg-soft",
  fora_da_area: "bg-amber-100 text-amber-900 dark:bg-amber-950/60 dark:text-amber-100",
  sem_retorno: "bg-red-100 text-red-900 dark:bg-red-950/60 dark:text-red-100",
  outro: "bg-surface-muted text-fg-soft",
};

function emReais(valor: number): string {
  return valor.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  });
}

function Coluna({ grupo }: { grupo: GrupoFinalizado }) {
  return (
    <section className="flex min-w-0 flex-col rounded-xl border border-surface-border bg-surface-muted/40">
      <header className={cn("rounded-t-xl px-4 py-2.5", TOM[grupo.motivo])}>
        <h2 className="flex items-baseline justify-between gap-2 text-sm font-medium">
          <span>{grupo.rotulo}</span>
          <span className="tabular-nums">{grupo.total}</span>
        </h2>
      </header>

      <p className="px-4 py-2 text-xs text-fg-muted">{EXPLICACAO[grupo.motivo]}</p>

      <div className="flex flex-col gap-2 px-3 pb-3">
        {grupo.casos.length === 0 ? (
          <p className="py-6 text-center text-xs text-fg-faint">Nenhum caso aqui</p>
        ) : (
          grupo.casos.map((caso) => (
            <article
              key={caso.lead_id}
              className="rounded-lg border border-surface-border bg-surface p-3"
            >
              <h3 className="truncate text-sm font-medium text-fg">
                {caso.nome ?? "Sem nome"}
              </h3>
              <p className="truncate text-xs text-fg-muted">
                {formatarTelefone(caso.phone_number)}
              </p>

              {caso.empresa_ou_resumo && (
                <p className="mt-1 line-clamp-2 text-xs text-fg-soft">
                  {caso.empresa_ou_resumo}
                </p>
              )}

              {caso.valor_estimado_min !== null && caso.valor_estimado_max !== null && (
                <p className="mt-1 text-xs tabular-nums text-fg-soft">
                  {emReais(caso.valor_estimado_min)}–{emReais(caso.valor_estimado_max)}
                </p>
              )}

              {/* Quem arquivou só aparece quando foi gente: "arquivado pela
                  triagem" em todo card seria repetir o óbvio em 90% deles. */}
              {caso.arquivado_por && (
                <p className="mt-1 text-xs text-fg-faint">
                  arquivado por {caso.arquivado_por}
                </p>
              )}
            </article>
          ))
        )}
      </div>
    </section>
  );
}

/**
 * Os casos que acabaram, separados pelo motivo.
 *
 * Tudo caía em "Arquivado" e o board não dizia por quê. Mas "não era da nossa
 * área" e "o caso é pequeno demais" pedem coisas opostas do escritório: o
 * primeiro é volume de marketing errado, o segundo é o piso comercial
 * funcionando como devia.
 */
export function Finalizados({ agentId }: { agentId: string }) {
  const [dias, setDias] = useState(90);
  const [dados, setDados] = useState<FinalizadosResponse | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setDados(await buscarFinalizados(agentId, dias));
      setErro(null);
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível carregar os casos finalizados."));
    } finally {
      setCarregando(false);
    }
  }, [agentId, dias]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2" role="group" aria-label="Período">
        {PERIODOS.map((opcao) => (
          <button
            key={opcao.dias}
            type="button"
            onClick={() => setDias(opcao.dias)}
            aria-pressed={dias === opcao.dias}
            className={
              dias === opcao.dias
                ? "rounded-full bg-ink-900 px-3 py-1.5 text-sm font-medium text-white dark:bg-ink-100 dark:text-ink-950"
                : "rounded-full border border-surface-border bg-surface px-3 py-1.5 text-sm text-fg-soft hover:bg-surface-muted"
            }
          >
            {opcao.rotulo}
          </button>
        ))}

        {dados && (
          <p className="ml-auto text-sm text-fg-muted" role="status">
            {dados.total === 1 ? "1 caso finalizado" : `${dados.total} casos finalizados`}
          </p>
        )}
      </div>

      {erro ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-5 dark:border-red-900 dark:bg-red-950/40">
          <p role="alert" className="text-sm text-red-700 dark:text-red-200">
            {erro}
          </p>
          <Button variant="secondary" className="mt-4" onClick={() => void carregar()}>
            Tentar novamente
          </Button>
        </div>
      ) : carregando && !dados ? (
        <div className="flex justify-center py-16">
          <LoadingSpinner label="Carregando..." />
        </div>
      ) : (
        // As colunas aparecem mesmo vazias: um board sem colunas parece
        // defeito, e o escritório precisa ver que "abaixo do piso" existe
        // como destino antes de haver um caso lá.
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {dados?.grupos.map((grupo) => (
            <Coluna key={grupo.motivo} grupo={grupo} />
          ))}
        </div>
      )}
    </div>
  );
}

export default Finalizados;
