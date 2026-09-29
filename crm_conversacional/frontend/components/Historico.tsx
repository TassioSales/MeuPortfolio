"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/Button";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { messageFrom } from "@/hooks/useAgents";
import { buscarHistorico } from "@/lib/historico";
import { formatarTelefone } from "@/lib/telefone";
import type { Movimento } from "@/types";

const PERIODOS = [
  { dias: 7, rotulo: "7 dias" },
  { dias: 30, rotulo: "30 dias" },
  { dias: 90, rotulo: "90 dias" },
];

function quando(iso: string): string {
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return "—";
  return data.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * O que aconteceu com os leads, e por ordem de quem.
 *
 * A trilha existia desde o começo e ninguém nunca a leu — e só a IA escrevia
 * nela. Card arrastado por gente e conversa assumida por gente não deixavam
 * rastro; num escritório com mais de uma pessoa no board, "quem mandou esse
 * caso para o arquivo?" não tinha resposta.
 */
export function Historico({ agentId }: { agentId: string }) {
  const [dias, setDias] = useState(30);
  const [apenasHumanos, setApenasHumanos] = useState(false);
  const [pagina, setPagina] = useState(1);

  const [movimentos, setMovimentos] = useState<Movimento[]>([]);
  const [total, setTotal] = useState(0);
  const [porPagina, setPorPagina] = useState(50);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const dados = await buscarHistorico(agentId, { dias, apenasHumanos, pagina });
      setMovimentos(dados.movimentos);
      setTotal(dados.total);
      setPorPagina(dados.por_pagina);
      setErro(null);
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível carregar o histórico."));
    } finally {
      setCarregando(false);
    }
  }, [agentId, dias, apenasHumanos, pagina]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const paginas = Math.max(1, Math.ceil(total / porPagina));

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Período">
          {PERIODOS.map((opcao) => (
            <button
              key={opcao.dias}
              type="button"
              onClick={() => {
                setDias(opcao.dias);
                setPagina(1);
              }}
              aria-pressed={dias === opcao.dias}
              className={
                dias === opcao.dias
                  ? "rounded-full bg-ink-900 px-3 py-1.5 text-sm font-medium text-white dark:bg-ink-100 dark:text-ink-950"
                  : "rounded-full border border-surface-border bg-surface px-3 py-1.5 text-sm text-fg-soft hover:bg-surface-muted"
              }
            >
              {opcao.rotulo}
            </button>
          ))}
        </div>

        {/* O filtro que faz a tela valer: a IA move dezenas de cards por dia
            e afoga as poucas ações de gente, que são as que se audita. */}
        <label className="flex items-center gap-2 text-sm text-fg-soft">
          <input
            type="checkbox"
            checked={apenasHumanos}
            onChange={(e) => {
              setApenasHumanos(e.target.checked);
              setPagina(1);
            }}
            className="bg-surface"
          />
          Só o que gente fez
        </label>

        <p className="ml-auto text-sm text-fg-muted" role="status">
          {total === 1 ? "1 movimento" : `${total} movimentos`}
        </p>
      </div>

      {erro ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-5 dark:border-red-900 dark:bg-red-950/40">
          <p role="alert" className="text-sm text-red-700 dark:text-red-200">
            {erro}
          </p>
          <Button variant="secondary" className="mt-4" onClick={() => void carregar()}>
            Tentar novamente
          </Button>
        </div>
      ) : carregando && movimentos.length === 0 ? (
        <div className="flex justify-center py-16">
          <LoadingSpinner label="Carregando histórico..." />
        </div>
      ) : movimentos.length === 0 ? (
        <p className="rounded-xl border border-surface-border bg-surface px-5 py-10 text-center text-sm text-fg-muted">
          {apenasHumanos
            ? "Ninguém do escritório mexeu em lead nenhum no período."
            : "Nada aconteceu no período."}
        </p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-surface-border bg-surface">
          <table className="w-full min-w-[44rem] border-collapse text-sm">
            <thead>
              <tr className="border-b border-surface-border text-left text-xs uppercase tracking-wide text-fg-muted">
                <th className="px-4 py-3 font-medium">Quando</th>
                <th className="px-4 py-3 font-medium">Lead</th>
                <th className="px-4 py-3 font-medium">O que aconteceu</th>
                <th className="px-4 py-3 font-medium">Quem</th>
              </tr>
            </thead>
            <tbody>
              {movimentos.map((m) => (
                <tr
                  key={m.id}
                  className="border-b border-surface-border last:border-0 hover:bg-surface-muted"
                >
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums text-fg-muted">
                    {quando(m.quando)}
                  </td>
                  <td className="px-4 py-3">
                    <span className="block font-medium text-fg">
                      {m.lead_nome ?? "Sem nome"}
                    </span>
                    <span className="block text-xs text-fg-muted">
                      {formatarTelefone(m.phone_number)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-fg-soft">
                    {m.motivo ?? `${m.status_anterior ?? "—"} → ${m.status_novo}`}
                  </td>
                  <td className="px-4 py-3">
                    {m.responsavel ? (
                      <span className="text-fg-soft">{m.responsavel}</span>
                    ) : (
                      // A ausência de nome é informação, não lacuna: foi a IA.
                      <span className="rounded bg-surface-muted px-1.5 py-0.5 text-xs text-fg-muted">
                        IA
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {paginas > 1 && (
        <div className="mt-4 flex items-center justify-center gap-3">
          <Button
            variant="secondary"
            disabled={pagina <= 1}
            onClick={() => setPagina((p) => Math.max(1, p - 1))}
          >
            Anterior
          </Button>
          <span className="text-sm tabular-nums text-fg-muted">
            {pagina} de {paginas}
          </span>
          <Button
            variant="secondary"
            disabled={pagina >= paginas}
            onClick={() => setPagina((p) => Math.min(paginas, p + 1))}
          >
            Próxima
          </Button>
        </div>
      )}
    </div>
  );
}

export default Historico;
