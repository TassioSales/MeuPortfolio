/**
 * A tela de casos finalizados.
 *
 * Tudo caía em "Arquivado" e o board não dizia por quê. Mas "não era da nossa
 * área" e "o caso é pequeno demais" pedem coisas opostas do escritório — o
 * primeiro é volume de marketing errado, o segundo é o piso comercial
 * funcionando. Estes casos travam essa separação e o texto que diz, em cada
 * coluna, o que fazer com ela.
 */

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Finalizados } from "@/components/Finalizados";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";
import type { CasoFinalizado, GrupoFinalizado, MotivoDeFim } from "@/types";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}

function caso(over: Partial<CasoFinalizado> = {}): CasoFinalizado {
  return {
    lead_id: "lead-1",
    nome: "Marina",
    phone_number: "5561999887766",
    empresa_ou_resumo: "Justa causa por abandono",
    valor_estimado_min: 2000,
    valor_estimado_max: 9000,
    arquivado_em: "2026-08-10T10:00:00",
    arquivado_por: null,
    ...over,
  };
}

const ROTULOS: Record<MotivoDeFim, string> = {
  abaixo_do_piso: "Abaixo do piso",
  fora_da_area: "Fora da área",
  sem_retorno: "Sem retorno",
  outro: "Outro",
};

function resposta(porMotivo: Partial<Record<MotivoDeFim, CasoFinalizado[]>>) {
  const grupos: GrupoFinalizado[] = (
    ["abaixo_do_piso", "fora_da_area", "sem_retorno", "outro"] as MotivoDeFim[]
  ).map((motivo) => ({
    motivo,
    rotulo: ROTULOS[motivo],
    total: (porMotivo[motivo] ?? []).length,
    casos: porMotivo[motivo] ?? [],
  }));

  return {
    agent_id: "ag-1",
    dias: 90,
    total: grupos.reduce((soma, g) => soma + g.total, 0),
    grupos,
  };
}

beforeEach(() => setStoredToken("token-abc"));
afterEach(() => clearStoredTokens());

describe("casos finalizados", () => {
  it("separa o caso pequeno do caso de outra área", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(
        resposta({
          abaixo_do_piso: [caso({ lead_id: "l1", nome: "Pequeno" })],
          fora_da_area: [caso({ lead_id: "l2", nome: "De família" })],
        }),
      ),
    );

    render(<Finalizados agentId="ag-1" />);

    const piso = (await screen.findByText("Abaixo do piso")).closest("section")!;
    const area = screen.getByText("Fora da área").closest("section")!;

    expect(within(piso).getByText("Pequeno")).toBeInTheDocument();
    expect(within(area).getByText("De família")).toBeInTheDocument();
  });

  it("cada coluna diz o que fazer com ela", async () => {
    // Uma coluna cujo nome não diz o que fazer com ela vira só um lugar onde
    // caso morre.
    mockFetch.mockResolvedValue(jsonResponse(resposta({})));

    render(<Finalizados agentId="ag-1" />);

    expect(await screen.findByText(/piso comercial funcionando/)).toBeInTheDocument();
    expect(screen.getByText(/anúncio errado/)).toBeInTheDocument();
    expect(screen.getByText(/é aqui que se perde quem tinha caso/i)).toBeInTheDocument();
  });

  it("as colunas aparecem mesmo vazias", async () => {
    // Board sem colunas parece defeito, e o escritório precisa ver que
    // "abaixo do piso" existe como destino antes de haver um caso lá.
    mockFetch.mockResolvedValue(jsonResponse(resposta({})));

    render(<Finalizados agentId="ag-1" />);

    expect(await screen.findByText("Abaixo do piso")).toBeInTheDocument();
    expect(screen.getAllByText("Nenhum caso aqui")).toHaveLength(4);
  });

  it("mostra a faixa estimada sem centavos", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(resposta({ abaixo_do_piso: [caso()] })),
    );

    render(<Finalizados agentId="ag-1" />);

    expect(await screen.findByText(/2\.000.*9\.000/)).toBeInTheDocument();
  });

  it("só diz quem arquivou quando foi gente", async () => {
    // "Arquivado pela triagem" em todo card seria repetir o óbvio em 90%
    // deles.
    mockFetch.mockResolvedValue(
      jsonResponse(
        resposta({
          abaixo_do_piso: [caso({ lead_id: "l1", arquivado_por: "Tássio" })],
          sem_retorno: [caso({ lead_id: "l2", nome: "Sumiu", arquivado_por: null })],
        }),
      ),
    );

    render(<Finalizados agentId="ag-1" />);

    expect(await screen.findByText("arquivado por Tássio")).toBeInTheDocument();
    expect(screen.getAllByText(/arquivado por/)).toHaveLength(1);
  });

  it("trocar o período refaz a consulta", async () => {
    mockFetch.mockResolvedValue(jsonResponse(resposta({})));

    render(<Finalizados agentId="ag-1" />);
    await screen.findByText("Abaixo do piso");

    await userEvent.click(screen.getByRole("button", { name: "1 ano" }));

    await waitFor(() => {
      const [url] = mockFetch.mock.calls[mockFetch.mock.calls.length - 1];
      expect(String(url)).toContain("dias=365");
    });
  });

  it("erro do servidor não vira board vazio", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "Erro interno" }, 500));

    render(<Finalizados agentId="ag-1" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Erro interno");
  });
});
