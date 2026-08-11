/**
 * Testes do cliente HTTP: header de autorização, tratamento de erro
 * e renovação automática do token em 401.
 */
import { api, ApiError, API_URL } from "@/lib/api";
import {
  clearStoredTokens,
  getStoredToken,
  setStoredRefreshToken,
  setStoredToken,
} from "@/lib/tokens";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("apiCall", () => {
  afterEach(() => clearStoredTokens());

  it("monta a URL a partir de NEXT_PUBLIC_API_URL", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }));

    await api.get("/api/v1/health");

    expect(mockFetch).toHaveBeenCalledWith(
      `${API_URL}/api/v1/health`,
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("anexa o Bearer token quando há sessão", async () => {
    setStoredToken("token-abc");
    mockFetch.mockResolvedValueOnce(jsonResponse({ id: "1" }));

    await api.get("/api/v1/auth/me");

    const [, init] = mockFetch.mock.calls[0];
    expect(init.headers.Authorization).toBe("Bearer token-abc");
  });

  it("não anexa Authorization quando skipAuth é usado", async () => {
    setStoredToken("token-abc");
    mockFetch.mockResolvedValueOnce(jsonResponse({ access_token: "x" }));

    await api.post("/api/v1/auth/login", { email: "a@b.c" }, { skipAuth: true });

    const [, init] = mockFetch.mock.calls[0];
    expect(init.headers.Authorization).toBeUndefined();
  });

  it("converte erro do backend em ApiError com o detail", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ detail: "Invalid credentials" }, 401),
    );

    await expect(
      api.post("/api/v1/auth/login", {}, { skipAuth: true }),
    ).rejects.toMatchObject({ status: 401, message: "Invalid credentials" });
  });

  it("usa mensagem padrão quando a resposta de erro não tem corpo JSON", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error("sem corpo");
      },
    } as unknown as Response);

    await expect(api.get("/api/v1/agents")).rejects.toBeInstanceOf(ApiError);
  });

  it("renova o token em 401 e repete a requisição original", async () => {
    setStoredToken("token-velho");
    setStoredRefreshToken("refresh-valido");

    mockFetch
      .mockResolvedValueOnce(jsonResponse({ detail: "expirado" }, 401)) // 1ª tentativa
      .mockResolvedValueOnce(
        jsonResponse({ access_token: "token-novo", expires_in: 1800 }),
      ) // refresh
      .mockResolvedValueOnce(jsonResponse({ id: "agent-1" })); // repetição

    const result = await api.get<{ id: string }>("/api/v1/agents/agent-1");

    expect(result).toEqual({ id: "agent-1" });
    expect(mockFetch).toHaveBeenCalledTimes(3);
    expect(getStoredToken()).toBe("token-novo");

    const [, retryInit] = mockFetch.mock.calls[2];
    expect(retryInit.headers.Authorization).toBe("Bearer token-novo");
  });

  it("limpa a sessão quando o refresh também falha", async () => {
    setStoredToken("token-velho");
    setStoredRefreshToken("refresh-invalido");

    mockFetch
      .mockResolvedValueOnce(jsonResponse({ detail: "expirado" }, 401))
      .mockResolvedValueOnce(jsonResponse({ detail: "invalid refresh" }, 401));

    await expect(api.get("/api/v1/agents")).rejects.toMatchObject({ status: 401 });
    expect(getStoredToken()).toBeNull();
  });

  it("não tenta renovar quando não há refresh token", async () => {
    setStoredToken("token-velho");

    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "expirado" }, 401));

    await expect(api.get("/api/v1/agents")).rejects.toMatchObject({ status: 401 });
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });
});
