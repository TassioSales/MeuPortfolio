"use client";

import clsx from "clsx";
import type { Transcription } from "@/lib/types";
import { exportTranscription } from "@/lib/api";

interface TranscriptViewProps {
  transcription: Transcription;
}

const STATUS_CONFIG = {
  processing: {
    label: "Processando",
    className: "bg-yellow-900/40 text-yellow-300 border-yellow-700",
  },
  done: {
    label: "Concluído",
    className: "bg-green-900/40 text-green-300 border-green-700",
  },
  error: {
    label: "Erro",
    className: "bg-red-900/40 text-red-300 border-red-700",
  },
};

const LANGUAGE_LABELS: Record<string, string> = {
  pt: "Português",
  en: "English",
  es: "Español",
  fr: "Français",
  de: "Deutsch",
  it: "Italiano",
};

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

function formatDate(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return isoString;
  }
}

export default function TranscriptView({ transcription }: TranscriptViewProps) {
  const status = STATUS_CONFIG[transcription.status] ?? STATUS_CONFIG.processing;

  const handleExport = () => {
    exportTranscription(transcription.id, "txt");
  };

  if (transcription.status === "processing") {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8">
        <div className="text-center fade-in">
          <div className="relative inline-flex items-center justify-center w-20 h-20 mb-6">
            <div className="absolute inset-0 rounded-full border-4 border-[#1f2937]" />
            <div className="absolute inset-0 rounded-full border-4 border-t-violet-500 animate-spin" />
            <svg
              className="w-8 h-8 text-violet-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
              />
            </svg>
          </div>
          <h3 className="text-xl font-bold text-white mb-2">
            Transcrevendo áudio...
          </h3>
          <p className="text-gray-400 text-sm">
            {transcription.filename}
          </p>
          <p className="text-gray-600 text-xs mt-2">
            O Whisper está processando seu arquivo. Isso pode levar alguns segundos.
          </p>
        </div>
      </div>
    );
  }

  if (transcription.status === "error") {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8">
        <div className="text-center fade-in">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-red-900/30 border border-red-800 mb-4">
            <svg
              className="w-8 h-8 text-red-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <h3 className="text-xl font-bold text-white mb-2">
            Erro na transcrição
          </h3>
          <p className="text-gray-400 text-sm">{transcription.filename}</p>
          <p className="text-red-400/80 text-xs mt-2">
            Ocorreu um erro durante o processamento. Tente novamente com outro arquivo.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden fade-in">
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-[#1f2937] flex-shrink-0">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span
              className={clsx(
                "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border",
                status.className
              )}
            >
              {status.label}
            </span>
            <span className="text-gray-500 text-xs">
              {LANGUAGE_LABELS[transcription.language] ?? transcription.language}
            </span>
            <span className="text-gray-600 text-xs">•</span>
            <span className="text-gray-500 text-xs">
              {formatDuration(transcription.duration_seconds)}
            </span>
            <span className="text-gray-600 text-xs">•</span>
            <span className="text-gray-500 text-xs">
              {formatDate(transcription.created_at)}
            </span>
          </div>
          <h2 className="text-white font-semibold truncate">
            {transcription.filename}
          </h2>
        </div>

        <button
          onClick={handleExport}
          className="ml-3 flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 bg-[#1f2937] hover:bg-[#374151] border border-[#374151] hover:border-[#4b5563] text-gray-300 hover:text-white text-xs font-medium rounded-lg transition-all duration-150"
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
              d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          Exportar TXT
        </button>
      </div>

      {/* Two-column content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Full transcript */}
        <div className="flex-1 flex flex-col border-r border-[#1f2937] overflow-hidden">
          <div className="px-4 py-2 bg-[#0d1117] border-b border-[#1f2937] flex-shrink-0">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Transcrição Completa
            </span>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <p className="font-mono text-sm text-gray-300 leading-relaxed whitespace-pre-wrap break-words">
              {transcription.transcript || "Sem conteúdo transcrito."}
            </p>
          </div>
        </div>

        {/* Right: Summary + key points + metadata */}
        <div className="w-80 flex flex-col overflow-hidden flex-shrink-0">
          {/* Summary */}
          <div className="border-b border-[#1f2937]">
            <div className="px-4 py-2 bg-[#0d1117] border-b border-[#1f2937]">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Resumo
              </span>
            </div>
            <div className="p-4 max-h-48 overflow-y-auto">
              <p className="text-sm text-gray-300 leading-relaxed">
                {transcription.summary || "Resumo não disponível."}
              </p>
            </div>
          </div>

          {/* Key Points */}
          <div className="border-b border-[#1f2937] flex-1 overflow-hidden flex flex-col">
            <div className="px-4 py-2 bg-[#0d1117] border-b border-[#1f2937] flex-shrink-0">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Pontos Principais
              </span>
            </div>
            <div className="p-4 overflow-y-auto flex-1">
              {transcription.key_points && transcription.key_points.length > 0 ? (
                <ul className="space-y-2">
                  {transcription.key_points.map((point, idx) => (
                    <li key={idx} className="flex gap-2">
                      <span className="flex-shrink-0 w-5 h-5 rounded-full bg-[#4c1d95]/50 border border-[#7c3aed]/40 flex items-center justify-center text-violet-400 text-xs font-bold mt-0.5">
                        {idx + 1}
                      </span>
                      <span className="text-sm text-gray-300 leading-relaxed">
                        {point}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-gray-600">
                  Nenhum ponto principal identificado.
                </p>
              )}
            </div>
          </div>

          {/* Metadata */}
          <div className="p-4 bg-[#0d1117] flex-shrink-0">
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-gray-600">Arquivo</span>
                <span className="text-gray-400 truncate max-w-[140px] text-right">
                  {transcription.filename}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-600">Idioma</span>
                <span className="text-gray-400">
                  {LANGUAGE_LABELS[transcription.language] ?? transcription.language}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-600">Duração</span>
                <span className="text-gray-400">
                  {formatDuration(transcription.duration_seconds)}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-600">Data</span>
                <span className="text-gray-400">
                  {formatDate(transcription.created_at)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
