"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { useAgentEvents } from "@/hooks/useAgentEvents";
import { useConversations } from "@/hooks/useConversations";
import { cn } from "@/lib/utils";
import { ParecerPreliminar } from "./ParecerPreliminar";
import { CasosDoContato } from "./CasosDoContato";
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
        iaAtiva ? "bg-brand-50 dark:bg-brand-900/40 text-brand-700 dark:text-brand-200" : "bg-amber-100 dark:bg-amber-950/40 text-amber-800 dark:text-amber-200",
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
          ativa ? "bg-brand-50 dark:bg-brand-900/40" : "hover:bg-surface-muted",
        )}
      >
        <div className="flex items-baseline justify-between gap-2">
          <span className="truncate text-sm font-medium text-fg">{titulo}</span>
          <span className="shrink-0 text-xs text-fg-muted">
            {formatarQuando(conversa.data_ultima_msg)}
          </span>
        </div>

        {conversa.lead_nome && (
          <p className="mt-0.5 truncate text-xs text-fg-muted">
            {conversa.phone_number}
          </p>
        )}

        <p className="mt-1 truncate text-sm text-fg-muted">
          {conversa.ultimo_remetente === "assistant" && (
            <span className="text-fg-faint">IA: </span>
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
    responder,
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

  // A transcrição abria no começo: o operador via a primeira frase de um
  // atendimento de trinta mensagens e precisava rolar até o fim para achar o
  // que o cliente acabou de perguntar. Aqui ela abre onde a conversa está.
  const caixaDeMensagens = useRef<HTMLDivElement>(null);
  // Só arrasta para baixo quem já estava embaixo. Puxar a tela de quem subiu
  // para reler uma mensagem antiga é pior do que não rolar nada.
  const noFim = useRef(true);
  const conversaAberta = transcript?.conversation_id ?? null;
  const totalDeMensagens = transcript?.messages.length ?? 0;

  useEffect(() => {
    // Conversa nova sempre começa no fim, independente de onde a anterior
    // estava.
    noFim.current = true;
  }, [conversaAberta]);

  useEffect(() => {
    const caixa = caixaDeMensagens.current;
    if (!caixa || !noFim.current) return;
    caixa.scrollTop = caixa.scrollHeight;
  }, [conversaAberta, totalDeMensagens]);

  function aoRolar() {
    const caixa = caixaDeMensagens.current;
    if (!caixa) return;
    // Uma linha de folga: rolagem por trackpad raramente para no pixel exato.
    const FOLGA = 40;
    noFim.current = caixa.scrollHeight - caixa.scrollTop - caixa.clientHeight < FOLGA;
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner label="Carregando atendimentos..." />
      </div>
    );
  }

  if (error && conversations.length === 0) {
    return (
      <div className="rounded-xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/40 p-5">
        <p role="alert" className="text-sm text-red-700 dark:text-red-200">
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
      <p className="mb-3 flex items-center gap-2 text-xs text-fg-muted">
        <span
          aria-hidden="true"
          className={cn(
            "inline-block h-2 w-2 rounded-full",
            isConnected ? "bg-emerald-500" : "bg-fg-faint",
          )}
        />
        {isConnected ? "Atualizando em tempo real" : "Sem conexão em tempo real"}
      </p>

      {error && (
        <p
          role="alert"
          className="mb-3 rounded-lg border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/40 px-3 py-2 text-sm text-red-700 dark:text-red-200"
        >
          {error}
        </p>
      )}

      <div className="grid gap-4 md:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
        <div className="overflow-hidden rounded-xl border border-surface-border bg-surface">
          <h2 className="border-b border-surface-border px-4 py-3 text-sm font-medium text-fg">
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

        <div className="rounded-xl border border-surface-border bg-surface">
          {!selectedId ? (
            <div className="px-6 py-14 text-center text-sm text-fg-muted">
              Escolha um atendimento para ler a conversa e decidir se assume.
            </div>
          ) : isLoadingTranscript ? (
            <div className="flex justify-center py-14">
              <LoadingSpinner label="Abrindo conversa..." />
            </div>
          ) : !transcript ? (
            <div className="px-6 py-14 text-center text-sm text-fg-muted">
              Não foi possível abrir esta conversa.
            </div>
          ) : (
            <>
              <header className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-border px-4 py-3">
                <div className="min-w-0">
                  <h2 className="truncate text-sm font-medium text-fg">
                    {transcript.lead_nome ?? transcript.phone_number}
                  </h2>
                  {transcript.lead_nome && (
                    <p className="truncate text-xs text-fg-muted">
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

              <p className="border-b border-surface-border bg-surface-muted px-4 py-2 text-xs text-fg-muted">
                {transcript.ia_ativa
                  ? "O agente está respondendo automaticamente. Assuma para que ele pare."
                  : "A IA parou de responder. As mensagens do cliente continuam chegando e ficam registradas aqui."}
              </p>

              <CasosDoContato
                casos={transcript.casos}
                contato={transcript.lead_nome ?? transcript.phone_number}
              />

              {/* O parecer solto é de antes da separação entre contato e
                  caso: some assim que o contato tiver algum caso arquivado. */}
              {transcript.casos.length === 0 && transcript.analise_preliminar && (
                <ParecerPreliminar texto={transcript.analise_preliminar} />
              )}

              <div
                ref={caixaDeMensagens}
                onScroll={aoRolar}
                className="max-h-[26rem] space-y-3 overflow-y-auto px-4 py-4"
              >
                {transcript.messages.length === 0 ? (
                  <p className="py-8 text-center text-sm text-fg-muted">
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
                              ? "rounded-bl-sm bg-surface-muted text-fg"
                              : "rounded-br-sm bg-ink-900 text-white",
                          )}
                        >
                          {mensagem.conteudo}
                        </div>
                        <span className="mt-1 text-xs text-fg-faint">
                          {/* Quem falou importa para quem lê depois: "o
                              escritório disse" é diferente de "a IA disse". */}
                          {doCliente
                            ? "Cliente"
                            : mensagem.remetente === "operador"
                              ? "Você"
                              : "Agente"}{" "}
                          · {formatarHorario(mensagem.timestamp)}
                        </span>
                      </div>
                    );
                  })
                )}
              </div>

              <CaixaDeResposta
                habilitada={!transcript.ia_ativa}
                onEnviar={responder}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Onde o operador escreve.
 *
 * Desabilitada enquanto a IA responde, com o motivo à vista: o backend recusa
 * com 409 de qualquer jeito, e descobrir isso depois de digitar é pior do que
 * ver de antemão por que não dá.
 */
function CaixaDeResposta({
  habilitada,
  onEnviar,
}: {
  habilitada: boolean;
  onEnviar: (conteudo: string) => Promise<void>;
}) {
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const conteudo = texto.trim();
    if (!conteudo || enviando) return;

    setEnviando(true);
    setErro(null);
    try {
      await onEnviar(conteudo);
      // Só limpa depois de dar certo: apagar o que a pessoa escreveu quando o
      // envio falhou faz ela redigitar tudo.
      setTexto("");
    } catch {
      setErro("Não foi possível enviar. A mensagem continua aqui.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form
      onSubmit={enviar}
      className="border-t border-surface-border p-3"
      aria-label="Responder ao cliente"
    >
      {erro && (
        <p role="alert" className="mb-2 text-xs text-red-600 dark:text-red-300">
          {erro}
        </p>
      )}
      <div className="flex items-end gap-2">
        <textarea
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          disabled={!habilitada || enviando}
          rows={2}
          placeholder={
            habilitada
              ? "Escreva para o cliente..."
              : "Assuma a conversa para responder."
          }
          className="min-w-0 flex-1 resize-none rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-fg placeholder:text-fg-faint focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100 disabled:cursor-not-allowed disabled:bg-surface-muted"
        />
        <Button type="submit" disabled={!habilitada || !texto.trim()} isLoading={enviando}>
          Enviar
        </Button>
      </div>
    </form>
  );
}

export default ConversationsPanel;
