import { api } from "./api";
import type {
  ChatHistoryMessage,
  ConversationStatus,
  ConversationSummary,
  ConversationTranscript,
} from "@/types";

/**
 * Atendimentos e a pausa humana.
 *
 * A listagem é subrecurso do agente (`/agents/{id}/conversations`), mas pausar
 * e retomar operam sobre a conversa direto — é como o backend separa os dois
 * routers.
 */

export async function listConversations(
  agentId: string,
): Promise<ConversationSummary[]> {
  return api.get<ConversationSummary[]>(`/api/v1/agents/${agentId}/conversations`);
}

export async function getTranscript(
  conversationId: string,
): Promise<ConversationTranscript> {
  return api.get<ConversationTranscript>(
    `/api/v1/conversations/${conversationId}/messages`,
  );
}

/** Humano assume: a IA para de responder, as mensagens continuam chegando. */
export async function pauseConversation(
  conversationId: string,
): Promise<ConversationStatus> {
  return api.post<ConversationStatus>(
    `/api/v1/conversations/${conversationId}/pause`,
  );
}

export async function resumeConversation(
  conversationId: string,
): Promise<ConversationStatus> {
  return api.post<ConversationStatus>(
    `/api/v1/conversations/${conversationId}/resume`,
  );
}

export async function getConversationStatus(
  conversationId: string,
): Promise<ConversationStatus> {
  return api.get<ConversationStatus>(
    `/api/v1/conversations/${conversationId}/status`,
  );
}

/**
 * O operador escreve ao cliente.
 *
 * Só funciona com a conversa assumida — com a IA ativa o backend responde 409,
 * porque os dois responderiam à mesma pergunta.
 */
export async function enviarComoOperador(
  conversationId: string,
  conteudo: string,
): Promise<ChatHistoryMessage> {
  return api.post<ChatHistoryMessage>(
    `/api/v1/conversations/${conversationId}/mensagens`,
    { conteudo },
  );
}
