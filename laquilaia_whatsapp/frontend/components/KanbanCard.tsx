"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { cn } from "@/lib/utils";
import { formatarTelefone, linkDoWhatsapp } from "@/lib/telefone";
import type { KanbanCard as KanbanCardType } from "@/types";

interface KanbanCardProps {
  card: KanbanCardType;
  /** Cópia estática mostrada sob o cursor enquanto arrasta. */
  isOverlay?: boolean;
  /** Abre o dossiê do contato. Ausente na cópia que segue o cursor. */
  onAbrir?: (leadId: string) => void;
}

/** Faixas de cor do score, para leitura rápida da qualificação. */
function scoreTone(score: number): string {
  if (score >= 70) return "bg-green-50 text-green-700";
  if (score >= 40) return "bg-amber-50 text-amber-700";
  return "bg-surface-muted text-fg-muted";
}

export function KanbanCardItem({ card, isOverlay = false, onAbrir }: KanbanCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id, data: { card } });

  const whatsapp = linkDoWhatsapp(card.phone_number);

  return (
    <article
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      {...attributes}
      {...listeners}
      aria-label={`Lead ${card.nome}`}
      // O sensor do dnd-kit só considera arrasto depois de 6px, então clique
      // simples chega aqui inteiro (ver `KanbanBoard`).
      onClick={() => onAbrir?.(card.id)}
      className={cn(
        "cursor-grab rounded-lg border border-surface-border bg-surface p-3 active:cursor-grabbing",
        onAbrir && "hover:border-ink-300",
        // O original fica esmaecido enquanto a cópia acompanha o cursor.
        isDragging && !isOverlay && "opacity-40",
        isOverlay && "shadow-lg",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <h4 className="min-w-0 truncate text-sm font-medium text-fg">
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

      {whatsapp ? (
        <a
          href={whatsapp}
          target="_blank"
          rel="noopener noreferrer"
          // Sem isto, tocar no número abriria o dossiê junto — e o dossiê é
          // uma tela inteira aparecendo por cima de um link que já foi seguido.
          onClick={(e) => e.stopPropagation()}
          onPointerDown={(e) => e.stopPropagation()}
          className="mt-1 block truncate text-xs text-ink-700 underline-offset-2 hover:underline"
          title="Abrir esta conversa no WhatsApp"
        >
          {formatarTelefone(card.phone_number)}
        </a>
      ) : (
        <p className="mt-1 truncate text-xs text-fg-muted">
          {formatarTelefone(card.phone_number)}
        </p>
      )}
      {card.email && <p className="truncate text-xs text-fg-muted">{card.email}</p>}
    </article>
  );
}

export default KanbanCardItem;
