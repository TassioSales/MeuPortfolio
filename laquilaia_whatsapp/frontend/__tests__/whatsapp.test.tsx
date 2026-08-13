/**
 * A tela de conexão do WhatsApp.
 *
 * O que estes casos travam é a diferença entre três telas que se pareceriam:
 * conectado (sem QR, sem repescagem), desconectado (com QR e repescando), e a
 * Evolution fora do ar — que não é o número caído e não deve mandar ninguém
 * ler QR nenhum.
 */

import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConexaoWhatsapp } from "@/components/ConexaoWhatsapp";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

const CONECTADO = { estado: "conectado", instancia: "laquilaia", detalhe: null };
const DESCONECTADO = { estado: "desconectado", instancia: "laquilaia", detalhe: null };
const QR = {
  qrcode: "data:image/png;base64,iVBORw0KGgo=",
  codigo: null,
  detalhe: null,
};

beforeEach(() => setStoredToken("token-abc"));
afterEach(() => {
  clearStoredTokens();
  jest.useRealTimers();
});

describe("ConexaoWhatsapp", () => {
  it("conectado não mostra QR", async () => {
    // Pedir o QR de um número já pareado é gastar requisição para receber
    // "já está conectado".
    mockFetch.mockResolvedValueOnce(jsonResponse(CONECTADO));

    render(<ConexaoWhatsapp />);

    expect(await screen.findByText("Conectado")).toBeInTheDocument();
    expect(screen.queryByAltText(/QR code/)).not.toBeInTheDocument();
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("desconectado mostra o QR e diz o que fazer no celular", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(DESCONECTADO))
      .mockResolvedValueOnce(jsonResponse(QR));

    render(<ConexaoWhatsapp />);

    expect(await screen.findByAltText(/QR code/)).toHaveAttribute("src", QR.qrcode);
    expect(screen.getByText(/Aparelhos conectados/)).toBeInTheDocument();
  });

  it("Evolution fora do ar não vira 'número desconectado'", async () => {
    // São problemas diferentes, com donos diferentes: um se resolve lendo um
    // QR, o outro subindo um serviço.
    mockFetch.mockResolvedValueOnce(
      jsonResponse({
        estado: "indisponivel",
        instancia: "laquilaia",
        detalhe: "HTTP 502",
      }),
    );

    render(<ConexaoWhatsapp />);

    expect(await screen.findByText("Evolution fora do ar")).toBeInTheDocument();
    expect(screen.getByText(/problema está no serviço/)).toBeInTheDocument();
    expect(screen.queryByAltText(/QR code/)).not.toBeInTheDocument();
  });

  it("sem QR e sem código, explica em vez de mostrar quadrado vazio", async () => {
    // É a resposta que as issues #2380 e #2385 da Evolution relatam.
    mockFetch
      .mockResolvedValueOnce(jsonResponse(DESCONECTADO))
      .mockResolvedValueOnce(
        jsonResponse({
          qrcode: null,
          codigo: null,
          detalhe: "a Evolution respondeu sem QR",
        }),
      );

    render(<ConexaoWhatsapp />);

    expect(
      await screen.findByText(/respondeu sem QR e sem código de pareamento/),
    ).toBeInTheDocument();
  });

  it("mostra o código de pareamento quando não há QR", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(DESCONECTADO))
      .mockResolvedValueOnce(
        jsonResponse({ qrcode: null, codigo: "ABCD-1234", detalhe: null }),
      );

    render(<ConexaoWhatsapp />);

    expect(await screen.findByText("ABCD-1234")).toBeInTheDocument();
  });

  it("repesca enquanto desconectado, e para depois de conectar", async () => {
    // O QR do WhatsApp expira em segundos; sem repescar, a tela mostra um
    // código que já não vale. Continuar repescando depois de pareado é o
    // desperdício simétrico.
    jest.useFakeTimers();
    mockFetch
      .mockResolvedValueOnce(jsonResponse(DESCONECTADO))
      .mockResolvedValueOnce(jsonResponse(QR))
      .mockResolvedValueOnce(jsonResponse(CONECTADO));

    render(<ConexaoWhatsapp />);

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(2));

    await act(async () => {
      jest.advanceTimersByTime(20_000);
    });

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(3));

    // Agora conectado: o relógio avança e nada mais é pedido.
    await act(async () => {
      jest.advanceTimersByTime(60_000);
    });

    expect(mockFetch).toHaveBeenCalledTimes(3);
  });

  it("o botão de atualizar relê na hora", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(CONECTADO))
      .mockResolvedValueOnce(jsonResponse(CONECTADO));

    render(<ConexaoWhatsapp />);
    await screen.findByText("Conectado");

    await userEvent.click(screen.getByRole("button", { name: "Atualizar" }));

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(2));
  });
});
