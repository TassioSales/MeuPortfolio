"use client";

import { useEffect, useState } from "react";
import { AgentCard } from "@/components/AgentCard";
import { AgentForm } from "@/components/AgentForm";
import { Button } from "@/components/Button";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EmptyState } from "@/components/EmptyState";
import { FullPageLoader } from "@/components/LoadingSpinner";
import { Modal } from "@/components/Modal";
import { useAgents } from "@/hooks/useAgents";
import type { Agent, AgentInput } from "@/types";

type DialogState =
  | { kind: "closed" }
  | { kind: "create" }
  | { kind: "edit"; agent: Agent }
  | { kind: "delete"; agent: Agent };

export default function AgentsPage() {
  const { agents, isLoading, error, fetchAgents, createAgent, updateAgent, removeAgent } =
    useAgents();

  const [dialog, setDialog] = useState<DialogState>({ kind: "closed" });

  useEffect(() => {
    void fetchAgents();
  }, [fetchAgents]);

  function closeDialog() {
    setDialog({ kind: "closed" });
  }

  async function handleCreate(data: AgentInput) {
    await createAgent(data);
    closeDialog();
  }

  async function handleUpdate(agentId: string, data: AgentInput) {
    await updateAgent(agentId, data);
    closeDialog();
  }

  async function handleDelete(agentId: string) {
    await removeAgent(agentId);
    closeDialog();
  }

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-fg">Agentes</h1>
          <p className="mt-1 text-sm text-fg-muted">
            Cada agente tem seu próprio system prompt e responde às conversas do WhatsApp.
          </p>
        </div>
        <Button onClick={() => setDialog({ kind: "create" })}>Novo agente</Button>
      </header>

      {isLoading ? (
        <FullPageLoader label="Carregando agentes..." />
      ) : error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-5">
          <p role="alert" className="text-sm text-red-700">
            {error}
          </p>
          <Button variant="secondary" className="mt-4" onClick={() => void fetchAgents()}>
            Tentar novamente
          </Button>
        </div>
      ) : agents.length === 0 ? (
        <EmptyState
          icon="🤖"
          title="Nenhum agente ainda"
          description="Crie o primeiro agente para começar a atender e qualificar leads no WhatsApp."
          action={
            <Button onClick={() => setDialog({ kind: "create" })}>Criar primeiro agente</Button>
          }
        />
      ) : (
        <section className="grid gap-4 sm:grid-cols-2">
          {agents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onEdit={(target) => setDialog({ kind: "edit", agent: target })}
              onDelete={(target) => setDialog({ kind: "delete", agent: target })}
            />
          ))}
        </section>
      )}

      <Modal
        isOpen={dialog.kind === "create"}
        onClose={closeDialog}
        title="Novo agente"
        description="Defina o comportamento do agente pelo system prompt."
        size="lg"
      >
        <AgentForm onSubmit={handleCreate} onCancel={closeDialog} />
      </Modal>

      <Modal
        isOpen={dialog.kind === "edit"}
        onClose={closeDialog}
        title="Editar agente"
        size="lg"
      >
        {dialog.kind === "edit" && (
          <AgentForm
            agent={dialog.agent}
            onSubmit={(data) => handleUpdate(dialog.agent.id, data)}
            onCancel={closeDialog}
          />
        )}
      </Modal>

      <ConfirmDialog
        isOpen={dialog.kind === "delete"}
        title="Excluir agente"
        message={
          dialog.kind === "delete"
            ? `O agente "${dialog.agent.nome}" será removido permanentemente. As conversas já existentes não são apagadas.`
            : ""
        }
        confirmLabel="Excluir"
        onConfirm={() => (dialog.kind === "delete" ? handleDelete(dialog.agent.id) : undefined)}
        onCancel={closeDialog}
      />
    </div>
  );
}
