"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/Button";
import { ListaDeClientes } from "@/components/ListaDeClientes";
import { FullPageLoader } from "@/components/LoadingSpinner";
import { SemAgente } from "@/components/SemAgente";
import { useAgents } from "@/hooks/useAgents";

function ClientesContent() {
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
      <div className="rounded-xl border border-red-200 bg-red-50 p-5 dark:border-red-900 dark:bg-red-950/40">
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
        icone="👥"
        titulo="Nenhum agente ainda"
        paraOAdmin="Os contatos chegam pelo WhatsApp e pertencem a um agente. Crie um para começar."
      />
    );
  }

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-fg">Clientes</h1>
        <p className="mt-1 text-sm text-fg-muted">
          Todo mundo que já escreveu para o escritório. O Kanban mostra o que está
          travado; aqui você acha uma pessoa.
        </p>
      </header>

      {agents.length > 1 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {agents.map((agent) => (
            <button
              key={agent.id}
              type="button"
              onClick={() => router.replace(`/dashboard/clientes?agent=${agent.id}`)}
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

      {/* `key` remonta a lista ao trocar de agente: sem isso a busca digitada
          continuaria valendo para um agente que não é o dela. */}
      {selected && <ListaDeClientes key={selected.id} agentId={selected.id} />}
    </div>
  );
}

export default function ClientesPage() {
  return (
    <Suspense fallback={<FullPageLoader label="Carregando..." />}>
      <ClientesContent />
    </Suspense>
  );
}
