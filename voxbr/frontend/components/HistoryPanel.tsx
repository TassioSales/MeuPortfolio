"use client";

import { useState } from "react";
import clsx from "clsx";
import type { Transcription } from "@/lib/types";
import { deleteTranscription } from "@/lib/api";

interface HistoryPanelProps {
  transcriptions: Transcription[];
  selectedId: number | null;
  onSelect: (transcription: Transcription) => void;
  onDelete: (id: number) => void;
  onNewTranscription: () => void;
}

const STATUS_DOT = {
  processing: "bg-yellow-400 animate-pulse",
  done: "bg-green-400",
  error: "bg-red-400",
};

const STATUS_LABEL = {
  processing: "Processando",
  done: "Concluído",
  error: "Erro",
};

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

function formatRelativeDate(isoString: string): string {
  try {
    const d = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMin < 1) return "agora";
    if (diffMin < 60) return `${diffMin}min atrás`;
    if (diffHours < 24) return `${diffHours}h atrás`;
    if (diffDays < 7) return `${diffDays}d atrás`;

    return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
  } catch {
    return "";
  }
}

function truncateFilename(filename: string, maxLen = 28): string {
  if (filename.length <= maxLen) return filename;
  const ext = filename.includes(".")
    ? "." + filename.split(".").pop()
    : "";
  const base = filename.slice(0, maxLen - ext.length - 3);
  return `${base}...${ext}`;
}

export default function HistoryPanel({
  transcriptions,
  selectedId,
  onSelect,
  onDelete,
  onNewTranscription,
}: HistoryPanelProps) {
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const handleDeleteClick = (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    setConfirmDeleteId(id);
  };

  const handleConfirmDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    setDeletingId(id);
    setConfirmDeleteId(null);
    try {
      await deleteTranscription(id);
      onDelete(id);
    } catch (err) {
      console.error("Failed to delete:", err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleCancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setConfirmDeleteId(null);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-[#1f2937] flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <svg
              className="w-5 h-5 text-violet-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M4 6h16M4 10h16M4 14h16M4 18h16"
              />
            </svg>
            <h2 className="text-sm font-semibold text-white">Histórico</h2>
            {transcriptions.length > 0 && (
              <span className="text-xs bg-[#1f2937] text-gray-400 rounded-full px-1.5 py-0.5">
                {transcriptions.length}
              </span>
            )}
          </div>
        </div>

        <button
          onClick={onNewTranscription}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 bg-[#4c1d95]/40 hover:bg-[#4c1d95]/70 border border-[#6d28d9]/40 hover:border-[#8b5cf6]/60 text-violet-300 hover:text-violet-200 text-sm font-medium rounded-lg transition-all duration-150"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          Nova Transcrição
        </button>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {transcriptions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full p-6 text-center">
            <div className="w-12 h-12 rounded-xl bg-[#1f2937] flex items-center justify-center mb-3">
              <svg
                className="w-6 h-6 text-gray-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <p className="text-gray-600 text-sm">
              Nenhuma transcrição ainda
            </p>
            <p className="text-gray-700 text-xs mt-1">
              Faça upload de um áudio para começar
            </p>
          </div>
        ) : (
          <ul className="p-2 space-y-1">
            {transcriptions.map((item) => {
              const isSelected = item.id === selectedId;
              const isDeleting = item.id === deletingId;
              const isConfirming = item.id === confirmDeleteId;
              const dotClass =
                STATUS_DOT[item.status] ?? "bg-gray-500";

              return (
                <li key={item.id}>
                  <button
                    onClick={() => onSelect(item)}
                    disabled={isDeleting}
                    className={clsx(
                      "w-full text-left p-3 rounded-xl border transition-all duration-150 group relative",
                      {
                        "bg-[#1e1b4b]/60 border-[#4c1d95]/60":
                          isSelected,
                        "bg-[#111827] border-transparent hover:bg-[#1a1f2e] hover:border-[#1f2937]":
                          !isSelected,
                        "opacity-50 cursor-not-allowed": isDeleting,
                      }
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5 mb-0.5">
                          <span
                            className={clsx(
                              "flex-shrink-0 w-1.5 h-1.5 rounded-full",
                              dotClass
                            )}
                          />
                          <span
                            className={clsx(
                              "text-xs",
                              {
                                "text-violet-300": isSelected,
                                "text-gray-400": !isSelected,
                              }
                            )}
                          >
                            {STATUS_LABEL[item.status] ?? item.status}
                          </span>
                          <span className="text-gray-700 text-xs ml-auto">
                            {formatRelativeDate(item.created_at)}
                          </span>
                        </div>
                        <p
                          className={clsx("text-sm font-medium truncate", {
                            "text-white": isSelected,
                            "text-gray-300": !isSelected,
                          })}
                        >
                          {truncateFilename(item.filename)}
                        </p>
                        {item.duration_seconds > 0 && (
                          <p className="text-gray-600 text-xs mt-0.5">
                            {formatDuration(item.duration_seconds)}
                          </p>
                        )}
                      </div>

                      {/* Delete button */}
                      {!isConfirming ? (
                        <button
                          onClick={(e) => handleDeleteClick(e, item.id)}
                          className="flex-shrink-0 w-6 h-6 rounded-lg bg-transparent hover:bg-red-900/30 text-transparent hover:text-red-400 group-hover:text-gray-600 transition-all duration-150 flex items-center justify-center"
                          title="Deletar"
                        >
                          <svg
                            className="w-3.5 h-3.5"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                            />
                          </svg>
                        </button>
                      ) : (
                        <div className="flex gap-1 flex-shrink-0">
                          <button
                            onClick={(e) => handleConfirmDelete(e, item.id)}
                            className="w-6 h-6 rounded bg-red-900/50 hover:bg-red-700/70 text-red-400 hover:text-red-300 flex items-center justify-center transition-all"
                            title="Confirmar exclusão"
                          >
                            <svg
                              className="w-3 h-3"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={3}
                                d="M5 13l4 4L19 7"
                              />
                            </svg>
                          </button>
                          <button
                            onClick={handleCancelDelete}
                            className="w-6 h-6 rounded bg-[#1f2937] hover:bg-[#374151] text-gray-400 hover:text-gray-300 flex items-center justify-center transition-all"
                            title="Cancelar"
                          >
                            <svg
                              className="w-3 h-3"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={3}
                                d="M6 18L18 6M6 6l12 12"
                              />
                            </svg>
                          </button>
                        </div>
                      )}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
