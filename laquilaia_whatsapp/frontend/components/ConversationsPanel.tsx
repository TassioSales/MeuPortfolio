"use client";

import { useCallback } from "react";

import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { useAgentEvents } from "@/hooks/useAgentEvents";
import { useConversations } from "@/hooks/useConversations";
import { cn } from "@/lib/utils";
import { ParecerPreliminar } from "./ParecerPreliminar";
import type { ConversationSummary } from "@/types";

/** Data curta e legível; o ano só aparece quando não é o corrente. */
function formatarQuando(iso: string | null): string {
  if (!iso) return "—";
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return "—";

  const hoje = new Date();
  const mesmoDia =
    data.getDate() === hoje.getDate() &&
    data.getMonth() === hoje.getMonth() &&
    data.getFullYear() === hoje.getFullYear();

  if (mesmoDia) {
    return data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  }
  return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

function formatarHorario(iso: string): string {
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return "";
  return data.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Quem está respondendo.
 *
 * O texto acompanha a cor porque a distinção entre "IA" e "humano" é a
 * informação mais importante da tela e não pode depender de enxergar cor.
 */
function SeloDeAutomacao({ iaAtiva }: { iaAtiva: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        iaAtiva ? "bg-brand-50 text-brand-700" : "bg-amber-100 text-amber-800",
      )}
    >
      <span aria-hidden="true">{iaAtiva ? "🤖" : "🙋"}</span>
      {iaAtiva ? "IA responde" : "Humano assumiu"}
    </span>
  );
}

function ItemDaFila({
  conversa,
  ativa,
  onSelect,
}: {
  conversa: ConversationSummary;
  ativa: boolean;
  onSelect: () => void;
}) {
  const titulo = conversa.lead_nome ?? conversa.phone_number;

  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        aria-current={ativa ? "true" : undefined}
        className={cn(
          "w-full border-b border-surface-border px-4 py-3 text-left transition-colors",
          ativa ? "bg-brand-50" : "hover:bg-surface-muted",
        )}
      >
        <div className="flex items-baseline justify-between gap-2">
          <span className="truncate text-sm font-medium text-gray-900">{titulo}</span>
          <span className="shrink-0 text-xs text-gray-500">
            {formatarQuando(conversa.data_ultima_msg)}
          </span>
        </div>

        {conversa.lead_nome && (
          <p className="mt-0.5 truncate text-xs text-gray-500">
            {conversa.phone_number}
          </p>
        )}

        <p className="mt-1 truncate text-sm text-gray-600">
          {conversa.ultimo_remetente === "assistant" && (
            <span className="text-gray-400">IA: </span>
          )}
          {conversa.ultima_mensagem ?? "Sem mensagens"}
        </p>

        {!conversa.ia_ativa && (
          <span className="mt-2 inline-block">
            <SeloDeAutomacao iaAtiva={false} />
          </span>
        )}
      </button>
    </li>
  );
}

/**
 * Fila de atendimentos com a transcrição e o controle da pausa humana.
 *
 * Existe porque a IA responde sozinha por padrão: quando o operador precisa
 * assumir, ele pausa a conversa aqui e o agente para de responder. As
 * mensagens do cliente continuam sendo registradas — é justamente elas que o
 * operador precisa ler.
 */
export function ConversationsPanel({ agentId }: { agentId: string }) {
  const {
    conversations,
    selectedId,
    transcript,
    isLoading,
    isLoadingTranscript,
    isTogglingPause,
    error,
    openConversation,
    togglePause,
    reload,
  } = useConversations(agentId);

  // Mensagem nova de qualquer conversa deste agente atualiza a fila. O evento
  // não carrega o conteúdo de propósito; quem precisa dele busca pela API.
  const aoReceberEvento = useCallback(
    (evento: { type: string }) => {
      if (evento.type === "new_message") void reload();
    },
    [reload],
  );
  const { isConnected } = useAgentEvents(agentId, aoReceberEvento);

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner label="Carregando atendimentos..." />
      </div>
    );
  }

  if (error && conversations.length === 0) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-5">
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
        <Button variant="secondary" className="mt-4" onClick={() => void reload()}>
          Tentar novamente
        </Button>
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <EmptyState
        icon="💤"
        title="Nenhum atendimento ainda"
        description="As conversas aparecem aqui quando chegam pelo WhatsApp. As do chat de teste não entram nesta fila."
      />
    );
  }

  return (
    <div>
      <p className="mb-3 flex items-center gap-2 text-xs text-gray-500">
        <span
          aria-hidden="true"
          className={cn(
            "inline-block h-2 w-2 rounded-full",
            isConnected ? "bg-green-500" : "bg-gray-300",
          )}
        />
        {isConnected ? "Atualizando em tempo real" : "Sem conexão em tempo real"}
      </p>

      {error && (
        <p
          role="alert"
          className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {error}
        </p>
      )}

      <div className="grid gap-4 md:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
        <div className="overflow-hidden rounded-xl border border-surface-border bg-white">
          <h2 className="border-b border-surface-border px-4 py-3 text-sm font-medium text-gray-900">
            Atendimentos ({conversations.length})
          </h2>
          <ul className="max-h-[32rem] overflow-y-auto">
            {conversations.map((conversa) => (
              <ItemDaFila
                key={conversa.id}
                conversa={conversa}
                ativa={conversa.id === selectedId}
                onSelect={() => void openConversation(conversa.id)}
              />
            ))}
          </ul>
        </div>

        <div className="rounded-xl border border-surface-border bg-white">
          {!selectedId ? (
            <div className="px-6 py-14 text-center text-sm text-gray-600">
              Escolha um atendimento para ler a conversa e decidir se assume.
            </div>
          ) : isLoadingTranscript ? (
            <div className="flex justify-center py-14">
              <LoadingSpinner label="Abrindo conversa..." />
            </div>
          ) : !transcript ? (
            <div className="px-6 py-14 text-center text-sm text-gray-600">
              Não foi possível abrir esta conversa.
            </div>
          ) : (
            <>
              <header className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-border px-4 py-3">
                <div className="min-w-0">
                  <h2 className="truncate text-sm font-medium text-gray-900">
                    {transcript.lead_nome ?? transcript.phone_number}
                  </h2>
                  {transcript.lead_nome && (
                    <p className="truncate text-xs text-gray-500">
                      {transcript.phone_number}
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  <SeloDeAutomacao iaAtiva={transcript.ia_ativa} />
                  <Button
                    variant={transcript.ia_ativa ? "secondary" : "primary"}
                    isLoading={isTogglingPause}
                    onClick={() => void togglePause()}
                  >
                    {transcript.ia_ativa ? "Assumir conversa" : "Devolver para a IA"}
                  </Button>
                </div>
              </header>

              <p className="border-b border-surface-border bg-surface-muted px-4 py-2 text-xs text-gray-600">
                {transcript.ia_ativa
                  ? "O agente está respondendo automaticamente. Assuma para que ele pare."
                  : "A IA parou de responder. As mensagens do cliente continuam chegando e ficam registradas aqui."}
              </p>

              {transcript.analise_preliminar && (
                <ParecerPreliminar texto={transcript.analise_preliminar} />
              )}

              <div className="max-h-[26rem] space-y-3 overflow-y-auto px-4 py-4">
                {transcript.messages.length === 0 ? (
                  <p className="py-8 text-center text-sm text-gray-500">
                    Nenhuma mensagem nesta conversa ainda.
                  </p>
                ) : (
                  transcript.messages.map((mensagem) => {
                    const doCliente = mensagem.remetente === "user";
                    return (
                      <div
                        key={mensagem.id}
                        className={cn(
                          "flex flex-col",
                          doCliente ? "items-start" : "items-end",
                        )}
                      >
                        <div
                          className={cn(
                            "max-w-[85%] rounded-2xl px-3 py-2 text-sm",
                            doCliente
                              ? "rounded-bl-sm bg-surface-muted text-gray-800"
                              : "rounded-br-sm bg-brand-600 text-white",
                          )}
                        >
                          {mensagem.conteudo}
                        </div>
                        <span className="mt-1 text-xs text-gray-400">
                          {doCliente ? "Cliente" : "Agente"} ·{" "}
                          {formatarHorario(mensagem.timestamp)}
                        </span>
                      </div>
                    );
                  })
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default ConversationsPanel;
