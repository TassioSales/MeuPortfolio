/**
 * Testes do playground: envio, estado de espera, reset e recuperação de erro.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatPlayground } from "@/components/ChatPlayground";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";
import type { Agent } from "@/types";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

const AGENT: Agent = {
  id: "agent-1",
  user_id: "user-1",
  nome: "Qualificador",
  descricao: null,
  system_prompt: "Você é um assistente.",
  temperatura: 0.7,
  max_tokens: 1024,
  anexos_habilitados: false,
  status: "ativo",
  data_criacao: "2026-08-11T00:00:00Z",
  data_atualizacao: "2026-08-11T00:00:00Z",
};

const EMPTY_HISTORY = { conversation_id: null, messages: [] };

function reply(text: string, conversationId = "conv-1") {
  return {
    response: text,
    conversation_id: conversationId,
    tokens_used: { input_tokens: 10, output_tokens: 5, total_tokens: 15 },
    timestamp: "2026-08-11T00:00:00Z",
    model: "claude-sonnet-5",
  };
}

beforeEach(() => {
  setStoredToken("token-abc");
  // jsdom não implementa scrollIntoView.
  Element.prototype.scrollIntoView = jest.fn();
});
afterEach(() => clearStoredTokens());

describe("ChatPlayground", () => {
  it("mostra o estado vazio quando o agente nunca foi testado", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(EMPTY_HISTORY));

    render(<ChatPlayground agent={AGENT} />);

    expect(await screen.findByText("Converse com o agente")).toBeInTheDocument();
  });

  it("carrega o histórico existente ao abrir", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({
        conversation_id: "conv-1",
        messages: [
          { id: "m1", remetente: "user", conteudo: "Oi", timestamp: "2026-08-11T00:00:00Z" },
          {
            id: "m2",
            remetente: "assistant",
            conteudo: "Olá! Tudo bem?",
            timestamp: "2026-08-11T00:00:01Z",
          },
        ],
      }),
    );

    render(<ChatPlayground agent={AGENT} />);

    expect(await screen.findByText("Oi")).toBeInTheDocument();
    expect(screen.getByText("Olá! Tudo bem?")).toBeInTheDocument();
  });

  it("envia a mensagem e mostra a resposta do agente", async () => {
    const user = userEvent.setup();
    mockFetch
      .mockResolvedValueOnce(jsonResponse(EMPTY_HISTORY))
      .mockResolvedValueOnce(jsonResponse(reply("Claro, posso ajudar!")));

    render(<ChatPlayground agent={AGENT} />);
    await screen.findByText("Converse com o agente");

    await user.type(screen.getByLabelText("Mensagem"), "Preciso de ajuda");
    await user.click(screen.getByRole("button", { name: "Enviar" }));

    expect(await screen.findByText("Claro, posso ajudar!")).toBeInTheDocument();
    expect(screen.getByText("Preciso de ajuda")).toBeInTheDocument();
  });

  it("mostra o total de tokens da resposta", async () => {
    const user = userEvent.setup();
    mockFetch
      .mockResolvedValueOnce(jsonResponse(EMPTY_HISTORY))
      .mockResolvedValueOnce(jsonResponse(reply("Resposta")));

    render(<ChatPlayground agent={AGENT} />);
    await screen.findByText("Converse com o agente");

    await user.type(screen.getByLabelText("Mensagem"), "Oi");
    await user.click(screen.getByRole("button", { name: "Enviar" }));

    expect(await screen.findByText("15 tokens")).toBeInTheDocument();
  });

  it("reenvia usando o conversation_id devolvido, mantendo o contexto", async () => {
    const user = userEvent.setup();
    mockFetch
      .mockResolvedValueOnce(jsonResponse(EMPTY_HISTORY))
      .mockResolvedValueOnce(jsonResponse(reply("Primeira resposta")))
      .mockResolvedValueOnce(jsonResponse(reply("Segunda resposta")));

    render(<ChatPlayground agent={AGENT} />);
    await screen.findByText("Converse com o agente");

    await user.type(screen.getByLabelText("Mensagem"), "Um");
    await user.click(screen.getByRole("button", { name: "Enviar" }));
    await screen.findByText("Primeira resposta");

    await user.type(screen.getByLabelText("Mensagem"), "Dois");
    await user.click(screen.getByRole("button", { name: "Enviar" }));
    await screen.findByText("Segunda resposta");

    const secondCall = mockFetch.mock.calls[2];
    expect(JSON.parse(secondCall[1].body)).toEqual({
      message: "Dois",
      conversation_id: "conv-1",
    });
  });

  it("não envia mensagem em branco", async () => {
    const user = userEvent.setup();
    mockFetch.mockResolvedValueOnce(jsonResponse(EMPTY_HISTORY));

    render(<ChatPlayground agent={AGENT} />);
    await screen.findByText("Converse com o agente");

    await user.type(screen.getByLabelText("Mensagem"), "   ");

    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
  });

  it("devolve o texto ao usuário quando o envio falha", async () => {
    const user = userEvent.setup();
    mockFetch
      .mockResolvedValueOnce(jsonResponse(EMPTY_HISTORY))
      .mockResolvedValueOnce(jsonResponse({ detail: "Rate limit exceeded" }, 422));

    render(<ChatPlayground agent={AGENT} />);
    await screen.findByText("Converse com o agente");

    await user.type(screen.getByLabelText("Mensagem"), "Mensagem cara");
    await user.click(screen.getByRole("button", { name: "Enviar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Rate limit exceeded");
    // Nada de perder o que foi digitado — o texto volta para a caixa.
    expect(screen.getByLabelText("Mensagem")).toHaveValue("Mensagem cara");
  });

  it("limpar conversa fica desabilitado sem mensagens", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(EMPTY_HISTORY));

    render(<ChatPlayground agent={AGENT} />);
    await screen.findByText("Converse com o agente");

    expect(screen.getByRole("button", { name: "Limpar conversa" })).toBeDisabled();
  });

  it("limpar conversa pede confirmação e esvazia a tela", async () => {
    const user = userEvent.setup();
    mockFetch
      .mockResolvedValueOnce(
        jsonResponse({
          conversation_id: "conv-1",
          messages: [
            {
              id: "m1",
              remetente: "user",
              conteudo: "Mensagem antiga",
              timestamp: "2026-08-11T00:00:00Z",
            },
          ],
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ detail: "reset", deleted: 1 }));

    render(<ChatPlayground agent={AGENT} />);
    await screen.findByText("Mensagem antiga");

    await user.click(screen.getByRole("button", { name: "Limpar conversa" }));
    await user.click(screen.getByRole("button", { name: "Limpar" }));

    await waitFor(() =>
      expect(screen.queryByText("Mensagem antiga")).not.toBeInTheDocument(),
    );

    const [url, init] = mockFetch.mock.calls[1];
    expect(url).toContain("/chat/history");
    expect(init.method).toBe("DELETE");
  });

  it("mostra erro quando o histórico não carrega", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "Agent not found" }, 404));

    render(<ChatPlayground agent={AGENT} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Agent not found");
  });
});
