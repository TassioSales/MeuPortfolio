"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { messageFrom } from "@/hooks/useAgents";
import { listarAgendamentos, marcarAgendamento, mudarSituacao } from "@/lib/agendamentos";
import { formatarTelefone } from "@/lib/telefone";
import { cn } from "@/lib/utils";
import type { Agendamento } from "@/types";

function horario(iso: string): string {
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return "—";
  return data.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function atrasoEmPalavras(minutos: number): string {
  if (minutos < 60) return `${minutos} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `${horas}h`;
  return `${Math.floor(horas / 24)}d`;
}

function Linha({
  agendamento,
  onFechar,
}: {
  agendamento: Agendamento;
  onFechar: (id: string, status: "realizado" | "cancelado") => void;
}) {
  const atrasado = agendamento.minutos_de_atraso > 0;

  return (
    <li
      className={cn(
        "flex flex-wrap items-center gap-3 border-b border-surface-border px-4 py-3 last:border-0",
        agendamento.status !== "pendente" && "opacity-60",
      )}
    >
      <span
        className={cn(
          "shrink-0 rounded px-2 py-0.5 text-xs tabular-nums",
          atrasado
            ? "bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-200"
            : "bg-surface-muted text-fg-soft",
        )}
      >
        {horario(agendamento.quando)}
      </span>

      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium text-fg">
          {agendamento.lead_nome ?? formatarTelefone(agendamento.phone_number)}
        </span>
        <span className="block truncate text-xs text-fg-muted">
          {agendamento.motivo ?? "Retorno combinado"}
          {agendamento.criado_por && ` · marcado por ${agendamento.criado_por}`}
        </span>
      </span>

      {atrasado && (
        <span className="shrink-0 text-xs font-medium text-red-700 dark:text-red-300">
          atrasado {atrasoEmPalavras(agendamento.minutos_de_atraso)}
        </span>
      )}

      {agendamento.status === "pendente" ? (
        <span className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={() => onFechar(agendamento.id, "realizado")}
            className="text-xs font-medium text-brand-700 underline-offset-2 hover:underline dark:text-brand-300"
          >
            Concluir
          </button>
          <button
            type="button"
            onClick={() => onFechar(agendamento.id, "cancelado")}
            className="text-xs text-fg-muted underline-offset-2 hover:underline"
          >
            Cancelar
          </button>
        </span>
      ) : (
        <span className="shrink-0 text-xs uppercase tracking-wide text-fg-faint">
          {agendamento.status}
        </span>
      )}
    </li>
  );
}

/**
 * Os retornos combinados com o cliente.
 *
 * "Te ligo amanhã às 15h" era dito na conversa e morria ali: virava um
 * compromisso que só existia na cabeça de quem prometeu, enquanto o cliente
 * esperava a ligação que ninguém marcou.
 *
 * O grupo que justifica a tela é **atrasado** — retorno cuja hora passou e
 * ninguém fechou. É a mesma omissão que a faixa de pendências trata nas
 * conversas: não aparece em lugar nenhum até o cliente reclamar.
 */
export function Agendamentos({
  agentId,
  leadId,
  nomeDoLead,
}: {
  agentId: string;
  /** Quando presente, a tela vira a agenda daquele contato e oferece marcar. */
  leadId?: string;
  nomeDoLead?: string;
}) {
  const [lista, setLista] = useState<Agendamento[]>([]);
  const [incluirFechados, setIncluirFechados] = useState(false);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const [quando, setQuando] = useState("");
  const [motivo, setMotivo] = useState("");
  const [salvando, setSalvando] = useState(false);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setLista(await listarAgendamentos(agentId, incluirFechados));
      setErro(null);
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível carregar os retornos."));
    } finally {
      setCarregando(false);
    }
  }, [agentId, incluirFechados]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const visiveis = useMemo(
    () => (leadId ? lista.filter((a) => a.lead_id === leadId) : lista),
    [lista, leadId],
  );
  const atrasados = visiveis.filter((a) => a.minutos_de_atraso > 0).length;

  async function marcar(evento: React.FormEvent) {
    evento.preventDefault();
    if (!leadId || !quando) return;

    setSalvando(true);
    setErro(null);
    try {
      await marcarAgendamento(agentId, {
        lead_id: leadId,
        // O `<input type="datetime-local">` dá hora local sem fuso; o backend
        // guarda em UTC. Sem o `toISOString`, um retorno marcado para as 15h
        // apareceria às 18h para quem está em UTC-3.
        quando: new Date(quando).toISOString(),
        motivo: motivo.trim() || null,
      });
      setQuando("");
      setMotivo("");
      await carregar();
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível marcar o retorno."));
    } finally {
      setSalvando(false);
    }
  }

  async function fechar(id: string, status: "realizado" | "cancelado") {
    setErro(null);
    try {
      await mudarSituacao(id, status);
      await carregar();
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível atualizar o retorno."));
    }
  }

  if (carregando && lista.length === 0) {
    return <LoadingSpinner label="Carregando retornos..." />;
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-fg-soft">
          <input
            type="checkbox"
            checked={incluirFechados}
            onChange={(e) => setIncluirFechados(e.target.checked)}
            className="bg-surface"
          />
          Mostrar concluídos
        </label>

        {atrasados > 0 && (
          <p className="ml-auto text-sm font-medium text-red-700 dark:text-red-300" role="status">
            {atrasados === 1 ? "1 retorno atrasado" : `${atrasados} retornos atrasados`}
          </p>
        )}
      </div>

      {erro && (
        <p
          role="alert"
          className="mb-3 rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200"
        >
          {erro}
        </p>
      )}

      {leadId && (
        <form
          onSubmit={marcar}
          className="mb-4 rounded-xl border border-surface-border bg-surface p-4"
        >
          <h3 className="mb-3 text-sm font-medium text-fg">
            Marcar retorno{nomeDoLead ? ` com ${nomeDoLead}` : ""}
          </h3>
          <div className="grid items-end gap-3 sm:grid-cols-3">
            <Input
              label="Quando"
              type="datetime-local"
              value={quando}
              onChange={(e) => setQuando(e.target.value)}
              required
            />
            <Input
              label="Motivo"
              maxLength={500}
              placeholder="Coletar documentos"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
            />
            <Button type="submit" isLoading={salvando} disabled={!quando}>
              Marcar
            </Button>
          </div>
        </form>
      )}

      {visiveis.length === 0 ? (
        <p className="rounded-xl border border-surface-border bg-surface px-5 py-8 text-center text-sm text-fg-muted">
          Nenhum retorno combinado.
        </p>
      ) : (
        <ul className="overflow-hidden rounded-xl border border-surface-border bg-surface">
          {visiveis.map((agendamento) => (
            <Linha key={agendamento.id} agendamento={agendamento} onFechar={fechar} />
          ))}
        </ul>
      )}
    </div>
  );
}

export default Agendamentos;
