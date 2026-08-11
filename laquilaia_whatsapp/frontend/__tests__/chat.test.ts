/**
 * Testes da camada de chat (lib/chat) — verbos, corpos e continuidade
 * da conversa.
 */
import * as chatApi from "@/lib/chat";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

const REPLY = {
  response: "Olá!",
  conversation_id: "conv-1",
  tokens_used: { input_tokens: 10, output_tokens: 5, total_tokens: 15 },
  timestamp: "2026-08-11T00:00:00Z",
  model: "claude-sonnet-5",
};

describe("lib/chat", () => {
  beforeEach(() => setStoredToken("token-abc"));
  afterEach(() => clearStoredTokens());

  it("sendMessage faz POST no endpoint de chat do agente", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(REPLY));

    await chatApi.sendMessage("agent-1", "Oi");

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/agents/agent-1/chat");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ message: "Oi" });
  });

  it("sendMessage envia conversation_id quando há conversa em andamento", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(REPLY));

    await chatApi.sendMessage("agent-1", "Segunda", "conv-1");

    const [, init] = mockFetch.mock.calls[0];
    expect(JSON.parse(init.body)).toEqual({
      message: "Segunda",
      conversation_id: "conv-1",
    });
  });

  it("sendMessage omite conversation_id quando ainda não existe conversa", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(REPLY));

    await chatApi.sendMessage("agent-1", "Primeira", null);

    const [, init] = mockFetch.mock.calls[0];
    expect(JSON.parse(init.body)).not.toHaveProperty("conversation_id");
  });

  it("sendMessage devolve o conversation_id para continuar a conversa", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(REPLY));

    const reply = await chatApi.sendMessage("agent-1", "Oi");

    expect(reply.conversation_id).toBe("conv-1");
    expect(reply.tokens_used.total_tokens).toBe(15);
  });

  it("getHistory faz GET no histórico do agente", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ conversation_id: "conv-1", messages: [] }),
    );

    await chatApi.getHistory("agent-1");

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/agents/agent-1/chat/history");
    expect(init.method).toBe("GET");
  });

  it("resetHistory faz DELETE no histórico do agente", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "reset", deleted: 2 }));

    await chatApi.resetHistory("agent-1");

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/agents/agent-1/chat/history");
    expect(init.method).toBe("DELETE");
  });

  it("propaga o erro do backend com a mensagem de detail", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "Agent not found" }, 404));

    await expect(chatApi.sendMessage("inexistente", "Oi")).rejects.toMatchObject({
      status: 404,
      message: "Agent not found",
    });
  });
});
