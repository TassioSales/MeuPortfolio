/**
 * Testes da proteção de rotas feita no middleware (edge).
 *
 * @jest-environment node
 *
 * Roda em `node`, e não em jsdom, porque `next/server` depende dos globais
 * web (`Request`/`Response`) que o jsdom não implementa — o mesmo ambiente
 * que o middleware encontra no edge runtime.
 */
import { NextRequest } from "next/server";
import { middleware } from "@/middleware";
import { ACCESS_TOKEN_KEY } from "@/lib/constants";

function requestFor(path: string, { withSession = false } = {}): NextRequest {
  const request = new NextRequest(new URL(path, "http://localhost:3000"));
  if (withSession) request.cookies.set(ACCESS_TOKEN_KEY, "token-abc");
  return request;
}

describe("middleware", () => {
  it("redireciona para /login quem acessa /dashboard sem sessão", () => {
    const response = middleware(requestFor("/dashboard"));

    const location = new URL(response.headers.get("location") as string);
    expect(response.status).toBe(307);
    expect(location.pathname).toBe("/login");
  });

  it("guarda a rota pretendida em ?next para voltar depois do login", () => {
    const response = middleware(requestFor("/dashboard/agents"));

    const location = new URL(response.headers.get("location") as string);
    expect(location.searchParams.get("next")).toBe("/dashboard/agents");
  });

  it("deixa passar quem tem sessão", () => {
    const response = middleware(requestFor("/dashboard", { withSession: true }));

    expect(response.headers.get("location")).toBeNull();
  });

  it("manda quem já está logado de /login para o dashboard", () => {
    const response = middleware(requestFor("/login", { withSession: true }));

    const location = new URL(response.headers.get("location") as string);
    expect(location.pathname).toBe("/dashboard");
  });

  it("não interfere em /login sem sessão", () => {
    const response = middleware(requestFor("/login"));

    expect(response.headers.get("location")).toBeNull();
  });

  it("não protege rotas públicas", () => {
    const response = middleware(requestFor("/register"));

    expect(response.headers.get("location")).toBeNull();
  });
});
