"use client";

import { useState } from "react";
import clsx from "clsx";
import { createNote, extractEntities } from "@/lib/api";
import type { Entity, Relation } from "@/lib/types";

interface NoteEditorProps {
  onSaved?: () => void;
}

const LABEL_COLORS: Record<string, string> = {
  PERSON: "bg-blue-900 text-blue-200",
  PER: "bg-blue-900 text-blue-200",
  ORG: "bg-green-900 text-green-200",
  LOC: "bg-orange-900 text-orange-200",
  LOCATION: "bg-orange-900 text-orange-200",
  GPE: "bg-red-900 text-red-200",
  DATE: "bg-purple-900 text-purple-200",
  TIME: "bg-purple-900 text-purple-200",
};

function labelClass(label: string) {
  return LABEL_COLORS[label] ?? "bg-gray-700 text-gray-300";
}

type Step = "editing" | "previewing" | "saving";

export default function NoteEditor({ onSaved }: NoteEditorProps) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [step, setStep] = useState<Step>("editing");
  const [entities, setEntities] = useState<Entity[]>([]);
  const [relations, setRelations] = useState<Relation[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze() {
    if (!content.trim()) {
      setError("O conteúdo não pode estar vazio.");
      return;
    }
    setError(null);
    setStep("previewing");

    try {
      const result = await extractEntities(content);
      setEntities(result.entities);
      setRelations(result.relations);
    } catch (err) {
      setError(
        `Falha ao extrair entidades: ${err instanceof Error ? err.message : String(err)}`
      );
      setStep("editing");
    }
  }

  async function handleSave() {
    if (!title.trim()) {
      setError("O título não pode estar vazio.");
      return;
    }
    setError(null);
    setStep("saving");

    try {
      await createNote(title, content, entities, relations);
      setTitle("");
      setContent("");
      setEntities([]);
      setRelations([]);
      setStep("editing");
      onSaved?.();
    } catch (err) {
      setError(
        `Falha ao salvar nota: ${err instanceof Error ? err.message : String(err)}`
      );
      setStep("previewing");
    }
  }

  function handleBack() {
    setStep("editing");
    setEntities([]);
    setRelations([]);
    setError(null);
  }

  return (
    <div className="flex flex-col gap-4 h-full">
      <h2 className="text-sm font-semibold text-[#8b949e] uppercase tracking-wider">
        Nova Nota
      </h2>

      {error && (
        <div className="rounded-md bg-red-900/40 border border-red-700 px-3 py-2 text-red-300 text-sm">
          {error}
        </div>
      )}

      {step === "editing" && (
        <>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Título da nota..."
            className="w-full bg-[#0d1117] border border-[#30363d] rounded-md px-3 py-2 text-[#e6edf3] placeholder-[#8b949e] focus:outline-none focus:border-[#58a6ff] text-sm"
          />
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Escreva sua nota aqui... O MemMap vai extrair entidades e relações automaticamente."
            rows={10}
            className="w-full bg-[#0d1117] border border-[#30363d] rounded-md px-3 py-2 text-[#e6edf3] placeholder-[#8b949e] focus:outline-none focus:border-[#58a6ff] text-sm resize-none flex-1"
          />
          <button
            onClick={handleAnalyze}
            disabled={!content.trim()}
            className={clsx(
              "w-full py-2 rounded-md text-sm font-medium transition-colors",
              content.trim()
                ? "bg-[#238636] hover:bg-[#2ea043] text-white"
                : "bg-[#21262d] text-[#8b949e] cursor-not-allowed"
            )}
          >
            Analisar & Salvar
          </button>
        </>
      )}

      {step === "previewing" && (
        <>
          <div className="flex flex-col gap-3 overflow-y-auto flex-1">
            <div>
              <p className="text-xs text-[#8b949e] mb-2">
                {entities.length} entidade(s) encontrada(s):
              </p>
              {entities.length === 0 ? (
                <p className="text-xs text-[#8b949e] italic">
                  Nenhuma entidade detectada neste texto.
                </p>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {entities.map((e, i) => (
                    <span
                      key={i}
                      className={clsx(
                        "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium",
                        labelClass(e.label)
                      )}
                    >
                      {e.text}
                      <span className="opacity-60 text-[10px]">{e.label}</span>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {relations.length > 0 && (
              <div>
                <p className="text-xs text-[#8b949e] mb-2">
                  {relations.length} relação(ões):
                </p>
                <ul className="space-y-1">
                  {relations.slice(0, 6).map((r, i) => (
                    <li key={i} className="text-xs text-[#8b949e]">
                      <span className="text-[#e6edf3]">{r.source}</span>
                      {" → "}
                      <span className="text-[#e6edf3]">{r.target}</span>
                    </li>
                  ))}
                  {relations.length > 6 && (
                    <li className="text-xs text-[#8b949e] italic">
                      +{relations.length - 6} mais…
                    </li>
                  )}
                </ul>
              </div>
            )}
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleBack}
              className="flex-1 py-2 rounded-md text-sm font-medium bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] transition-colors"
            >
              Voltar
            </button>
            <button
              onClick={handleSave}
              className="flex-1 py-2 rounded-md text-sm font-medium bg-[#238636] hover:bg-[#2ea043] text-white transition-colors"
            >
              Confirmar & Salvar
            </button>
          </div>
        </>
      )}

      {step === "saving" && (
        <div className="flex items-center justify-center flex-1">
          <p className="text-[#8b949e] text-sm">Salvando nota…</p>
        </div>
      )}
    </div>
  );
}
