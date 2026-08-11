"use client";

import { useCallback, useEffect, useState } from "react";
import * as kanbanApi from "@/lib/kanban";
import { messageFrom } from "./useAgents";
import type { KanbanBoard, KanbanCard } from "@/types";

/**
 * Estado do board de um agente.
 *
 * Como o playground, o estado é local à página: cada agente tem seu próprio
 * board e uma store global só criaria risco de misturar os dois.
 */
export function useKanban(agentId: string) {
  const [board, setBoard] = useState<KanbanBoard | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadBoard = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      let data = await kanbanApi.getBoard(agentId);

      // Agente novo ainda não tem colunas; cria as padrão e recarrega.
      if (data.columns.length === 0) {
        await kanbanApi.initColumns(agentId);
        data = await kanbanApi.getBoard(agentId);
      }

      setBoard(data);
    } catch (err) {
      setError(messageFrom(err, "Não foi possível carregar o board."));
    } finally {
      setIsLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    void loadBoard();
  }, [loadBoard]);

  /**
   * Move um card para outra coluna.
   *
   * A tela é atualizada antes da resposta do backend (o arrastar precisa
   * parecer instantâneo); se a chamada falhar, o board anterior é restaurado.
   */
  const moveCard = useCallback(
    async (leadId: string, targetColumnId: string, newOrder: number) => {
      if (!board) return;

      const previous = board;
      const card = board.columns
        .flatMap((column) => column.cards)
        .find((c) => c.id === leadId);
      if (!card) return;

      const moved: KanbanCard = { ...card, ordem: newOrder };
      setBoard({
        ...board,
        columns: board.columns.map((column) => {
          const withoutCard = column.cards.filter((c) => c.id !== leadId);
          if (column.id !== targetColumnId) {
            return { ...column, cards: withoutCard };
          }
          const cards = [...withoutCard];
          cards.splice(newOrder, 0, moved);
          return { ...column, cards };
        }),
      });

      setError(null);
      try {
        await kanbanApi.moveCard(agentId, {
          lead_id: leadId,
          target_column_id: targetColumnId,
          new_order: newOrder,
        });
      } catch (err) {
        setBoard(previous);
        setError(messageFrom(err, "Não foi possível mover o lead."));
      }
    },
    [agentId, board],
  );

  return { board, isLoading, error, moveCard, reload: loadBoard };
}
