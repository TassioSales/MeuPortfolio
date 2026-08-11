"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { cn } from "@/lib/utils";
import type { KanbanCard as KanbanCardType } from "@/types";

interface KanbanCardProps {
  card: KanbanCardType;
  /** Cópia estática mostrada sob o cursor enquanto arrasta. */
  isOverlay?: boolean;
}

/** Faixas de cor do score, para leitura rápida da qualificação. */
function scoreTone(score: number): string {
  if (score >= 70) return "bg-green-50 text-green-700";
  if (score >= 40) return "bg-amber-50 text-amber-700";
  return "bg-surface-muted text-gray-600";
}

export function KanbanCardItem({ card, isOverlay = false }: KanbanCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id, data: { card } });

  return (
    <article
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      {...attributes}
      {...listeners}
      aria-label={`Lead ${card.nome}`}
      className={cn(
        "cursor-grab rounded-lg border border-surface-border bg-white p-3 active:cursor-grabbing",
        // O original fica esmaecido enquanto a cópia acompanha o cursor.
        isDragging && !isOverlay && "opacity-40",
        isOverlay && "shadow-lg",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <h4 className="min-w-0 truncate text-sm font-medium text-gray-900">
          {card.nome || "Sem nome"}
        </h4>
        <span
          className={cn(
            "shrink-0 rounded-full px-2 py-0.5 text-xs font-medium",
            scoreTone(card.score_qualificacao),
          )}
        >
          {card.score_qualificacao}
        </span>
      </div>

      <p className="mt-1 truncate text-xs text-gray-600">{card.phone_number}</p>
      {card.email && <p className="truncate text-xs text-gray-500">{card.email}</p>}
    </article>
  );
}

export default KanbanCardItem;
