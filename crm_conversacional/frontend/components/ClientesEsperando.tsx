"use client";

import { useCallback, useEffect, useState } from "react";

import { messageFrom } from "@/hooks/useAgents";
import { buscarAlertas } from "@/lib/alertas";
import { cn } from "@/lib/utils";
import type { ClienteEsperando } from "@/types";

/** De quanto em quanto tempo a faixa se atualiza sozinha. */
const INTERVALO_MS = 60_000;

/** Quantas linhas cabem antes de virar parede de texto. */
const VISIVEIS = 5;

function tempoEmPalavras(minutos: number): string {
  if (minutos < 60) return `${minutos} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `${horas}h`;
  return `${Math.floor(horas / 24)}d`;
}

/**
 * Quem está esperando resposta agora.
 *
 * O painel mostrava conversas e leads, e nada mostrava **omissão**: quem
 * escreveu de madrugada e não foi respondido tinha a mesma aparência de quem
 * foi atendido. O escritório descobria pelo cliente reclamando.
 *
 * Some quando não há ninguém esperando, de propósito. Uma faixa permanente
 * dizendo "0 pendências" vira paisagem, e no dia em que marcar 12 ninguém
 * repara.
 */
export function ClientesEsperando({
  agentId,
  onAbrir,
}: {
  agentId: string;
  /** Levar o operador direto para a conversa é o ponto da tela. */
  onAbrir?: (conversationId: string) => void;
}) {
  const [conversas, setConversas] = useState<ClienteEsperando[]>([]);
  const [totalIa, setTotalIa] = useState(0);
  const [totalHumano, setTotalHumano] = useState(0);
  const [erro, setErro] = useState<string | null>(null);
  const [expandido, setExpandido] = useState(false);

  const carregar = useCallback(async () => {
    try {
      const dados = await buscarAlertas(agentId);
      setConversas(dados.conversas);
      setTotalIa(dados.total_ia);
      setTotalHumano(dados.total_humano);
      setErro(null);
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível checar quem está esperando."));
    }
  }, [agentId]);

  useEffect(() => {
    void carregar();
    // Releitura periódica: o tempo de espera cresce sozinho e uma tela aberta
    // desde as 8h não pode continuar dizendo "20 min" ao meio-dia.
    const timer = setInterval(() => void carregar(), INTERVALO_MS);
    return () => clearInterval(timer);
  }, [carregar]);

  // O erro não vira faixa vermelha no topo do painel: falhar em *checar*
  // pendência não é uma pendência, e alarme falso custa a credibilidade dos
  // alarmes verdadeiros.
  if (erro || conversas.length === 0) return null;

  const total = totalIa + totalHumano;
  const mostradas = expandido ? conversas : conversas.slice(0, VISIVEIS);

  return (
    <section
      aria-label="Clientes esperando resposta"
      className="mb-4 overflow-hidden rounded-xl border border-amber-300 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/40"
    >
      <header className="flex flex-wrap items-baseline justify-between gap-2 px-4 py-3">
        <h2 className="text-sm font-semibold text-amber-900 dark:text-amber-100">
          {total === 1
            ? "1 cliente esperando resposta"
            : `${total} clientes esperando resposta`}
        </h2>
        <p className="text-xs text-amber-800 dark:text-amber-200">
          {/* Os dois números aparecem separados porque pedem donos diferentes:
              a IA parada é problema de sistema, o humano parado é de agenda. */}
          {totalIa > 0 && `${totalIa} sem resposta da IA`}
          {totalIa > 0 && totalHumano > 0 && " · "}
          {totalHumano > 0 && `${totalHumano} com humano que assumiu`}
        </p>
      </header>

      <ul className="divide-y divide-amber-200 dark:divide-amber-900">
        {mostradas.map((conversa) => {
          const daIa = conversa.tipo === "ia_sem_resposta";
          return (
            <li key={conversa.conversation_id}>
              <button
                type="button"
                onClick={() => onAbrir?.(conversa.conversation_id)}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-amber-100 dark:hover:bg-amber-900/40"
              >
                <span
                  className={cn(
                    "shrink-0 rounded px-1.5 py-0.5 text-[11px] font-medium",
                    daIa
                      ? "bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-200"
                      : "bg-amber-200 text-amber-900 dark:bg-amber-900/60 dark:text-amber-100",
                  )}
                >
                  {daIa ? "IA parada" : "humano assumiu"}
                </span>

                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-amber-950 dark:text-amber-50">
                    {conversa.lead_nome ?? conversa.phone_number}
                  </span>
                  <span className="block truncate text-xs text-amber-800 dark:text-amber-200">
                    {conversa.ultima_mensagem}
                  </span>
                </span>

                <span className="shrink-0 text-xs font-medium tabular-nums text-amber-900 dark:text-amber-100">
                  há {tempoEmPalavras(conversa.minutos_esperando)}
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      {conversas.length > VISIVEIS && (
        <button
          type="button"
          onClick={() => setExpandido((atual) => !atual)}
          className="w-full border-t border-amber-200 px-4 py-2 text-xs font-medium text-amber-900 hover:bg-amber-100 dark:border-amber-900 dark:text-amber-100 dark:hover:bg-amber-900/40"
        >
          {expandido
            ? "Mostrar menos"
            : `Ver os outros ${conversas.length - VISIVEIS}`}
        </button>
      )}
    </section>
  );
}

export default ClientesEsperando;
