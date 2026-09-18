/**
 * A assinatura pública.
 *
 * Único módulo que fala com o backend **sem** token de sessão: quem abre esta
 * página é o cliente do escritório, que não tem conta. A credencial é o
 * endereço em si.
 */

import { API_URL, ApiError } from "./api";
import type { ContratoParaAssinar } from "@/types";

const ROTA = "/api/v1/assinatura";

async function ler(resposta: Response): Promise<never> {
  let detalhe = "Não foi possível concluir.";
  try {
    const corpo = await resposta.json();
    if (corpo?.detail) detalhe = String(corpo.detail);
  } catch {
    // Resposta sem JSON (502 do proxy, por exemplo): fica a mensagem padrão.
  }
  throw new ApiError(resposta.status, detalhe);
}

export async function buscarParaAssinar(
  token: string,
): Promise<ContratoParaAssinar> {
  const r = await fetch(`${API_URL}${ROTA}/${encodeURIComponent(token)}`);
  if (!r.ok) await ler(r);
  return (await r.json()) as ContratoParaAssinar;
}

export async function assinar(
  token: string,
  nome: string,
  /** O `data:image/png;base64,...` do canvas. Opcional — ver a página. */
  assinaturaPng?: string | null,
): Promise<ContratoParaAssinar> {
  const r = await fetch(`${API_URL}${ROTA}/${encodeURIComponent(token)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      nome,
      aceite: true,
      assinatura_png: assinaturaPng ?? null,
    }),
  });
  if (!r.ok) await ler(r);
  return (await r.json()) as ContratoParaAssinar;
}
