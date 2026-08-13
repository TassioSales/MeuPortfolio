import { api } from "./api";
import {
  clearStoredTokens,
  getStoredRefreshToken,
  getStoredToken,
  setStoredRefreshToken,
  setStoredToken,
} from "./tokens";
import type { TokenResponse, User } from "@/types";

/** Endpoints de `backend/app/routers/auth.py`. */
const LOGIN = "/api/v1/auth/login";
const REGISTER = "/api/v1/auth/register";
const ME = "/api/v1/auth/me";

/**
 * Autentica e devolve o usuário.
 *
 * O `POST /login` responde só com os tokens, então o usuário vem de um
 * `GET /me` logo em seguida — é a mesma chamada que o dashboard usa para
 * validar a sessão, e assim o formato do usuário sai de um lugar só.
 */
export async function login(email: string, senha: string): Promise<User> {
  const tokens = await api.post<TokenResponse>(
    LOGIN,
    { email, senha },
    { skipAuth: true },
  );

  setStoredToken(tokens.access_token, tokens.expires_in);
  if (tokens.refresh_token) setStoredRefreshToken(tokens.refresh_token);

  return getCurrentUser();
}

/**
 * Cria a conta. Não abre sessão: o backend devolve o usuário, não tokens —
 * quem chama decide se autentica em seguida (é o que `useAuthStore` faz).
 */
export async function register(
  nome: string,
  email: string,
  senha: string,
): Promise<User> {
  return api.post<User>(REGISTER, { nome, email, senha }, { skipAuth: true });
}

export async function getCurrentUser(): Promise<User> {
  return api.get<User>(ME);
}

/**
 * Encerra a sessão no cliente.
 *
 * Não há chamada ao backend: os JWT não são revogáveis, então apagar os
 * cookies é tudo o que o logout pode de fato garantir.
 */
export function logout(): void {
  clearStoredTokens();
}

/**
 * Há token guardado? Diz apenas isso — a validade quem confirma é o `GET /me`.
 *
 * Conta o refresh token, e não só o access. O `middleware.ts` já contava os
 * dois; aqui só o access era lido, e a diferença travava o painel numa volta
 * infinita: passados os 30 minutos do access, com o refresh ainda válido por
 * sete dias, o servidor dizia "tem sessão" e liberava `/dashboard`, o cliente
 * dizia "não tem" e mandava para `/login`, e o middleware devolvia para
 * `/dashboard` — sem nunca chegar a perguntar quem era o usuário. Na tela isso
 * é um carregando que não termina, e nos logs do backend é o silêncio: nenhuma
 * requisição chegava.
 */
export function hasStoredSession(): boolean {
  return getStoredToken() !== null || getStoredRefreshToken() !== null;
}
