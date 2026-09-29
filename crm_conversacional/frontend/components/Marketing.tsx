"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { messageFrom } from "@/hooks/useAgents";
import { useAuth } from "@/hooks/useAuth";
import {
  apagarLancamento,
  buscarResumo,
  criarLancamento,
  listarLancamentos,
} from "@/lib/marketing";
import type { LancamentoMarketing, ResumoMarketing } from "@/types";

const PERIODOS = [
  { dias: 30, rotulo: "30 dias" },
  { dias: 90, rotulo: "90 dias" },
  { dias: 365, rotulo: "1 ano" },
];

function emReais(valor: number): string {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function hoje(): string {
  return new Date().toISOString().slice(0, 10);
}

function dataCurta(iso: string): string {
  // `T00:00` força hora local: `new Date("2026-08-19")` é UTC, e num fuso
  // negativo isso vira 18/08 na tela.
  const data = new Date(`${iso}T00:00`);
  if (Number.isNaN(data.getTime())) return iso;
  return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "2-digit" });
}

function Indicador({
  rotulo,
  valor,
  nota,
  destaque,
}: {
  rotulo: string;
  valor: string;
  nota?: string;
  destaque?: boolean;
}) {
  return (
    <div className="rounded-xl border border-surface-border bg-surface p-4">
      <p className="text-xs uppercase tracking-wide text-fg-muted">{rotulo}</p>
      <p
        className={
          destaque
            ? "mt-1 text-2xl font-semibold tabular-nums text-fg"
            : "mt-1 text-xl font-medium tabular-nums text-fg-soft"
        }
      >
        {valor}
      </p>
      {nota && <p className="mt-1 text-xs text-fg-muted">{nota}</p>}
    </div>
  );
}

/**
 * Quanto custa trazer cada cliente.
 *
 * Era o número que faltava: o painel tinha volume e conversão, e nenhum
 * custo — então "vale a pena?" só tinha resposta no chute.
 *
 * O gasto com anúncio entra à mão porque só o escritório sabe. O consumo de
 * IA não: ele é somado do banco. Pedir os dois digitados é o que o produto
 * concorrente faz, e nos prints dele o campo está em branco.
 */
export function Marketing({ agentId }: { agentId: string }) {
  const { user } = useAuth();
  const eAdmin = user?.papel === "admin";

  const [dias, setDias] = useState(30);
  const [resumo, setResumo] = useState<ResumoMarketing | null>(null);
  const [lancamentos, setLancamentos] = useState<LancamentoMarketing[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const [data, setData] = useState(hoje);
  const [valor, setValor] = useState("");
  const [observacao, setObservacao] = useState("");
  const [salvando, setSalvando] = useState(false);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const [r, l] = await Promise.all([
        buscarResumo(agentId, dias),
        listarLancamentos(dias),
      ]);
      setResumo(r);
      setLancamentos(l);
      setErro(null);
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível carregar os custos."));
    } finally {
      setCarregando(false);
    }
  }, [agentId, dias]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  async function lancar(evento: React.FormEvent) {
    evento.preventDefault();
    // A vírgula do teclado brasileiro chega como "250,50" e `Number` daria
    // NaN — que o backend recusaria com um 422 sem explicação útil.
    const numero = Number(valor.replace(",", "."));
    if (!Number.isFinite(numero) || numero < 0) {
      setErro("Informe um valor válido, como 250,50.");
      return;
    }

    setSalvando(true);
    setErro(null);
    try {
      await criarLancamento({
        data,
        investimento_ads: numero,
        observacao: observacao.trim() || null,
      });
      setValor("");
      setObservacao("");
      await carregar();
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível lançar."));
    } finally {
      setSalvando(false);
    }
  }

  async function remover(id: string) {
    setErro(null);
    try {
      await apagarLancamento(id);
      await carregar();
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível apagar o lançamento."));
    }
  }

  if (carregando && !resumo) return <LoadingSpinner label="Carregando custos..." />;

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Período">
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

      {erro && (
        <p
          role="alert"
          className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200"
        >
          {erro}
        </p>
      )}

      {resumo && (
        <section aria-label="Custo de aquisição" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Indicador rotulo="Investido em anúncios" valor={emReais(resumo.investimento_ads)} />
          <Indicador
            rotulo="Custo por lead"
            valor={resumo.custo_por_lead === null ? "—" : emReais(resumo.custo_por_lead)}
            nota={`${resumo.leads} lead${resumo.leads === 1 ? "" : "s"} no período`}
          />
          {/* O número que decide: um anúncio traz cem pessoas baratas e
              nenhuma da área, e ainda parece ótimo no custo por lead. */}
          <Indicador
            rotulo="Custo por lead qualificado"
            valor={
              resumo.custo_por_lead_qualificado === null
                ? "—"
                : emReais(resumo.custo_por_lead_qualificado)
            }
            nota={`${resumo.leads_qualificados} qualificado${resumo.leads_qualificados === 1 ? "" : "s"}`}
            destaque
          />
          <Indicador
            rotulo="Tokens consumidos"
            valor={resumo.tokens_consumidos.toLocaleString("pt-BR")}
            nota="somado do banco, não digitado"
          />
        </section>
      )}

      {eAdmin && (
        <form
          onSubmit={lancar}
          className="mt-6 rounded-xl border border-surface-border bg-surface p-5"
        >
          <h2 className="mb-4 text-sm font-medium text-fg">Lançar gasto com anúncio</h2>
          <div className="grid items-end gap-4 sm:grid-cols-4">
            <Input
              label="Data"
              type="date"
              value={data}
              onChange={(e) => setData(e.target.value)}
              required
            />
            <Input
              label="Valor (R$)"
              inputMode="decimal"
              placeholder="250,50"
              value={valor}
              onChange={(e) => setValor(e.target.value)}
              required
            />
            <Input
              label="Observação"
              maxLength={500}
              placeholder="Meta Ads — campanha trabalhista"
              value={observacao}
              onChange={(e) => setObservacao(e.target.value)}
            />
            <Button type="submit" isLoading={salvando}>
              Lançar
            </Button>
          </div>
        </form>
      )}

      <section className="mt-6" aria-label="Lançamentos">
        <h2 className="mb-3 text-sm font-medium text-fg">Lançamentos do período</h2>
        {lancamentos.length === 0 ? (
          <p className="rounded-xl border border-surface-border bg-surface px-5 py-8 text-center text-sm text-fg-muted">
            Nenhum gasto lançado. Sem isso, o custo por lead não tem como ser
            calculado.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-surface-border bg-surface">
            <table className="w-full min-w-[36rem] border-collapse text-sm">
              <thead>
                <tr className="border-b border-surface-border text-left text-xs uppercase tracking-wide text-fg-muted">
                  <th className="px-4 py-3 font-medium">Data</th>
                  <th className="px-4 py-3 font-medium">Valor</th>
                  <th className="px-4 py-3 font-medium">Observação</th>
                  <th className="px-4 py-3 font-medium">Quem lançou</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {lancamentos.map((lancamento) => (
                  <tr
                    key={lancamento.id}
                    className="border-b border-surface-border last:border-0"
                  >
                    <td className="whitespace-nowrap px-4 py-3 tabular-nums text-fg-soft">
                      {dataCurta(lancamento.data)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 tabular-nums text-fg">
                      {emReais(lancamento.investimento_ads)}
                    </td>
                    <td className="px-4 py-3 text-fg-soft">{lancamento.observacao ?? "—"}</td>
                    <td className="px-4 py-3 text-fg-muted">{lancamento.criado_por ?? "—"}</td>
                    <td className="px-4 py-3 text-right">
                      {eAdmin && (
                        <button
                          type="button"
                          onClick={() => void remover(lancamento.id)}
                          className="text-xs text-red-700 underline-offset-2 hover:underline dark:text-red-300"
                        >
                          Apagar
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

export default Marketing;
