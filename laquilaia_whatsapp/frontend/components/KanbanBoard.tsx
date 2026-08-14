"use client";

import { useState } from "react";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useDroppable } from "@dnd-kit/core";
import { KanbanCardItem } from "./KanbanCard";
import { LeadDossiePanel } from "./LeadDossie";
import { Button } from "./Button";
import { FullPageLoader } from "./LoadingSpinner";
import { useKanban } from "@/hooks/useKanban";
import { useAgentEvents } from "@/hooks/useAgentEvents";
import type { KanbanCard, KanbanColumn } from "@/types";

interface KanbanBoardProps {
  agentId: string;
}

function Column({
  column,
  onAbrir,
}: {
  column: KanbanColumn;
  onAbrir: (leadId: string) => void;
}) {
  // A coluna inteira é área de soltura, para aceitar card em coluna vazia.
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
    data: { columnId: column.id },
  });

  return (
    <section
      className="flex w-72 shrink-0 flex-col rounded-xl border border-surface-border bg-surface-muted"
      aria-label={column.nome}
    >
      <header className="flex items-center justify-between gap-2 px-3 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <span
            aria-hidden="true"
            className="h-2.5 w-2.5 shrink-0 rounded-full"
            style={{ backgroundColor: column.cor_hex }}
          />
          <h3 className="truncate text-sm font-medium text-fg">{column.nome}</h3>
        </div>
        <span className="shrink-0 rounded-full bg-surface px-2 py-0.5 text-xs text-fg-muted">
          {column.cards.length}
        </span>
      </header>

      <div
        ref={setNodeRef}
        className={
          "flex min-h-[8rem] flex-1 flex-col gap-2 rounded-b-xl p-3 pt-0 transition-colors " +
          (isOver ? "bg-brand-50 dark:bg-brand-900/40" : "")
        }
      >
        <SortableContext
          items={column.cards.map((card) => card.id)}
          strategy={verticalListSortingStrategy}
        >
          {column.cards.map((card) => (
            <KanbanCardItem key={card.id} card={card} onAbrir={onAbrir} />
          ))}
        </SortableContext>

        {column.cards.length === 0 && (
          <p className="px-1 py-4 text-center text-xs text-fg-faint">
            Nenhum lead nesta etapa
          </p>
        )}
      </div>
    </section>
  );
}

export function KanbanBoard({ agentId }: KanbanBoardProps) {
  const { board, isLoading, error, moveCard, reload } = useKanban(agentId);
  // Qual card está aberto. Nulo é o normal — o dossiê é modal.
  const [leadAberto, setLeadAberto] = useState<string | null>(null);
  const [dragging, setDragging] = useState<KanbanCard | null>(null);

  // Tempo real: um lead qualificado pelo agente no WhatsApp aparece no board
  // sem precisar recarregar. Recarrega o board inteiro em vez de aplicar o
  // evento na mão — o evento diz o que mudou, não o estado final de todas as
  // colunas, e refazer a leitura evita divergir do backend.
  const { isConnected } = useAgentEvents(agentId, (event) => {
    if (event.type === "lead_moved" || event.type === "new_message") {
      void reload();
    }
  });

  const sensors = useSensors(
    // A distância mínima evita que um clique simples vire arrasto.
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  function handleDragStart(event: DragStartEvent) {
    setDragging((event.active.data.current?.card as KanbanCard) ?? null);
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setDragging(null);
    if (!over || !board) return;

    const leadId = String(active.id);

    // O alvo pode ser a coluna (área vazia) ou outro card dentro dela.
    const targetColumn =
      board.columns.find((column) => column.id === over.id) ??
      board.columns.find((column) => column.cards.some((c) => c.id === over.id));
    if (!targetColumn) return;

    const source = board.columns.find((column) =>
      column.cards.some((c) => c.id === leadId),
    );
    const overIndex = targetColumn.cards.findIndex((c) => c.id === over.id);
    const newOrder = overIndex >= 0 ? overIndex : targetColumn.cards.length;

    // Soltar na mesma posição não precisa ir ao backend.
    if (source?.id === targetColumn.id) {
      const currentIndex = source.cards.findIndex((c) => c.id === leadId);
      if (currentIndex === newOrder) return;
    }

    void moveCard(leadId, targetColumn.id, newOrder);
  }

  if (isLoading) return <FullPageLoader label="Carregando board..." />;

  if (error && !board) {
    return (
      <div className="rounded-xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/40 p-5">
        <p role="alert" className="text-sm text-red-700 dark:text-red-200">
          {error}
        </p>
        <Button variant="secondary" className="mt-4" onClick={() => void reload()}>
          Tentar novamente
        </Button>
      </div>
    );
  }

  if (!board) return null;

  const totalCards = board.columns.reduce((sum, c) => sum + c.cards.length, 0);

  return (
    <div>
      {/* Erro de movimentação: o board já voltou ao estado anterior. */}
      {error && (
        <p
          role="alert"
          className="mb-4 rounded-lg bg-red-50 dark:bg-red-950/40 px-3 py-2 text-sm text-red-700 dark:text-red-200"
        >
          {error}
        </p>
      )}

      <p className="mb-4 flex items-center gap-2 text-xs text-fg-muted">
        <span
          aria-hidden="true"
          className={
            "h-2 w-2 rounded-full " + (isConnected ? "bg-emerald-500" : "bg-fg-faint")
          }
        />
        {isConnected
          ? "Atualizando em tempo real"
          : "Sem conexão em tempo real — recarregue para ver novidades"}
      </p>

      {totalCards === 0 && (
        <p className="mb-4 rounded-lg border border-surface-border bg-surface px-4 py-3 text-sm text-fg-muted">
          Nenhum lead ainda. Os leads entram no funil automaticamente conforme o agente
          qualifica as conversas do WhatsApp.
        </p>
      )}

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onDragCancel={() => setDragging(null)}
      >
        <div className="flex gap-4 overflow-x-auto pb-4">
          {board.columns.map((column) => (
            <Column key={column.id} column={column} onAbrir={setLeadAberto} />
          ))}
        </div>

        {/* Cópia sob o cursor: sem ela o card sumiria ao sair da coluna. */}
        <DragOverlay>
          {dragging && <KanbanCardItem card={dragging} isOverlay />}
        </DragOverlay>
      </DndContext>

      <LeadDossiePanel
        agentId={agentId}
        leadId={leadAberto}
        onClose={() => setLeadAberto(null)}
      />
    </div>
  );
}

export default KanbanBoard;
