/**
 * O funil de venda.
 *
 * Endpoint de `backend/app/routers/funil.py`.
 */

import { api } from "./api";
import type { FunilResponse } from "@/types";

/** `dias = 0` é desde sempre. */
export async function buscarFunil(agentId: string, dias = 0): Promise<FunilResponse> {
  const query = dias ? `?dias=${dias}` : "";
  return api.get<FunilResponse>(`/api/v1/agents/${agentId}/metrics/funil${query}`);
}
