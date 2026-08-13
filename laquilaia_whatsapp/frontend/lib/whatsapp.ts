import { api } from "./api";
import type { EstadoDaConexao, QrCode } from "@/types";

/** Endpoints de `backend/app/routers/whatsapp.py`. Só administrador. */

export async function getStatus(): Promise<EstadoDaConexao> {
  return api.get<EstadoDaConexao>("/api/v1/whatsapp/status");
}

export async function getQrCode(): Promise<QrCode> {
  return api.get<QrCode>("/api/v1/whatsapp/qrcode");
}
