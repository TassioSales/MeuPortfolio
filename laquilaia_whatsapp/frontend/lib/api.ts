import {
  clearStoredTokens,
  getStoredRefreshToken,
  getStoredToken,
  setStoredRefreshToken,
  setStoredToken,
} from "./tokens";

/**
 * Cliente HTTP do frontend.
 *
 * Concentra três coisas que não devem ser repetidas em cada chamada: a base da
 * URL, o cabeçalho de autorização e a renovação do token quando o backend
 * responde 401.
 */

/** Lida pelo browser, então é o endereço público da API — nunca o host interno. */
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const REFRESH_PATH = "/api/v1/auth/refresh";
const FALLBACK_MESSAGE = "Não foi possível concluir a operação.";

/** Erro de resposta do backend, já com o `detail` extraído. */
export class ApiError extends Error {
  readonly status: number;
  readonly errorCode?: string;

  constructor(status: number, message: string, errorCode?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errorCode = errorCode;
  }
}

export interface RequestOptions {
  /** Não anexa o Bearer token. Usado no login/registro, que ainda não têm sessão. */
  skipAuth?: boolean;
}

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

/**
 * Cabeçalhos como objeto simples, e não `Headers`.
 *
 * O `fetch` aceita os dois, mas o objeto é o que os testes conseguem
 * inspecionar sem instanciar a API do browser.
 */
function buildHeaders(skipAuth: boolean, hasBody: boolean): Record<string, string> {
  const headers: Record<string, string> = {};

  if (hasBody) headers["Content-Type"] = "application/json";

  if (!skipAuth) {
    const token = getStoredToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  return headers;
}

/**
 * Converte a resposta de erro em `ApiError`.
 *
 * O corpo pode não ser JSON (502 de proxy, resposta vazia), por isso o parse
 * fica protegido — sem isso o erro real viraria um `SyntaxError` sem status.
 */
async function toApiError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as { detail?: string; error_code?: string };
    return new ApiError(
      response.status,
      typeof body?.detail === "string" ? body.detail : FALLBACK_MESSAGE,
      body?.error_code,
    );
  } catch {
    return new ApiError(response.status, FALLBACK_MESSAGE);
  }
}

/**
 * Renovação em andamento.
 *
 * Uma tela como a de métricas dispara três chamadas em paralelo; sem esta
 * trava as três tentariam renovar o token ao mesmo tempo e duas das
 * renovações seriam descartadas.
 */
let refreshInFlight: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  const refreshToken = getStoredRefreshToken();
  // Sem refresh token não há o que tentar: poupa uma ida ao servidor que já
  // se sabe que vai falhar.
  if (!refreshToken) return false;

  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        // Chamada crua, sem passar por `request`: usar o próprio cliente aqui
        // faria o 401 do refresh disparar outro refresh, em laço.
        const response = await fetch(`${API_URL}${REFRESH_PATH}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (!response.ok) return false;

        const data = (await response.json()) as {
          access_token?: string;
          refresh_token?: string | null;
          expires_in?: number;
        };

        if (!data?.access_token) return false;

        setStoredToken(data.access_token, data.expires_in);
        if (data.refresh_token) setStoredRefreshToken(data.refresh_token);
        return true;
      } catch {
        return false;
      } finally {
        refreshInFlight = null;
      }
    })();
  }

  return refreshInFlight;
}

async function request<T>(
  method: Method,
  path: string,
  body?: unknown,
  options: RequestOptions = {},
): Promise<T> {
  const url = `${API_URL}${path}`;
  const hasBody = body !== undefined;
  const skipAuth = options.skipAuth === true;

  const init: RequestInit = { method, headers: buildHeaders(skipAuth, hasBody) };
  if (hasBody) init.body = JSON.stringify(body);

  let response = await fetch(url, init);

  if (response.status === 401 && !skipAuth) {
    // Guardado antes da renovação: se ela falhar, é este o erro que o
    // chamador precisa ver, não o do refresh.
    const original = await toApiError(response);

    if (!(await refreshSession())) {
      clearStoredTokens();
      throw original;
    }

    // Os cabeçalhos são remontados para pegar o token novo.
    response = await fetch(url, { ...init, headers: buildHeaders(false, hasBody) });
  }

  if (!response.ok) throw await toApiError(response);

  // 204 não tem corpo; chamar `json()` aqui estouraria.
  if (response.status === 204) return undefined as T;

  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>("GET", path, undefined, options),

  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>("POST", path, body, options),

  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>("PUT", path, body, options),

  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>("PATCH", path, body, options),

  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>("DELETE", path, undefined, options),
};
