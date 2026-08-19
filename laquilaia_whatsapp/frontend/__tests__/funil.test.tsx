/**
 * O funil de venda no painel.
 *
 * O número que trabalha aqui não é o percentual do topo — é a conversão da
 * etapa. "20% chegaram à Viabilidade" não diz se a perda foi na Entrevista ou
 * na Coleta.
 *
 * E o caso que mais importa: amostra pequena. Três leads viram "33% de
 * conversão" no primeiro descarte e "0%" no segundo. O número é verdadeiro e
 * informa uma coisa falsa; um painel que mostra números sem significado
 * treina quem lê a ignorá-los.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FunilDeVenda } from "@/components/FunilDeVenda";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";
import type { EtapaDoFunil } from "@/types";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}

function etapa(nome: string, over: Partial<EtapaDoFunil> = {}): EtapaDoFunil {
  return {
    nome,
    ordem: 0,
    parados_aqui: 0,
    chegaram: 0,
    percentual_do_topo: 0,
    conversao_da_etapa: 0,
    com_intervencao_humana: 0,
    ...over,
  };
}

/** Um funil com base suficiente para os percentuais aparecerem. */
function funilCheio() {
  return {
    agent_id: "ag-1",
    dias: null,
    total_de_leads: 60,
    arquivados: 10,
    etapas: [
      etapa("Closer", { chegaram: 50, parados_aqui: 40, percentual_do_topo: 100, conversao_da_etapa: 100 }),
      etapa("Entrevista", { chegaram: 10, parados_aqui: 6, percentual_do_topo: 20, conversao_da_etapa: 20 }),
      etapa("Viabilidade", { chegaram: 4, parados_aqui: 3, percentual_do_topo: 8, conversao_da_etapa: 40, com_intervencao_humana: 2 }),
      etapa("Revisão", { chegaram: 1, parados_aqui: 1, percentual_do_topo: 2, conversao_da_etapa: 25 }),
    ],
  };
}

beforeEach(() => setStoredToken("token-abc"));
afterEach(() => clearStoredTokens());

describe("funil de venda", () => {
  it("mostra quantos chegaram a cada etapa e a forma do funil", async () => {
    mockFetch.mockResolvedValue(jsonResponse(funilCheio()));

    render(<FunilDeVenda agentId="ag-1" />);

    expect(await screen.findByText("Closer")).toBeInTheDocument();
    expect(screen.getByText("50")).toBeInTheDocument();
    // "100%" aparece duas vezes no primeiro card, e é correto: o topo é 100%
    // do topo e converte 100% de si mesmo.
    expect(screen.getAllByText("100%").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("20%").length).toBeGreaterThanOrEqual(1);
  });

  it("aponta a etapa onde o funil aperta", async () => {
    // 20% na Entrevista é a menor conversão do exemplo. Destacar todas é não
    // destacar nenhuma.
    mockFetch.mockResolvedValue(jsonResponse(funilCheio()));

    render(<FunilDeVenda agentId="ag-1" />);

    const aviso = await screen.findByText(/O funil aperta em/);
    expect(aviso).toHaveTextContent("Entrevista");
    expect(aviso).toHaveTextContent("20 passam");
  });

  it("conta os arquivados à parte", async () => {
    // Fora da cadeia: quem foi arquivado no primeiro contato não avançou.
    // Somá-los ao funil inverteria o sinal — descarte lido como sucesso.
    mockFetch.mockResolvedValue(jsonResponse(funilCheio()));

    render(<FunilDeVenda agentId="ag-1" />);

    expect(await screen.findByText("60 leads, 10 arquivados")).toBeInTheDocument();
    expect(screen.queryByText("Arquivado")).not.toBeInTheDocument();
  });

  it("com amostra pequena, esconde a conversão e explica por quê", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({
        agent_id: "ag-1",
        dias: null,
        total_de_leads: 3,
        arquivados: 0,
        etapas: [
          etapa("Closer", { chegaram: 3, parados_aqui: 2, percentual_do_topo: 100, conversao_da_etapa: 100 }),
          etapa("Entrevista", { chegaram: 1, parados_aqui: 1, percentual_do_topo: 33.3, conversao_da_etapa: 33.3 }),
        ],
      }),
    );

    render(<FunilDeVenda agentId="ag-1" />);

    expect(await screen.findByText(/não significa nada/)).toBeInTheDocument();
    expect(screen.queryByText(/O funil aperta em/)).not.toBeInTheDocument();

    // A conversão vira traço. O percentual do topo fica: "1 de 3" é uma
    // proporção que se lê direto, não uma taxa que finge estabilidade.
    const conversoes = screen.getAllByText("Conversão da etapa");
    for (const rotulo of conversoes) {
      expect(rotulo.parentElement).toHaveTextContent("—");
    }
  });

  it("funil vazio não vira tela de erro", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ agent_id: "ag-1", dias: null, total_de_leads: 0, arquivados: 0, etapas: [] }),
    );

    render(<FunilDeVenda agentId="ag-1" />);

    expect(await screen.findByText(/Nenhum lead no período/)).toBeInTheDocument();
  });

  it("trocar o período refaz a consulta com o filtro", async () => {
    mockFetch.mockResolvedValue(jsonResponse(funilCheio()));

    render(<FunilDeVenda agentId="ag-1" />);
    await screen.findByText("Closer");

    await userEvent.click(screen.getByRole("button", { name: "30 dias" }));

    await waitFor(() => {
      const [url] = mockFetch.mock.calls[mockFetch.mock.calls.length - 1];
      expect(String(url)).toContain("dias=30");
    });
  });

  it("desde sempre não manda filtro nenhum", async () => {
    // É o padrão: um escritório com poucos leads por semana não tem funil em
    // sete dias, e abrir em "0 de 0" parece defeito.
    mockFetch.mockResolvedValue(jsonResponse(funilCheio()));

    render(<FunilDeVenda agentId="ag-1" />);

    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    expect(String(mockFetch.mock.calls[0][0])).not.toContain("dias=");
  });

  it("erro do servidor não vira funil vazio", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "Erro interno" }, 500));

    render(<FunilDeVenda agentId="ag-1" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Erro interno");
  });
});
