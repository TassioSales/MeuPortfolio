/**
 * A tela de custo de aquisição.
 *
 * Era o número que faltava no painel: havia volume e conversão, e nenhum
 * custo — então "vale a pena?" só tinha resposta no chute.
 *
 * O caso que mais importa aqui é a vírgula: o teclado brasileiro manda
 * "250,50", e `Number("250,50")` é `NaN`. Sem tratar, o escritório digita o
 * valor certo e leva um 422 sem explicação.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Marketing } from "@/components/Marketing";
import { useAuthStore } from "@/hooks/useAuth";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";
import type { LancamentoMarketing, Papel, ResumoMarketing, User } from "@/types";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}

function resumo(over: Partial<ResumoMarketing> = {}): ResumoMarketing {
  return {
    agent_id: "ag-1",
    dias: 30,
    investimento_ads: 300,
    tokens_consumidos: 125000,
    leads: 3,
    leads_qualificados: 2,
    custo_por_lead: 100,
    custo_por_lead_qualificado: 150,
    ...over,
  };
}

function lancamento(over: Partial<LancamentoMarketing> = {}): LancamentoMarketing {
  return {
    id: "lc-1",
    data: "2026-08-15",
    investimento_ads: 250.5,
    observacao: "Meta Ads",
    criado_por: "Tássio",
    ...over,
  };
}

/** A tela pede resumo e lançamentos em paralelo. */
function respondeCom(r: ResumoMarketing, ls: LancamentoMarketing[]) {
  mockFetch.mockImplementation((url: string) =>
    Promise.resolve(
      String(url).includes("/resumo") ? jsonResponse(r) : jsonResponse(ls),
    ),
  );
}

function entrarComo(papel: Papel) {
  const user: User = {
    id: "u1", email: "x@example.com", nome: "Tássio", status: "ativo", papel,
    data_criacao: "2026-01-01T00:00:00",
  };
  useAuthStore.setState({ user, isLoading: false, error: null });
}

beforeEach(() => setStoredToken("token-abc"));
afterEach(() => {
  clearStoredTokens();
  useAuthStore.setState({ user: null, isLoading: true, error: null });
});

describe("custo de aquisição", () => {
  it("mostra o custo por lead e o por lead qualificado", async () => {
    entrarComo("admin");
    respondeCom(resumo(), [lancamento()]);

    render(<Marketing agentId="ag-1" />);

    expect(await screen.findByText("Custo por lead")).toBeInTheDocument();
    // Os três valores são distintos de propósito: com "investido" e "custo
    // por qualificado" iguais, um deles poderia sumir da tela sem o teste
    // reparar.
    expect(screen.getByText("R$ 300,00")).toBeInTheDocument();
    expect(screen.getByText("R$ 100,00")).toBeInTheDocument();
    expect(screen.getByText("R$ 150,00")).toBeInTheDocument();
  });

  it("sem lead nenhum, o custo é traço e não infinito", async () => {
    entrarComo("admin");
    respondeCom(
      resumo({ leads: 0, leads_qualificados: 0, custo_por_lead: null, custo_por_lead_qualificado: null }),
      [],
    );

    render(<Marketing agentId="ag-1" />);

    await screen.findByText("Custo por lead");
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(2);
  });

  it("diz que o consumo de IA vem do banco, não da digitação", async () => {
    entrarComo("admin");
    respondeCom(resumo(), []);

    render(<Marketing agentId="ag-1" />);

    expect(await screen.findByText("somado do banco, não digitado")).toBeInTheDocument();
  });

  it("aceita a vírgula do teclado brasileiro", async () => {
    // `Number("250,50")` é NaN. Sem tratar, quem digita o valor certo leva um
    // 422 sem explicação.
    entrarComo("admin");
    respondeCom(resumo(), []);

    render(<Marketing agentId="ag-1" />);
    await screen.findByLabelText("Valor (R$)");

    await userEvent.type(screen.getByLabelText("Valor (R$)"), "250,50");
    await userEvent.click(screen.getByRole("button", { name: "Lançar" }));

    await waitFor(() => {
      const post = mockFetch.mock.calls.find(([, init]) => init?.method === "POST");
      expect(post).toBeDefined();
      expect(JSON.parse(post![1].body).investimento_ads).toBe(250.5);
    });
  });

  it("valor inválido não vai ao servidor", async () => {
    entrarComo("admin");
    respondeCom(resumo(), []);

    render(<Marketing agentId="ag-1" />);
    await screen.findByLabelText("Valor (R$)");
    mockFetch.mockClear();

    await userEvent.type(screen.getByLabelText("Valor (R$)"), "abc");
    await userEvent.click(screen.getByRole("button", { name: "Lançar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("valor válido");
    expect(mockFetch.mock.calls.some(([, init]) => init?.method === "POST")).toBe(false);
  });

  it("o operador vê os números e não lança dinheiro", async () => {
    entrarComo("operador");
    respondeCom(resumo(), [lancamento()]);

    render(<Marketing agentId="ag-1" />);

    expect(await screen.findByText("Custo por lead")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Lançar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apagar" })).not.toBeInTheDocument();
  });

  it("sem lançamento, diz por que a conta não sai", async () => {
    entrarComo("admin");
    respondeCom(resumo(), []);

    render(<Marketing agentId="ag-1" />);

    expect(await screen.findByText(/não tem como ser\s+calculado/)).toBeInTheDocument();
  });

  it("erro do servidor aparece", async () => {
    entrarComo("admin");
    mockFetch.mockResolvedValue(jsonResponse({ detail: "Erro interno" }, 500));

    render(<Marketing agentId="ag-1" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Erro interno");
  });
});
