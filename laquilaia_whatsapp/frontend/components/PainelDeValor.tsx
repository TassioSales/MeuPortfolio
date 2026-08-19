"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/Button";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { messageFrom } from "@/hooks/useAgents";
import { buscarValor } from "@/lib/valor";
import { cn } from "@/lib/utils";
import type { ValorResponse } from "@/types";

const PERIODOS = [
  { dias: 30, rotulo: "30 dias" },
  { dias: 90, rotulo: "90 dias" },
  { dias: 365, rotulo: "1 ano" },
];

/** Sem centavos: a estimativa não tem essa precisão. */
function emReais(valor: number): string {
  return valor.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  });
}

function dataCurta(iso: string): string {
  const data = new Date(`${iso}T00:00`);
  if (Number.isNaN(data.getTime())) return iso;
  return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

/**
 * O valor entrando ao longo do tempo, em barras proporcionais.
 *
 * Um gráfico de verdade traria uma biblioteca inteira para desenhar quinze
 * barras. Estas são divs com largura proporcional — leem-se igual, funcionam
 * no tema escuro e não pesam nada.
 */
function PorDia({ dados }: { dados: ValorResponse }) {
  const teto = Math.max(1, ...dados.por_dia.map((d) => d.total_max));

  if (dados.por_dia.length === 0) {
    return (
      <p className="rounded-xl border border-surface-border bg-surface px-5 py-8 text-center text-sm text-fg-muted">
        Nenhum caso dimensionado no período.
      </p>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-surface-border bg-surface">
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">Valor estimado por dia</caption>
        <tbody>
          {dados.por_dia.map((dia) => (
            <tr key={dia.data} className="border-b border-surface-border last:border-0">
              <th
                scope="row"
                className="w-20 px-4 py-2 text-left text-xs font-normal tabular-nums text-fg-muted"
              >
                {dataCurta(dia.data)}
              </th>
              <td className="py-2 pr-2">
                <div className="h-4 overflow-hidden rounded bg-surface-muted">
                  <div
                    className="h-full rounded bg-brand-600"
                    style={{ width: `${(dia.total_max / teto) * 100}%` }}
                  />
                </div>
              </td>
              <td className="w-32 px-4 py-2 text-right text-xs tabular-nums text-fg-soft">
                {emReais(dia.total_max)}
              </td>
              <td className="w-16 px-2 py-2 text-right text-xs tabular-nums text-fg-muted">
                {dia.casos}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Quanto vale o que entrou, e de onde veio.
 *
 * As métricas contavam gente. Um escritório não vive de quantidade de
 * conversa — vive do tamanho das causas. Dois meses com o mesmo número de
 * leads podem valer dez vezes um ao outro, e o painel dizia que eram iguais.
 */
export function PainelDeValor({ agentId }: { agentId: string }) {
  const [dias, setDias] = useState(30);
  const [dados, setDados] = useState<ValorResponse | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setDados(await buscarValor(agentId, dias));
      setErro(null);
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível carregar os valores."));
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

      <section className="rounded-xl border border-surface-border bg-surface p-5">
        <p className="text-xs uppercase tracking-wide text-fg-muted">
          Valor estimado que entrou
        </p>
        {/* A faixa inteira, não uma média: o parecer estima faixa porque não
            tem documento, e achatar isso inventa precisão. */}
        <p className="mt-1 text-3xl font-semibold tabular-nums text-fg">
          {emReais(dados.total_min)} – {emReais(dados.total_max)}
        </p>
        <p className="mt-1 text-sm text-fg-muted">
          {dados.casos_dimensionados} caso{dados.casos_dimensionados === 1 ? "" : "s"} dimensionado
          {dados.casos_dimensionados === 1 ? "" : "s"}
          {/* Os sem estimativa aparecem para a soma não parecer o total. */}
          {dados.casos_sem_valor > 0 &&
            ` · ${dados.casos_sem_valor} sem estimativa, fora da soma`}
        </p>
        <p className="mt-2 text-xs text-fg-faint">
          Estimativa de parecer preliminar, sem documento na mão. Serve para
          comparar períodos e campanhas, não para prometer a ninguém.
        </p>
      </section>

      <section>
        <h3 className="mb-2 text-sm font-medium text-fg">Por porte</h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {dados.por_porte.map((faixa) => (
            <div
              key={faixa.porte}
              className={cn(
                "rounded-xl border border-surface-border bg-surface p-4",
                faixa.porte === "alto" && "ring-1 ring-brand-500",
              )}
            >
              <p className="text-xs uppercase tracking-wide text-fg-muted">
                {faixa.porte === "indeterminado" ? "Sem estimativa" : faixa.porte}
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-fg">
                {faixa.casos}
              </p>
              <p className="mt-1 text-xs text-fg-soft">{faixa.rotulo}</p>
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs text-fg-muted">
          A média esconde: dez causas de mil e uma de cem mil dão a mesma média
          que onze de dez mil, e não são o mesmo escritório.
        </p>
      </section>

      <section>
        <h3 className="mb-2 text-sm font-medium text-fg">Por dia</h3>
        <PorDia dados={dados} />
      </section>

      <section>
        <h3 className="mb-2 text-sm font-medium text-fg">De onde vem</h3>
        {dados.por_uf.length === 0 ? (
          <p className="rounded-xl border border-surface-border bg-surface px-5 py-8 text-center text-sm text-fg-muted">
            Nenhum caso no período.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-surface-border bg-surface">
            <table className="w-full min-w-[28rem] border-collapse text-sm">
              <thead>
                <tr className="border-b border-surface-border text-left text-xs uppercase tracking-wide text-fg-muted">
                  <th className="px-4 py-3 font-medium">Estado</th>
                  <th className="px-4 py-3 font-medium">Casos</th>
                  <th className="px-4 py-3 font-medium">Dimensionados</th>
                  <th className="px-4 py-3 text-right font-medium">Valor até</th>
                </tr>
              </thead>
              <tbody>
                {dados.por_uf.map((estado) => (
                  <tr
                    key={estado.uf}
                    className="border-b border-surface-border last:border-0"
                  >
                    <td className="px-4 py-2 font-medium text-fg">
                      {estado.uf === "??" ? "Não identificado" : estado.uf}
                    </td>
                    <td className="px-4 py-2 tabular-nums text-fg-soft">{estado.leads}</td>
                    <td className="px-4 py-2 tabular-nums text-fg-soft">
                      {estado.casos_dimensionados}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums text-fg-soft">
                      {emReais(estado.total_max)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-2 text-xs text-fg-muted">
          Lido do DDD do telefone — não há campo de endereço no cadastro. O DDD
          diz a origem da linha, não onde a pessoa mora: serve para decidir
          campanha, não para endereço processual.
        </p>
      </section>
    </div>
  );
}

export default PainelDeValor;
