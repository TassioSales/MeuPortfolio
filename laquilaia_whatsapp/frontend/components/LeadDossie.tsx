"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getLeadDossie } from "@/lib/kanban";
import { formatarTelefone, linkDoWhatsapp } from "@/lib/telefone";
import { cn } from "@/lib/utils";
import type { CasoDoContato, LeadDossie as Dossie } from "@/types";
import { CasosDoContato } from "./CasosDoContato";
import { LoadingSpinner } from "./LoadingSpinner";
import { Modal } from "./Modal";

/**
 * O que o escritório sabe sobre um contato.
 *
 * O card do funil mostrava nome, telefone e um número de 0 a 100. O número
 * sozinho não diz nada — quem abre um card quer saber do que se trata, quanto
 * vale e o que fazer primeiro. Tudo isso já estava gravado e não tinha por
 * onde sair.
 *
 * A ordem das seções é a da decisão, não a do banco: primeiro o porte e o
 * resumo do caso, que é o que faz alguém pegar ou não o caso; depois o que
 * falta perguntar; o parecer inteiro por último, atrás de um clique, porque
 * são doze mil caracteres e ninguém os lê para triar.
 */

interface LeadDossieProps {
  agentId: string;
  leadId: string | null;
  onClose: () => void;
}

function Campo({ titulo, texto }: { titulo: string; texto: string | null }) {
  if (!texto) return null;

  return (
    <div>
      <h4 className="text-xs font-medium uppercase tracking-wide text-fg-muted">
        {titulo}
      </h4>
      <p className="mt-1 whitespace-pre-line text-sm text-fg">{texto}</p>
    </div>
  );
}

function faixaDoCaso(caso: CasoDoContato): string | null {
  if (caso.valor_estimado_min === null || caso.valor_estimado_max === null) {
    return null;
  }
  const reais = (v: number) =>
    v.toLocaleString("pt-BR", {
      style: "currency",
      currency: "BRL",
      maximumFractionDigits: 0,
    });
  return `${reais(caso.valor_estimado_min)} a ${reais(caso.valor_estimado_max)}`;
}

/** O porte do caso mais recente, em destaque no topo. */
function Porte({ casos }: { casos: CasoDoContato[] }) {
  const caso = casos[0];
  if (!caso) return null;

  const faixa = faixaDoCaso(caso);
  const abaixo = caso.viabilidade === "abaixo_do_piso";
  const semDimensionar =
    caso.viabilidade === "indeterminado" || caso.viabilidade === "nao_se_aplica";

  return (
    <div
      className={cn(
        "rounded-lg border p-4",
        semDimensionar
          ? "border-surface-border bg-surface-muted"
          : abaixo
            ? "border-gray-300 bg-gray-50"
            : "border-emerald-200 bg-emerald-50",
      )}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-fg-muted">
        Porte estimado
      </p>
      {semDimensionar ? (
        <p className="mt-1 text-sm text-fg-soft">
          {caso.viabilidade === "nao_se_aplica"
            ? "Não se dimensiona por valor."
            : "Ainda não dimensionado — falta dado na triagem."}
        </p>
      ) : (
        <>
          <p className="mt-1 text-xl font-semibold tracking-tight text-fg">
            {faixa ?? (abaixo ? "Abaixo do piso" : "Acima do piso")}
          </p>
          <p className="mt-0.5 text-xs text-fg-muted">
            {abaixo
              ? "Abaixo do piso do escritório — estimativa preliminar, sem documentos."
              : "Acima do piso do escritório — estimativa preliminar, sem documentos."}
          </p>
        </>
      )}
    </div>
  );
}

export function LeadDossiePanel({ agentId, leadId, onClose }: LeadDossieProps) {
  const [dossie, setDossie] = useState<Dossie | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  useEffect(() => {
    if (!leadId) return;

    let cancelado = false;
    setCarregando(true);
    setErro(null);
    setDossie(null);

    getLeadDossie(agentId, leadId)
      .then((d) => {
        if (!cancelado) setDossie(d);
      })
      .catch(() => {
        if (!cancelado) setErro("Não foi possível carregar este contato.");
      })
      .finally(() => {
        if (!cancelado) setCarregando(false);
      });

    return () => {
      cancelado = true;
    };
  }, [agentId, leadId]);

  const telefone = dossie?.phone_number ?? "";
  const whatsapp = linkDoWhatsapp(telefone);

  return (
    <Modal
      isOpen={leadId !== null}
      onClose={onClose}
      size="lg"
      title={dossie?.nome || "Contato"}
      description={dossie ? formatarTelefone(dossie.phone_number) : undefined}
    >
      {carregando && (
        <div className="flex justify-center py-10">
          <LoadingSpinner />
        </div>
      )}

      {erro && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {erro}
        </p>
      )}

      {dossie && (
        <div className="flex flex-col gap-5">
          <div className="flex flex-wrap gap-2">
            {whatsapp && (
              <a
                href={whatsapp}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-lg bg-ink-900 px-3 py-2 text-sm font-medium text-white hover:bg-ink-800 dark:bg-ink-100 dark:text-ink-950 dark:hover:bg-white"
              >
                Responder no WhatsApp
              </a>
            )}
            {dossie.conversation_id && (
              <Link
                href={`/dashboard/conversations?conversa=${dossie.conversation_id}`}
                className="rounded-lg border border-surface-border px-3 py-2 text-sm font-medium text-fg hover:bg-surface-muted"
              >
                Ver o atendimento
              </Link>
            )}
            {dossie.email && (
              <a
                href={`mailto:${dossie.email}`}
                className="rounded-lg border border-surface-border px-3 py-2 text-sm text-fg-soft hover:bg-surface-muted"
              >
                {dossie.email}
              </a>
            )}
          </div>

          <Porte casos={dossie.casos} />

          <Campo titulo="Números que a pessoa deu" texto={dossie.dados_economicos} />
          <Campo titulo="Documentos em mãos" texto={dossie.documentos_em_maos} />
          <Campo titulo="O que fazer primeiro" texto={dossie.recomendacoes} />
          <Campo titulo="O que ficou faltando" texto={dossie.inconsistencias} />
          <Campo titulo="Riscos apontados" texto={dossie.problemas_detectados} />

          {dossie.casos.length > 0 ? (
            <CasosDoContato
              casos={dossie.casos}
              contato={dossie.nome || "quem escreve"}
            />
          ) : (
            <p className="text-sm text-fg-muted">
              Este contato ainda não tem caso arquivado. O caso é aberto quando a
              triagem fecha e o parecer identifica a área.
            </p>
          )}
        </div>
      )}
    </Modal>
  );
}

export default LeadDossiePanel;
