/**
 * Custo de aquisição: quanto o escritório gasta para trazer cada cliente.
 *
 * Endpoints de `backend/app/routers/marketing.py`.
 */

import { api } from "./api";
import type { LancamentoMarketing, NovoLancamento, ResumoMarketing } from "@/types";

const LANCAMENTOS = "/api/v1/marketing/lancamentos";

export async function listarLancamentos(dias = 90): Promise<LancamentoMarketing[]> {
  return api.get<LancamentoMarketing[]>(`${LANCAMENTOS}?dias=${dias}`);
}

export async function criarLancamento(
  dados: NovoLancamento,
): Promise<LancamentoMarketing> {
  return api.post<LancamentoMarketing>(LANCAMENTOS, dados);
}

export async function apagarLancamento(id: string): Promise<void> {
  await api.delete<void>(`${LANCAMENTOS}/${id}`);
}

export async function buscarResumo(
  agentId: string,
  dias = 30,
): Promise<ResumoMarketing> {
  return api.get<ResumoMarketing>(
    `/api/v1/agents/${agentId}/marketing/resumo?dias=${dias}`,
  );
}
