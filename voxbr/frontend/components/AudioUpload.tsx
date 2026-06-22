"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import clsx from "clsx";
import type { Transcription, Language } from "@/lib/types";
import { LANGUAGE_LABELS, SUPPORTED_EXTENSIONS } from "@/lib/types";
import { uploadAudio, getTranscription } from "@/lib/api";

interface Toast {
  id: number;
  message: string;
  type: "info" | "success" | "error";
}

interface AudioUploadProps {
  onTranscriptionReady: (transcription: Transcription) => void;
}

export default function AudioUpload({ onTranscriptionReady }: AudioUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [language, setLanguage] = useState<Language>("pt");
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [pollingId, setPollingId] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const toastCounterRef = useRef(0);
  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const addToast = useCallback(
    (message: string, type: Toast["type"] = "info") => {
      const id = ++toastCounterRef.current;
      setToasts((prev) => [...prev, { id, message, type }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 5000);
    },
    []
  );

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const startPolling = useCallback(
    (transcriptionId: number) => {
      setPollingId(transcriptionId);
      pollingIntervalRef.current = setInterval(async () => {
        try {
          const updated = await getTranscription(transcriptionId);
          if (updated.status === "done") {
            clearInterval(pollingIntervalRef.current!);
            pollingIntervalRef.current = null;
            setPollingId(null);
            setUploading(false);
            setProgress(0);
            setSelectedFile(null);
            addToast("Transcrição concluída com sucesso!", "success");
            onTranscriptionReady(updated);
          } else if (updated.status === "error") {
            clearInterval(pollingIntervalRef.current!);
            pollingIntervalRef.current = null;
            setPollingId(null);
            setUploading(false);
            setProgress(0);
            addToast(
              "Erro durante a transcrição. Tente novamente.",
              "error"
            );
          }
        } catch {
          // Network error during polling — keep polling
        }
      }, 3000);
    },
    [addToast, onTranscriptionReady]
  );

  const isValidFile = (file: File): boolean => {
    const ext = "." + (file.name.split(".").pop() || "").toLowerCase();
    return SUPPORTED_EXTENSIONS.includes(ext);
  };

  const handleFile = useCallback(
    (file: File) => {
      if (!isValidFile(file)) {
        addToast(
          `Formato não suportado. Use: ${SUPPORTED_EXTENSIONS.join(", ")}`,
          "error"
        );
        return;
      }
      setSelectedFile(file);
    },
    [addToast]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleUpload = async () => {
    if (!selectedFile || uploading) return;

    setUploading(true);
    setProgress(10);

    // Fake progress animation
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 85) {
          clearInterval(progressInterval);
          return 85;
        }
        return prev + Math.random() * 8;
      });
    }, 300);

    try {
      const result = await uploadAudio(selectedFile, language);
      clearInterval(progressInterval);
      setProgress(100);
      addToast(
        "Arquivo enviado! Processando transcrição... pode levar alguns segundos.",
        "info"
      );
      startPolling(result.id);
    } catch (err) {
      clearInterval(progressInterval);
      setUploading(false);
      setProgress(0);
      addToast(
        `Erro ao enviar arquivo: ${err instanceof Error ? err.message : "Erro desconhecido"}`,
        "error"
      );
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="flex flex-col items-center justify-center h-full p-8">
      {/* Toast notifications */}
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={clsx(
              "toast-enter px-4 py-3 rounded-lg text-sm font-medium shadow-lg max-w-sm",
              {
                "bg-[#1e1b4b] border border-[#8b5cf6] text-violet-200":
                  toast.type === "info",
                "bg-[#14532d] border border-[#22c55e] text-green-200":
                  toast.type === "success",
                "bg-[#7f1d1d] border border-[#ef4444] text-red-200":
                  toast.type === "error",
              }
            )}
          >
            {toast.message}
          </div>
        ))}
      </div>

      <div className="w-full max-w-xl fade-in">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[#1e1b4b] border border-[#4c1d95] mb-4">
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
          <h2 className="text-2xl font-bold text-white mb-2">
            Nova Transcrição
          </h2>
          <p className="text-gray-400 text-sm">
            Faça upload de um arquivo de áudio para transcrição automática com IA
          </p>
        </div>

        {/* Drop Zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !uploading && fileInputRef.current?.click()}
          className={clsx(
            "relative border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all duration-200",
            {
              "border-[#8b5cf6] bg-[#1e1b4b]/50 drop-zone-active": isDragging,
              "border-[#374151] bg-[#111827] hover:border-[#6d28d9] hover:bg-[#1a1f2e]":
                !isDragging && !selectedFile,
              "border-[#5b21b6] bg-[#1e1b4b]/30": selectedFile && !isDragging,
              "opacity-75 cursor-not-allowed": uploading,
            }
          )}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".mp3,.mp4,.wav,.m4a,.ogg,.flac,.webm,audio/*"
            onChange={handleInputChange}
            className="hidden"
            disabled={uploading}
          />

          {selectedFile ? (
            <div className="space-y-2">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#4c1d95]/50 mb-2">
                <svg
                  className="w-6 h-6 text-violet-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
                  />
                </svg>
              </div>
              <p className="text-white font-medium truncate max-w-xs mx-auto">
                {selectedFile.name}
              </p>
              <p className="text-gray-400 text-sm">
                {formatFileSize(selectedFile.size)}
              </p>
              {!uploading && (
                <p className="text-violet-400 text-xs mt-1">
                  Clique para trocar o arquivo
                </p>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#1f2937] mb-2">
                <svg
                  className="w-6 h-6 text-gray-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                  />
                </svg>
              </div>
              <div>
                <p className="text-gray-300 font-medium">
                  Arraste um arquivo aqui ou{" "}
                  <span className="text-violet-400">clique para selecionar</span>
                </p>
                <p className="text-gray-500 text-sm mt-1">
                  {SUPPORTED_EXTENSIONS.join(", ")} • Máx. 500MB
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Language selector */}
        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Idioma do áudio
          </label>
          <div className="flex gap-2">
            {(Object.keys(LANGUAGE_LABELS) as Language[]).map((lang) => (
              <button
                key={lang}
                onClick={() => setLanguage(lang)}
                disabled={uploading}
                className={clsx(
                  "flex-1 py-2 px-4 rounded-lg text-sm font-medium border transition-all duration-150",
                  {
                    "bg-[#4c1d95] border-[#8b5cf6] text-violet-200":
                      language === lang,
                    "bg-[#111827] border-[#1f2937] text-gray-400 hover:border-[#374151]":
                      language !== lang,
                    "opacity-50 cursor-not-allowed": uploading,
                  }
                )}
              >
                {LANGUAGE_LABELS[lang]}
              </button>
            ))}
          </div>
        </div>

        {/* Progress bar */}
        {uploading && (
          <div className="mt-4">
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>
                {progress < 100
                  ? pollingId
                    ? "Transcrevendo..."
                    : "Enviando arquivo..."
                  : "Processando..."}
              </span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="w-full bg-[#1f2937] rounded-full h-2 overflow-hidden">
              <div
                className="h-full rounded-full progress-shimmer transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            {pollingId && (
              <p className="text-gray-500 text-xs mt-2 text-center">
                Aguardando resultado... verificando a cada 3 segundos
              </p>
            )}
          </div>
        )}

        {/* Upload button */}
        <button
          onClick={handleUpload}
          disabled={!selectedFile || uploading}
          className={clsx(
            "mt-4 w-full py-3 rounded-xl font-semibold text-sm transition-all duration-200",
            {
              "bg-[#8b5cf6] hover:bg-[#7c3aed] text-white cursor-pointer shadow-lg shadow-violet-900/30":
                selectedFile && !uploading,
              "bg-[#1f2937] text-gray-600 cursor-not-allowed": !selectedFile,
              "bg-[#4c1d95] text-violet-300 cursor-not-allowed": uploading,
            }
          )}
        >
          {uploading ? (
            <span className="flex items-center justify-center gap-2">
              <svg
                className="animate-spin w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              Processando...
            </span>
          ) : (
            "Transcrever Áudio"
          )}
        </button>

        <p className="text-center text-gray-600 text-xs mt-3">
          Powered by OpenAI Whisper + Mistral AI
        </p>
      </div>
    </div>
  );
}
