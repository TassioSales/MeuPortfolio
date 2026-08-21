/**
 * Modelos de contrato, dados civis do cliente e contratos emitidos.
 *
 * Endpoints de `backend/app/routers/contratos.py`. Escrever **modelo** exige
 * administrador; preencher dados e emitir contrato, não — quem fecha o
 * atendimento faz as duas coisas.
 */

import { api } from "./api";
import type {
  Contrato,
  DadosDoContrato,
  ModeloDeContrato,
  VariavelDeContrato,
} from "@/types";

const ROTA = "/api/v1/contratos";

export async function listarVariaveis(): Promise<VariavelDeContrato[]> {
  return api.get<VariavelDeContrato[]>(`${ROTA}/variaveis`);
}

export async function listarModelos(): Promise<ModeloDeContrato[]> {
  return api.get<ModeloDeContrato[]>(`${ROTA}/modelos`);
}

export async function criarModelo(dados: {
  nome: string;
  corpo: string;
  ativo: boolean;
}): Promise<ModeloDeContrato> {
  return api.post<ModeloDeContrato>(`${ROTA}/modelos`, dados);
}

export async function atualizarModelo(
  id: string,
  dados: { nome: string; corpo: string; ativo: boolean },
): Promise<ModeloDeContrato> {
  return api.put<ModeloDeContrato>(`${ROTA}/modelos/${id}`, dados);
}

export async function excluirModelo(id: string): Promise<void> {
  await api.delete<void>(`${ROTA}/modelos/${id}`);
}

export async function buscarDados(leadId: string): Promise<DadosDoContrato> {
  return api.get<DadosDoContrato>(`${ROTA}/leads/${leadId}/dados`);
}

/** PUT: manda todos os campos. Apagar um é edição legítima. */
export async function salvarDados(
  leadId: string,
  dados: DadosDoContrato,
): Promise<DadosDoContrato> {
  return api.put<DadosDoContrato>(`${ROTA}/leads/${leadId}/dados`, dados);
}

export async function listarContratos(leadId: string): Promise<Contrato[]> {
  return api.get<Contrato[]>(`${ROTA}/leads/${leadId}`);
}

/** Sem `modeloId`, usa o modelo ativo — que é o caso normal. */
export async function gerarContrato(
  leadId: string,
  modeloId?: string,
): Promise<Contrato> {
  return api.post<Contrato>(`${ROTA}/leads/${leadId}`, {
    modelo_id: modeloId ?? null,
  });
}

/**
 * Abre o PDF numa aba nova.
 *
 * Não é um `<a href>` para o endpoint porque a autorização vai no cabeçalho
 * `Bearer`, e uma aba nova não o manda — o link abriria um 401 em branco. Por
 * isso o binário é baixado com credencial e só depois vira endereço local.
 */
export async function abrirPdf(contratoId: string): Promise<void> {
  const blob = await api.blob(`${ROTA}/${contratoId}/pdf`);
  const endereco = URL.createObjectURL(blob);
  window.open(endereco, "_blank", "noopener,noreferrer");
  // O endereço fica válido enquanto a aba de origem viver; revogar na hora
  // fecharia o PDF antes de ele abrir. Um minuto é folga suficiente e evita
  // segurar o arquivo em memória pela sessão inteira.
  window.setTimeout(() => URL.revokeObjectURL(endereco), 60_000);
}
