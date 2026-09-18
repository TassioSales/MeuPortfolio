/**
 * A assinatura gerada a partir do nome.
 *
 * Existe porque assinar com o dedo numa tela sai um garrancho, e muita gente
 * desiste ou fica com vergonha do resultado. É o que Autentique e DocuSign
 * oferecem ao lado do desenho.
 *
 * O que importa travar aqui: que o resultado seja **o mesmo PNG** do desenho
 * (um formato só para validar, guardar e desenhar no PDF), que a fonte seja
 * esperada antes de pintar, e que um nome longo não seja cortado.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AssinaturaDigitada } from "@/components/AssinaturaDigitada";

function fingirCanvas(larguraDoTexto = 300) {
  const ctx = {
    clearRect: jest.fn(),
    fillText: jest.fn(),
    measureText: jest.fn(() => ({ width: larguraDoTexto })),
    font: "",
    fillStyle: "",
    textAlign: "",
    textBaseline: "",
  };
  HTMLCanvasElement.prototype.getContext = jest.fn(() => ctx) as never;
  HTMLCanvasElement.prototype.toDataURL = jest.fn(
    () => "data:image/png;base64,DIGITADA",
  ) as never;
  return ctx;
}

beforeEach(() => {
  // O jsdom não tem `document.fonts`; sem isto o componente estoura antes de
  // pintar. O `catch` do componente cobre o navegador que também não tem.
  Object.defineProperty(document, "fonts", {
    configurable: true,
    value: { load: jest.fn().mockResolvedValue([]), ready: Promise.resolve() },
  });
});

describe("assinatura digitada", () => {
  it("gera o mesmo formato do desenho", async () => {
    // Um formato só: o backend não sabe (nem precisa) se o traço veio de um
    // dedo ou de uma fonte.
    fingirCanvas();
    const onChange = jest.fn();
    render(<AssinaturaDigitada nome="Maria Aparecida" onChange={onChange} />);

    await waitFor(() =>
      expect(onChange).toHaveBeenCalledWith("data:image/png;base64,DIGITADA"),
    );
  });

  it("espera a fonte antes de pintar", async () => {
    // Sem esperar, o primeiro desenho sai na fonte de reserva e a pessoa
    // assina com o nome em Times — que não parece assinatura nenhuma.
    const ctx = fingirCanvas();
    render(<AssinaturaDigitada nome="Maria" onChange={jest.fn()} />);

    await waitFor(() => expect(ctx.fillText).toHaveBeenCalled());
    expect(document.fonts.load).toHaveBeenCalled();
  });

  it("encolhe a letra até o nome caber", async () => {
    // "Tassio Lucian de Jesus Sales" estoura a largura no tamanho cheio, e
    // cortar o nome de alguém num contrato é pior que uma letra menor.
    const ctx = fingirCanvas(5000);
    render(
      <AssinaturaDigitada
        nome="Tassio Lucian de Jesus Sales"
        onChange={jest.fn()}
      />,
    );

    await waitFor(() => expect(ctx.fillText).toHaveBeenCalled());
    const tamanho = Number(String(ctx.font).match(/(\d+)px/)?.[1]);
    expect(tamanho).toBeLessThan(84);
  });

  it("nome vazio não vira assinatura", async () => {
    fingirCanvas();
    const onChange = jest.fn();
    render(<AssinaturaDigitada nome="   " onChange={onChange} />);

    await waitFor(() => expect(onChange).toHaveBeenCalledWith(null));
  });

  it("trocar o estilo gera uma assinatura nova", async () => {
    fingirCanvas();
    const onChange = jest.fn();
    render(<AssinaturaDigitada nome="Maria" onChange={onChange} />);
    await waitFor(() => expect(onChange).toHaveBeenCalled());

    const antes = onChange.mock.calls.length;
    await userEvent.click(screen.getByRole("radio", { name: /Caneta/ }));

    await waitFor(() =>
      expect(onChange.mock.calls.length).toBeGreaterThan(antes),
    );
  });

  it("mostra o nome da pessoa em cada opção", async () => {
    fingirCanvas();
    render(<AssinaturaDigitada nome="Maria Aparecida" onChange={jest.fn()} />);

    expect(screen.getAllByText("Maria Aparecida")).toHaveLength(3);
  });
});
