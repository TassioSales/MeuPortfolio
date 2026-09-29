/**
 * Os dados do escritório.
 *
 * Endpoints de `backend/app/routers/escritorio.py`. Leitura para quem tem
 * conta; escrita só para administrador.
 */

import { api } from "./api";
import type { Escritorio } from "@/types";

const ROTA = "/api/v1/escritorio";

export async function buscarEscritorio(): Promise<Escritorio> {
  return api.get<Escritorio>(ROTA);
}

/** PUT: manda todos os campos. Apagar um campo é uma edição legítima. */
export async function salvarEscritorio(dados: Escritorio): Promise<Escritorio> {
  return api.put<Escritorio>(ROTA, dados);
}
