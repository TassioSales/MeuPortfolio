/**
 * A tela de histórico.
 *
 * O que ela precisa acertar é a distinção entre o que a IA fez e o que gente
 * fez. Sem isso a lista é um log de sistema; com isso é a resposta para "quem
 * mandou esse caso para o arquivo?".
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Historico } from "@/components/Historico";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";
import type { Movimento } from "@/types";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}

function movimento(over: Partial<Movimento> = {}): Movimento {
  return {
    id: "mv-1",
    lead_id: "lead-1",
    lead_nome: "Marina",
    phone_number: "5561999887766",
    status_anterior: "novo",
    status_novo: "qualificado",
    motivo: "Movido para Viabilidade no painel",
    responsavel: "Tássio",
    quando: "2026-08-19T14:30:00",
    ...over,
  };
}

function resposta(movimentos: Movimento[], total = movimentos.length) {
  return { agent_id: "ag-1", total, pagina: 1, por_pagina: 50, movimentos };
}

beforeEach(() => setStoredToken("token-abc"));
afterEach(() => clearStoredTokens());

describe("histórico", () => {
  it("mostra o que aconteceu e por ordem de quem", async () => {
    mockFetch.mockResolvedValue(jsonResponse(resposta([movimento()])));

    render(<Historico agentId="ag-1" />);

    expect(await screen.findByText("Marina")).toBeInTheDocument();
    expect(screen.getByText("Movido para Viabilidade no painel")).toBeInTheDocument();
    expect(screen.getByText("Tássio")).toBeInTheDocument();
  });

  it("movimento da IA é marcado como IA, não como lacuna", async () => {
    // A ausência de nome é informação. Deixar a célula vazia faria parecer
    // dado faltando, e alguém iria procurar de quem foi.
    mockFetch.mockResolvedValue(
      jsonResponse(resposta([movimento({ responsavel: null })])),
    );

    render(<Historico agentId="ag-1" />);

    expect(await screen.findByText("IA")).toBeInTheDocument();
  });

  it("sem motivo, mostra a transição crua em vez de nada", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(resposta([movimento({ motivo: null })])),
    );

    render(<Historico agentId="ag-1" />);

    expect(await screen.findByText("novo → qualificado")).toBeInTheDocument();
  });

  it("o filtro de ações humanas vai para o servidor", async () => {
    mockFetch.mockResolvedValue(jsonResponse(resposta([movimento()])));

    render(<Historico agentId="ag-1" />);
    await screen.findByText("Marina");

    await userEvent.click(screen.getByLabelText("Só o que gente fez"));

    await waitFor(() => {
      const [url] = mockFetch.mock.calls[mockFetch.mock.calls.length - 1];
      expect(String(url)).toContain("apenas_humanos=true");
    });
  });

  it("vazio com filtro explica que foi o filtro", async () => {
    mockFetch.mockResolvedValue(jsonResponse(resposta([])));

    render(<Historico agentId="ag-1" />);
    await screen.findByText("Nada aconteceu no período.");

    await userEvent.click(screen.getByLabelText("Só o que gente fez"));

    expect(
      await screen.findByText("Ninguém do escritório mexeu em lead nenhum no período."),
    ).toBeInTheDocument();
  });

  it("trocar o período refaz a consulta", async () => {
    mockFetch.mockResolvedValue(jsonResponse(resposta([movimento()])));

    render(<Historico agentId="ag-1" />);
    await screen.findByText("Marina");

    await userEvent.click(screen.getByRole("button", { name: "90 dias" }));

    await waitFor(() => {
      const [url] = mockFetch.mock.calls[mockFetch.mock.calls.length - 1];
      expect(String(url)).toContain("dias=90");
    });
  });

  it("erro do servidor não vira histórico vazio", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "Erro interno" }, 500));

    render(<Historico agentId="ag-1" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Erro interno");
  });
});
