/**
 * A lista de contatos.
 *
 * O Kanban é bom para trabalhar o funil e péssimo para achar uma pessoa: a
 * primeira coluna do escritório tem 155 cards. O que estes casos travam é o
 * comportamento da busca — que digita a cada tecla, contra um banco — e a
 * paginação, que é onde uma lista costuma mentir.
 */

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ListaDeClientes } from "@/components/ListaDeClientes";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";
import type { ClienteNaLista } from "@/types";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}

function cliente(over: Partial<ClienteNaLista> = {}): ClienteNaLista {
  return {
    lead_id: "lead-1",
    nome: "Alexandre Santos",
    phone_number: "5564931207",
    email: null,
    empresa: "Nutrisa",
    cargo: "Auxiliar de produção",
    score_qualificacao: 72,
    etapa: "Closer",
    dias_parado: 0,
    data_criacao: "2026-08-10T10:00:00",
    conversation_id: "conv-1",
    ...over,
  };
}

function resposta(clientes: ClienteNaLista[], total = clientes.length) {
  return { agent_id: "ag-1", total, pagina: 1, por_pagina: 50, clientes };
}

beforeEach(() => {
  setStoredToken("token-abc");
  jest.useFakeTimers({ advanceTimers: true });
});
afterEach(() => {
  clearStoredTokens();
  jest.useRealTimers();
});

/** A lista espera 300ms antes de buscar; os testes pulam essa espera. */
async function passarODebounce() {
  await waitFor(() => expect(mockFetch).toHaveBeenCalled(), { timeout: 2000 });
}

describe("lista de contatos", () => {
  it("mostra o que identifica o caso sem obrigar a abrir", async () => {
    mockFetch.mockResolvedValue(jsonResponse(resposta([cliente()])));

    render(<ListaDeClientes agentId="ag-1" />);

    expect(await screen.findByText("Alexandre Santos")).toBeInTheDocument();
    expect(screen.getByText("Nutrisa · Auxiliar de produção")).toBeInTheDocument();
    // Dentro da tabela: "Closer" também é uma das opções do filtro de etapa,
    // e um `getByText` solto casaria com o `<option>`.
    expect(within(screen.getByRole("table")).getByText("Closer")).toBeInTheDocument();
  });

  it("contato sem nome não vira linha anônima", async () => {
    mockFetch.mockResolvedValue(jsonResponse([cliente({ nome: null })].length
      ? resposta([cliente({ nome: null })])
      : resposta([])));

    render(<ListaDeClientes agentId="ag-1" />);

    expect(await screen.findByText("Sem nome")).toBeInTheDocument();
  });

  it("uma letra não vira consulta ao banco", async () => {
    // Uma letra casa com metade da base e faz o banco varrer tudo para não
    // filtrar nada. O backend também a ignora — nem vale a viagem.
    mockFetch.mockResolvedValue(jsonResponse(resposta([cliente()])));

    render(<ListaDeClientes agentId="ag-1" />);
    await passarODebounce();
    mockFetch.mockClear();

    await userEvent.type(screen.getByLabelText("Buscar"), "a");
    await waitFor(() => expect(mockFetch).toHaveBeenCalled());

    const [url] = mockFetch.mock.calls[mockFetch.mock.calls.length - 1];
    expect(String(url)).not.toContain("busca=");
  });

  it("a partir de duas letras a busca vai para o servidor", async () => {
    mockFetch.mockResolvedValue(jsonResponse(resposta([cliente()])));

    render(<ListaDeClientes agentId="ag-1" />);
    await passarODebounce();
    mockFetch.mockClear();

    await userEvent.type(screen.getByLabelText("Buscar"), "alex");

    await waitFor(() => {
      const [url] = mockFetch.mock.calls[mockFetch.mock.calls.length - 1] ?? [""];
      expect(String(url)).toContain("busca=alex");
    });
  });

  it("digitar rápido não dispara uma consulta por tecla", async () => {
    // Sem espera, "Alexandre" viraria nove requisições, e as respostas
    // chegariam fora de ordem — a tela piscaria o resultado de "Alexand"
    // depois do de "Alexandre".
    mockFetch.mockResolvedValue(jsonResponse(resposta([cliente()])));

    render(<ListaDeClientes agentId="ag-1" />);
    await passarODebounce();
    mockFetch.mockClear();

    await userEvent.type(screen.getByLabelText("Buscar"), "alexandre");
    await waitFor(() => expect(mockFetch).toHaveBeenCalled());

    expect(mockFetch.mock.calls.length).toBeLessThan(4);
  });

  it("diz quantos achou, e é o total da busca", async () => {
    // 300 na base, 50 na página: mostrar o tamanho da página faria a lista
    // mentir e a paginação nunca oferecer a página 2.
    mockFetch.mockResolvedValue(
      jsonResponse({ ...resposta([cliente()]), total: 300, por_pagina: 50 }),
    );

    render(<ListaDeClientes agentId="ag-1" />);

    expect(await screen.findByText("300 contatos")).toBeInTheDocument();
  });

  it("oferece paginação quando passa de uma página", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ ...resposta([cliente()]), total: 120, por_pagina: 50 }),
    );

    render(<ListaDeClientes agentId="ag-1" />);

    expect(await screen.findByText("1 de 3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();
  });

  it("uma página só não ganha paginação", async () => {
    mockFetch.mockResolvedValue(jsonResponse(resposta([cliente()])));

    render(<ListaDeClientes agentId="ag-1" />);

    await screen.findByText("Alexandre Santos");
    expect(screen.queryByRole("button", { name: "Próxima" })).not.toBeInTheDocument();
  });

  it("buscar volta para a primeira página", async () => {
    // Ficar na página 3 depois de trocar a busca deixa a tela vazia: página 3
    // de um resultado que agora tem 4 linhas.
    mockFetch.mockResolvedValue(
      jsonResponse({ ...resposta([cliente()]), total: 200, por_pagina: 50 }),
    );

    render(<ListaDeClientes agentId="ag-1" />);
    await screen.findByText("1 de 4");

    await userEvent.click(screen.getByRole("button", { name: "Próxima" }));
    await screen.findByText("2 de 4");

    await userEvent.type(screen.getByLabelText("Buscar"), "alex");

    await waitFor(() => expect(screen.getByText("1 de 4")).toBeInTheDocument());
  });

  it("marca o contato parado há muito tempo", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(resposta([cliente({ dias_parado: 14 })])),
    );

    render(<ListaDeClientes agentId="ag-1" />);

    expect(await screen.findByText("14d")).toBeInTheDocument();
  });

  it("recém-chegado não ganha marca", async () => {
    mockFetch.mockResolvedValue(jsonResponse(resposta([cliente({ dias_parado: 1 })])));

    render(<ListaDeClientes agentId="ag-1" />);

    await screen.findByText("Alexandre Santos");
    expect(screen.queryByText("1d")).not.toBeInTheDocument();
  });

  it("busca sem resultado explica que foi a busca", async () => {
    mockFetch.mockResolvedValue(jsonResponse(resposta([])));

    render(<ListaDeClientes agentId="ag-1" />);
    await passarODebounce();

    await userEvent.type(screen.getByLabelText("Buscar"), "zzzz");

    expect(
      await screen.findByText("Nenhum contato com esses critérios."),
    ).toBeInTheDocument();
  });

  it("base vazia diz outra coisa — não é busca sem resultado", async () => {
    mockFetch.mockResolvedValue(jsonResponse(resposta([])));

    render(<ListaDeClientes agentId="ag-1" />);

    expect(await screen.findByText(/Nenhum contato ainda/)).toBeInTheDocument();
  });

  it("erro do servidor não vira lista vazia", async () => {
    // "Nenhum contato" quando o servidor caiu é uma mentira tranquilizadora.
    mockFetch.mockResolvedValue(jsonResponse({ detail: "Erro interno" }, 500));

    render(<ListaDeClientes agentId="ag-1" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Erro interno");
  });
});
