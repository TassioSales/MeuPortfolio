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
 * **Dentro dele, cada seção também é um sanfona.** O parecer tinha meia dúzia
 * de linhas quando esta tela foi feita; hoje tem nove seções e doze mil
 * caracteres, e um bloco de rolagem de 320px com tudo dentro obriga a rolar às
 * cegas para achar "Prazos e urgência". Com as seções fechadas, os títulos
 * viram o índice — que é como se lê parecer: pelo que se procura.
 *
 * Resumo e Ficha nascem abertos porque são as duas que se lê sempre: do que se
 * trata e de quem é o caso.
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
      <strong key={i} className="font-semibold text-fg">
        {parte.slice(2, -2)}
      </strong>
    ) : (
      <span key={i}>{parte}</span>
    ),
  );
}

/** Uma seção do parecer: o título e o que vem até o próximo título. */
interface Secao {
  titulo: string;
  blocos: Bloco[];
}

/**
 * Agrupa os blocos por seção.
 *
 * O que vier antes do primeiro título entra numa seção sem nome, e não é
 * descartado: parecer que não seguiu o formato ainda precisa aparecer inteiro.
 */
function seccionar(blocos: Bloco[]): Secao[] {
  const secoes: Secao[] = [];

  for (const bloco of blocos) {
    if (bloco.tipo === "titulo") {
      secoes.push({ titulo: bloco.texto, blocos: [] });
      continue;
    }
    if (secoes.length === 0) secoes.push({ titulo: "", blocos: [] });
    secoes[secoes.length - 1].blocos.push(bloco);
  }

  return secoes;
}

/** As duas que se lê sempre: do que se trata e de quem é o caso. */
const ABERTAS_POR_PADRAO = ["resumo", "ficha"];

function Conteudo({ blocos }: { blocos: Bloco[] }) {
  return (
    <>
      {blocos.map((bloco, i) => {
        if (bloco.tipo === "lista") {
          return (
            <ul key={i} className="mt-1 list-disc space-y-1 pl-5">
              {bloco.itens.map((item, j) => (
                <li key={j} className="text-sm text-fg-soft">
                  {comNegrito(item)}
                </li>
              ))}
            </ul>
          );
        }
        return (
          <p key={i} className="mt-1 text-sm leading-relaxed text-fg-soft">
            {comNegrito(bloco.texto)}
          </p>
        );
      })}
    </>
  );
}

function SecaoDoParecer({ secao }: { secao: Secao }) {
  const [aberta, setAberta] = useState(
    ABERTAS_POR_PADRAO.some((nome) => secao.titulo.toLowerCase().startsWith(nome)),
  );

  // Texto solto antes do primeiro título não vira sanfona: não há o que
  // dobrar sem um título para clicar.
  if (!secao.titulo) return <Conteudo blocos={secao.blocos} />;

  return (
    <div className="border-t border-surface-border first:border-t-0">
      <button
        type="button"
        onClick={() => setAberta((v) => !v)}
        aria-expanded={aberta}
        className="flex w-full items-center justify-between gap-2 py-2 text-left"
      >
        <span className="text-sm font-semibold text-fg">{secao.titulo}</span>
        <span aria-hidden="true" className="shrink-0 text-xs text-fg-muted">
          {aberta ? "−" : "+"}
        </span>
      </button>
      {aberta && <div className="pb-3">{<Conteudo blocos={secao.blocos} />}</div>}
    </div>
  );
}

export function ParecerPreliminar({ texto }: ParecerPreliminarProps) {
  const [aberto, setAberto] = useState(false);
  const secoes = seccionar(analisar(texto));

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
          <span className="text-sm font-medium text-fg">
            Análise preliminar do caso
          </span>
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-900">
            interno
          </span>
        </span>
        <span className="text-xs text-fg-muted">
          {aberto ? "ocultar" : "ler"}
        </span>
      </button>

      {aberto && (
        <div className="max-h-[32rem] overflow-y-auto px-4 pb-4">
          <p className="mb-2 text-xs text-fg-muted">
            Gerada por IA a partir da conversa, sem acesso a documentos. É ponto
            de partida para o advogado, não parecer — e o cliente nunca a recebe.
          </p>

          {secoes.map((secao, i) => (
            <SecaoDoParecer key={`${secao.titulo}-${i}`} secao={secao} />
          ))}
        </div>
      )}
    </section>
  );
}

export default ParecerPreliminar;
