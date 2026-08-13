"use client";

import { useCallback, useEffect, useState } from "react";

import * as conversationsApi from "@/lib/conversations";
import { messageFrom } from "./useAgents";
import type { ConversationSummary, ConversationTranscript } from "@/types";

/**
 * Fila de atendimentos de um agente e a conversa aberta.
 *
 * Como `useChat` e `useKanban`, o estado é local à página: cada agente tem a
 * sua fila, e uma store global arriscaria mostrar a conversa de um agente na
 * tela de outro.
 */
export function useConversations(agentId: string) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<ConversationTranscript | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingTranscript, setIsLoadingTranscript] = useState(false);
  const [isTogglingPause, setIsTogglingPause] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadConversations = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setConversations(await conversationsApi.listConversations(agentId));
    } catch (err) {
      setError(messageFrom(err, "Não foi possível carregar os atendimentos."));
    } finally {
      setIsLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  const openConversation = useCallback(async (conversationId: string) => {
    setSelectedId(conversationId);
    setIsLoadingTranscript(true);
    setError(null);
    try {
      setTranscript(await conversationsApi.getTranscript(conversationId));
    } catch (err) {
      setTranscript(null);
      setError(messageFrom(err, "Não foi possível abrir a conversa."));
    } finally {
      setIsLoadingTranscript(false);
    }
  }, []);

  /**
   * Passa a conversa para o humano, ou devolve para a IA.
   *
   * Ao contrário do arrastar no Kanban, aqui não há atualização otimista: quem
   * responde ao cliente depende deste estado, e mostrar "pausado" antes da
   * confirmação faria o operador escrever achando que a IA parou.
   */
  const togglePause = useCallback(async () => {
    if (!transcript || isTogglingPause) return;

    setIsTogglingPause(true);
    setError(null);
    try {
      const novo = transcript.ia_ativa
        ? await conversationsApi.pauseConversation(transcript.conversation_id)
        : await conversationsApi.resumeConversation(transcript.conversation_id);

      setTranscript((atual) =>
        atual && atual.conversation_id === novo.conversation_id
          ? { ...atual, status: novo.status, ia_ativa: novo.ia_ativa }
          : atual,
      );
      // A lista mostra o mesmo estado; sem isto o selo continuaria o antigo.
      setConversations((atuais) =>
        atuais.map((conversa) =>
          conversa.id === novo.conversation_id
            ? { ...conversa, status: novo.status, ia_ativa: novo.ia_ativa }
            : conversa,
        ),
      );
    } catch (err) {
      setError(messageFrom(err, "Não foi possível mudar quem responde."));
    } finally {
      setIsTogglingPause(false);
    }
  }, [transcript, isTogglingPause]);

  /** Recarrega a fila e, se houver conversa aberta, também a transcrição. */
  const reload = useCallback(async () => {
    await loadConversations();
    if (selectedId) {
      try {
        setTranscript(await conversationsApi.getTranscript(selectedId));
      } catch {
        // A fila já foi atualizada; falhar aqui não deve limpar a tela.
      }
    }
  }, [loadConversations, selectedId]);

  /**
   * Manda a mensagem do operador e a acrescenta à transcrição na hora.
   *
   * Sem o acréscimo local, a mensagem só apareceria no próximo carregamento —
   * e quem acabou de escrever ficaria olhando para uma tela que não mudou,
   * sem saber se foi.
   */
  const responder = useCallback(
    async (conteudo: string) => {
      if (!selectedId) return;

      const mensagem = await conversationsApi.enviarComoOperador(selectedId, conteudo);
      setTranscript((atual) =>
        atual ? { ...atual, messages: [...atual.messages, mensagem] } : atual,
      );
    },
    [selectedId],
  );

  return {
    conversations,
    selectedId,
    transcript,
    isLoading,
    isLoadingTranscript,
    isTogglingPause,
    error,
    openConversation,
    togglePause,
    responder,
    reload,
  };
}
