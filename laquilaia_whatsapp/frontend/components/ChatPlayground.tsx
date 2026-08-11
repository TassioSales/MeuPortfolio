"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Button } from "./Button";
import { ConfirmDialog } from "./ConfirmDialog";
import { LoadingSpinner } from "./LoadingSpinner";
import { useChat } from "@/hooks/useChat";
import { cn } from "@/lib/utils";
import type { Agent } from "@/types";

interface ChatPlaygroundProps {
  agent: Agent;
}

export function ChatPlayground({ agent }: ChatPlaygroundProps) {
  const { messages, isLoadingHistory, isSending, error, send, reset } = useChat(agent.id);

  const [draft, setDraft] = useState("");
  const [isResetOpen, setIsResetOpen] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  // Mantém a conversa rolada para a última mensagem.
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = draft;
    setDraft("");
    try {
      await send(text);
    } catch {
      // Falhou: devolve o texto para o usuário poder reenviar.
      setDraft(text);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter envia, Shift+Enter quebra linha.
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <div className="flex h-[calc(100vh-10rem)] flex-col rounded-xl border border-surface-border bg-white">
      <header className="flex items-start justify-between gap-4 border-b border-surface-border px-5 py-4">
        <div className="min-w-0">
          <h2 className="truncate text-sm font-semibold text-gray-900">{agent.nome}</h2>
          <p className="mt-0.5 text-xs text-gray-500">
            temperatura {agent.temperatura} · máx. {agent.max_tokens} tokens
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={() => setIsResetOpen(true)}
          disabled={messages.length === 0}
        >
          Limpar conversa
        </Button>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        {isLoadingHistory ? (
          <div className="flex h-full items-center justify-center">
            <LoadingSpinner label="Carregando conversa..." />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <span aria-hidden="true" className="text-3xl">
              💬
            </span>
            <p className="text-sm font-medium text-gray-900">Converse com o agente</p>
            <p className="max-w-sm text-sm text-gray-600">
              As mensagens usam o system prompt configurado. É o mesmo comportamento que
              o cliente teria no WhatsApp.
            </p>
          </div>
        ) : (
          messages.map((message) => {
            const isUser = message.remetente === "user";
            return (
              <div
                key={message.id}
                className={cn("flex", isUser ? "justify-end" : "justify-start")}
              >
                <div
                  className={cn(
                    "max-w-[75%] rounded-2xl px-4 py-2.5 text-sm",
                    isUser
                      ? "bg-brand-600 text-white"
                      : "bg-surface-muted text-gray-900",
                  )}
                >
                  {message.pending ? (
                    <span className="flex items-center gap-2 text-gray-500">
                      <LoadingSpinner size="sm" label="Aguardando resposta" />
                      digitando...
                    </span>
                  ) : (
                    <p className="whitespace-pre-wrap break-words">{message.conteudo}</p>
                  )}
                  {message.tokens !== undefined && (
                    <p className="mt-1 text-xs text-gray-500">{message.tokens} tokens</p>
                  )}
                </div>
              </div>
            );
          })
        )}
        <div ref={endRef} />
      </div>

      {error && (
        <p
          role="alert"
          className="mx-5 mb-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {error}
        </p>
      )}

      <form
        onSubmit={handleSubmit}
        className="flex items-end gap-3 border-t border-surface-border p-4"
      >
        <label htmlFor="chat-draft" className="sr-only">
          Mensagem
        </label>
        <textarea
          id="chat-draft"
          name="message"
          rows={1}
          placeholder="Escreva como se fosse o cliente..."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          className="max-h-32 min-h-[2.75rem] flex-1 resize-y rounded-lg border border-surface-border px-3 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
        />
        <Button type="submit" isLoading={isSending} disabled={!draft.trim()}>
          Enviar
        </Button>
      </form>

      <ConfirmDialog
        isOpen={isResetOpen}
        title="Limpar conversa"
        message="As mensagens desta conversa de teste serão apagadas. Os agentes e as conversas reais do WhatsApp não são afetados."
        confirmLabel="Limpar"
        onConfirm={async () => {
          await reset();
          setIsResetOpen(false);
        }}
        onCancel={() => setIsResetOpen(false)}
      />
    </div>
  );
}

export default ChatPlayground;
