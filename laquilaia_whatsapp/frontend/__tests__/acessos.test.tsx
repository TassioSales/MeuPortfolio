/**
 * O que cada papel vê e pode fazer — pela tela.
 *
 * A autorização de verdade está no backend, rota por rota (e coberta por
 * `tests/test_controle_de_acesso.py`). O que se trava aqui é a outra metade:
 * o operador não deve **encontrar** as telas de configuração, e o
 * administrador não deve encontrar botão para se rebaixar. Link que leva a um
 * 404 é uma promessa quebrada; botão que só serve para mostrar erro também.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import UsuariosPage from "@/app/dashboard/usuarios/page";
import { SemAgente } from "@/components/SemAgente";
import { Sidebar } from "@/components/Sidebar";
import { useAuthStore } from "@/hooks/useAuth";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";
import type { Papel, User } from "@/types";

const mockFetch = global.fetch as jest.Mock;

jest.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

function usuario(id: string, papel: Papel, extras: Partial<User> = {}): User {
  return {
    id,
    email: `${id}@example.com`,
    nome: id,
    status: "ativo",
    papel,
    data_criacao: "2026-01-01T00:00:00",
    ...extras,
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}

function entrarComo(u: User) {
  useAuthStore.setState({ user: u, isLoading: false, error: null });
}

beforeEach(() => setStoredToken("token-abc"));
afterEach(() => {
  clearStoredTokens();
  useAuthStore.setState({ user: null, isLoading: true, error: null });
});

describe("menu por papel", () => {
  it("operador não vê agentes, WhatsApp, chat de teste nem acessos", () => {
    // São exatamente as telas em que o backend responde 404 ao operador.
    entrarComo(usuario("ana", "operador"));

    render(<Sidebar />);

    expect(screen.queryByText("Agentes")).not.toBeInTheDocument();
    expect(screen.queryByText("WhatsApp")).not.toBeInTheDocument();
    expect(screen.queryByText("Chat de teste")).not.toBeInTheDocument();
    expect(screen.queryByText("Acessos")).not.toBeInTheDocument();
  });

  it("operador continua vendo o que ele usa para trabalhar", () => {
    entrarComo(usuario("ana", "operador"));

    render(<Sidebar />);

    expect(screen.getByText("Atendimentos")).toBeInTheDocument();
    expect(screen.getByText("Clientes")).toBeInTheDocument();
    // O escritório o operador vê: é dele o telefone do suporte que ele
    // repassa quando é ele atendendo.
    expect(screen.getByText("Escritório")).toBeInTheDocument();
    expect(screen.getByText("Kanban CRM")).toBeInTheDocument();
    expect(screen.getByText("Métricas")).toBeInTheDocument();
    expect(screen.getByText("Histórico")).toBeInTheDocument();
  });

  it("administrador vê tudo", () => {
    entrarComo(usuario("dono", "admin"));

    render(<Sidebar />);

    for (const item of ["Agentes", "WhatsApp", "Chat de teste", "Acessos"]) {
      expect(screen.getByText(item)).toBeInTheDocument();
    }
  });
});

describe("tela de acessos", () => {
  it("não oferece botão para o administrador mexer em si mesmo", async () => {
    // O backend recusa com 400. Mostrar o botão seria oferecer uma ação que
    // sempre falha — e sugerir que rebaixar a si mesmo é uma opção.
    const eu = usuario("dono", "admin");
    entrarComo(eu);
    mockFetch.mockResolvedValueOnce(jsonResponse([eu, usuario("ana", "operador")]));

    render(<UsuariosPage />);

    await screen.findByText("ana");
    // Duas linhas na lista, um único par de botões — o da outra pessoa.
    expect(screen.getAllByRole("button", { name: "Tornar admin" })).toHaveLength(1);
    expect(screen.queryByRole("button", { name: "Tornar operador" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Desativar" })).toHaveLength(1);
    expect(screen.getByText("administrador desta conta")).toBeInTheDocument();
  });

  it("desativar troca o botão por reativar e marca a linha", async () => {
    const eu = usuario("dono", "admin");
    const ana = usuario("ana", "operador");
    entrarComo(eu);
    mockFetch
      .mockResolvedValueOnce(jsonResponse([eu, ana]))
      .mockResolvedValueOnce(jsonResponse({ ...ana, status: "inativo" }));

    render(<UsuariosPage />);
    await screen.findByText("ana");

    await userEvent.click(screen.getByRole("button", { name: "Desativar" }));

    await waitFor(() => expect(screen.getByText("inativo")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Reativar" })).toBeInTheDocument();

    const [, chamada] = mockFetch.mock.calls[1];
    expect(chamada.method).toBe("PATCH");
    expect(JSON.parse(chamada.body)).toEqual({ status: "inativo" });
  });

  it("o erro do backend aparece na tela em vez de sumir", async () => {
    const eu = usuario("dono", "admin");
    entrarComo(eu);
    mockFetch
      .mockResolvedValueOnce(jsonResponse([eu, usuario("ana", "operador")]))
      .mockResolvedValueOnce(
        jsonResponse({ detail: "Você não pode remover o próprio acesso." }, 400),
      );

    render(<UsuariosPage />);
    await screen.findByText("ana");

    await userEvent.click(screen.getByRole("button", { name: "Desativar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Você não pode remover o próprio acesso.",
    );
  });

  it("o acesso novo nasce operador, não administrador", async () => {
    // O padrão é o menor privilégio: quem cria acesso às pressas não deve
    // distribuir administrador sem perceber.
    const eu = usuario("dono", "admin");
    entrarComo(eu);
    mockFetch
      .mockResolvedValueOnce(jsonResponse([eu]))
      .mockResolvedValueOnce(jsonResponse(usuario("ana", "operador")));

    render(<UsuariosPage />);
    await screen.findByText("dono");

    await userEvent.click(screen.getByRole("button", { name: "Novo acesso" }));
    await userEvent.type(screen.getByLabelText("Nome"), "Ana");
    await userEvent.type(screen.getByLabelText("E-mail"), "ana@example.com");
    await userEvent.type(screen.getByLabelText("Senha inicial"), "SenhaDaAna123");
    await userEvent.click(screen.getByRole("button", { name: "Criar acesso" }));

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(2));
    const [, chamada] = mockFetch.mock.calls[1];
    expect(JSON.parse(chamada.body)).toEqual({
      nome: "Ana",
      email: "ana@example.com",
      senha: "SenhaDaAna123",
      papel: "operador",
    });
  });
});

describe("tela vazia sem agente", () => {
  it("ao operador, não oferece a porta que ele não pode abrir", async () => {
    // Foi o que o painel real fez: o operador entrou no Kanban, leu "Nenhum
    // agente ainda" e ganhou um botão "Ir para Agentes" — uma tela onde o
    // backend responde 404 para ele.
    entrarComo(usuario("ana", "operador"));

    render(
      <SemAgente icone="🗂️" titulo="Nenhum agente ainda" paraOAdmin="Crie um agente." />,
    );

    expect(screen.queryByRole("link", { name: "Ir para Agentes" })).not.toBeInTheDocument();
    expect(screen.getByText(/Peça isso a um administrador/)).toBeInTheDocument();
  });

  it("ao administrador, oferece — ele é quem resolve", () => {
    entrarComo(usuario("dono", "admin"));

    render(
      <SemAgente icone="🗂️" titulo="Nenhum agente ainda" paraOAdmin="Crie um agente." />,
    );

    expect(screen.getByRole("link", { name: "Ir para Agentes" })).toHaveAttribute(
      "href",
      "/dashboard/agents",
    );
  });
});
