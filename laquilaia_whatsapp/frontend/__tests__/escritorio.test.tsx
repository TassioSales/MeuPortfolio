/**
 * A tela de dados do escritório.
 *
 * O que ela precisa acertar é quem pode o quê: o operador consulta (ele
 * repassa o telefone do suporte quando é ele atendendo) e não altera —
 * mudar o telefone muda o que a IA diz a todo cliente.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import EscritorioPage from "@/app/dashboard/escritorio/page";
import { useAuthStore } from "@/hooks/useAuth";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";
import type { Escritorio, Papel, User } from "@/types";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}

const VAZIO: Escritorio = {
  nome: null,
  cnpj: null,
  oab_responsavel: null,
  fundador: null,
  endereco: null,
  cidade: null,
  email: null,
  telefone: null,
  telefone_suporte: null,
  horario_atendimento: null,
  site: null,
  instagram: null,
};

function entrarComo(papel: Papel) {
  const user: User = {
    id: "u1",
    email: "x@example.com",
    nome: "Fulano",
    status: "ativo",
    papel,
    data_criacao: "2026-01-01T00:00:00",
  };
  useAuthStore.setState({ user, isLoading: false, error: null });
}

beforeEach(() => setStoredToken("token-abc"));
afterEach(() => {
  clearStoredTokens();
  useAuthStore.setState({ user: null, isLoading: true, error: null });
});

describe("dados do escritório", () => {
  it("escritório vazio abre o formulário, não uma tela de erro", async () => {
    // Estado inicial, não falha: é justamente na instalação nova que esta
    // tela é usada.
    entrarComo("admin");
    mockFetch.mockResolvedValueOnce(jsonResponse(VAZIO));

    render(<EscritorioPage />);

    expect(await screen.findByLabelText("Nome do escritório")).toHaveValue("");
  });

  it("o administrador edita e salva", async () => {
    entrarComo("admin");
    mockFetch
      .mockResolvedValueOnce(jsonResponse(VAZIO))
      .mockResolvedValueOnce(jsonResponse({ ...VAZIO, nome: "Borges e Lopes" }));

    render(<EscritorioPage />);

    await userEvent.type(await screen.findByLabelText("Nome do escritório"), "Borges e Lopes");
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(2));
    const [, chamada] = mockFetch.mock.calls[1];
    expect(chamada.method).toBe("PUT");
    expect(JSON.parse(chamada.body).nome).toBe("Borges e Lopes");
    expect(await screen.findByRole("status")).toHaveTextContent("Salvo");
  });

  it("o operador consulta mas não altera", async () => {
    entrarComo("operador");
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ ...VAZIO, telefone_suporte: "61 99883-1516" }),
    );

    render(<EscritorioPage />);

    expect(await screen.findByLabelText("Telefone do suporte")).toHaveValue("61 99883-1516");
    expect(screen.getByLabelText("Telefone do suporte")).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Salvar" })).not.toBeInTheDocument();
  });

  it("explica ao operador por que ele não edita", async () => {
    entrarComo("operador");
    mockFetch.mockResolvedValueOnce(jsonResponse(VAZIO));

    render(<EscritorioPage />);

    expect(
      await screen.findByText(/Só um administrador altera estes dados/),
    ).toBeInTheDocument();
  });

  it("o telefone do suporte diz para que serve", async () => {
    // O número sozinho não resolve: quem lê a tela precisa saber que ele é
    // para cliente antigo, não para lead novo.
    entrarComo("admin");
    mockFetch.mockResolvedValueOnce(jsonResponse(VAZIO));

    render(<EscritorioPage />);

    expect(await screen.findByText(/já é cliente/)).toBeInTheDocument();
  });

  it("erro ao salvar aparece e não é confundido com sucesso", async () => {
    entrarComo("admin");
    mockFetch
      .mockResolvedValueOnce(jsonResponse(VAZIO))
      .mockResolvedValueOnce(jsonResponse({ detail: "Not found" }, 404));

    render(<EscritorioPage />);

    await userEvent.type(await screen.findByLabelText("Nome do escritório"), "X");
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Not found");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
