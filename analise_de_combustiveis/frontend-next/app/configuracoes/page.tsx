"use client";

import { useState, useEffect } from "react";
import { BrainCircuit, CheckCircle2, ChevronRight, Eye, EyeOff, Key, Trash2, XCircle } from "lucide-react";

import { Card } from "@/components/ui/card";
import { useSettingsStore } from "@/lib/store";

const MODELS = [
  { id: "mistral-small-latest", label: "Mistral Small", note: "Rapido e economico" },
  { id: "mistral-large-latest", label: "Mistral Large", note: "Mais preciso, mais lento" },
];

const TUTORIAL_STEPS = [
  {
    n: "01",
    title: "Acesse o console da Mistral AI",
    body: "Va ate console.mistral.ai e crie uma conta gratuita. Nao e necessario cartao de credito para o plano gratuito.",
    tag: "Gratuito",
  },
  {
    n: "02",
    title: "Gere uma API Key",
    body: 'No menu lateral, clique em "API Keys" e depois em "Create new key". Copie a chave gerada — ela so aparece uma vez.',
    tag: "API Keys",
  },
  {
    n: "03",
    title: "Cole a chave aqui",
    body: 'Cole a chave no campo acima e clique em "Salvar chave". Ela fica salva no seu navegador e nunca e enviada para nenhum servidor externo.',
    tag: "Seguro",
  },
];

export default function ConfiguracoesPage() {
  const { mistralKey, mistralModel, setMistralKey, setMistralModel, clearKey } = useSettingsStore();

  const [inputKey, setInputKey] = useState("");
  const [inputModel, setInputModel] = useState(mistralModel);
  const [showKey, setShowKey] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setInputKey(mistralKey);
    setInputModel(mistralModel);
  }, [mistralKey, mistralModel]);

  function handleSave() {
    setMistralKey(inputKey.trim());
    setMistralModel(inputModel);
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  }

  function handleClear() {
    clearKey();
    setInputKey("");
    setSaved(false);
  }

  const hasKey = Boolean(mistralKey);
  const inputChanged = inputKey.trim() !== mistralKey || inputModel !== mistralModel;

  return (
    <main className="space-y-6 pb-10">
      <div className="space-y-2">
        <p className="text-xs font-bold uppercase tracking-[0.4em] text-accent">Intelligence Setup</p>
        <h1 className="font-display text-4xl text-white">Configuracoes de IA</h1>
        <p className="text-sm leading-7 text-mist/80">
          A chave fica armazenada apenas no seu navegador e e enviada diretamente para a API da Mistral sem passar por nenhum servidor intermediario.
        </p>
      </div>

      {/* Status badge */}
      <div className="flex items-center gap-3">
        {hasKey ? (
          <span className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-4 py-1.5 text-xs font-bold uppercase tracking-[0.2em] text-accent">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Chave configurada — Mistral ativo
          </span>
        ) : (
          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-1.5 text-xs font-bold uppercase tracking-[0.2em] text-white/40">
            <XCircle className="h-3.5 w-3.5" />
            Sem chave — modo fallback
          </span>
        )}
      </div>

      {/* Key input card */}
      <Card className="space-y-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-black/20">
            <Key className="h-5 w-5 text-accent" />
          </div>
          <div>
            <p className="font-semibold text-white">Mistral API Key</p>
            <p className="text-xs text-mist/60">Salva localmente no navegador</p>
          </div>
        </div>

        <div className="relative">
          <input
            type={showKey ? "text" : "password"}
            value={inputKey}
            onChange={(e) => setInputKey(e.target.value)}
            placeholder="Digite ou cole sua API key aqui..."
            spellCheck={false}
            className="w-full rounded-[1.4rem] border border-white/10 bg-black/25 px-5 py-4 pr-14 text-sm text-white placeholder:text-white/25 outline-none transition focus:border-accent/40 focus:bg-black/35"
          />
          <button
            type="button"
            onClick={() => setShowKey((v) => !v)}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/70 transition"
          >
            {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-[0.3em] text-white/35">Modelo</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {MODELS.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setInputModel(m.id)}
                className={`flex items-start gap-3 rounded-[1.4rem] border p-4 text-left transition ${
                  inputModel === m.id
                    ? "border-accent/30 bg-accent/10 text-white"
                    : "border-white/8 bg-white/[0.03] text-mist hover:bg-white/[0.06]"
                }`}
              >
                <div className={`mt-0.5 h-3 w-3 shrink-0 rounded-full border-2 ${inputModel === m.id ? "border-accent bg-accent" : "border-white/20"}`} />
                <div>
                  <p className="text-sm font-semibold">{m.label}</p>
                  <p className="text-xs text-mist/60">{m.note}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={handleSave}
            disabled={!inputChanged && !saved}
            className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-6 py-2.5 text-sm font-semibold text-accent transition hover:bg-accent/20 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {saved ? <CheckCircle2 className="h-4 w-4" /> : <Key className="h-4 w-4" />}
            {saved ? "Salvo!" : "Salvar chave"}
          </button>

          {hasKey && (
            <button
              type="button"
              onClick={handleClear}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-6 py-2.5 text-sm font-semibold text-white/50 transition hover:border-coral/30 hover:text-coral"
            >
              <Trash2 className="h-4 w-4" />
              Remover chave
            </button>
          )}
        </div>
      </Card>

      {/* Tutorial */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <BrainCircuit className="h-5 w-5 text-accent/70" />
          <p className="text-xs font-bold uppercase tracking-[0.4em] text-white/40">Como obter sua chave</p>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          {TUTORIAL_STEPS.map((step) => (
            <Card key={step.n} className="flex flex-col gap-5 border-white/[0.06] bg-black/15">
              <div className="flex items-start justify-between">
                <span className="font-display text-4xl font-bold text-white/10">{step.n}</span>
                <span className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-white/35">
                  {step.tag}
                </span>
              </div>
              <div>
                <p className="font-semibold text-white">{step.title}</p>
                <p className="mt-2 text-sm leading-7 text-mist/75">{step.body}</p>
              </div>
            </Card>
          ))}
        </div>

        {/* Highlight box */}
        <Card className="border-accent/15 bg-[linear-gradient(135deg,rgba(54,214,167,0.07),rgba(107,184,255,0.05))]">
          <div className="grid gap-6 lg:grid-cols-[1fr_auto]">
            <div className="space-y-3">
              <p className="text-xs font-bold uppercase tracking-[0.3em] text-accent/70">Por que a Mistral?</p>
              <p className="font-display text-2xl text-white">IA local, plano gratuito e JSON nativo</p>
              <ul className="space-y-2">
                {[
                  "Plano free com limite generoso — suficiente para uso diario neste dashboard.",
                  "Suporte nativo a JSON estruturado, essencial para os briefings do sistema.",
                  "Latencia baixa e sem dependencia de nuvem proprietaria.",
                  "Sem a chave, o sistema usa fallback analitico local (sem IA generativa).",
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3 text-sm text-mist/80">
                    <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-accent/50" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex items-center">
              <a
                href="https://console.mistral.ai"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-6 py-3 text-sm font-semibold text-accent transition hover:bg-accent/20 whitespace-nowrap"
              >
                Abrir console
                <ChevronRight className="h-4 w-4" />
              </a>
            </div>
          </div>
        </Card>
      </div>
    </main>
  );
}
