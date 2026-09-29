/**
 * Clientes esperando resposta.
 *
 * Endpoint de `backend/app/routers/alertas.py`.
 */

import { api } from "./api";
import type { AlertasResponse } from "@/types";

export async function buscarAlertas(
  agentId: string,
  minutos = 30,
): Promise<AlertasResponse> {
  return api.get<AlertasResponse>(
    `/api/v1/agents/${agentId}/alertas?minutos=${minutos}`,
  );
}
