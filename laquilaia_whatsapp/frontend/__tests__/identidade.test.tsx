/**
 * A marca e a moldura.
 *
 * Não dá para testar se um desenho está bonito, e não é isso que está aqui. O
 * que estes casos travam é o que quebra sem ninguém perceber: o nome do
 * produto escrito errado, a marca sem texto alternativo, e a navegação
 * marcando a página errada como atual.
 */

import { render, screen } from "@testing-library/react";
import { Logo, Marca } from "@/components/Logo";
import { Sidebar } from "@/components/Sidebar";

jest.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
}));

jest.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ user: mockUser }),
}));

let mockPathname = "/dashboard";
let mockUser: { papel: string } | null = { papel: "admin" };

beforeEach(() => {
  mockPathname = "/dashboard";
  mockUser = { papel: "admin" };
});

describe("Marca", () => {
  it("tem nome acessível — é um símbolo, não enfeite", () => {
    render(<Marca />);

    expect(screen.getByRole("img", { name: "AdvogAi" })).toBeInTheDocument();
  });

  it("escreve o nome com o A do meio em maiúscula", () => {
    // "Advogai" e "AdvogAI" são erros que passam despercebidos em revisão de
    // código e aparecem em toda tela do produto.
    const { container } = render(<Logo />);

    expect(container.textContent).toBe("AdvogAi");
  });

  it("pode aparecer só como símbolo, sem o nome", () => {
    const { container } = render(<Logo soMarca />);

    expect(container.textContent).toBe("");
    expect(screen.getByRole("img", { name: "AdvogAi" })).toBeInTheDocument();
  });
});

describe("Navegação lateral", () => {
  it("marca a página atual, e só ela", () => {
    mockPathname = "/dashboard/kanban";
    render(<Sidebar />);

    expect(screen.getByRole("link", { name: /Kanban/ })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: /Métricas/ })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("a visão geral não fica ativa em toda página do painel", () => {
    // O href dela é prefixo de todos os outros: sem a comparação exata, ela
    // ficaria acesa junto com a página em que se está.
    mockPathname = "/dashboard/agents";
    render(<Sidebar />);

    expect(screen.getByRole("link", { name: /Visão geral/ })).not.toHaveAttribute(
      "aria-current",
    );
  });
});


describe("Menu por papel", () => {
  it("o administrador vê as telas de configuração", () => {
    mockUser = { papel: "admin" };
    render(<Sidebar />);

    expect(screen.getByRole("link", { name: /Agentes/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Chat de teste/ })).toBeInTheDocument();
  });

  it("o operador não vê link que bate em 404", () => {
    // O backend responde 404 nessas telas para quem não é admin. Deixar o link
    // visível é oferecer uma porta que bate na cara de quem clica.
    mockUser = { papel: "operador" };
    render(<Sidebar />);

    expect(screen.queryByRole("link", { name: /Agentes/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Chat de teste/ })).not.toBeInTheDocument();
    // O que ele usa continua lá.
    expect(screen.getByRole("link", { name: /Atendimentos/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Kanban/ })).toBeInTheDocument();
  });

  it("sem sessão carregada, esconde em vez de piscar", () => {
    // Mostrar e esconder meio segundo depois faz o menu parecer defeito.
    mockUser = null;
    render(<Sidebar />);

    expect(screen.queryByRole("link", { name: /Agentes/ })).not.toBeInTheDocument();
  });
});
