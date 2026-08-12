import Cookies from "js-cookie";

import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from "./constants";

/**
 * Guarda dos tokens de sessão.
 *
 * Ficam em **cookie**, não em `localStorage`, porque o `middleware.ts` roda no
 * servidor e só enxerga cookies — com `localStorage` a proteção de rotas no
 * edge não teria como saber se há sessão.
 */

/** `secure` só sob TLS: em http://localhost o browser descartaria o cookie. */
function isSecureContext(): boolean {
  return typeof window !== "undefined" && window.location.protocol === "https:";
}

function baseAttributes(): Cookies.CookieAttributes {
  return {
    path: "/",
    sameSite: "lax",
    secure: isSecureContext(),
  };
}

function read(name: string): string | null {
  // js-cookie devolve undefined quando não existe; o resto do código
  // distingue "sem sessão" por null.
  return Cookies.get(name) ?? null;
}

export function getStoredToken(): string | null {
  return read(ACCESS_TOKEN_KEY);
}

export function getStoredRefreshToken(): string | null {
  return read(REFRESH_TOKEN_KEY);
}

/**
 * Grava o access token.
 *
 * `expiresInSeconds` vem do `expires_in` do backend. Sem ele o cookie é de
 * sessão e some ao fechar o browser, que é o comportamento seguro por padrão.
 */
export function setStoredToken(token: string, expiresInSeconds?: number): void {
  const attributes = baseAttributes();
  if (expiresInSeconds && expiresInSeconds > 0) {
    attributes.expires = new Date(Date.now() + expiresInSeconds * 1000);
  }
  Cookies.set(ACCESS_TOKEN_KEY, token, attributes);
}

/**
 * Dias que o cookie do refresh token dura.
 *
 * Acompanha a validade do JWT emitido em `auth_service.create_refresh_token`.
 * Era cookie de sessão, e por isso fechar o navegador deslogava: o token
 * continuava válido por uma semana no servidor e sumia do cliente.
 */
const REFRESH_DIAS = 7;

export function setStoredRefreshToken(token: string): void {
  Cookies.set(REFRESH_TOKEN_KEY, token, {
    ...baseAttributes(),
    expires: REFRESH_DIAS,
  });
}

export function clearStoredTokens(): void {
  // Os atributos precisam bater com os da gravação: `path` diferente apaga
  // outro cookie (ou nenhum) e a sessão sobreviveria ao logout.
  const { path, sameSite, secure } = baseAttributes();
  Cookies.remove(ACCESS_TOKEN_KEY, { path, sameSite, secure });
  Cookies.remove(REFRESH_TOKEN_KEY, { path, sameSite, secure });
}
