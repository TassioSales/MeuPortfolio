/**
 * Testes do fluxo de autenticação (lib/auth + store useAuthStore).
 */
import * as auth from "@/lib/auth";
import { clearStoredTokens, getStoredRefreshToken, getStoredToken } from "@/lib/tokens";
import { useAuthStore } from "@/hooks/useAuth";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

const TOKENS = {
  access_token: "access-123",
  refresh_token: "refresh-123",
  token_type: "bearer",
  expires_in: 1800,
};

const USER = {
  id: "user-1",
  email: "tassio@example.com",
  nome: "Tassio",
  status: "ativo",
  data_criacao: "2026-08-11T00:00:00Z",
};

describe("lib/auth", () => {
  afterEach(() => clearStoredTokens());

  it("login salva os dois tokens e devolve o usuário", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(TOKENS)) // POST /login
      .mockResolvedValueOnce(jsonResponse(USER)); // GET /me

    const user = await auth.login("tassio@example.com", "senha12345");

    expect(user).toEqual(USER);
    expect(getStoredToken()).toBe("access-123");
    expect(getStoredRefreshToken()).toBe("refresh-123");
  });

  it("login com credencial errada propaga o erro e não cria sessão", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "Invalid credentials" }, 401));

    await expect(auth.login("errado@example.com", "senha-errada")).rejects.toMatchObject({
      status: 401,
    });
    expect(getStoredToken()).toBeNull();
  });

  it("register envia nome, email e senha no formato do backend", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(USER, 201));

    await auth.register("Tassio", "tassio@example.com", "senha12345");

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/auth/register");
    expect(JSON.parse(init.body)).toEqual({
      nome: "Tassio",
      email: "tassio@example.com",
      senha: "senha12345",
    });
  });

  it("logout apaga os tokens armazenados", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(TOKENS))
      .mockResolvedValueOnce(jsonResponse(USER));
    await auth.login("tassio@example.com", "senha12345");

    auth.logout();

    expect(getStoredToken()).toBeNull();
    expect(getStoredRefreshToken()).toBeNull();
    expect(auth.hasStoredSession()).toBe(false);
  });
});

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, isLoading: true, error: null });
  });
  afterEach(() => clearStoredTokens());

  it("login popula o usuário e desliga o loading", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(TOKENS))
      .mockResolvedValueOnce(jsonResponse(USER));

    await useAuthStore.getState().login("tassio@example.com", "senha12345");

    const state = useAuthStore.getState();
    expect(state.user).toEqual(USER);
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });

  it("login com falha guarda a mensagem de erro do backend", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "Invalid credentials" }, 401));

    await expect(
      useAuthStore.getState().login("errado@example.com", "x"),
    ).rejects.toBeDefined();

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.error).toBe("Invalid credentials");
    expect(state.isLoading).toBe(false);
  });

  it("register autentica em seguida para o usuário já entrar logado", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(USER, 201)) // register
      .mockResolvedValueOnce(jsonResponse(TOKENS)) // login
      .mockResolvedValueOnce(jsonResponse(USER)); // me

    await useAuthStore.getState().register("Tassio", "tassio@example.com", "senha12345");

    expect(useAuthStore.getState().user).toEqual(USER);
    expect(getStoredToken()).toBe("access-123");
  });

  it("loadSession sem cookie não chama a API", async () => {
    await useAuthStore.getState().loadSession();

    expect(mockFetch).not.toHaveBeenCalled();
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().isLoading).toBe(false);
  });

  it("loadSession com token válido recupera o usuário", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(TOKENS))
      .mockResolvedValueOnce(jsonResponse(USER));
    await auth.login("tassio@example.com", "senha12345");
    useAuthStore.setState({ user: null, isLoading: true });

    mockFetch.mockResolvedValueOnce(jsonResponse(USER));
    await useAuthStore.getState().loadSession();

    expect(useAuthStore.getState().user).toEqual(USER);
  });

  it("loadSession com token inválido descarta a sessão", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(TOKENS))
      .mockResolvedValueOnce(jsonResponse(USER));
    await auth.login("tassio@example.com", "senha12345");
    useAuthStore.setState({ user: null, isLoading: true });

    // GET /me falha e não há refresh válido para recuperar.
    mockFetch
      .mockResolvedValueOnce(jsonResponse({ detail: "expirado" }, 401))
      .mockResolvedValueOnce(jsonResponse({ detail: "invalid" }, 401));

    await useAuthStore.getState().loadSession();

    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().isLoading).toBe(false);
    expect(getStoredToken()).toBeNull();
  });

  it("logout limpa usuário e tokens", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(TOKENS))
      .mockResolvedValueOnce(jsonResponse(USER));
    await useAuthStore.getState().login("tassio@example.com", "senha12345");

    useAuthStore.getState().logout();

    expect(useAuthStore.getState().user).toBeNull();
    expect(getStoredToken()).toBeNull();
  });
});
