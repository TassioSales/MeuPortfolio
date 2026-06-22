"use client";

import clsx from "clsx";
import type { GraphNode, Note } from "@/lib/types";

interface NodePanelProps {
  node: GraphNode;
  notes: Note[];
  onClose?: () => void;
}

const GROUP_LABELS: Record<string, string> = {
  PERSON: "Pessoa",
  PER: "Pessoa",
  ORG: "Organização",
  GPE: "Local Geo-Político",
  LOC: "Localização",
  LOCATION: "Localização",
  DATE: "Data",
  TIME: "Tempo",
  MONEY: "Dinheiro",
  PRODUCT: "Produto",
  EVENT: "Evento",
  WORK_OF_ART: "Obra",
  LAW: "Lei",
  LANGUAGE: "Idioma",
  PERCENT: "Percentagem",
  QUANTITY: "Quantidade",
};

const GROUP_COLORS: Record<string, string> = {
  PERSON: "text-blue-400",
  PER: "text-blue-400",
  ORG: "text-green-400",
  GPE: "text-red-400",
  LOC: "text-orange-400",
  LOCATION: "text-orange-400",
  DATE: "text-purple-400",
  TIME: "text-purple-400",
};

export default function NodePanel({ node, notes, onClose }: NodePanelProps) {
  // Find notes that mention this entity
  const relatedNotes = notes.filter((n) =>
    n.content.toLowerCase().includes(node.label.toLowerCase()) ||
    n.title.toLowerCase().includes(node.label.toLowerCase())
  );

  const colorClass = GROUP_COLORS[node.group] ?? "text-[#8b949e]";
  const groupLabel = GROUP_LABELS[node.group] ?? node.group;

  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="flex items-start justify-between gap-2">
        <h2 className="text-sm font-semibold text-[#8b949e] uppercase tracking-wider">
          Detalhes do Nó
        </h2>
        {onClose && (
          <button
            onClick={onClose}
            className="text-[#8b949e] hover:text-[#e6edf3] text-lg leading-none"
            aria-label="Fechar painel"
          >
            ×
          </button>
        )}
      </div>

      <div className="bg-[#0d1117] rounded-lg p-4 border border-[#30363d]">
        <p className="text-[#e6edf3] text-lg font-semibold break-words">{node.label}</p>
        <p className={clsx("text-sm mt-1 font-medium", colorClass)}>{groupLabel}</p>
        <div className="mt-3 flex gap-4">
          <div className="text-center">
            <p className="text-[#58a6ff] text-xl font-bold">{node.count}</p>
            <p className="text-[#8b949e] text-xs">aparições</p>
          </div>
          <div className="text-center">
            <p className="text-[#3fb950] text-xl font-bold">{relatedNotes.length}</p>
            <p className="text-[#8b949e] text-xs">notas</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <p className="text-xs text-[#8b949e] mb-2 font-medium uppercase tracking-wider">
          Notas relacionadas
        </p>
        {relatedNotes.length === 0 ? (
          <p className="text-xs text-[#8b949e] italic">
            Nenhuma nota encontrada com este termo.
          </p>
        ) : (
          <ul className="space-y-2">
            {relatedNotes.map((note) => (
              <li
                key={note.id}
                className="bg-[#0d1117] border border-[#30363d] rounded-md p-3"
              >
                <p className="text-[#e6edf3] text-sm font-medium line-clamp-1">
                  {note.title}
                </p>
                <p className="text-[#8b949e] text-xs mt-1 line-clamp-2">
                  {note.content}
                </p>
                <p className="text-[#8b949e] text-[10px] mt-1">
                  {new Date(note.updated_at).toLocaleDateString("pt-BR")}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
