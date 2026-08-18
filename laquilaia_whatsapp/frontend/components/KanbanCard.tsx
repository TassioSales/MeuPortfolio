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
  if (score >= 70) return "bg-green-50 dark:bg-green-950/40 text-green-700 dark:text-green-200";
  if (score >= 40) return "bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-200";
  return "bg-surface-muted text-fg-muted";
}

/**
 * O porte do caso, em tarja.
 *
 * `indeterminado` não vira tarja: caso recém-chegado ainda não foi
 * dimensionado, e uma tarja em todo card não informa nada. Também não vira
 * tarja o que o parecer ainda não analisou — ele roda dois minutos depois de
 * o card nascer, e "sem porte" é estado normal nesse intervalo.
 */
function Porte({ card }: { card: KanbanCardType }) {
  if (
    !card.viabilidade ||
    card.viabilidade === "indeterminado" ||
    card.viabilidade === "nao_se_aplica"
  ) {
    return null;
  }

  const abaixo = card.viabilidade === "abaixo_do_piso";
  const faixa =
    card.valor_estimado_min !== null && card.valor_estimado_max !== null
      ? `${emReais(card.valor_estimado_min)}–${emReais(card.valor_estimado_max)}`
      : abaixo
        ? "abaixo do piso"
        : "acima do piso";

  return (
    <span
      className={cn(
        "mt-2 inline-block rounded-full px-2 py-0.5 text-xs",
        abaixo
          ? "bg-surface-muted text-fg-soft ring-1 ring-surface-border"
          : "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100",
      )}
      title={
        abaixo
          ? "O parecer estimou o caso abaixo do piso do escritório. É estimativa preliminar, sem documentos."
          : "O parecer estimou o caso acima do piso do escritório. É estimativa preliminar, sem documentos."
      }
    >
      {faixa}
    </span>
  );
}

/** Sem centavos: a estimativa não tem essa precisão, e o card não tem espaço. */
function emReais(valor: number): string {
  return valor.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  });
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
      {/* Empresa e cargo antes do e-mail: num caso trabalhista, é isso que
          identifica o caso. O e-mail serve para contato, não para triar. */}
      {(card.empresa || card.cargo) && (
        <p className="mt-1 truncate text-xs text-fg-soft" title={[card.empresa, card.cargo].filter(Boolean).join(" · ")}>
          {[card.empresa, card.cargo].filter(Boolean).join(" · ")}
        </p>
      )}

      {card.email && <p className="truncate text-xs text-fg-muted">{card.email}</p>}

      <Porte card={card} />
    </article>
  );
}

export default KanbanCardItem;
