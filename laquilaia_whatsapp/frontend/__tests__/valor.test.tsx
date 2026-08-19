/**
 * As abas de Valor e Produtividade.
 *
 * As métricas contavam gente. Um escritório vive do tamanho das causas — dois
 * meses com o mesmo número de leads podem valer dez vezes um ao outro.
 *
 * O caso que mais importa na aba de Valor é o do **caso sem estimativa**: ele
 * não pode sumir da tela, senão o total parece o total quando não é.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PainelDeProdutividade } from "@/components/PainelDeProdutividade";
import { PainelDeValor } from "@/components/PainelDeValor";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";
import type { ProdutividadeResponse, ValorResponse } from "@/types";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}

function valor(over: Partial<ValorResponse> = {}): ValorResponse {
  return {
    agent_id: "ag-1",
    dias: 30,
    casos_dimensionados: 3,
    casos_sem_valor: 0,
    total_min: 30000,
    total_max: 120000,
    por_dia: [
      { data: "2026-08-17", casos: 1, total_min: 10000, total_max: 40000 },
      { data: "2026-08-18", casos: 2, total_min: 20000, total_max: 80000 },
    ],
    por_porte: [
      { porte: "alto", rotulo: "Acima de R$ 75.000", casos: 1, total_min: 20000, total_max: 80000 },
      { porte: "medio", rotulo: "R$ 15.000 a R$ 75.000", casos: 2, total_min: 10000, total_max: 40000 },
      { porte: "baixo", rotulo: "Abaixo de R$ 15.000", casos: 0, total_min: 0, total_max: 0 },
      { porte: "indeterminado", rotulo: "Sem estimativa", casos: 0, total_min: 0, total_max: 0 },
    ],
    por_uf: [
      { uf: "DF", leads: 2, casos_dimensionados: 2, total_max: 90000 },
      { uf: "SP", leads: 1, casos_dimensionados: 1, total_max: 30000 },
    ],
    ...over,
  };
}

function produtividade(over: Partial<ProdutividadeResponse> = {}): ProdutividadeResponse {
  return {
    agent_id: "ag-1",
    dias: 30,
    acoes_de_gente: 4,
    acoes_da_ia: 16,
    percentual_humano: 20,
    pessoas: [
      {
        nome: "Tássio",
        acoes: 4,
        conversas_assumidas: 1,
        conversas_devolvidas: 1,
        cards_movidos: 2,
        leads_atendidos: 3,
      },
    ],
    ...over,
  };
}

beforeEach(() => setStoredToken("token-abc"));
afterEach(() => clearStoredTokens());

describe("aba Valor", () => {
  it("mostra a faixa somada, e não uma média", async () => {
    // O parecer estima faixa porque não tem documento; achatar isso inventa
    // uma precisão que a estimativa não tem.
    mockFetch.mockResolvedValue(jsonResponse(valor()));

    render(<PainelDeValor agentId="ag-1" />);

    expect(await screen.findByText(/R\$ 30\.000\s*–\s*R\$ 120\.000/)).toBeInTheDocument();
  });

  it("o caso sem estimativa aparece, fora da soma", async () => {
    // Somar zero e sumir faz o total mentir para menos, e ninguém percebe
    // porque o número continua plausível.
    mockFetch.mockResolvedValue(jsonResponse(valor({ casos_sem_valor: 2 })));

    render(<PainelDeValor agentId="ag-1" />);

    expect(await screen.findByText(/2 sem estimativa, fora da soma/)).toBeInTheDocument();
  });

  it("separa por porte em vez de dar uma média", async () => {
    mockFetch.mockResolvedValue(jsonResponse(valor()));

    render(<PainelDeValor agentId="ag-1" />);

    expect(await screen.findByText("Acima de R$ 75.000")).toBeInTheDocument();
    expect(screen.getByText("Abaixo de R$ 15.000")).toBeInTheDocument();
    expect(screen.getByText(/a média esconde/i)).toBeInTheDocument();
  });

  it("mostra de onde vêm os casos", async () => {
    mockFetch.mockResolvedValue(jsonResponse(valor()));

    render(<PainelDeValor agentId="ag-1" />);

    expect(await screen.findByText("DF")).toBeInTheDocument();
    expect(screen.getByText("SP")).toBeInTheDocument();
  });

  it("telefone ilegível vira rótulo, não some", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(valor({ por_uf: [{ uf: "??", leads: 1, casos_dimensionados: 0, total_max: 0 }] })),
    );

    render(<PainelDeValor agentId="ag-1" />);

    expect(await screen.findByText("Não identificado")).toBeInTheDocument();
  });

  it("avisa que o estado vem do DDD e não é endereço", async () => {
    // Alguém vai querer usar isso para petição. A tela precisa dizer que não.
    mockFetch.mockResolvedValue(jsonResponse(valor()));

    render(<PainelDeValor agentId="ag-1" />);

    expect(await screen.findByText(/não para endereço processual/)).toBeInTheDocument();
  });

  it("período vazio não vira erro", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(valor({ casos_dimensionados: 0, total_min: 0, total_max: 0, por_dia: [], por_uf: [] })),
    );

    render(<PainelDeValor agentId="ag-1" />);

    expect(await screen.findByText("Nenhum caso dimensionado no período.")).toBeInTheDocument();
  });

  it("erro do servidor aparece", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "Erro interno" }, 500));

    render(<PainelDeValor agentId="ag-1" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Erro interno");
  });
});

describe("aba Produtividade", () => {
  it("mostra a razão entre o que a IA resolveu e o que gente fez", async () => {
    mockFetch.mockResolvedValue(jsonResponse(produtividade()));

    render(<PainelDeProdutividade agentId="ag-1" />);

    expect(await screen.findByText("16")).toBeInTheDocument();
    expect(screen.getByText("20%")).toBeInTheDocument();
  });

  it("avisa quando o funil está andando por gente", async () => {
    // Um agente que resolve menos da metade não está atendendo — está
    // gerando trabalho.
    mockFetch.mockResolvedValue(jsonResponse(produtividade({ percentual_humano: 70 })));

    render(<PainelDeProdutividade agentId="ag-1" />);

    expect(
      await screen.findByText("Mais da metade do funil está andando por gente."),
    ).toBeInTheDocument();
  });

  it("com pouca intervenção, não alarma", async () => {
    mockFetch.mockResolvedValue(jsonResponse(produtividade({ percentual_humano: 12 })));

    render(<PainelDeProdutividade agentId="ag-1" />);

    await screen.findByText("12%");
    expect(screen.queryByText(/Mais da metade/)).not.toBeInTheDocument();
  });

  it("mostra contatos ao lado de ações", async () => {
    // Quinze ações num lead só não é o mesmo trabalho que uma em quinze.
    mockFetch.mockResolvedValue(jsonResponse(produtividade()));

    render(<PainelDeProdutividade agentId="ag-1" />);

    expect(await screen.findByText("Tássio")).toBeInTheDocument();
    expect(screen.getByText("Contatos")).toBeInTheDocument();
  });

  it("ninguém agiu não é o mesmo que erro", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(produtividade({ pessoas: [], acoes_de_gente: 0, percentual_humano: 0 })),
    );

    render(<PainelDeProdutividade agentId="ag-1" />);

    expect(
      await screen.findByText("Ninguém do escritório mexeu em lead nenhum no período."),
    ).toBeInTheDocument();
  });

  it("trocar o período refaz a consulta", async () => {
    mockFetch.mockResolvedValue(jsonResponse(produtividade()));

    render(<PainelDeProdutividade agentId="ag-1" />);
    await screen.findByText("Tássio");

    await userEvent.click(screen.getByRole("button", { name: "7 dias" }));

    await waitFor(() => {
      const [url] = mockFetch.mock.calls[mockFetch.mock.calls.length - 1];
      expect(String(url)).toContain("dias=7");
    });
  });
});
