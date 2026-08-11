"use client";

import { Button } from "./Button";
import { cn } from "@/lib/utils";
import type { Agent } from "@/types";

interface AgentCardProps {
  agent: Agent;
  onEdit: (agent: Agent) => void;
  onDelete: (agent: Agent) => void;
}

function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function AgentCard({ agent, onEdit, onDelete }: AgentCardProps) {
  const isActive = agent.status === "ativo";

  return (
    <article className="flex flex-col rounded-xl border border-surface-border bg-white p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-gray-900">{agent.nome}</h3>
          <p className="mt-0.5 line-clamp-2 text-sm text-gray-600">
            {agent.descricao || "Sem descrição"}
          </p>
        </div>
        <span
          className={cn(
            "shrink-0 rounded-full px-2 py-0.5 text-xs font-medium",
            isActive ? "bg-green-50 text-green-700" : "bg-surface-muted text-gray-500",
          )}
        >
          {agent.status}
        </span>
      </div>

      <p className="mt-3 line-clamp-3 rounded-lg bg-surface-muted p-3 font-mono text-xs text-gray-600">
        {agent.system_prompt}
      </p>

      <dl className="mt-4 flex flex-wrap gap-x-6 gap-y-1 text-xs text-gray-500">
        <div className="flex gap-1">
          <dt>Temperatura:</dt>
          <dd className="font-medium text-gray-700">{agent.temperatura}</dd>
        </div>
        <div className="flex gap-1">
          <dt>Max tokens:</dt>
          <dd className="font-medium text-gray-700">{agent.max_tokens}</dd>
        </div>
        <div className="flex gap-1">
          <dt>Criado em:</dt>
          <dd className="font-medium text-gray-700">{formatDate(agent.data_criacao)}</dd>
        </div>
      </dl>

      <div className="mt-5 flex gap-2 border-t border-surface-border pt-4">
        <Button variant="secondary" onClick={() => onEdit(agent)}>
          Editar
        </Button>
        <Button variant="ghost" onClick={() => onDelete(agent)}>
          Excluir
        </Button>
      </div>
    </article>
  );
}

export default AgentCard;
