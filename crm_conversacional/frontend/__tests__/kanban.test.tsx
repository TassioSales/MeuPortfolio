/**
 * Testes do Kanban: camada de API e renderização do board.
 *
 * O arrastar em si (@dnd-kit) não é exercitado aqui — depende de eventos de
 * ponteiro que o jsdom não simula de forma fiel. O que importa e é testável
 * está coberto: a chamada de movimentação, a atualização otimista e o
 * rollback quando o backend recusa.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderHook, act } from "@testing-library/react";
import * as kanbanApi from "@/lib/kanban";
import { useKanban } from "@/hooks/useKanban";
import { KanbanBoard } from "@/components/KanbanBoard";
import { KanbanCardItem } from "@/components/KanbanCard";
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
          dias_parado: 0,
          empresa: null,
          cargo: null,
          valor_estimado_min: null,
          valor_estimado_max: null,
          viabilidade: null,
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
    // Formatado, e como link: o número cru é ilegível e inútil para responder.
    expect(screen.getByText("+55 61 99999-0001")).toBeInTheDocument();
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


describe("Dossiê do contato", () => {
  const DOSSIE = {
    lead_id: "lead-1",
    nome: "Maria Silva",
    email: "maria@example.com",
    phone_number: "5561999990001",
    status_funil: "qualificado",
    score_qualificacao: 85,
    data_criacao: "2026-08-10T09:00:00Z",
    conversation_id: "conv-1",
    dados_economicos: "salário R$ 2.100, 4 anos de casa",
    documentos_em_maos: "atestado e prints do RH",
    inconsistencias: "Não disse se recebeu a rescisão",
    problemas_detectados: "Prazo apertado",
    recomendacoes: "Pedir a carta de justa causa",
    analise_preliminar: null,
    casos: [
      {
        id: "caso-1",
        area: "trabalhista",
        resumo: "Justa causa por abandono.",
        titular: null,
        score_qualificacao: 85,
        valor_estimado_min: 18000,
        valor_estimado_max: 75000,
        viabilidade: "acima_do_piso",
        data_abertura: "2026-08-10T09:00:00Z",
        analise_preliminar: "## Resumo\nCliente relata demissão.",
      },
    ],
  };

  async function abrirCard(dossie: unknown = DOSSIE) {
    mockFetch.mockResolvedValueOnce(jsonResponse(BOARD));
    mockFetch.mockResolvedValueOnce(jsonResponse(dossie));
    render(<KanbanBoard agentId="agent-1" />);

    await userEvent.click(await screen.findByText("Maria Silva"));
  }

  it("clicar no card abre o porte e o que a triagem coletou", async () => {
    // O card mostrava nome, telefone e um número de 0 a 100 — e o número
    // sozinho não diz nada sobre o caso.
    await abrirCard();

    expect(await screen.findByText(/R\$\s?18\.000 a R\$\s?75\.000/)).toBeInTheDocument();
    expect(screen.getByText(/salário R\$ 2\.100/)).toBeInTheDocument();
    expect(screen.getByText("Pedir a carta de justa causa")).toBeInTheDocument();
  });

  it("o caso sem dimensionar não vira um valor inventado", async () => {
    await abrirCard({
      ...DOSSIE,
      casos: [
        {
          ...DOSSIE.casos[0],
          valor_estimado_min: null,
          valor_estimado_max: null,
          viabilidade: "indeterminado",
        },
      ],
    });

    expect(await screen.findByText(/Ainda não dimensionado/)).toBeInTheDocument();
  });

  it("oferece responder no WhatsApp e abrir o atendimento", async () => {
    await abrirCard();

    expect(await screen.findByRole("link", { name: /Responder no WhatsApp/ }))
      .toHaveAttribute("href", "https://wa.me/5561999990001");
    expect(screen.getByRole("link", { name: /Ver o atendimento/ }))
      .toHaveAttribute("href", "/dashboard/conversations?conversa=conv-1");
  });

  it("contato sem caso abre mesmo assim", async () => {
    // Lead que entrou no funil e nunca foi qualificado é o estado normal da
    // primeira coluna — a mais cheia do board.
    await abrirCard({ ...DOSSIE, casos: [], dados_economicos: null });

    expect(await screen.findByText(/ainda não tem caso arquivado/)).toBeInTheDocument();
  });

  it("o número do card é um link para o WhatsApp", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(BOARD));
    render(<KanbanBoard agentId="agent-1" />);

    const link = await screen.findByRole("link", { name: "+55 61 99999-0001" });
    expect(link).toHaveAttribute("href", "https://wa.me/5561999990001");
  });

  it("clicar no número não abre o dossiê junto", async () => {
    // O dossiê é uma tela inteira aparecendo por cima de um link que já foi
    // seguido — o clique no número tem que parar nele.
    mockFetch.mockResolvedValueOnce(jsonResponse(BOARD));
    render(<KanbanBoard agentId="agent-1" />);

    await userEvent.click(await screen.findByRole("link", { name: "+55 61 99999-0001" }));

    expect(screen.queryByText(/Porte estimado/)).not.toBeInTheDocument();
  });
});


describe("O card diz de que caso se trata", () => {
  /**
   * Nome e score obrigam a abrir card por card para descobrir o assunto — e
   * um funil real tem cento e cinquenta deles numa coluna só. Empresa, cargo
   * e porte resolvem a triagem no olho.
   */
  const CARD = {
    id: "lead-1",
    nome: "Tássio Sales",
    email: null,
    phone_number: "5561955555555",
    score_qualificacao: 85,
    status_funil: "qualificado",
    ordem: 0,
    dias_parado: 0,
    empresa: "Supermercado Tático",
    cargo: "Repositor",
    valor_estimado_min: 90000,
    valor_estimado_max: 280000,
    viabilidade: "acima_do_piso" as const,
  };

  it("mostra empresa, cargo e a faixa de valor", () => {
    render(<KanbanCardItem card={CARD} />);

    expect(screen.getByText("Supermercado Tático · Repositor")).toBeInTheDocument();
    // Sem centavos: a estimativa não tem essa precisão.
    expect(screen.getByText(/90\.000/)).toBeInTheDocument();
    expect(screen.getByText(/280\.000/)).toBeInTheDocument();
  });

  it("sem parecer ainda, o card aparece sem tarja de porte", () => {
    // O parecer roda dois minutos depois de o card nascer. Nesse intervalo,
    // "sem porte" é estado normal — não é caso sem valor.
    render(
      <KanbanCardItem
        card={{
          ...CARD,
          valor_estimado_min: null,
          valor_estimado_max: null,
          viabilidade: null,
        }}
      />,
    );

    expect(screen.getByText("Supermercado Tático · Repositor")).toBeInTheDocument();
    expect(screen.queryByText(/piso/)).not.toBeInTheDocument();
  });

  it("indeterminado não vira tarja", () => {
    // Tarja em todo card não informa nada.
    render(<KanbanCardItem card={{ ...CARD, viabilidade: "indeterminado" }} />);

    expect(screen.queryByText(/piso/)).not.toBeInTheDocument();
    expect(screen.queryByText(/90\.000/)).not.toBeInTheDocument();
  });

  it("caso recém-chegado não ganha selo de parado", () => {
    // Selo em todo card vira paisagem, e caso que entrou anteontem não está
    // parado — está sendo trabalhado.
    render(<KanbanCardItem card={{ ...CARD, dias_parado: 2 }} />);

    expect(screen.queryByText(/parado há/)).not.toBeInTheDocument();
  });

  it("a partir de três dias o selo aparece", () => {
    render(<KanbanCardItem card={{ ...CARD, dias_parado: 5 }} />);

    expect(screen.getByText("parado há 5d")).toBeInTheDocument();
  });

  it("o tom sobe quando passa de dez dias", () => {
    // A leitura útil é periférica: o operador varre a coluna e o vermelho
    // salta, sem ler número por número.
    const { rerender } = render(<KanbanCardItem card={{ ...CARD, dias_parado: 5 }} />);
    expect(screen.getByText("parado há 5d").className).toMatch(/amber/);

    rerender(<KanbanCardItem card={{ ...CARD, dias_parado: 14 }} />);
    expect(screen.getByText("parado há 14d").className).toMatch(/red/);
  });

  it("sem empresa nem cargo, não sobra linha vazia", () => {
    render(<KanbanCardItem card={{ ...CARD, empresa: null, cargo: null }} />);

    expect(screen.queryByText("·")).not.toBeInTheDocument();
    expect(screen.getByText("Tássio Sales")).toBeInTheDocument();
  });
});
