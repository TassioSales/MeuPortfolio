"use client";
import { useState, useRef } from "react";
import { Play, Send } from "lucide-react";
import { streamSimulation } from "@/lib/api";
import { PageTransition } from "@/components/layout/PageTransition";

const SCENARIOS = [
  { id: "client_requirements", label: "Reunião de Requisitos", desc: "Cliente exigente em meeting de levantamento" },
  { id: "technical_interview", label: "Entrevista Técnica", desc: "Entrevistador senior avaliando suas habilidades" },
  { id: "stakeholder_update", label: "Update para Stakeholder", desc: "Executivo querendo status conciso do projeto" },
  { id: "code_review", label: "Code Review", desc: "Senior dev revisando seu código" },
];

interface Msg { role: "ai" | "user"; content: string; }

export default function SimulationPage() {
  const [scenario, setScenario] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  async function startSim(sc: string) {
    setScenario(sc);
    setMessages([]);
    setLoading(true);
    setSessionId(null);

    let buf = "";
    setMessages([{ role: "ai", content: "" }]);

    await streamSimulation(
      "start",
      { scenario: sc },
      (token) => {
        buf += token;
        setMessages([{ role: "ai", content: buf }]);
      },
      (sid) => setSessionId(sid),
    );

    setLoading(false);
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }

  async function respond() {
    if (!input.trim() || loading) return;
    const msg = input.trim();
    setInput("");

    const history = messages.map((m) => ({
      role: m.role === "ai" ? "assistant" : "user",
      content: m.content,
    }));

    setMessages((m) => [...m, { role: "user", content: msg }]);
    setLoading(true);

    let buf = "";
    setMessages((m) => [...m, { role: "ai", content: "" }]);

    await streamSimulation(
      "respond",
      { scenario, session_id: sessionId ?? "", user_message: msg, history },
      (token) => {
        buf += token;
        setMessages((m) => {
          const copy = [...m];
          copy[copy.length - 1] = { role: "ai", content: buf };
          return copy;
        });
      },
    );

    setLoading(false);
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <PageTransition>
      <div className="p-6 h-full flex flex-col max-w-3xl">
        <h1 className="text-xl font-bold text-text-primary mb-1">Simulation</h1>
        <p className="text-text-muted text-sm mb-4">Pratique cenários reais com IA antes de encarar o cliente</p>

        {!scenario ? (
          <div className="grid grid-cols-2 gap-3">
            {SCENARIOS.map((s) => (
              <button key={s.id} onClick={() => startSim(s.id)}
                aria-label={`Iniciar simulação: ${s.label}`}
                className="bg-surface-raised border border-border hover:border-accent/40 rounded-xl p-4 text-left transition-all group"
              >
                <Play size={16} className="text-text-muted group-hover:text-accent mb-2 transition-colors" />
                <p className="font-semibold text-text-primary text-sm">{s.label}</p>
                <p className="text-xs text-text-muted mt-0.5">{s.desc}</p>
              </button>
            ))}
          </div>
        ) : (
          <div className="flex flex-col flex-1 min-h-0">
            <div className="flex items-center gap-2 mb-4">
              <span className="text-xs text-accent bg-accent/10 px-2 py-1 rounded-full">
                {SCENARIOS.find((s) => s.id === scenario)?.label}
              </span>
              <button onClick={() => setScenario("")}
                className="text-xs text-text-muted hover:text-text-primary ml-auto">
                Trocar cenário
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 mb-4">
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[80%] px-3 py-2 rounded-xl text-sm ${
                    m.role === "user"
                      ? "bg-accent text-surface font-medium"
                      : "bg-surface-raised border border-border text-text-primary"
                  }`}>
                    {m.content || <span className="animate-pulse">▊</span>}
                  </div>
                </div>
              ))}
              <div ref={endRef} />
            </div>

            <div className="flex gap-2">
              <input value={input} onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && respond()}
                placeholder="Sua resposta..." disabled={loading}
                aria-label="Sua resposta na simulação"
                className="flex-1 bg-surface border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder:text-text-muted outline-none focus:border-accent/60"
              />
              <button onClick={respond} disabled={loading || !input.trim()}
                aria-label="Enviar resposta"
                className="p-2.5 bg-accent text-surface rounded-lg disabled:opacity-40 hover:bg-accent-dim transition-colors">
                <Send size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </PageTransition>
  );
}
