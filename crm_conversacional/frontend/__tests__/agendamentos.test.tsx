/**
 * A agenda de retornos.
 *
 * "Te ligo amanhã às 15h" era dito na conversa e morria ali. O grupo que
 * justifica a tela é o **atrasado** — retorno cuja hora passou e ninguém
 * fechou; a mesma omissão que a faixa de pendências trata nas conversas.
 *
 * O caso do fuso é o mais fácil de errar e o mais difícil de notar: um
 * retorno marcado para as 15h aparecendo às 18h só se percebe depois de o
 * cliente ficar esperando.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Agendamentos } from "@/components/Agendamentos";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";
import type { Agendamento } from "@/types";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}

function agendamento(over: Partial<Agendamento> = {}): Agendamento {
  return {
    id: "ag-1",
    lead_id: "lead-1",
    lead_nome: "Andreia",
    phone_number: "5561999887766",
    quando: "2026-08-19T18:00:00",
    motivo: "Coletar documentos",
    status: "pendente",
    criado_por: "Tássio",
    minutos_de_atraso: 0,
    ...over,
  };
}

beforeEach(() => setStoredToken("token-abc"));
afterEach(() => clearStoredTokens());

describe("agenda de retornos", () => {
  it("mostra com quem, quando e por quê", async () => {
    mockFetch.mockResolvedValue(jsonResponse([agendamento()]));

    render(<Agendamentos agentId="ag-1" />);

    expect(await screen.findByText("Andreia")).toBeInTheDocument();
    expect(screen.getByText(/Coletar documentos/)).toBeInTheDocument();
    expect(screen.getByText(/marcado por Tássio/)).toBeInTheDocument();
  });

  it("destaca o que passou da hora", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse([agendamento({ minutos_de_atraso: 150 })]),
    );

    render(<Agendamentos agentId="ag-1" />);

    expect(await screen.findByText("atrasado 2h")).toBeInTheDocument();
    expect(screen.getByText("1 retorno atrasado")).toBeInTheDocument();
  });

  it("sem atraso, não inventa alarme", async () => {
    mockFetch.mockResolvedValue(jsonResponse([agendamento()]));

    render(<Agendamentos agentId="ag-1" />);

    await screen.findByText("Andreia");
    expect(screen.queryByText(/atrasado/)).not.toBeInTheDocument();
  });

  it("concluir manda a mudança e recarrega", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse([agendamento()]))
      .mockResolvedValueOnce(jsonResponse(agendamento({ status: "realizado" })))
      .mockResolvedValueOnce(jsonResponse([]));

    render(<Agendamentos agentId="ag-1" />);

    await userEvent.click(await screen.findByRole("button", { name: "Concluir" }));

    await waitFor(() => {
      const patch = mockFetch.mock.calls.find(([, init]) => init?.method === "PATCH");
      expect(patch).toBeDefined();
      expect(JSON.parse(patch![1].body).status).toBe("realizado");
    });
  });

  it("marcar converte a hora local para UTC", async () => {
    // O `datetime-local` dá hora sem fuso e o backend guarda em UTC. Sem a
    // conversão, um retorno marcado para as 15h apareceria às 18h para quem
    // está em UTC-3 — e só se descobre depois de o cliente ficar esperando.
    mockFetch
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(agendamento()))
      .mockResolvedValueOnce(jsonResponse([agendamento()]));

    render(<Agendamentos agentId="ag-1" leadId="lead-1" nomeDoLead="Andreia" />);

    await userEvent.type(await screen.findByLabelText("Quando"), "2026-08-20T15:00");
    await userEvent.click(screen.getByRole("button", { name: "Marcar" }));

    await waitFor(() => {
      const post = mockFetch.mock.calls.find(([, init]) => init?.method === "POST");
      expect(post).toBeDefined();
      const enviado = JSON.parse(post![1].body).quando;
      expect(enviado).toBe(new Date("2026-08-20T15:00").toISOString());
    });
  });

  it("o formulário de marcar só aparece com um contato escolhido", async () => {
    // Na agenda geral não há para quem marcar; oferecer o formulário seria
    // pedir um dado que a tela não tem.
    mockFetch.mockResolvedValue(jsonResponse([agendamento()]));

    render(<Agendamentos agentId="ag-1" />);

    await screen.findByText("Andreia");
    expect(screen.queryByRole("button", { name: "Marcar" })).not.toBeInTheDocument();
  });

  it("duplicata do servidor aparece como o que é", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(
        jsonResponse({ detail: "Já existe um retorno marcado para este contato nesse horário." }, 409),
      );

    render(<Agendamentos agentId="ag-1" leadId="lead-1" />);

    await userEvent.type(await screen.findByLabelText("Quando"), "2026-08-20T15:00");
    await userEvent.click(screen.getByRole("button", { name: "Marcar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Já existe um retorno marcado");
  });

  it("agenda vazia diz que está vazia", async () => {
    mockFetch.mockResolvedValue(jsonResponse([]));

    render(<Agendamentos agentId="ag-1" />);

    expect(await screen.findByText("Nenhum retorno combinado.")).toBeInTheDocument();
  });

  it("erro do servidor não vira agenda vazia", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "Erro interno" }, 500));

    render(<Agendamentos agentId="ag-1" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Erro interno");
  });
});
