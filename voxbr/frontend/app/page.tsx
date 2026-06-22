"use client";

import { useState, useEffect, useCallback } from "react";
import type { Transcription } from "@/lib/types";
import { getTranscriptions } from "@/lib/api";
import HistoryPanel from "@/components/HistoryPanel";
import AudioUpload from "@/components/AudioUpload";
import TranscriptView from "@/components/TranscriptView";

export default function HomePage() {
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [showUpload, setShowUpload] = useState(true);
  const [loading, setLoading] = useState(true);

  const selectedTranscription =
    selectedId !== null
      ? transcriptions.find((t) => t.id === selectedId) ?? null
      : null;

  const loadTranscriptions = useCallback(async () => {
    try {
      const data = await getTranscriptions();
      setTranscriptions(data);
    } catch (err) {
      console.error("Failed to load transcriptions:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTranscriptions();
  }, [loadTranscriptions]);

  const handleTranscriptionReady = useCallback(
    (transcription: Transcription) => {
      setTranscriptions((prev) => {
        const exists = prev.find((t) => t.id === transcription.id);
        if (exists) {
          return prev.map((t) =>
            t.id === transcription.id ? transcription : t
          );
        }
        return [transcription, ...prev];
      });
      setSelectedId(transcription.id);
      setShowUpload(false);
    },
    []
  );

  const handleSelect = useCallback((transcription: Transcription) => {
    setSelectedId(transcription.id);
    setShowUpload(false);
  }, []);

  const handleDelete = useCallback(
    (id: number) => {
      setTranscriptions((prev) => prev.filter((t) => t.id !== id));
      if (selectedId === id) {
        setSelectedId(null);
        setShowUpload(true);
      }
    },
    [selectedId]
  );

  const handleNewTranscription = useCallback(() => {
    setSelectedId(null);
    setShowUpload(true);
  }, []);

  // Polling for "processing" items already in history
  useEffect(() => {
    const processingItems = transcriptions.filter(
      (t) => t.status === "processing"
    );
    if (processingItems.length === 0) return;

    const interval = setInterval(async () => {
      try {
        const updated = await getTranscriptions();
        setTranscriptions(updated);
      } catch {
        // Ignore network errors during polling
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [transcriptions]);

  return (
    <div className="flex h-screen bg-[#0a0e1a] overflow-hidden">
      {/* Sidebar: History Panel (30%) */}
      <aside className="w-[30%] min-w-[240px] max-w-[320px] bg-[#111827] border-r border-[#1f2937] flex flex-col overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 rounded-full border-2 border-[#1f2937] border-t-violet-500 animate-spin" />
              <p className="text-gray-600 text-xs">Carregando...</p>
            </div>
          </div>
        ) : (
          <HistoryPanel
            transcriptions={transcriptions}
            selectedId={selectedId}
            onSelect={handleSelect}
            onDelete={handleDelete}
            onNewTranscription={handleNewTranscription}
          />
        )}
      </aside>

      {/* Main Area (70%) */}
      <main className="flex-1 bg-[#0d1117] flex flex-col overflow-hidden">
        {/* Top bar */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-[#1f2937] flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-[#4c1d95] flex items-center justify-center">
                <svg
                  className="w-4 h-4 text-violet-300"
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
              <span className="text-white font-bold text-lg tracking-tight">
                VoxBR
              </span>
            </div>
            <span className="text-gray-700 text-sm hidden sm:block">
              Transcrição de áudio com IA
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs text-gray-600">
            <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
            <span>Whisper ativo</span>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {showUpload || !selectedTranscription ? (
            <AudioUpload onTranscriptionReady={handleTranscriptionReady} />
          ) : (
            <TranscriptView transcription={selectedTranscription} />
          )}
        </div>
      </main>
    </div>
  );
}
