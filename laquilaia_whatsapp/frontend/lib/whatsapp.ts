import { api } from "./api";
import type { EstadoDaConexao, QrCode, ResultadoDaDesconexao } from "@/types";

/** Endpoints de `backend/app/routers/whatsapp.py`. Só administrador. */

export async function getStatus(): Promise<EstadoDaConexao> {
  return api.get<EstadoDaConexao>("/api/v1/whatsapp/status");
}

export async function getQrCode(): Promise<QrCode> {
  return api.get<QrCode>("/api/v1/whatsapp/qrcode");
}

/**
 * Despareia o número. Derruba o atendimento até alguém ler o QR de novo.
 *
 * `POST` porque muda estado: um `GET` seria disparado por pré-carregamento de
 * link ou por extensão que visita URLs.
 */
export async function desconectar(): Promise<ResultadoDaDesconexao> {
  return api.post<ResultadoDaDesconexao>("/api/v1/whatsapp/desconectar");
}
