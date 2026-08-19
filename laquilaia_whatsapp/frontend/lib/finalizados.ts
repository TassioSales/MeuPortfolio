/**
 * Os casos que acabaram, agrupados pelo motivo.
 *
 * Endpoint de `backend/app/routers/finalizados.py`.
 */

import { api } from "./api";
import type { FinalizadosResponse } from "@/types";

export async function buscarFinalizados(
  agentId: string,
  dias = 90,
): Promise<FinalizadosResponse> {
  return api.get<FinalizadosResponse>(
    `/api/v1/agents/${agentId}/finalizados?dias=${dias}`,
  );
}
