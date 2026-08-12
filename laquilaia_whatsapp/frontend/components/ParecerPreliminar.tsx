"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

/**
 * O parecer preliminar do caso, para quem atende.
 *
 * Vem fechado de propósito: quem abre a conversa quer ler a conversa. O
 * parecer é consulta, não leitura corrida — e deixá-lo aberto empurraria a
 * transcrição para fora da tela.
 *
 * Renderiza um markdown restrito (títulos `##`, listas e `**negrito**`), e não
 * um markdown completo: o texto vem de um modelo de linguagem, e interpretar
 * HTML de uma fonte dessas seria abrir uma porta sem necessidade nenhuma.
 */

interface ParecerPreliminarProps {
  texto: string;
}

type Bloco =
  | { tipo: "titulo"; texto: string }
  | { tipo: "lista"; itens: string[] }
  | { tipo: "paragrafo"; texto: string };

function analisar(markdown: string): Bloco[] {
  const blocos: Bloco[] = [];
  let listaAberta: string[] | null = null;

  for (const linha of markdown.split("\n")) {
    const conteudo = linha.trim();

    if (!conteudo) {
      listaAberta = null;
      continue;
    }

    if (conteudo.startsWith("#")) {
      listaAberta = null;
      blocos.push({ tipo: "titulo", texto: conteudo.replace(/^#+\s*/, "") });
      continue;
    }

    // `- item` e `1. item` viram a mesma lista.
    const item = conteudo.match(/^(?:[-*]|\d+\.)\s+(.*)$/);
    if (item) {
      if (listaAberta) {
        listaAberta.push(item[1]);
      } else {
        listaAberta = [item[1]];
        blocos.push({ tipo: "lista", itens: listaAberta });
      }
      continue;
    }

    listaAberta = null;
    blocos.push({ tipo: "paragrafo", texto: conteudo });
  }

  return blocos;
}

/** Só `**negrito**`. O resto do texto passa como texto. */
function comNegrito(texto: string) {
  return texto.split(/(\*\*[^*]+\*\*)/g).map((parte, i) =>
    parte.startsWith("**") && parte.endsWith("**") ? (
      <strong key={i} className="font-semibold text-gray-900">
        {parte.slice(2, -2)}
      </strong>
    ) : (
      <span key={i}>{parte}</span>
    ),
  );
}

export function ParecerPreliminar({ texto }: ParecerPreliminarProps) {
  const [aberto, setAberto] = useState(false);
  const blocos = analisar(texto);

  return (
    <section className="border-b border-surface-border bg-amber-50/60">
      <button
        type="button"
        onClick={() => setAberto((v) => !v)}
        aria-expanded={aberto}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <span className="flex items-center gap-2">
          <span aria-hidden="true">⚖️</span>
          <span className="text-sm font-medium text-gray-900">
            Análise preliminar do caso
          </span>
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-900">
            interno
          </span>
        </span>
        <span className="text-xs text-gray-600">
          {aberto ? "ocultar" : "ler"}
        </span>
      </button>

      {aberto && (
        <div className="max-h-80 overflow-y-auto px-4 pb-4">
          <p className="mb-3 text-xs text-gray-600">
            Gerada por IA a partir da conversa, sem acesso a documentos. É ponto
            de partida para o advogado, não parecer — e o cliente nunca a recebe.
          </p>

          {blocos.map((bloco, i) => {
            if (bloco.tipo === "titulo") {
              return (
                <h4
                  key={i}
                  className={cn(
                    "text-sm font-semibold text-gray-900",
                    i === 0 ? "" : "mt-4",
                  )}
                >
                  {bloco.texto}
                </h4>
              );
            }
            if (bloco.tipo === "lista") {
              return (
                <ul key={i} className="mt-1 list-disc space-y-1 pl-5">
                  {bloco.itens.map((item, j) => (
                    <li key={j} className="text-sm text-gray-700">
                      {comNegrito(item)}
                    </li>
                  ))}
                </ul>
              );
            }
            return (
              <p key={i} className="mt-1 text-sm leading-relaxed text-gray-700">
                {comNegrito(bloco.texto)}
              </p>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default ParecerPreliminar;
