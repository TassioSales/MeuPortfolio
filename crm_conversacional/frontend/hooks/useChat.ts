"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import * as chatApi from "@/lib/chat";
import { messageFrom } from "./useAgents";
import type { ChatBubble } from "@/types";

/**
 * Estado do playground de um agente.
 *
 * Não usa Zustand como `useAgents`: aqui o estado é local à página e some ao
 * sair dela. Uma store global só criaria risco de vazar a conversa de um
 * agente para outro.
 */
export function useChat(agentId: string) {
  const [messages, setMessages] = useState<ChatBubble[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Cada balão temporário precisa de uma chave estável para o React.
  const nextId = useRef(0);
  const makeId = () => `local-${nextId.current++}`;

  const loadHistory = useCallback(async () => {
    setIsLoadingHistory(true);
    setError(null);
    try {
      const history = await chatApi.getHistory(agentId);
      setConversationId(history.conversation_id);
      setMessages(
        history.messages.map((message) => ({
          id: message.id,
          remetente: message.remetente,
          conteudo: message.conteudo,
        })),
      );
    } catch (err) {
      setError(messageFrom(err, "Não foi possível carregar a conversa."));
    } finally {
      setIsLoadingHistory(false);
    }
  }, [agentId]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const send = useCallback(
    async (text: string) => {
      const content = text.trim();
      if (!content || isSending) return;

      setError(null);
      setIsSending(true);

      // A mensagem do usuário aparece na hora, junto do balão "digitando".
      const userBubble: ChatBubble = {
        id: makeId(),
        remetente: "user",
        conteudo: content,
      };
      const pendingBubble: ChatBubble = {
        id: makeId(),
        remetente: "assistant",
        conteudo: "",
        pending: true,
      };
      setMessages((current) => [...current, userBubble, pendingBubble]);

      try {
        const reply = await chatApi.sendMessage(agentId, content, conversationId);
        setConversationId(reply.conversation_id);
        setMessages((current) =>
          current.map((bubble) =>
            bubble.id === pendingBubble.id
              ? {
                  ...bubble,
                  conteudo: reply.response,
                  pending: false,
                  tokens: reply.tokens_used.total_tokens,
                }
              : bubble,
          ),
        );
      } catch (err) {
        // Remove o balão de espera e devolve o texto para o usuário reenviar.
        setMessages((current) =>
          current.filter(
            (bubble) => bubble.id !== pendingBubble.id && bubble.id !== userBubble.id,
          ),
        );
        setError(messageFrom(err, "Não foi possível enviar a mensagem."));
        throw err;
      } finally {
        setIsSending(false);
      }
    },
    [agentId, conversationId, isSending],
  );

  const reset = useCallback(async () => {
    setError(null);
    try {
      await chatApi.resetHistory(agentId);
      setMessages([]);
      setConversationId(null);
    } catch (err) {
      setError(messageFrom(err, "Não foi possível limpar a conversa."));
      throw err;
    }
  }, [agentId]);

  return {
    messages,
    conversationId,
    isLoadingHistory,
    isSending,
    error,
    send,
    reset,
    reload: loadHistory,
  };
}
