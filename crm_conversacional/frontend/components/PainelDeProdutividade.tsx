"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/Button";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { messageFrom } from "@/hooks/useAgents";
import { buscarProdutividade } from "@/lib/valor";
import type { ProdutividadeResponse } from "@/types";

const PERIODOS = [
  { dias: 7, rotulo: "7 dias" },
  { dias: 30, rotulo: "30 dias" },
  { dias: 90, rotulo: "90 dias" },
];

/**
 * Acima disto, o escritório está empurrando o funil à mão.
 *
 * O corte não é ciência — é um sinal para alguém olhar. Um agente que resolve
 * menos da metade do que aparece não está atendendo, está gerando trabalho.
 */
const LIMIAR_DE_ALERTA = 50;

/**
 * O que gente fez, e quem fez.
 *
 * Nos prints do produto concorrente esta tela existe e está vazia: todo card
 * diz "Sem responsável", e o ranking mostra uma pessoa com zero concluídas.
 * Não é defeito de tela — é que lá ninguém registra quem agiu. Aqui dá para
 * preencher porque a trilha passou a gravar cada ação humana.
 *
 * O número que importa não é o total: é a **razão** entre o que a IA resolveu
 * sozinha e o que precisou de gente.
 */
export function PainelDeProdutividade({ agentId }: { agentId: string }) {
  const [dias, setDias] = useState(30);
  const [dados, setDados] = useState<ProdutividadeResponse | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setDados(await buscarProdutividade(agentId, dias));
      setErro(null);
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível carregar a produtividade."));
    } finally {
      setCarregando(false);
    }
  }, [agentId, dias]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  if (carregando && !dados) return <LoadingSpinner label="Carregando..." />;

  if (erro) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-5 dark:border-red-900 dark:bg-red-950/40">
        <p role="alert" className="text-sm text-red-700 dark:text-red-200">
          {erro}
        </p>
        <Button variant="secondary" className="mt-4" onClick={() => void carregar()}>
          Tentar novamente
        </Button>
      </div>
    );
  }

  if (!dados) return null;

  const puxado = dados.percentual_humano >= LIMIAR_DE_ALERTA;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap gap-2" role="group" aria-label="Período">
        {PERIODOS.map((opcao) => (
          <button
            key={opcao.dias}
            type="button"
            onClick={() => setDias(opcao.dias)}
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

      <section className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-surface-border bg-surface p-4">
          <p className="text-xs uppercase tracking-wide text-fg-muted">A IA resolveu</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-fg">
            {dados.acoes_da_ia}
          </p>
        </div>
        <div className="rounded-xl border border-surface-border bg-surface p-4">
          <p className="text-xs uppercase tracking-wide text-fg-muted">Gente precisou agir</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-fg">
            {dados.acoes_de_gente}
          </p>
        </div>
        <div
          className={
            puxado
              ? "rounded-xl border border-amber-300 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/40"
              : "rounded-xl border border-surface-border bg-surface p-4"
          }
        >
          <p className="text-xs uppercase tracking-wide text-fg-muted">Empurrado à mão</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-fg">
            {dados.percentual_humano}%
          </p>
          {puxado && (
            <p className="mt-1 text-xs text-amber-800 dark:text-amber-200">
              Mais da metade do funil está andando por gente.
            </p>
          )}
        </div>
      </section>

      <section>
        <h3 className="mb-2 text-sm font-medium text-fg">Por pessoa</h3>
        {dados.pessoas.length === 0 ? (
          <p className="rounded-xl border border-surface-border bg-surface px-5 py-8 text-center text-sm text-fg-muted">
            Ninguém do escritório mexeu em lead nenhum no período.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-surface-border bg-surface">
            <table className="w-full min-w-[38rem] border-collapse text-sm">
              <thead>
                <tr className="border-b border-surface-border text-left text-xs uppercase tracking-wide text-fg-muted">
                  <th className="px-4 py-3 font-medium">Pessoa</th>
                  <th className="px-4 py-3 font-medium">Ações</th>
                  <th className="px-4 py-3 font-medium">Contatos</th>
                  <th className="px-4 py-3 font-medium">Assumiu</th>
                  <th className="px-4 py-3 font-medium">Devolveu</th>
                  <th className="px-4 py-3 font-medium">Moveu card</th>
                </tr>
              </thead>
              <tbody>
                {dados.pessoas.map((pessoa) => (
                  <tr
                    key={pessoa.nome}
                    className="border-b border-surface-border last:border-0"
                  >
                    <td className="px-4 py-2 font-medium text-fg">{pessoa.nome}</td>
                    <td className="px-4 py-2 tabular-nums text-fg-soft">{pessoa.acoes}</td>
                    {/* Contatos distintos ao lado das ações: quinze ações num
                        lead só não é o mesmo trabalho que uma em quinze. */}
                    <td className="px-4 py-2 tabular-nums text-fg-soft">
                      {pessoa.leads_atendidos}
                    </td>
                    <td className="px-4 py-2 tabular-nums text-fg-soft">
                      {pessoa.conversas_assumidas}
                    </td>
                    <td className="px-4 py-2 tabular-nums text-fg-soft">
                      {pessoa.conversas_devolvidas}
                    </td>
                    <td className="px-4 py-2 tabular-nums text-fg-soft">
                      {pessoa.cards_movidos}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-2 text-xs text-fg-muted">
          Só conta o que passou pelo sistema. Ligação feita pelo celular e
          conversa no corredor não entram — a tela não mede esforço, mede
          registro.
        </p>
      </section>
    </div>
  );
}

export default PainelDeProdutividade;
