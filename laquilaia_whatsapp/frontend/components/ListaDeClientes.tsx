"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { messageFrom } from "@/hooks/useAgents";
import { listarClientes } from "@/lib/clientes";
import { formatarTelefone } from "@/lib/telefone";
import { cn } from "@/lib/utils";
import type { ClienteNaLista } from "@/types";

/**
 * Quanto tempo depois da última tecla a busca sai.
 *
 * Sem espera, digitar "Alexandre" dispara nove consultas e as respostas
 * chegam fora de ordem — a tela pisca resultados de "Alexand" depois dos de
 * "Alexandre". 300ms é o intervalo em que a pessoa ainda não percebeu que
 * esperou.
 */
const ESPERA_MS = 300;

/** Espelha `BUSCA_MINIMA` no backend: abaixo disto ele nem filtra. */
const BUSCA_MINIMA = 2;

const ETAPAS = [
  "Closer",
  "Entrevista",
  "Viabilidade",
  "Coleta de documentos",
  "Saneamento",
  "Revisão",
  "Arquivado",
];

function quandoChegou(iso: string | null): string {
  if (!iso) return "—";
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return "—";
  return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "2-digit" });
}

/**
 * Todos os contatos do agente, com busca.
 *
 * Existe ao lado do Kanban, não no lugar dele: são duas perguntas diferentes.
 * O board responde "o que está travado?"; esta lista responde "cadê o
 * fulano?" — e com 155 cards na primeira coluna, a segunda pergunta não tinha
 * resposta nenhuma no painel.
 */
export function ListaDeClientes({ agentId }: { agentId: string }) {
  const [busca, setBusca] = useState("");
  const [etapa, setEtapa] = useState("");
  const [pagina, setPagina] = useState(1);

  const [clientes, setClientes] = useState<ClienteNaLista[]>([]);
  const [total, setTotal] = useState(0);
  const [porPagina, setPorPagina] = useState(50);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  // Cada busca leva um número; só a resposta do último pedido é aceita.
  // Sem isto, uma consulta lenta de "Ale" pode chegar depois da de
  // "Alexandre" e sobrescrever a tela com o resultado errado.
  const pedido = useRef(0);

  const carregar = useCallback(
    async (termo: string, filtro: string, pag: number) => {
      const meu = ++pedido.current;
      setCarregando(true);
      try {
        const dados = await listarClientes(agentId, {
          busca: termo,
          etapa: filtro,
          pagina: pag,
        });
        if (meu !== pedido.current) return;
        setClientes(dados.clientes);
        setTotal(dados.total);
        setPorPagina(dados.por_pagina);
        setErro(null);
      } catch (e) {
        if (meu !== pedido.current) return;
        setErro(messageFrom(e, "Não foi possível carregar os contatos."));
      } finally {
        if (meu === pedido.current) setCarregando(false);
      }
    },
    [agentId],
  );

  useEffect(() => {
    const termo = busca.trim();
    // Uma letra não filtra nada e faz o banco varrer tudo — o backend também
    // a ignora, então nem vale a viagem.
    const efetivo = termo.length >= BUSCA_MINIMA ? termo : "";

    const timer = setTimeout(() => void carregar(efetivo, etapa, pagina), ESPERA_MS);
    return () => clearTimeout(timer);
  }, [busca, etapa, pagina, carregar]);

  const paginas = Math.max(1, Math.ceil(total / porPagina));

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="min-w-[16rem] flex-1">
          <Input
            label="Buscar"
            value={busca}
            onChange={(e) => {
              setBusca(e.target.value);
              // Trocar a busca sem voltar para a primeira página deixaria a
              // tela vazia: página 3 de um resultado que agora tem 4 linhas.
              setPagina(1);
            }}
            placeholder="Nome, telefone ou e-mail"
          />
        </div>

        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-fg-soft">Etapa</span>
          <select
            value={etapa}
            onChange={(e) => {
              setEtapa(e.target.value);
              setPagina(1);
            }}
            className="rounded-lg border border-surface-border bg-surface px-3 py-2.5 text-sm text-fg focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
          >
            <option value="">Todas</option>
            {ETAPAS.map((nome) => (
              <option key={nome} value={nome}>
                {nome}
              </option>
            ))}
          </select>
        </label>

        <p className="pb-3 text-sm text-fg-muted" role="status">
          {total === 1 ? "1 contato" : `${total} contatos`}
        </p>
      </div>

      {erro ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-5 dark:border-red-900 dark:bg-red-950/40">
          <p role="alert" className="text-sm text-red-700 dark:text-red-200">
            {erro}
          </p>
          <Button
            variant="secondary"
            className="mt-4"
            onClick={() => void carregar(busca.trim(), etapa, pagina)}
          >
            Tentar novamente
          </Button>
        </div>
      ) : carregando && clientes.length === 0 ? (
        <div className="flex justify-center py-16">
          <LoadingSpinner label="Carregando contatos..." />
        </div>
      ) : clientes.length === 0 ? (
        <p className="rounded-xl border border-surface-border bg-surface px-5 py-10 text-center text-sm text-fg-muted">
          {busca.trim() || etapa
            ? "Nenhum contato com esses critérios."
            : "Nenhum contato ainda. Eles aparecem aqui quando chegam pelo WhatsApp."}
        </p>
      ) : (
        // A tabela rola dentro do próprio quadro: sem isto, um nome de
        // empresa longo empurraria a página inteira para o lado.
        <div className="overflow-x-auto rounded-xl border border-surface-border bg-surface">
          <table className="w-full min-w-[48rem] border-collapse text-sm">
            <thead>
              <tr className="border-b border-surface-border text-left text-xs uppercase tracking-wide text-fg-muted">
                <th className="px-4 py-3 font-medium">Contato</th>
                <th className="px-4 py-3 font-medium">Onde trabalhava</th>
                <th className="px-4 py-3 font-medium">Etapa</th>
                <th className="px-4 py-3 font-medium">Score</th>
                <th className="px-4 py-3 font-medium">Desde</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {clientes.map((cliente) => (
                <tr
                  key={cliente.lead_id}
                  className="border-b border-surface-border last:border-0 hover:bg-surface-muted"
                >
                  <td className="px-4 py-3">
                    <span className="block font-medium text-fg">
                      {cliente.nome ?? "Sem nome"}
                    </span>
                    <span className="block text-xs text-fg-muted">
                      {formatarTelefone(cliente.phone_number)}
                    </span>
                  </td>

                  <td className="px-4 py-3 text-fg-soft">
                    {[cliente.empresa, cliente.cargo].filter(Boolean).join(" · ") || "—"}
                  </td>

                  <td className="px-4 py-3">
                    <span className="text-fg-soft">{cliente.etapa ?? "—"}</span>
                    {/* O "parado há" vem aqui e não numa coluna própria: só
                        existe quando é ruim, e coluna vazia em 90% das linhas
                        é espaço gasto para não dizer nada. */}
                    {cliente.dias_parado !== null && cliente.dias_parado >= 3 && (
                      <span
                        className={cn(
                          "ml-2 rounded-full px-1.5 py-0.5 text-[11px] tabular-nums",
                          cliente.dias_parado >= 10
                            ? "bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-200"
                            : "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-200",
                        )}
                      >
                        {cliente.dias_parado}d
                      </span>
                    )}
                  </td>

                  <td className="px-4 py-3 tabular-nums text-fg-soft">
                    {cliente.score_qualificacao || "—"}
                  </td>

                  <td className="px-4 py-3 text-fg-muted">
                    {quandoChegou(cliente.data_criacao)}
                  </td>

                  <td className="px-4 py-3 text-right">
                    {cliente.conversation_id && (
                      <Link
                        href={`/dashboard/conversations?agent=${agentId}&conversa=${cliente.conversation_id}`}
                        className="text-xs font-medium text-brand-700 underline-offset-2 hover:underline dark:text-brand-300"
                      >
                        Ver atendimento
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {paginas > 1 && (
        <div className="mt-4 flex items-center justify-center gap-3">
          <Button
            variant="secondary"
            disabled={pagina <= 1}
            onClick={() => setPagina((p) => Math.max(1, p - 1))}
          >
            Anterior
          </Button>
          <span className="text-sm tabular-nums text-fg-muted">
            {pagina} de {paginas}
          </span>
          <Button
            variant="secondary"
            disabled={pagina >= paginas}
            onClick={() => setPagina((p) => Math.min(paginas, p + 1))}
          >
            Próxima
          </Button>
        </div>
      )}
    </div>
  );
}

export default ListaDeClientes;
