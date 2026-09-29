"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { Button } from "@/components/Button";
import { ChatPlayground } from "@/components/ChatPlayground";
import { EmptyState } from "@/components/EmptyState";
import { FullPageLoader } from "@/components/LoadingSpinner";
import { useAgents } from "@/hooks/useAgents";

function ChatTestContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { agents, isLoading, error, fetchAgents } = useAgents();

  useEffect(() => {
    void fetchAgents();
  }, [fetchAgents]);

  // O agente escolhido vive na URL, para o link do playground ser compartilhável.
  const requestedId = searchParams.get("agent");
  const selected = agents.find((agent) => agent.id === requestedId) ?? agents[0] ?? null;

  function selectAgent(agentId: string) {
    router.replace(`/dashboard/chat-test?agent=${agentId}`);
  }

  if (isLoading) return <FullPageLoader label="Carregando agentes..." />;

  if (error) {
    return (
      <div className="mx-auto max-w-5xl rounded-xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/40 p-5">
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
      <div className="mx-auto max-w-5xl">
        <EmptyState
          icon="🤖"
          title="Nenhum agente para testar"
          description="Crie um agente para conversar com ele aqui antes de publicá-lo no WhatsApp."
          action={
            <Link
              href="/dashboard/agents"
              className="rounded-lg bg-ink-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-ink-800 dark:bg-ink-100 dark:text-ink-950 dark:hover:bg-white"
            >
              Ir para Agentes
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-fg">Chat de teste</h1>
        <p className="mt-1 text-sm text-fg-muted">
          Converse com o agente antes de publicá-lo. Esta conversa é separada das
          conversas reais do WhatsApp.
        </p>
      </header>

      {agents.length > 1 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {agents.map((agent) => (
            <button
              key={agent.id}
              type="button"
              onClick={() => selectAgent(agent.id)}
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

      {selected && (
        // `key` força um playground novo ao trocar de agente, senão a conversa
        // de um apareceria na tela do outro.
        <ChatPlayground key={selected.id} agent={selected} />
      )}
    </div>
  );
}

export default function ChatTestPage() {
  return (
    <Suspense fallback={<FullPageLoader />}>
      <ChatTestContent />
    </Suspense>
  );
}
