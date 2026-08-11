/**
 * Constantes compartilhadas entre o middleware (edge), os componentes de
 * servidor e o cliente.
 *
 * Ficam num módulo sem dependências de propósito: o `middleware.ts` roda no
 * edge runtime, onde importar o cliente HTTP arrastaria `js-cookie` e o
 * `fetch` do browser para um lugar que não os tem.
 */

/** Nome do cookie do access token. O middleware confere a presença dele. */
export const ACCESS_TOKEN_KEY = "laquilaia_access_token";

/** Nome do cookie do refresh token, usado para renovar a sessão em 401. */
export const REFRESH_TOKEN_KEY = "laquilaia_refresh_token";

/** Para onde vai quem já está autenticado. */
export const DEFAULT_AUTHENTICATED_ROUTE = "/dashboard";
