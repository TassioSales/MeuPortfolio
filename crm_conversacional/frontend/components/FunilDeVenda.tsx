"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/Button";
import { FullPageLoader } from "@/components/LoadingSpinner";
import { messageFrom } from "@/hooks/useAgents";
import { buscarFunil } from "@/lib/funil";
import { cn } from "@/lib/utils";
import type { EtapaDoFunil, FunilResponse } from "@/types";

const PERIODOS = [
  { dias: 0, rotulo: "Desde sempre" },
  { dias: 30, rotulo: "30 dias" },
  { dias: 7, rotulo: "7 dias" },
];

/**
 * Abaixo disto a conversão é ruído.
 *
 * Três leads viram "33% de conversão" no primeiro descarte e "0%" no segundo.
 * O número existe, mas não significa nada — e um painel que mostra números
 * sem significado treina quem lê a ignorá-los.
 */
const AMOSTRA_MINIMA = 10;

function Barra({ percentual, apertou }: { percentual: number; apertou: boolean }) {
  return (
    <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-muted">
      <div
        className={cn("h-full rounded-full", apertou ? "bg-amber-500" : "bg-brand-600")}
        style={{ width: `${Math.min(100, Math.max(0, percentual))}%` }}
      />
    </div>
  );
}

function Etapa({
  etapa,
  posicao,
  confiavel,
  apertou,
}: {
  etapa: EtapaDoFunil;
  posicao: number;
  confiavel: boolean;
  apertou: boolean;
}) {
  return (
    <article className="rounded-xl border border-surface-border bg-surface p-4">
      <header className="flex items-baseline justify-between gap-2">
        <h3 className="truncate text-sm font-medium text-fg" title={etapa.nome}>
          {etapa.nome}
        </h3>
        <span className="shrink-0 text-xs tabular-nums text-fg-faint">
          {String(posicao).padStart(2, "0")}
        </span>
      </header>

      <p className="mt-2 flex items-baseline gap-2">
        <span className="text-3xl font-semibold tabular-nums text-fg">
          {etapa.chegaram}
        </span>
        <span className="text-sm tabular-nums text-fg-muted">
          {etapa.percentual_do_topo}%
        </span>
      </p>

      <Barra percentual={etapa.percentual_do_topo} apertou={apertou} />

      <dl className="mt-3 space-y-1 text-xs">
        <div className="flex justify-between gap-2">
          <dt className="text-fg-muted">Conversão da etapa</dt>
          <dd
            className={cn(
              "tabular-nums",
              apertou ? "font-semibold text-amber-700 dark:text-amber-300" : "text-fg-soft",
            )}
          >
            {/* Sem amostra, o traço em vez do número: "33%" com três leads é
                um número verdadeiro que informa uma coisa falsa. */}
            {confiavel ? `${etapa.conversao_da_etapa}%` : "—"}
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-fg-muted">Parados aqui</dt>
          <dd className="tabular-nums text-fg-soft">{etapa.parados_aqui}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-fg-muted">Interv. humana</dt>
          <dd className="tabular-nums text-fg-soft">{etapa.com_intervencao_humana}</dd>
        </div>
      </dl>
    </article>
  );
}

/**
 * De cada cem que escrevem, quantos viram caso — e onde os outros somem.
 *
 * As métricas que já existiam contam volume: atendimentos, taxa de
 * qualificação, tempo de resposta. Nenhuma responde essa pergunta, que é a
 * que o dono do escritório faz.
 *
 * O número que trabalha aqui não é o percentual do topo — é a **conversão da
 * etapa**. "20% chegaram à Viabilidade" não diz se a perda foi na Entrevista
 * ou na Coleta; a conversão etapa a etapa diz, e é por isso que a etapa mais
 * estreita fica destacada.
 */
export function FunilDeVenda({ agentId }: { agentId: string }) {
  const [dias, setDias] = useState(0);
  const [dados, setDados] = useState<FunilResponse | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setDados(await buscarFunil(agentId, dias));
      setErro(null);
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível carregar o funil."));
    } finally {
      setCarregando(false);
    }
  }, [agentId, dias]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  if (carregando && !dados) return <FullPageLoader label="Carregando o funil..." />;

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

  const confiavel = dados.total_de_leads >= AMOSTRA_MINIMA;

  // A etapa que mais perde, entre as que têm alguém chegando. É a única que
  // merece destaque: destacar todas é não destacar nenhuma.
  const gargalo = confiavel
    ? dados.etapas
        .slice(1)
        .filter((e) => e.chegaram > 0 || e.conversao_da_etapa > 0)
        .reduce<EtapaDoFunil | null>(
          (pior, e) => (pior === null || e.conversao_da_etapa < pior.conversao_da_etapa ? e : pior),
          null,
        )
    : null;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2" role="group" aria-label="Período">
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

        <p className="ml-auto text-sm text-fg-muted" role="status">
          {dados.total_de_leads} lead{dados.total_de_leads === 1 ? "" : "s"}
          {dados.arquivados > 0 && `, ${dados.arquivados} arquivado${dados.arquivados === 1 ? "" : "s"}`}
        </p>
      </div>

      {dados.total_de_leads === 0 ? (
        <p className="rounded-xl border border-surface-border bg-surface px-5 py-10 text-center text-sm text-fg-muted">
          Nenhum lead no período. O funil aparece quando os primeiros contatos
          chegarem pelo WhatsApp.
        </p>
      ) : (
        <>
          {!confiavel && (
            <p className="mb-4 rounded-lg border border-surface-border bg-surface-muted px-4 py-2.5 text-xs text-fg-soft">
              Com menos de {AMOSTRA_MINIMA} leads a conversão entre etapas não
              significa nada — um descarte mexe o número dezenas de pontos. Os
              percentuais aparecem quando houver base para eles.
            </p>
          )}

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {dados.etapas.map((etapa, i) => (
              <Etapa
                key={etapa.nome}
                etapa={etapa}
                posicao={i + 1}
                confiavel={confiavel}
                apertou={gargalo?.nome === etapa.nome}
              />
            ))}
          </div>

          {gargalo && (
            <p className="mt-4 text-sm text-fg-soft">
              O funil aperta em <strong className="font-medium text-fg">{gargalo.nome}</strong>:
              de cada 100 que chegam à etapa anterior, {Math.round(gargalo.conversao_da_etapa)} passam.
            </p>
          )}
        </>
      )}
    </div>
  );
}

export default FunilDeVenda;
