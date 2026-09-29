/**
 * Tema claro, escuro e o do sistema.
 *
 * O que estes casos travam não é a aparência — é o comportamento que some sem
 * ninguém perceber: a escolha não sobreviver ao recarregamento, "sistema"
 * deixar de seguir o sistema, e o script anti-piscada parar de rodar antes da
 * primeira pintura.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SeletorDeTema } from "@/components/SeletorDeTema";
import {
  CHAVE_DO_TEMA,
  SCRIPT_ANTI_PISCADA,
  aplicarTema,
  lerTemaSalvo,
  temaEfetivo,
} from "@/lib/tema";

function sistemaEscuro(escuro: boolean) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (consulta: string) => ({
      matches: escuro && consulta.includes("dark"),
      media: consulta,
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    }),
  });
}

beforeEach(() => {
  window.localStorage.clear();
  document.documentElement.classList.remove("dark");
  sistemaEscuro(false);
});

describe("lib/tema", () => {
  it("sem escolha salva, segue o sistema", () => {
    expect(lerTemaSalvo()).toBe("sistema");
  });

  it("valor estranho no armazenamento não vira tema", () => {
    // `localStorage` é editável por qualquer um pelo console do navegador.
    window.localStorage.setItem(CHAVE_DO_TEMA, "roxo");

    expect(lerTemaSalvo()).toBe("sistema");
  });

  it("'sistema' resolve para o que o sistema pede", () => {
    sistemaEscuro(true);
    expect(temaEfetivo("sistema")).toBe("escuro");

    sistemaEscuro(false);
    expect(temaEfetivo("sistema")).toBe("claro");
  });

  it("a escolha explícita vence a do sistema", () => {
    sistemaEscuro(true);

    expect(temaEfetivo("claro")).toBe("claro");
  });

  it("aplicar escuro põe a classe no <html>", () => {
    aplicarTema("escuro");
    expect(document.documentElement).toHaveClass("dark");

    aplicarTema("claro");
    expect(document.documentElement).not.toHaveClass("dark");
  });
});

describe("script anti-piscada", () => {
  it("lê a mesma chave que o seletor grava", () => {
    // Se as duas se separarem, a página nasce com um tema e troca para outro
    // ao montar — exatamente o flash que o script existe para evitar.
    expect(SCRIPT_ANTI_PISCADA).toContain(JSON.stringify(CHAVE_DO_TEMA));
  });

  it("não deixa erro escapar", () => {
    // `localStorage` estoura em navegação privada de alguns navegadores, e o
    // preço de falhar aqui seria a página não renderizar.
    expect(SCRIPT_ANTI_PISCADA).toContain("catch");
  });
});

describe("SeletorDeTema", () => {
  it("oferece as três opções, e não um interruptor", () => {
    // Com interruptor não há como voltar para "seguir o sistema" depois de
    // tocar uma vez — e é o estado padrão.
    render(<SeletorDeTema />);

    expect(screen.getByRole("radio", { name: "Claro" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Escuro" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Sistema" })).toBeInTheDocument();
  });

  it("escolher escuro aplica e guarda", async () => {
    render(<SeletorDeTema />);

    await userEvent.click(screen.getByRole("radio", { name: "Escuro" }));

    expect(document.documentElement).toHaveClass("dark");
    expect(window.localStorage.getItem(CHAVE_DO_TEMA)).toBe("escuro");
  });

  it("começa marcado no que estava salvo", async () => {
    window.localStorage.setItem(CHAVE_DO_TEMA, "claro");

    render(<SeletorDeTema />);

    expect(await screen.findByRole("radio", { name: "Claro", checked: true }))
      .toBeInTheDocument();
  });
});
