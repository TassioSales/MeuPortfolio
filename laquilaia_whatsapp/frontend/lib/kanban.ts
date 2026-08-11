import { api } from "./api";
import type { KanbanBoard, MoveCardRequest } from "@/types";

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
