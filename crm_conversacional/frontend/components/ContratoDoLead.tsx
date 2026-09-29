"use client";

import { useCallback, useEffect, useState } from "react";

import { messageFrom } from "@/hooks/useAgents";
import {
  abrirPdf,
  buscarDados,
  enviarParaAssinar,
  gerarContrato,
  gerarLink,
  listarContratos,
  salvarDados,
} from "@/lib/contratos";
import type { Contrato, DadosDoContrato } from "@/types";
import { Button } from "./Button";
import { Input } from "./Input";

/**
 * Fechar o caso: os dados que o contrato exige e o contrato saindo.
 *
 * Estes campos não são perguntados na triagem de propósito. Pedir CPF, RG e
 * endereço a quem ainda não sabe se vai ser cliente é onde a conversa morre —
 * eles só fazem sentido depois que o escritório decidiu aceitar o caso, que é
 * exatamente quando alguém abre este dossiê.
 *
 * A seção nasce fechada porque a maioria das vezes que se abre um card é para
 * ler o parecer, não para fechar contrato.
 */

interface ContratoDoLeadProps {
  leadId: string;
}

const VAZIO: DadosDoContrato = {
  cpf: null,
  rg: null,
  nacionalidade: null,
  estado_civil: null,
  profissao: null,
  endereco: null,
  cep: null,
  cidade: null,
  uf: null,
};

/**
 * O estado do contrato em uma frase.
 *
 * `status` sozinho ("enviado") não responde o que quem olha quer saber, que é
 * "estou esperando ou já acabou?". Assinado ganha destaque porque é o único
 * estado em que não há nada a fazer.
 */
function Estado({ contrato }: { contrato: Contrato }) {
  if (contrato.data_assinatura) {
    return (
      <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900/50 dark:text-green-200">
        assinado por {contrato.assinado_nome}
      </span>
    );
  }
  if (contrato.data_envio) {
    return (
      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900 dark:bg-amber-900/50 dark:text-amber-100">
        aguardando assinatura
      </span>
    );
  }
  return <span className="text-xs text-fg-muted">gerado, não enviado</span>;
}

function quando(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ContratoDoLead({ leadId }: ContratoDoLeadProps) {
  const [aberto, setAberto] = useState(false);
  const [dados, setDados] = useState<DadosDoContrato>(VAZIO);
  const [contratos, setContratos] = useState<Contrato[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [salvo, setSalvo] = useState(false);
  const [linkCopiado, setLinkCopiado] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const [d, lista] = await Promise.all([
        buscarDados(leadId),
        listarContratos(leadId),
      ]);
      setDados(d);
      setContratos(lista);
      setErro(null);
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível carregar os dados do contrato."));
    } finally {
      setCarregando(false);
    }
  }, [leadId]);

  useEffect(() => {
    if (aberto) void carregar();
  }, [aberto, carregar]);

  function campo(nome: keyof DadosDoContrato) {
    return {
      value: dados[nome] ?? "",
      onChange: (e: { target: { value: string } }) => {
        setDados((atual) => ({ ...atual, [nome]: e.target.value || null }));
        setSalvo(false);
      },
    };
  }

  async function salvar() {
    setOcupado(true);
    setErro(null);
    setSalvo(false);
    try {
      setDados(await salvarDados(leadId, dados));
      setSalvo(true);
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível salvar."));
    } finally {
      setOcupado(false);
    }
  }

  async function gerar() {
    setOcupado(true);
    setErro(null);
    try {
      // Salva antes de gerar: o contrato congela o texto no momento da
      // emissão, e emitir com o formulário editado e não salvo produziria um
      // documento sem os dados que estão na tela.
      const gravados = await salvarDados(leadId, dados);
      setDados(gravados);
      const novo = await gerarContrato(leadId);
      setContratos((atual) => [novo, ...atual]);
    } catch (e) {
      setErro(
        messageFrom(
          e,
          "Não foi possível gerar o contrato. Confira se há um modelo em uso.",
        ),
      );
    } finally {
      setOcupado(false);
    }
  }

  async function baixar(contrato: Contrato) {
    setErro(null);
    try {
      await abrirPdf(contrato.id);
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível abrir o PDF."));
    }
  }

  async function enviar(contrato: Contrato) {
    setOcupado(true);
    setErro(null);
    try {
      await enviarParaAssinar(contrato.id);
      // Recarrega em vez de remendar o estado local: o backend é quem decide
      // status, prazo e link, e adivinhá-los aqui criaria uma tela que discorda
      // do banco.
      await carregar();
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível enviar o contrato."));
    } finally {
      setOcupado(false);
    }
  }

  async function copiarLink(contrato: Contrato) {
    setOcupado(true);
    setErro(null);
    try {
      const { link } = await gerarLink(contrato.id);
      await navigator.clipboard.writeText(link);
      setLinkCopiado(link);
      await carregar();
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível gerar o link."));
    } finally {
      setOcupado(false);
    }
  }

  if (!aberto) {
    return (
      <button
        type="button"
        onClick={() => setAberto(true)}
        className="rounded-lg border border-surface-border px-3 py-2 text-left text-sm font-medium text-fg hover:bg-surface-muted"
      >
        Contrato
        <span className="mt-0.5 block text-xs font-normal text-fg-muted">
          Dados para o contrato e emissão do documento
        </span>
      </button>
    );
  }

  return (
    <section className="rounded-xl border border-surface-border bg-surface p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h4 className="text-sm font-medium text-fg">Contrato</h4>
        <button
          type="button"
          onClick={() => setAberto(false)}
          className="text-xs text-fg-muted hover:text-fg"
        >
          Fechar
        </button>
      </div>

      {carregando ? (
        <p className="text-sm text-fg-muted">Carregando...</p>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <Input label="CPF" maxLength={14} {...campo("cpf")} />
            <Input label="RG" maxLength={30} {...campo("rg")} />
            <Input label="Nacionalidade" maxLength={60} {...campo("nacionalidade")} />
            <Input label="Estado civil" maxLength={40} {...campo("estado_civil")} />
            <Input label="Profissão" maxLength={120} {...campo("profissao")} />
            <Input label="CEP" maxLength={9} {...campo("cep")} />
            <Input label="Cidade" maxLength={120} {...campo("cidade")} />
            <Input label="UF" maxLength={2} {...campo("uf")} />
          </div>
          <div className="mt-3">
            <Input label="Endereço" maxLength={2000} {...campo("endereco")} />
          </div>

          <p className="mt-2 text-xs text-fg-muted">
            O que ficar em branco sai como linha a preencher no contrato — em
            branco, para quem lê reparar.
          </p>

          {erro && (
            <p
              role="alert"
              className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-200"
            >
              {erro}
            </p>
          )}
          {salvo && (
            <p role="status" className="mt-3 text-sm text-green-700 dark:text-green-300">
              Dados salvos.
            </p>
          )}

          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="secondary" className="px-3 py-1.5" onClick={salvar} disabled={ocupado}>
              Salvar dados
            </Button>
            <Button className="px-3 py-1.5" onClick={gerar} isLoading={ocupado}>
              Gerar contrato
            </Button>
          </div>

          {linkCopiado && (
            <p role="status" className="mt-3 break-all rounded-lg bg-surface-muted px-3 py-2 text-xs text-fg-soft">
              Link copiado: {linkCopiado}
            </p>
          )}

          {contratos.length > 0 && (
            <ul className="mt-4 flex flex-col gap-3 border-t border-surface-border pt-3">
              {contratos.map((contrato) => (
                <li key={contrato.id} className="flex flex-col gap-1.5">
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="text-fg-soft">{quando(contrato.data_criacao)}</span>
                    <Estado contrato={contrato} />
                  </div>
                  <div className="flex flex-wrap gap-3 text-sm">
                    <button
                      type="button"
                      onClick={() => baixar(contrato)}
                      className="font-medium text-brand-700 hover:underline dark:text-brand-300"
                    >
                      Abrir PDF
                    </button>
                    {!contrato.data_assinatura && (
                      <>
                        <button
                          type="button"
                          onClick={() => enviar(contrato)}
                          disabled={ocupado}
                          className="font-medium text-brand-700 hover:underline disabled:opacity-50 dark:text-brand-300"
                        >
                          {contrato.data_envio
                            ? "Reenviar no WhatsApp"
                            : "Enviar para assinar"}
                        </button>
                        <button
                          type="button"
                          onClick={() => copiarLink(contrato)}
                          disabled={ocupado}
                          className="text-fg-muted hover:underline disabled:opacity-50"
                        >
                          Copiar link
                        </button>
                      </>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}

export default ContratoDoLead;
