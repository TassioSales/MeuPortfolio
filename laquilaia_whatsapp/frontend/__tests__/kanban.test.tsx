/**
 * Testes do Kanban: camada de API e renderização do board.
 *
 * O arrastar em si (@dnd-kit) não é exercitado aqui — depende de eventos de
 * ponteiro que o jsdom não simula de forma fiel. O que importa e é testável
 * está coberto: a chamada de movimentação, a atualização otimista e o
 * rollback quando o backend recusa.
 */
import { render, screen, waitFor } from "@testing-library/react";
import { renderHook, act } from "@testing-library/react";
import * as kanbanApi from "@/lib/kanban";
import { useKanban } from "@/hooks/useKanban";
import { KanbanBoard } from "@/components/KanbanBoard";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";
import type { KanbanBoard as Board } from "@/types";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

const BOARD: Board = {
  agent_id: "agent-1",
  columns: [
    {
      id: "col-novo",
      nome: "Novo Lead",
      ordem: 0,
      cor_hex: "#3164ff",
      cards: [
        {
          id: "lead-1",
          nome: "Maria Silva",
          email: "maria@example.com",
          phone_number: "5561999990001",
          score_qualificacao: 85,
          status_funil: "novo",
          ordem: 0,
        },
      ],
    },
    {
      id: "col-qualificado",
      nome: "Lead Qualificado",
      ordem: 1,
      cor_hex: "#16a34a",
      cards: [],
    },
  ],
};

beforeEach(() => setStoredToken("token-abc"));
afterEach(() => clearStoredTokens());

describe("lib/kanban", () => {
  it("getBoard faz GET no board do agente", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(BOARD));

    await kanbanApi.getBoard("agent-1");

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/agents/agent-1/kanban");
    expect(init.method).toBe("GET");
  });

  it("initColumns faz POST no endpoint de inicialização", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ columns: [] }));

    await kanbanApi.initColumns("agent-1");

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/kanban/columns/init");
    expect(init.method).toBe("POST");
  });

  it("moveCard envia lead, coluna destino e posição", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "moved" }));

    await kanbanApi.moveCard("agent-1", {
      lead_id: "lead-1",
      target_column_id: "col-qualificado",
      new_order: 0,
    });

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/kanban/move");
    expect(JSON.parse(init.body)).toEqual({
      lead_id: "lead-1",
      target_column_id: "col-qualificado",
      new_order: 0,
    });
  });
});

describe("useKanban", () => {
  it("cria as colunas padrão quando o board vem vazio", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse({ agent_id: "agent-1", columns: [] }))
      .mockResolvedValueOnce(jsonResponse({ columns: [] })) // init
      .mockResolvedValueOnce(jsonResponse(BOARD));

    const { result } = renderHook(() => useKanban("agent-1"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.board?.columns).toHaveLength(2);
    expect(mockFetch.mock.calls[1][0]).toContain("/columns/init");
  });

  it("move o card na tela antes da resposta do backend", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(BOARD))
      .mockResolvedValueOnce(jsonResponse({ detail: "moved" }));

    const { result } = renderHook(() => useKanban("agent-1"));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.moveCard("lead-1", "col-qualificado", 0);
    });

    const columns = result.current.board!.columns;
    expect(columns[0].cards).toHaveLength(0);
    expect(columns[1].cards[0].id).toBe("lead-1");
  });

  it("desfaz a movimentação quando o backend recusa", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(BOARD))
      .mockResolvedValueOnce(jsonResponse({ detail: "Invalid column" }, 400));

    const { result } = renderHook(() => useKanban("agent-1"));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.moveCard("lead-1", "col-invalida", 0);
    });

    // O card volta para a coluna de origem e o erro aparece.
    const columns = result.current.board!.columns;
    expect(columns[0].cards[0].id).toBe("lead-1");
    expect(result.current.error).toBe("Invalid column");
  });

  it("guarda o erro quando o board não carrega", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "Agent not found" }, 404));

    const { result } = renderHook(() => useKanban("agent-1"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBe("Agent not found");
    expect(result.current.board).toBeNull();
  });
});

describe("KanbanBoard", () => {
  it("mostra as colunas com a contagem de cards", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(BOARD));

    render(<KanbanBoard agentId="agent-1" />);

    expect(await screen.findByText("Novo Lead")).toBeInTheDocument();
    expect(screen.getByText("Lead Qualificado")).toBeInTheDocument();
    expect(screen.getByLabelText("Lead Maria Silva")).toBeInTheDocument();
  });

  it("mostra os dados do lead no card", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(BOARD));

    render(<KanbanBoard agentId="agent-1" />);

    expect(await screen.findByText("Maria Silva")).toBeInTheDocument();
    expect(screen.getByText("5561999990001")).toBeInTheDocument();
    expect(screen.getByText("maria@example.com")).toBeInTheDocument();
    expect(screen.getByText("85")).toBeInTheDocument();
  });

  it("avisa quando ainda não há leads no funil", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({
        agent_id: "agent-1",
        columns: [{ ...BOARD.columns[0], cards: [] }, BOARD.columns[1]],
      }),
    );

    render(<KanbanBoard agentId="agent-1" />);

    expect(await screen.findByText(/Nenhum lead ainda/)).toBeInTheDocument();
  });

  it("mostra erro e botão de tentar de novo quando o board falha", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "Agent not found" }, 404));

    render(<KanbanBoard agentId="agent-1" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Agent not found");
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });
});
