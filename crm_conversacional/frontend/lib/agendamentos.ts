/**
 * Os retornos combinados com o cliente.
 *
 * Endpoints de `backend/app/routers/agendamentos.py`.
 */

import { api } from "./api";
import type { Agendamento, NovoAgendamento, SituacaoDoAgendamento } from "@/types";

export async function listarAgendamentos(
  agentId: string,
  incluirFechados = false,
): Promise<Agendamento[]> {
  const query = incluirFechados ? "?incluir_fechados=true" : "";
  return api.get<Agendamento[]>(`/api/v1/agents/${agentId}/agendamentos${query}`);
}

export async function marcarAgendamento(
  agentId: string,
  dados: NovoAgendamento,
): Promise<Agendamento> {
  return api.post<Agendamento>(`/api/v1/agents/${agentId}/agendamentos`, dados);
}

export async function mudarSituacao(
  id: string,
  status: SituacaoDoAgendamento,
): Promise<Agendamento> {
  return api.patch<Agendamento>(`/api/v1/agendamentos/${id}`, { status });
}
