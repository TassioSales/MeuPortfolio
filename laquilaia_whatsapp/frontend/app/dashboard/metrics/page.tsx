"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { FullPageLoader } from "@/components/LoadingSpinner";
import { AtendimentosChart } from "@/components/charts/AtendimentosChart";
import { FunilChart } from "@/components/charts/FunilChart";
import { StatTile } from "@/components/charts/StatTile";
import { formatSeconds } from "@/components/charts/theme";
import { useAgents } from "@/hooks/useAgents";
import { useMetrics } from "@/hooks/useMetrics";
import type { MetricsPeriod } from "@/types";

const PERIODOS: Array<{ valor: MetricsPeriod; rotulo: string }> = [
  { valor: "day", rotulo: "Hoje" },
  { valor: "week", rotulo: "Semana" },
  { valor: "month", rotulo: "Mês" },
];

function Painel({ agentId }: { agentId: string }) {
  const [period, setPeriod] = useState<MetricsPeriod>("week");
  const { summary, responseTime, pontos, isLoading, error, reload } = useMetrics(
    agentId,
    period,
  );

  return (
    <div>
      {/* Filtros em uma linha acima dos gráficos. */}
      <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Período">
        {PERIODOS.map((opcao) => (
          <button
            key={opcao.valor}
            type="button"
            onClick={() => setPeriod(opcao.valor)}
            aria-pressed={period === opcao.valor}
            className={
              period === opcao.valor
                ? "rounded-full bg-ink-900 px-3 py-1.5 text-sm font-medium text-white"
                : "rounded-full border border-surface-border bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-surface-muted"
            }
          >
            {opcao.rotulo}
          </button>
        ))}
      </div>

      {isLoading ? (
        <FullPageLoader label="Carregando métricas..." />
      ) : error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-5">
          <p role="alert" className="text-sm text-red-700">
            {error}
          </p>
          <Button variant="secondary" className="mt-4" onClick={() => void reload()}>
            Tentar novamente
          </Button>
        </div>
      ) : (
        summary && (
          <div className="flex flex-col gap-6">
            <section
              aria-label="Indicadores"
              className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
            >
              <StatTile
                label="Atendimentos"
                value={String(summary.atendimentos_totais)}
                hint="no período"
              />
              <StatTile
                label="Taxa de qualificação"
                value={`${summary.taxa_qualificacao.toFixed(1)}%`}
                hint={`${summary.leads_por_status.qualificado} de ${summary.leads_por_status.total}`}
              />
              <StatTile
                label="Tempo médio de resposta"
                value={formatSeconds(summary.tempo_medio_resposta_seg)}
                hint={
                  responseTime
                    ? `p95 ${formatSeconds(responseTime.p95_seg)}`
                    : "por mensagem"
                }
                lowerIsBetter
              />
              <StatTile
                label="Leads no funil"
                value={String(summary.leads_por_status.total)}
                hint={`${summary.leads_por_status.agendado} agendados`}
              />
            </section>

            <AtendimentosChart pontos={pontos} />

            <FunilChart distribuicao={summary.leads_por_status} />

            {/* Tabela: a mesma informação sem depender de cor nem de gráfico. */}
            <details className="rounded-xl border border-surface-border bg-white p-5">
              <summary className="cursor-pointer text-sm font-medium text-gray-900">
                Ver os dados em tabela
              </summary>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-sm">
                  <caption className="sr-only">
                    Atendimentos e leads qualificados por dia
                  </caption>
                  <thead>
                    <tr className="border-b border-surface-border text-left text-xs text-gray-600">
                      <th scope="col" className="py-2 pr-4 font-medium">
                        Dia
                      </th>
                      <th scope="col" className="py-2 pr-4 font-medium">
                        Atendimentos
                      </th>
                      <th scope="col" className="py-2 font-medium">
                        Qualificados
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {pontos.map((ponto) => (
                      <tr key={ponto.data} className="border-b border-surface-border/60">
                        <td className="py-2 pr-4 text-gray-700">{ponto.data}</td>
                        <td className="py-2 pr-4 tabular-nums text-gray-900">
                          {ponto.atendimentos}
                        </td>
                        <td className="py-2 tabular-nums text-gray-900">
                          {ponto.leads_qualificados}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </div>
        )
      )}
    </div>
  );
}

function MetricsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { agents, isLoading, error, fetchAgents } = useAgents();

  useEffect(() => {
    void fetchAgents();
  }, [fetchAgents]);

  const requestedId = searchParams.get("agent");
  const selected = agents.find((agent) => agent.id === requestedId) ?? agents[0] ?? null;

  if (isLoading) return <FullPageLoader label="Carregando agentes..." />;

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-5">
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
        <Button variant="secondary" className="mt-4" onClick={() => void fetchAgents()}>
          Tentar novamente
        </Button>
      </div>
    );
  }

  if (agents.length === 0) {
    return (
      <EmptyState
        icon="📈"
        title="Nenhum agente ainda"
        description="As métricas são calculadas por agente. Crie um para começar a acompanhar o desempenho."
        action={
          <Link
            href="/dashboard/agents"
            className="rounded-lg bg-ink-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-ink-800"
          >
            Ir para Agentes
          </Link>
        }
      />
    );
  }

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Métricas</h1>
        <p className="mt-1 text-sm text-gray-600">
          Desempenho do agente no atendimento e na qualificação de leads.
        </p>
      </header>

      {agents.length > 1 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {agents.map((agent) => (
            <button
              key={agent.id}
              type="button"
              onClick={() => router.replace(`/dashboard/metrics?agent=${agent.id}`)}
              aria-pressed={agent.id === selected?.id}
              className={
                agent.id === selected?.id
                  ? "rounded-full bg-ink-900 px-3 py-1.5 text-sm font-medium text-white"
                  : "rounded-full border border-surface-border bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-surface-muted"
              }
            >
              {agent.nome}
            </button>
          ))}
        </div>
      )}

      {selected && <Painel key={selected.id} agentId={selected.id} />}
    </div>
  );
}

export default function MetricsPage() {
  return (
    <Suspense fallback={<FullPageLoader />}>
      <MetricsContent />
    </Suspense>
  );
}
