"use client";

import { Suspense, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { KanbanBoard } from "@/components/KanbanBoard";
import { FullPageLoader } from "@/components/LoadingSpinner";
import { useAgents } from "@/hooks/useAgents";

function KanbanContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { agents, isLoading, error, fetchAgents } = useAgents();

  useEffect(() => {
    void fetchAgents();
  }, [fetchAgents]);

  // Igual ao playground: o agente escolhido fica na URL.
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
        icon="🗂️"
        title="Nenhum agente ainda"
        description="O funil de leads pertence a um agente. Crie um para começar a acompanhar as qualificações."
        action={
          <Link
            href="/dashboard/agents"
            className="rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700"
          >
            Ir para Agentes
          </Link>
        }
      />
    );
  }

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Kanban CRM</h1>
        <p className="mt-1 text-sm text-gray-600">
          Arraste os leads entre as etapas do funil. Mover um card atualiza o status do
          lead no backend.
        </p>
      </header>

      {agents.length > 1 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {agents.map((agent) => (
            <button
              key={agent.id}
              type="button"
              onClick={() => router.replace(`/dashboard/kanban?agent=${agent.id}`)}
              aria-pressed={agent.id === selected?.id}
              className={
                agent.id === selected?.id
                  ? "rounded-full bg-brand-600 px-3 py-1.5 text-sm font-medium text-white"
                  : "rounded-full border border-surface-border bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-surface-muted"
              }
            >
              {agent.nome}
            </button>
          ))}
        </div>
      )}

      {/* `key` remonta o board ao trocar de agente. */}
      {selected && <KanbanBoard key={selected.id} agentId={selected.id} />}
    </div>
  );
}

export default function KanbanPage() {
  return (
    <Suspense fallback={<FullPageLoader />}>
      <KanbanContent />
    </Suspense>
  );
}
