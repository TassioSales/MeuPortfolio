/**
 * Tipos compartilhados do frontend.
 *
 * Os nomes de campos seguem exatamente o contrato do backend FastAPI
 * (`backend/app/models/schemas.py`), por isso ficam em português.
 */

// ========== Autenticação ==========

export interface User {
  id: string;
  email: string;
  nome: string;
  status: string;
  data_criacao: string;
}

export interface LoginRequest {
  email: string;
  senha: string;
}

export interface RegisterRequest {
  email: string;
  nome: string;
  senha: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string | null;
  token_type: string;
  expires_in: number;
}

// ========== Agentes ==========

export interface Agent {
  id: string;
  user_id: string;
  nome: string;
  descricao: string | null;
  system_prompt: string;
  temperatura: number;
  max_tokens: number;
  status: string;
  data_criacao: string;
  data_atualizacao: string;
}

/** Corpo de `POST /api/v1/agents` (schema `AgentCreate`). */
export interface AgentInput {
  nome: string;
  descricao?: string | null;
  system_prompt: string;
  temperatura: number;
  max_tokens: number;
}

/** Corpo de `PUT /api/v1/agents/{id}` — todos os campos são opcionais. */
export type AgentUpdateInput = Partial<AgentInput>;

/** Limites validados pelo backend em `agent_service.create_agent`. */
export const AGENT_LIMITS = {
  temperaturaMin: 0,
  temperaturaMax: 2,
  maxTokensMin: 1,
  maxTokensMax: 4096,
  nomeMaxLength: 255,
} as const;

// ========== Erros ==========

export interface ApiErrorBody {
  detail?: string;
  error_code?: string;
}
