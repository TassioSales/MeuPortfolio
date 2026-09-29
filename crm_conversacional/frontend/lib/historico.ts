/**
 * A trilha do que aconteceu com os leads.
 *
 * Endpoint de `backend/app/routers/historico.py`.
 */

import { api } from "./api";
import type { HistoricoResponse } from "@/types";

export async function buscarHistorico(
  agentId: string,
  opcoes: { dias?: number; apenasHumanos?: boolean; pagina?: number } = {},
): Promise<HistoricoResponse> {
  const params = new URLSearchParams();
  if (opcoes.dias) params.set("dias", String(opcoes.dias));
  if (opcoes.apenasHumanos) params.set("apenas_humanos", "true");
  if (opcoes.pagina && opcoes.pagina > 1) params.set("pagina", String(opcoes.pagina));

  const query = params.toString();
  return api.get<HistoricoResponse>(
    `/api/v1/agents/${agentId}/historico${query ? `?${query}` : ""}`,
  );
}
