"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { desconectar, getQrCode, getStatus } from "@/lib/whatsapp";
import { cn } from "@/lib/utils";
import type { EstadoDaConexao, EstadoDaInstancia, QrCode } from "@/types";
import { Button } from "./Button";
import { LoadingSpinner } from "./LoadingSpinner";

/**
 * A conexão do número, dentro do painel.
 *
 * Até aqui o QR só existia no Manager da Evolution: para reconectar, o
 * administrador saía do sistema, abria outra ferramenta e precisava saber que
 * ela existe. Quem opera um escritório não deveria precisar conhecer a
 * arquitetura para religar o WhatsApp.
 *
 * O QR do WhatsApp expira em segundos e a Evolution gera outro. Por isso a
 * tela repesca sozinha enquanto está desconectada — e **para** de repescar
 * assim que conecta: continuar batendo no endpoint depois de pareado é gastar
 * requisição para receber "já está conectado" a cada vinte segundos.
 */

const SEGUNDOS_ENTRE_LEITURAS = 20;

const APARENCIA: Record<
  EstadoDaInstancia,
  { rotulo: string; explicacao: string; cor: string }
> = {
  conectado: {
    rotulo: "Conectado",
    explicacao: "O número está no ar e recebendo mensagens.",
    cor: "bg-emerald-500",
  },
  conectando: {
    rotulo: "Conectando",
    explicacao: "A Evolution está estabelecendo a sessão. Aguarde alguns segundos.",
    cor: "bg-amber-500",
  },
  desconectado: {
    rotulo: "Desconectado",
    explicacao: "Ninguém está sendo atendido. Leia o QR abaixo para reconectar.",
    cor: "bg-red-500",
  },
  // A Evolution respondeu 404: ela está no ar, a instância é que não existe.
  // Acontece quando o container é recriado sem volume — o serviço sobe limpo
  // e a instância pareada se perde junto. Chamar isso de "fora do ar" manda
  // procurar o problema no lugar errado.
  inexistente: {
    rotulo: "Instância não criada",
    explicacao:
      "A Evolution está no ar, mas não conhece esta instância. Ela precisa ser criada antes de parear o número.",
    cor: "bg-amber-500",
  },
  // Estados diferentes de propósito: um é o número que caiu, o outro é a
  // Evolution que caiu. Quem conserta cada um é uma pessoa diferente.
  indisponivel: {
    rotulo: "Evolution fora do ar",
    explicacao:
      "Não deu para falar com a Evolution. O problema está no serviço, não no número.",
    cor: "bg-red-500",
  },
  desconhecido: {
    rotulo: "Estado desconhecido",
    explicacao: "A Evolution respondeu algo que este painel ainda não entende.",
    cor: "bg-fg-faint",
  },
};

export function ConexaoWhatsapp() {
  const [status, setStatus] = useState<EstadoDaConexao | null>(null);
  const [qr, setQr] = useState<QrCode | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);
  // Confirmação em dois passos, em vez de `window.confirm`: desconectar
  // derruba o atendimento do escritório inteiro, e o diálogo do navegador é
  // justamente aquele que todo mundo aprendeu a fechar sem ler.
  const [confirmando, setConfirmando] = useState(false);
  const [desconectando, setDesconectando] = useState(false);
  // Evita duas leituras simultâneas quando o botão é clicado durante o ciclo.
  const lendo = useRef(false);

  const ler = useCallback(async () => {
    if (lendo.current) return;
    lendo.current = true;

    try {
      const novoStatus = await getStatus();
      setStatus(novoStatus);
      setErro(null);

      // O QR só é pedido quando faz sentido pedir: já conectado não precisa,
      // e sem serviço ou sem instância o pedido volta com o mesmo erro — dois
      // 404 em vez de um, e nada a mostrar na tela.
      const vaisadiantar =
        novoStatus.estado !== "conectado" &&
        novoStatus.estado !== "indisponivel" &&
        novoStatus.estado !== "inexistente";

      setQr(vaisadiantar ? await getQrCode() : null);
    } catch {
      setErro("Não foi possível ler o estado da conexão.");
    } finally {
      lendo.current = false;
      setCarregando(false);
    }
  }, []);

  const encerrarSessao = useCallback(async () => {
    setDesconectando(true);
    try {
      const resultado = await desconectar();
      if (!resultado.desconectado) {
        // Dizer "pronto, desconectado" com o número no ar seria o pior
        // desfecho: o escritório pararia de olhar o WhatsApp que continua
        // recebendo.
        setErro(
          `Não foi possível desconectar${
            resultado.detalhe ? ` (${resultado.detalhe})` : ""
          }. O número pode continuar no ar.`,
        );
        return;
      }
      setConfirmando(false);
      await ler();
    } catch {
      setErro("Não foi possível desconectar. O número pode continuar no ar.");
    } finally {
      setDesconectando(false);
    }
  }, [ler]);

  useEffect(() => {
    void ler();
  }, [ler]);

  const conectado = status?.estado === "conectado";

  useEffect(() => {
    if (conectado) return;

    const id = setInterval(() => void ler(), SEGUNDOS_ENTRE_LEITURAS * 1000);
    return () => clearInterval(id);
  }, [conectado, ler]);

  const aparencia = APARENCIA[status?.estado ?? "desconhecido"];

  return (
    <section className="rounded-xl border border-surface-border bg-surface p-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-medium text-fg">
            <span
              aria-hidden="true"
              className={cn("h-2.5 w-2.5 rounded-full", aparencia.cor)}
            />
            {carregando ? "Lendo o estado..." : aparencia.rotulo}
          </h2>
          <p className="mt-1 text-sm text-fg-muted">
            {carregando ? " " : aparencia.explicacao}
          </p>
          {status && (
            <p className="mt-1 text-xs text-fg-faint">
              Instância <code>{status.instancia}</code>
              {status.detalhe ? ` — ${status.detalhe}` : ""}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Só aparece com o número no ar: desconectar o que já está
              desconectado não faz nada, e o botão parado convida ao clique. */}
          {conectado &&
            (confirmando ? (
              <>
                <span className="text-xs text-fg-muted">
                  Isso derruba o atendimento. Confirma?
                </span>
                <Button
                  variant="danger"
                  onClick={() => void encerrarSessao()}
                  disabled={desconectando}
                >
                  {desconectando ? "Desconectando..." : "Sim, desconectar"}
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => setConfirmando(false)}
                  disabled={desconectando}
                >
                  Cancelar
                </Button>
              </>
            ) : (
              <Button variant="secondary" onClick={() => setConfirmando(true)}>
                Desconectar
              </Button>
            ))}

          <Button variant="secondary" onClick={() => void ler()}>
            Atualizar
          </Button>
        </div>
      </header>

      {erro && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 dark:bg-red-950/40 px-3 py-2 text-sm text-red-700 dark:text-red-200">
          {erro}
        </p>
      )}

      {carregando && !status && (
        <div className="flex justify-center py-8">
          <LoadingSpinner />
        </div>
      )}

      {!conectado && qr && (
        <div className="mt-5 flex flex-col items-center gap-3 border-t border-surface-border pt-5">
          {qr.qrcode ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={qr.qrcode}
                alt="QR code para conectar o WhatsApp"
                className="h-56 w-56 rounded-lg bg-white p-2"
              />
              <p className="max-w-sm text-center text-xs text-fg-muted">
                No celular: WhatsApp → Aparelhos conectados → Conectar aparelho.
                O código muda sozinho a cada poucos segundos.
              </p>
            </>
          ) : qr.codigo ? (
            <>
              <p className="text-sm text-fg-muted">Código de pareamento:</p>
              <p className="font-mono text-2xl font-semibold tracking-widest text-fg">
                {qr.codigo}
              </p>
            </>
          ) : (
            // A Evolution já respondeu sem QR e sem código, sem erro nenhum
            // (issues #2380 e #2385). Dizer isso é melhor que mostrar um
            // quadrado vazio e deixar a pessoa esperando.
            <p className="max-w-md text-center text-sm text-fg-muted">
              A Evolution respondeu sem QR e sem código de pareamento
              {qr.detalhe ? ` (${qr.detalhe})` : ""}. Tente pelo Manager da
              Evolution e verifique se há atualização disponível.
            </p>
          )}
        </div>
      )}
    </section>
  );
}

export default ConexaoWhatsapp;
