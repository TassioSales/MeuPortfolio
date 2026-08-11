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

// ========== Erros ==========

export interface ApiErrorBody {
  detail?: string;
  error_code?: string;
}
