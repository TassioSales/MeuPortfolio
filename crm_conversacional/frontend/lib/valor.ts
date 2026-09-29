/**
 * Valor estimado e produtividade.
 *
 * Endpoints de `backend/app/routers/valor.py` e `produtividade.py`.
 */

import { api } from "./api";
import type { ProdutividadeResponse, ValorResponse } from "@/types";

export async function buscarValor(agentId: string, dias = 30): Promise<ValorResponse> {
  return api.get<ValorResponse>(`/api/v1/agents/${agentId}/metrics/valor?dias=${dias}`);
}

export async function buscarProdutividade(
  agentId: string,
  dias = 30,
): Promise<ProdutividadeResponse> {
  return api.get<ProdutividadeResponse>(
    `/api/v1/agents/${agentId}/metrics/produtividade?dias=${dias}`,
  );
}
