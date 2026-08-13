import { api } from "./api";
import type { KanbanBoard, LeadDossie, MoveCardRequest } from "@/types";

/** Endpoints de `backend/app/routers/kanban.py`. */
function kanbanPath(agentId: string): string {
  return `/api/v1/agents/${agentId}/kanban`;
}

export async function getBoard(agentId: string): Promise<KanbanBoard> {
  return api.get<KanbanBoard>(kanbanPath(agentId));
}

/** Cria as colunas padrão do funil. Idempotente no backend. */
export async function initColumns(agentId: string): Promise<void> {
  await api.post(`${kanbanPath(agentId)}/columns/init`);
}

/**
 * Move um lead para outra coluna.
 *
 * A posição vai junto porque a ordem dentro da coluna é do usuário — o
 * backend não a recalcula.
 */
export async function moveCard(
  agentId: string,
  payload: MoveCardRequest,
): Promise<void> {
  await api.post(`${kanbanPath(agentId)}/move`, payload);
}

/**
 * O dossiê de um contato: casos, porte e o que a triagem coletou.
 *
 * Buscado só ao abrir o card, e não junto do board: são casos e pareceres
 * inteiros por lead, e carregar isso para o funil todo seria pagar o dossiê de
 * cinquenta contatos para ler um.
 */
export async function getLeadDossie(
  agentId: string,
  leadId: string,
): Promise<LeadDossie> {
  return api.get<LeadDossie>(`${kanbanPath(agentId)}/leads/${leadId}`);
}
