"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import * as conversationsApi from "@/lib/conversations";
import { messageFrom } from "./useAgents";
import type { ConversationSummary, ConversationTranscript } from "@/types";

/**
 * Devolve a fila do servidor rearranjada na ordem que o operador já vê.
 *
 * Sem ordem congelada (`null`), a do servidor passa direto — que é o certo
 * enquanto ninguém está lendo nada.
 *
 * Conversa que não estava na foto é conversa que chegou agora: vai para o
 * topo, porque cliente novo esperando é exatamente o que a fila existe para
 * mostrar. Congelar a ordem não pode virar esconder quem chegou.
 */
export function aplicarOrdemCongelada(
  vindas: ConversationSummary[],
  ordem: string[] | null,
): ConversationSummary[] {
  if (!ordem) return vindas;

  const posicao = new Map(ordem.map((id, indice) => [id, indice]));
  // `-1` para as desconhecidas: elas ficam antes de todas as fotografadas, e
  // entre si mantêm a ordem do servidor (o `sort` do JS é estável).
  return [...vindas].sort(
    (a, b) => (posicao.get(a.id) ?? -1) - (posicao.get(b.id) ?? -1),
  );
}

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

  // A lista como está na tela agora, para congelar a ordem sem depender de
  // um `setConversations` recém-chamado.
  const listaRef = useRef<ConversationSummary[]>([]);
  listaRef.current = conversations;

  /**
   * A ordem em que a fila estava quando o operador abriu uma conversa.
   *
   * O servidor devolve a fila da mensagem mais recente para a mais antiga, e
   * isso está certo para quem chega: quem acabou de escrever precisa aparecer
   * em cima. O problema é que a **própria** resposta do operador também é uma
   * mensagem nova: ele escrevia, o WebSocket avisava, a fila era recarregada,
   * e a conversa que ele estava lendo pulava para o topo — a lista se mexendo
   * embaixo do cursor a cada frase digitada.
   *
   * Enquanto há conversa aberta, a fila fica parada. Ela se reordena de novo
   * quando o operador troca de conversa, que é quando ele quer mesmo ver a
   * fila atualizada.
   */
  const ordemCongelada = useRef<string[] | null>(null);
  const agenteJaCarregado = useRef<string | null>(null);

  const loadConversations = useCallback(async () => {
    // Só a primeira carga deste agente mostra o "Carregando atendimentos...".
    // As recargas vêm do WebSocket, várias por conversa: trocar a tela inteira
    // por um spinner a cada mensagem apaga o que o operador está lendo — e era
    // essa remontagem que jogava a transcrição de volta para o começo.
    const primeira = agenteJaCarregado.current !== agentId;
    if (primeira) setIsLoading(true);
    setError(null);
    try {
      const vindas = await conversationsApi.listConversations(agentId);
      setConversations(aplicarOrdemCongelada(vindas, ordemCongelada.current));
      agenteJaCarregado.current = agentId;
    } catch (err) {
      setError(messageFrom(err, "Não foi possível carregar os atendimentos."));
    } finally {
      if (primeira) setIsLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  const openConversation = useCallback(async (conversationId: string) => {
    // Trocar de conversa é o momento de aceitar a ordem nova: a fila que o
    // operador vê a partir daqui é a do servidor, e é essa que ele congela.
    ordemCongelada.current = listaRef.current.map((c) => c.id);
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
