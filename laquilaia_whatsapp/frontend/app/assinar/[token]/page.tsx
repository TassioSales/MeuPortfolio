"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { messageFrom } from "@/hooks/useAgents";
import { assinar, buscarParaAssinar } from "@/lib/assinatura";
import type { ContratoParaAssinar } from "@/types";

/**
 * A página que o cliente abre no celular para assinar.
 *
 * É a única tela do produto vista por quem não tem conta, e a única aberta na
 * internet. Três coisas mandam no desenho dela:
 *
 * 1. **Celular primeiro.** O link chega pelo WhatsApp; quase ninguém vai
 *    abri-lo num computador.
 * 2. **O contrato inteiro antes do botão.** Assinar sem rolar o texto é
 *    exatamente o que torna uma assinatura contestável — e é feio fazer com
 *    um cliente. Por isso o botão só habilita depois de a pessoa chegar ao
 *    fim do documento.
 * 3. **Nada de menu, logo de painel ou link para o sistema.** Quem está aqui
 *    veio assinar um contrato, não conhecer o software.
 */

function DataPorExtenso({ iso }: { iso: string | null }) {
  if (!iso) return null;
  const d = new Date(iso);
  return (
    <>
      {d.toLocaleDateString("pt-BR")} às{" "}
      {d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
    </>
  );
}

/**
 * O texto do contrato como parágrafos.
 *
 * Mesmas duas marcas do PDF (`#` título, `**negrito**`), para a pessoa ver na
 * tela o que vai ver no arquivo. Um markdown de verdade seria dependência a
 * mais para duas regras.
 */
function Corpo({ texto }: { texto: string }) {
  const linhas = texto.split("\n");

  return (
    <div className="flex flex-col gap-3">
      {linhas.map((linha, i) => {
        const conteudo = linha.trim();
        if (!conteudo) return <div key={i} className="h-1" />;

        if (conteudo.startsWith("#")) {
          return (
            <h2
              key={i}
              className="mt-2 text-center text-base font-semibold uppercase tracking-wide text-fg"
            >
              {conteudo.replace(/^#+\s*/, "")}
            </h2>
          );
        }

        // `split` com grupo de captura devolve o miolo dos delimitadores nos
        // índices ímpares — é o que evita `matchAll`, que o `target` deste
        // tsconfig não compila.
        const partes = conteudo.split(/\*\*(.+?)\*\*/g);
        return (
          <p key={i} className="text-justify text-[15px] leading-relaxed text-fg-soft">
            {partes.map((parte, j) =>
              j % 2 === 1 ? (
                <strong key={j} className="font-semibold text-fg">
                  {parte}
                </strong>
              ) : (
                <span key={j}>{parte}</span>
              ),
            )}
          </p>
        );
      })}
    </div>
  );
}

export default function AssinarPage() {
  const params = useParams<{ token: string }>();
  const token = params?.token ?? "";

  const [contrato, setContrato] = useState<ContratoParaAssinar | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [naoEncontrado, setNaoEncontrado] = useState(false);

  const [nome, setNome] = useState("");
  const [aceite, setAceite] = useState(false);
  const [leuAteOFim, setLeuAteOFim] = useState(false);

  const carregar = useCallback(async () => {
    if (!token) return;
    setCarregando(true);
    try {
      const dados = await buscarParaAssinar(token);
      setContrato(dados);
      setNome(dados.nome_do_cliente ?? "");
      setErro(null);
    } catch (e) {
      const status = (e as { status?: number })?.status;
      if (status === 404) setNaoEncontrado(true);
      else setErro(messageFrom(e, "Não foi possível abrir o contrato."));
    } finally {
      setCarregando(false);
    }
  }, [token]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setErro(null);
    try {
      setContrato(await assinar(token, nome.trim()));
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível registrar a assinatura."));
    } finally {
      setEnviando(false);
    }
  }

  if (carregando) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-surface-muted px-4">
        <p className="text-sm text-fg-muted">Abrindo o contrato...</p>
      </main>
    );
  }

  if (naoEncontrado) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-surface-muted px-4">
        <div className="max-w-md rounded-2xl bg-surface p-8 text-center shadow-sm">
          <h1 className="text-lg font-semibold text-fg">Link indisponível</h1>
          <p className="mt-3 text-sm leading-relaxed text-fg-muted">
            Este endereço não está mais válido. Links de assinatura têm prazo,
            e cada um serve a um contrato só.
          </p>
          <p className="mt-4 text-sm text-fg-muted">
            Responda a conversa no WhatsApp do escritório pedindo um link novo —
            leva um instante.
          </p>
        </div>
      </main>
    );
  }

  if (!contrato) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-surface-muted px-4">
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          {erro ?? "Não foi possível abrir o contrato."}
        </p>
      </main>
    );
  }

  const assinado = contrato.ja_assinado;
  const podeAssinar = leuAteOFim && aceite && nome.trim().length >= 3;

  return (
    <main className="min-h-screen bg-surface-muted px-4 py-6 sm:py-10">
      <div className="mx-auto max-w-2xl">
        <header className="mb-4 text-center">
          <p className="text-xs uppercase tracking-widest text-fg-muted">
            {contrato.nome_do_escritorio ?? "Contrato"}
          </p>
          <h1 className="mt-1 text-lg font-semibold text-fg">
            {assinado ? "Contrato assinado" : "Assinatura do contrato"}
          </h1>
        </header>

        {assinado && (
          <div className="mb-4 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-900 dark:border-green-900 dark:bg-green-950/50 dark:text-green-100">
            <p className="font-medium">Assinatura registrada.</p>
            <p className="mt-1">
              Por {contrato.assinado_por} em{" "}
              <DataPorExtenso iso={contrato.assinado_em} />. O escritório já foi
              avisado e vai continuar pelo WhatsApp.
            </p>
          </div>
        )}

        <article
          onScroll={(e) => {
            const el = e.currentTarget;
            // 40px de folga: em celular o último pixel raramente é alcançado,
            // e exigi-lo travaria o botão para quem leu tudo.
            if (el.scrollHeight - el.scrollTop - el.clientHeight < 40) {
              setLeuAteOFim(true);
            }
          }}
          className="max-h-[60vh] overflow-y-auto rounded-2xl bg-surface p-5 shadow-sm sm:p-8"
        >
          <Corpo texto={contrato.corpo} />
        </article>

        {!assinado && (
          <form
            onSubmit={enviar}
            className="mt-4 rounded-2xl bg-surface p-5 shadow-sm sm:p-6"
          >
            <label
              htmlFor="nome"
              className="text-sm font-medium text-fg-soft"
            >
              Seu nome completo
            </label>
            <input
              id="nome"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              maxLength={255}
              autoComplete="name"
              className="mt-1.5 w-full rounded-lg border border-surface-border bg-surface px-3 py-3 text-base text-fg placeholder:text-fg-faint focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
              placeholder="Como está no seu documento"
            />

            <label className="mt-4 flex items-start gap-3 text-sm text-fg-soft">
              <input
                type="checkbox"
                checked={aceite}
                onChange={(e) => setAceite(e.target.checked)}
                className="mt-0.5 h-5 w-5 shrink-0 rounded border-surface-border bg-surface accent-ink-900 dark:accent-ink-100"
              />
              <span>
                Li o contrato acima e concordo com as condições, assinando-o
                eletronicamente.
              </span>
            </label>

            {!leuAteOFim && (
              <p className="mt-3 rounded-lg bg-surface-muted px-3 py-2 text-xs text-fg-muted">
                Role o contrato até o fim para liberar a assinatura.
              </p>
            )}

            {erro && (
              <p
                role="alert"
                className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-200"
              >
                {erro}
              </p>
            )}

            <button
              type="submit"
              disabled={!podeAssinar || enviando}
              className="mt-4 w-full rounded-lg bg-ink-900 px-4 py-3.5 text-base font-medium text-white transition-colors hover:bg-ink-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-ink-100 dark:text-ink-950 dark:hover:bg-white"
            >
              {enviando ? "Registrando..." : "Assinar contrato"}
            </button>

            <p className="mt-3 text-center text-xs leading-relaxed text-fg-muted">
              Ao assinar, registramos a data, a hora, o endereço de acesso e uma
              impressão digital do texto — é o que comprova o que você aceitou.
            </p>
          </form>
        )}
      </div>
    </main>
  );
}
