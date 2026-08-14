"use client";

import { useState } from "react";
import type { CasoDoContato } from "@/types";
import { ParecerPreliminar } from "./ParecerPreliminar";
import { cn } from "@/lib/utils";

/**
 * Os assuntos que este contato trouxe.
 *
 * Um contato pode ter mais de um caso, e um deles pode ser de outra pessoa —
 * o irmão que pergunta pelo divórcio da irmã. Quando isso acontece o titular
 * aparece em destaque: abrir o caso achando que é do titular do WhatsApp é o
 * erro que a separação entre contato e caso existe para evitar.
 */

const ROTULO_DA_AREA: Record<string, string> = {
  trabalhista: "Trabalhista",
  familia: "Família",
  consumidor: "Consumidor",
  previdenciario: "Previdenciário",
  civel: "Cível",
  criminal: "Criminal",
  outro: "Outro",
};

/**
 * O porte do caso, como tarja.
 *
 * A faixa aparece junto do veredito sempre que existe: "abaixo do piso"
 * sozinho é uma etiqueta que ninguém consegue contestar, e contestar é
 * justamente o trabalho de quem lê. `indeterminado` não vira tarja — caso não
 * dimensionado é o estado normal de quem acabou de chegar, e uma tarja em todo
 * card não informa nada.
 */
function Porte({ caso }: { caso: CasoDoContato }) {
  if (caso.viabilidade === "indeterminado" || caso.viabilidade === "nao_se_aplica") {
    return null;
  }

  const abaixo = caso.viabilidade === "abaixo_do_piso";
  const faixa =
    caso.valor_estimado_min !== null && caso.valor_estimado_max !== null
      ? `${formatarReais(caso.valor_estimado_min)}–${formatarReais(caso.valor_estimado_max)}`
      : null;

  return (
    <span
      className={cn(
        "rounded-full px-2 py-0.5 text-xs",
        // A tarja clara com `text-fg-soft` virava texto claro sobre fundo
        // claro no tema escuro. O par `dark:` é obrigatório sempre que a cor
        // é literal em vez de token.
        abaixo
          ? "bg-surface-muted text-fg-soft ring-1 ring-surface-border"
          : "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100",
      )}
      title={
        abaixo
          ? "O parecer estimou o caso abaixo do piso do escritório. É estimativa preliminar, sem documentos."
          : "O parecer estimou o caso acima do piso do escritório."
      }
    >
      {faixa ?? (abaixo ? "abaixo do piso" : "acima do piso")}
    </span>
  );
}

function formatarReais(valor: number): string {
  return valor.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  });
}

interface CasosDoContatoProps {
  casos: CasoDoContato[];
  /** Nome de quem manda as mensagens, para contrastar com o titular. */
  contato: string;
}

function formatarData(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function Caso({ caso, contato }: { caso: CasoDoContato; contato: string }) {
  const [aberto, setAberto] = useState(false);
  const deTerceiro = Boolean(caso.titular);

  return (
    <li className="border-b border-surface-border last:border-b-0">
      <button
        type="button"
        onClick={() => setAberto((v) => !v)}
        aria-expanded={aberto}
        className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left hover:bg-surface-muted"
      >
        <span className="min-w-0">
          <span className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-fg">
              {ROTULO_DA_AREA[caso.area ?? ""] ?? "Sem área"}
            </span>
            {deTerceiro && (
              <span className="rounded-full bg-amber-100 dark:bg-amber-950/40 px-2 py-0.5 text-xs text-amber-900 dark:text-amber-200">
                de {caso.titular}
              </span>
            )}
            <Porte caso={caso} />
            {caso.score_qualificacao > 0 && (
              <span className="text-xs text-fg-muted">
                score {caso.score_qualificacao}
              </span>
            )}
          </span>
          {caso.resumo && (
            <span
              className={cn(
                "mt-1 block text-xs text-fg-muted",
                aberto ? "" : "line-clamp-2",
              )}
            >
              {caso.resumo}
            </span>
          )}
        </span>
        <span className="shrink-0 text-xs text-fg-faint">
          {formatarData(caso.data_abertura)}
        </span>
      </button>

      {aberto && caso.analise_preliminar && (
        <div className="pb-2">
          {deTerceiro && (
            <p className="px-4 pb-2 text-xs text-amber-900 dark:text-amber-200">
              A parte deste caso é <strong>{caso.titular}</strong>. Quem escreve
              pelo WhatsApp é {contato}.
            </p>
          )}
          <ParecerPreliminar texto={caso.analise_preliminar} />
        </div>
      )}
    </li>
  );
}

export function CasosDoContato({ casos, contato }: CasosDoContatoProps) {
  if (casos.length === 0) return null;

  return (
    <section className="border-b border-surface-border bg-surface">
      <h3 className="px-4 pt-3 text-xs font-medium uppercase tracking-wide text-fg-muted">
        {casos.length === 1 ? "Caso deste contato" : `Casos deste contato (${casos.length})`}
      </h3>
      <ul className="mt-1">
        {casos.map((caso) => (
          <Caso key={caso.id} caso={caso} contato={contato} />
        ))}
      </ul>
    </section>
  );
}

export default CasosDoContato;
