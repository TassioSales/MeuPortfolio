/**
 * A faixa de quem está esperando resposta.
 *
 * O que ela precisa acertar não é o desenho, é **quando aparecer**: some
 * quando não há ninguém esperando (faixa permanente de "0 pendências" vira
 * paisagem), e some também quando a própria checagem falha — falhar em
 * checar pendência não é uma pendência, e alarme falso gasta a credibilidade
 * dos alarmes verdadeiros.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ClientesEsperando } from "@/components/ClientesEsperando";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";
import type { ClienteEsperando } from "@/types";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}

function esperando(over: Partial<ClienteEsperando> = {}): ClienteEsperando {
  return {
    tipo: "ia_sem_resposta",
    conversation_id: "conv-1",
    phone_number: "5561999990000",
    lead_nome: "Marina",
    ultima_mensagem: "e aí, tem novidade?",
    desde: "2026-08-19T01:00:00",
    minutos_esperando: 95,
    ...over,
  };
}

function resposta(conversas: ClienteEsperando[]) {
  const total_ia = conversas.filter((c) => c.tipo === "ia_sem_resposta").length;
  return {
    agent_id: "ag-1",
    minutos: 30,
    total_ia,
    total_humano: conversas.length - total_ia,
    conversas,
  };
}

beforeEach(() => setStoredToken("token-abc"));
afterEach(() => clearStoredTokens());

describe("faixa de clientes esperando", () => {
  it("não aparece quando ninguém está esperando", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(resposta([])));

    const { container } = render(<ClientesEsperando agentId="ag-1" />);

    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("não aparece quando a checagem falha", async () => {
    // Uma faixa vermelha dizendo "não consegui checar" ensina o operador a
    // ignorar faixa vermelha.
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "erro" }, 500));

    const { container } = render(<ClientesEsperando agentId="ag-1" />);

    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("mostra quem espera, o que disse e há quanto tempo", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(resposta([esperando()])));

    render(<ClientesEsperando agentId="ag-1" />);

    expect(await screen.findByText("Marina")).toBeInTheDocument();
    expect(screen.getByText("e aí, tem novidade?")).toBeInTheDocument();
    // 95 minutos vira "1h": minutos crus acima de uma hora não se leem.
    expect(screen.getByText("há 1h")).toBeInTheDocument();
  });

  it("separa a dívida da IA da dívida do humano", async () => {
    // São problemas de donos diferentes: um é o sistema fora do ar, o outro
    // é gente ocupada. Juntar num número só apagaria essa diferença.
    mockFetch.mockResolvedValueOnce(
      jsonResponse(
        resposta([
          esperando({ conversation_id: "c1", tipo: "ia_sem_resposta" }),
          esperando({ conversation_id: "c2", tipo: "humano_sem_resposta" }),
        ]),
      ),
    );

    render(<ClientesEsperando agentId="ag-1" />);

    expect(await screen.findByText("2 clientes esperando resposta")).toBeInTheDocument();
    expect(screen.getByText(/1 sem resposta da IA/)).toBeInTheDocument();
    expect(screen.getByText(/1 com humano que assumiu/)).toBeInTheDocument();
    expect(screen.getByText("IA parada")).toBeInTheDocument();
    expect(screen.getByText("humano assumiu")).toBeInTheDocument();
  });

  it("sem nome, mostra o telefone — não deixa a linha anônima", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse(resposta([esperando({ lead_nome: null })])),
    );

    render(<ClientesEsperando agentId="ag-1" />);

    expect(await screen.findByText("5561999990000")).toBeInTheDocument();
  });

  it("clicar leva para a conversa", async () => {
    // É o ponto da faixa: ver a pendência e não ter que caçá-la na fila.
    const abrir = jest.fn();
    mockFetch.mockResolvedValueOnce(
      jsonResponse(resposta([esperando({ conversation_id: "conv-42" })])),
    );

    render(<ClientesEsperando agentId="ag-1" onAbrir={abrir} />);

    await userEvent.click(await screen.findByRole("button", { name: /Marina/ }));

    expect(abrir).toHaveBeenCalledWith("conv-42");
  });

  it("acima de cinco, esconde o resto atrás de um botão", async () => {
    const muitos = Array.from({ length: 8 }, (_, i) =>
      esperando({ conversation_id: `c${i}`, lead_nome: `Cliente ${i}` }),
    );
    mockFetch.mockResolvedValueOnce(jsonResponse(resposta(muitos)));

    render(<ClientesEsperando agentId="ag-1" />);

    expect(await screen.findByText("Cliente 0")).toBeInTheDocument();
    expect(screen.queryByText("Cliente 5")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Ver os outros 3" }));

    expect(screen.getByText("Cliente 7")).toBeInTheDocument();
  });

  it("o cabeçalho conta o total, não o que coube na tela", async () => {
    // O backend trunca a lista; se a faixa contasse as linhas, um escritório
    // com 300 pessoas esperando leria "50".
    mockFetch.mockResolvedValueOnce(
      jsonResponse({
        agent_id: "ag-1",
        minutos: 30,
        total_ia: 280,
        total_humano: 20,
        conversas: [esperando()],
      }),
    );

    render(<ClientesEsperando agentId="ag-1" />);

    expect(await screen.findByText("300 clientes esperando resposta")).toBeInTheDocument();
  });
});
