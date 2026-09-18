/**
 * O campo onde a pessoa assina com o dedo.
 *
 * O jsdom não implementa `CanvasRenderingContext2D`, então o que dá para
 * testar aqui é o contorno — o que o componente promete a quem o usa — e não
 * o desenho em si. Os detalhes que decidem se ele funciona no celular
 * (`touch-none`, Pointer Events, `devicePixelRatio`) são verificáveis como
 * atributos, e é isso que estes testes travam: a regressão que os removeria.
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { CampoDeAssinatura } from "@/components/CampoDeAssinatura";

/** O jsdom devolve `null` em `getContext`; sem isto o componente estoura. */
function fingirCanvas() {
  const ctx = {
    scale: jest.fn(), beginPath: jest.fn(), moveTo: jest.fn(),
    lineTo: jest.fn(), stroke: jest.fn(), clearRect: jest.fn(),
    lineWidth: 0, lineCap: "", lineJoin: "", strokeStyle: "",
  };
  HTMLCanvasElement.prototype.getContext = jest.fn(() => ctx) as never;
  HTMLCanvasElement.prototype.toDataURL = jest.fn(
    () => "data:image/png;base64,AAAA",
  ) as never;
  return ctx;
}

describe("campo de assinatura", () => {
  beforeEach(fingirCanvas);

  it("não rola a página enquanto o dedo desenha", () => {
    // Sem `touch-none`, arrastar o dedo rola a tela em vez de desenhar — e a
    // pessoa nunca consegue assinar no celular, que é onde o link chega.
    render(<CampoDeAssinatura onChange={jest.fn()} />);
    expect(screen.getByLabelText("Área para assinar")).toHaveClass("touch-none");
  });

  it("devolve o PNG quando o traço termina", () => {
    const onChange = jest.fn();
    render(<CampoDeAssinatura onChange={onChange} />);
    const canvas = screen.getByLabelText("Área para assinar");

    (canvas as HTMLCanvasElement).setPointerCapture = jest.fn();
    fireEvent.pointerDown(canvas, { clientX: 10, clientY: 10, pointerId: 1 });
    fireEvent.pointerMove(canvas, { clientX: 40, clientY: 30, pointerId: 1 });
    fireEvent.pointerUp(canvas, { pointerId: 1 });

    expect(onChange).toHaveBeenCalledWith("data:image/png;base64,AAAA");
  });

  it("um toque só também deixa marca", () => {
    // Sem o `lineTo(x + 0.1, y)`, quem toca e solta não desenha nada e acha
    // que o campo está quebrado.
    const ctx = fingirCanvas();
    const onChange = jest.fn();
    render(<CampoDeAssinatura onChange={onChange} />);
    const canvas = screen.getByLabelText("Área para assinar");

    (canvas as HTMLCanvasElement).setPointerCapture = jest.fn();
    fireEvent.pointerDown(canvas, { clientX: 10, clientY: 10, pointerId: 1 });
    fireEvent.pointerUp(canvas, { pointerId: 1 });

    expect(ctx.stroke).toHaveBeenCalled();
    expect(onChange).toHaveBeenCalledWith("data:image/png;base64,AAAA");
  });

  it("limpar apaga e avisa quem escuta", () => {
    const onChange = jest.fn();
    render(<CampoDeAssinatura onChange={onChange} />);
    const canvas = screen.getByLabelText("Área para assinar");

    (canvas as HTMLCanvasElement).setPointerCapture = jest.fn();
    fireEvent.pointerDown(canvas, { clientX: 10, clientY: 10, pointerId: 1 });
    fireEvent.pointerUp(canvas, { pointerId: 1 });

    fireEvent.click(screen.getByRole("button", { name: "limpar" }));
    expect(onChange).toHaveBeenLastCalledWith(null);
  });

  it("o botão de limpar só aparece depois do primeiro traço", () => {
    render(<CampoDeAssinatura onChange={jest.fn()} />);
    expect(screen.queryByRole("button", { name: "limpar" })).not.toBeInTheDocument();
  });

  it("o traço é preto fixo, não a cor do tema", () => {
    // O rabisco vai para um PDF de fundo branco. Um traço claro escolhido no
    // tema escuro sairia invisível no documento — defeito que só apareceria
    // depois de assinado.
    const ctx = fingirCanvas();
    render(<CampoDeAssinatura onChange={jest.fn()} />);
    expect(ctx.strokeStyle).toBe("#111111");
  });
});
