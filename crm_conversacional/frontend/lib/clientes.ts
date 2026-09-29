/**
 * A lista de contatos.
 *
 * Endpoint de `backend/app/routers/clientes.py`.
 */

import { api } from "./api";
import type { ClientesResponse } from "@/types";

export async function listarClientes(
  agentId: string,
  opcoes: { busca?: string; etapa?: string; pagina?: number } = {},
): Promise<ClientesResponse> {
  const params = new URLSearchParams();
  if (opcoes.busca) params.set("busca", opcoes.busca);
  if (opcoes.etapa) params.set("etapa", opcoes.etapa);
  if (opcoes.pagina && opcoes.pagina > 1) params.set("pagina", String(opcoes.pagina));

  const query = params.toString();
  return api.get<ClientesResponse>(
    `/api/v1/agents/${agentId}/clientes${query ? `?${query}` : ""}`,
  );
}
