import { api } from "./api";
import type { ChatHistoryResponse, ChatResponse } from "@/types";

/** Endpoints de `backend/app/routers/chat.py`. */
function chatPath(agentId: string): string {
  return `/api/v1/agents/${agentId}/chat`;
}

/**
 * Envia uma mensagem ao agente.
 *
 * `conversationId` é omitido do corpo quando não existe conversa ainda: o
 * schema `MessageRequest` trata a ausência como "abra uma nova", enquanto um
 * `conversation_id: null` explícito seria um id inválido a procurar.
 */
export async function sendMessage(
  agentId: string,
  message: string,
  conversationId?: string | null,
): Promise<ChatResponse> {
  const body: { message: string; conversation_id?: string } = { message };
  if (conversationId) body.conversation_id = conversationId;

  return api.post<ChatResponse>(chatPath(agentId), body);
}

export async function getHistory(agentId: string): Promise<ChatHistoryResponse> {
  return api.get<ChatHistoryResponse>(`${chatPath(agentId)}/history`);
}

/** Apaga a conversa do playground e devolve o agente ao estado inicial. */
export async function resetHistory(agentId: string): Promise<void> {
  await api.delete(`${chatPath(agentId)}/history`);
}
