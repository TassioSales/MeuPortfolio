"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/Button";
import { ConversationsPanel } from "@/components/ConversationsPanel";
import { SemAgente } from "@/components/SemAgente";
import { FullPageLoader } from "@/components/LoadingSpinner";
import { useAgents } from "@/hooks/useAgents";

function ConversationsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { agents, isLoading, error, fetchAgents } = useAgents();

  useEffect(() => {
    void fetchAgents();
  }, [fetchAgents]);

  // Como no Kanban e no playground: o agente escolhido fica na URL.
  const requestedId = searchParams.get("agent");
  const selected = agents.find((agent) => agent.id === requestedId) ?? agents[0] ?? null;

  if (isLoading) return <FullPageLoader label="Carregando agentes..." />;

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/40 p-5">
        <p role="alert" className="text-sm text-red-700 dark:text-red-200">
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
      <SemAgente
        icone="💬"
        titulo="Nenhum agente ainda"
        paraOAdmin="Os atendimentos pertencem a um agente. Crie um para começar a receber conversas."
      />
    );
  }

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-fg">Atendimentos</h1>
        <p className="mt-1 text-sm text-fg-muted">
          Leia a conversa e assuma quando precisar. Com a conversa assumida a IA para de
          responder, mas as mensagens do cliente continuam chegando.
        </p>
      </header>

      {agents.length > 1 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {agents.map((agent) => (
            <button
              key={agent.id}
              type="button"
              onClick={() => router.replace(`/dashboard/conversations?agent=${agent.id}`)}
              aria-pressed={agent.id === selected?.id}
              className={
                agent.id === selected?.id
                  ? "rounded-full bg-ink-900 px-3 py-1.5 text-sm font-medium text-white dark:bg-ink-100 dark:text-ink-950"
                  : "rounded-full border border-surface-border bg-surface px-3 py-1.5 text-sm text-fg-soft hover:bg-surface-muted"
              }
            >
              {agent.nome}
            </button>
          ))}
        </div>
      )}

      {/* `key` remonta o painel ao trocar de agente, para não vazar a fila de um
          agente para a tela de outro. */}
      {selected && <ConversationsPanel key={selected.id} agentId={selected.id} />}
    </div>
  );
}

export default function ConversationsPage() {
  return (
    <Suspense fallback={<FullPageLoader />}>
      <ConversationsContent />
    </Suspense>
  );
}
