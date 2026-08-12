import { NextResponse, type NextRequest } from "next/server";
import {
  ACCESS_TOKEN_KEY,
  DEFAULT_AUTHENTICATED_ROUTE,
  REFRESH_TOKEN_KEY,
} from "@/lib/constants";

/**
 * Primeira barreira de proteção de rotas: roda no servidor e só enxerga o
 * cookie, então confere apenas a *presença* do token. A validade é checada
 * no `DashboardLayout`, que consulta `GET /api/v1/auth/me`.
 */
const PRIVATE_PREFIXES = ["/dashboard"];
const AUTH_ROUTES = ["/login", "/register"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  // O refresh token conta como sessão.
  //
  // Conferindo só o access, o middleware expulsava para o login assim que ele
  // expirava — meia hora —, mesmo com refresh válido por uma semana. O
  // `api.ts` sabe renovar em 401, mas numa navegação o middleware responde
  // antes de qualquer requisição sair. Quem valida de fato é o
  // `DashboardLayout`, com `GET /auth/me`; aqui basta haver por onde renovar.
  const hasSession =
    request.cookies.has(ACCESS_TOKEN_KEY) ||
    request.cookies.has(REFRESH_TOKEN_KEY);

  const isPrivate = PRIVATE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );

  if (isPrivate && !hasSession) {
    const loginUrl = new URL("/login", request.url);
    // Guarda o destino para voltar a ele depois do login.
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Quem já tem sessão não precisa ver login/registro.
  if (AUTH_ROUTES.includes(pathname) && hasSession) {
    return NextResponse.redirect(new URL(DEFAULT_AUTHENTICATED_ROUTE, request.url));
  }

  return NextResponse.next();
}

export const config = {
  // Ignora estáticos e assets para o middleware não rodar à toa.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.svg$).*)"],
};
