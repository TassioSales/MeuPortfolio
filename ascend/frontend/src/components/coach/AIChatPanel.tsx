"use client";
import { useState, useRef, useEffect } from "react";
import { Send, Sparkles } from "lucide-react";
import { streamChat, api } from "@/lib/api";

interface Message { role: "user" | "assistant"; content: string; }

const WELCOME: Message = { role: "assistant", content: "Olá! Sou o Trilha, seu AI Coach de carreira. Como posso te ajudar hoje?" };
const SUGGESTED = [
  "O que devo priorizar esta semana?",
  "Como acelero meu progresso?",
  "Quais skills são mais valorizadas?",
];

const MAX_HISTORY = 20;

export function AIChatPanel() {
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [showSuggested, setShowSuggested] = useState(true);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  // Carrega histórico da API ao montar
  useEffect(() => {
    api.coach.history(0, 50).then((history) => {
      if (!history.length) return;
      const loaded: Message[] = history.map((m) => ({
        role: m.role as "user" | "assistant",
        content: m.content,
      }));
      setMessages(loaded);
      setShowSuggested(false);
    }).catch(() => {
      // falha silenciosa — mantém mensagem de boas-vindas
    });
  }, []);

  async function send(text?: string) {
    const content = (text ?? input).trim();
    if (!content || streaming) return;
    setInput("");
    setShowSuggested(false);

    const userMsg: Message = { role: "user", content };
    setMessages((m) => [...m, userMsg]);
    setStreaming(true);

    // Envia apenas as últimas MAX_HISTORY mensagens para não estourar o contexto do modelo
    const allMessages = [...messages, userMsg];
    const history = allMessages.slice(-MAX_HISTORY).map((m) => ({ role: m.role, content: m.content }));
    let buffer = "";
    setMessages((m) => [...m, { role: "assistant", content: "" }]);

    try {
      await streamChat(history, (token) => {
        buffer += token;
        setMessages((m) => {
          const copy = [...m];
          copy[copy.length - 1] = { role: "assistant", content: buffer };
          return copy;
        });
      });
    } finally {
      setStreaming(false);
    }
  }

  return (
    <div className="flex flex-col h-full rounded-xl border border-border bg-surface-card shadow-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2.5 px-4 py-3 border-b border-border bg-surface-raised">
        <div className="w-7 h-7 rounded-lg bg-accent/15 border border-accent/25 flex items-center justify-center">
          <Sparkles size={13} className="text-accent" />
        </div>
        <div>
          <p className="text-sm font-semibold text-text-primary leading-tight">AI Coach</p>
          <p className="text-[10px] text-text-muted">Personalizado para sua carreira</p>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-slow" />
          <span className="text-[10px] text-accent font-medium">Online</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-0">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            {m.role === "assistant" && (
              <div className="w-6 h-6 rounded-md bg-accent/15 border border-accent/25 flex items-center justify-center mr-2 mt-0.5 shrink-0">
                <Sparkles size={10} className="text-accent" />
              </div>
            )}
            <div
              className={`max-w-[80%] px-3 py-2 rounded-xl text-sm leading-relaxed ${
                m.role === "user"
                  ? "text-surface font-medium rounded-br-sm"
                  : "bg-surface-high border border-border text-text-primary rounded-bl-sm"
              }`}
              style={m.role === "user" ? { background: "linear-gradient(135deg,#00e87a,#00b85e)" } : {}}
            >
              {m.content || (streaming && i === messages.length - 1
                ? <span className="inline-flex gap-0.5 mt-1">
                    <span className="w-1 h-1 bg-accent rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1 h-1 bg-accent rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1 h-1 bg-accent rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </span>
                : null)}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {/* Suggested prompts */}
      {showSuggested && messages.length === 1 && (
        <div className="px-3 pb-2 flex flex-col gap-1">
          {SUGGESTED.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="text-left text-xs text-text-muted px-3 py-2 rounded-lg bg-surface-high border border-border hover:border-border-bright hover:text-text-primary transition-all"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="p-3 border-t border-border flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          placeholder="Pergunte ao seu coach..."
          disabled={streaming}
          aria-label="Mensagem para o coach"
          className="flex-1 bg-surface-high border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-dim outline-none focus:border-accent/50 transition-colors disabled:opacity-50"
        />
        <button
          onClick={() => send()}
          disabled={streaming || !input.trim()}
          aria-label="Enviar mensagem"
          className="p-2 rounded-lg text-surface disabled:opacity-40 transition-all shadow-accent-sm hover:shadow-accent-md"
          style={{ background: "linear-gradient(135deg,#00e87a,#00b85e)" }}
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}
