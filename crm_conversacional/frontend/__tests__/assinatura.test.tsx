/**
 * A página pública de assinatura.
 *
 * É a única tela do produto aberta na internet e vista por quem não tem
 * conta. O que ela precisa acertar, em ordem de importância:
 *
 * 1. **Não deixar assinar sem ler.** Assinatura de quem não rolou o contrato
 *    é assinatura contestável — e é feio de fazer com um cliente.
 * 2. **Link vencido não pode parecer defeito.** A pessoa precisa saber que é
 *    só pedir outro, não que o escritório quebrou.
 * 3. **Quem já assinou e volta ao link** tem de ver que assinou, não uma tela
 *    de erro que sugira que a assinatura se perdeu.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AssinarPage from "@/app/assinar/[token]/page";
import type { ContratoParaAssinar } from "@/types";

const mockFetch = global.fetch as jest.Mock;

/**
 * A página agora monta um `<canvas>` (desenhar) e usa `document.fonts`
 * (digitar). O jsdom não tem nenhum dos dois.
 */
beforeEach(() => {
  // A fila do `mockResolvedValueOnce` sobrevive entre testes: uma resposta
  // enfileirada e não consumida vaza para o teste seguinte, que abre a página
  // com o estado errado. Já aconteceu neste arquivo.
  mockFetch.mockReset();

  HTMLCanvasElement.prototype.getContext = jest.fn(() => ({
    scale: jest.fn(), beginPath: jest.fn(), moveTo: jest.fn(), lineTo: jest.fn(),
    stroke: jest.fn(), clearRect: jest.fn(), fillText: jest.fn(),
    measureText: jest.fn(() => ({ width: 100 })),
  })) as never;
  HTMLCanvasElement.prototype.toDataURL = jest.fn(
    () => "data:image/png;base64,AAAA",
  ) as never;
  Object.defineProperty(document, "fonts", {
    configurable: true,
    value: { load: jest.fn().mockResolvedValue([]), ready: Promise.resolve() },
  });
});

jest.mock("next/navigation", () => ({
  useParams: () => ({ token: "tok-abc" }),
}));

function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}

const CONTRATO: ContratoParaAssinar = {
  corpo: "# CONTRATO\nCláusula primeira, com **negrito**.\nCláusula segunda.",
  nome_do_cliente: "Maria Aparecida da Silva",
  nome_do_escritorio: "Sales Advocacia",
  ja_assinado: false,
  assinado_em: null,
  assinado_por: null,
};

/**
 * Simula a rolagem até o fim.
 *
 * O jsdom não tem layout: `scrollHeight`, `clientHeight` e `scrollTop` são
 * todos zero, e o handler leria "0 - 0 - 0 < 40" como fim do texto por
 * acidente. Definir os três é o que faz o teste exercitar a regra de verdade.
 */
function rolarAteOFim(elemento: HTMLElement, ateOFim = true) {
  Object.defineProperty(elemento, "scrollHeight", { value: 1000, configurable: true });
  Object.defineProperty(elemento, "clientHeight", { value: 400, configurable: true });
  Object.defineProperty(elemento, "scrollTop", {
    value: ateOFim ? 600 : 100,
    configurable: true,
  });
  fireEvent.scroll(elemento);
}

function oContrato(): HTMLElement {
  return screen.getByText(/Cláusula primeira/).closest("article") as HTMLElement;
}

describe("página de assinatura", () => {
  it("mostra o contrato e o nome do escritório", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(CONTRATO));

    render(<AssinarPage />);

    expect(await screen.findByText("Sales Advocacia")).toBeInTheDocument();
    expect(screen.getByText(/Cláusula primeira/)).toBeInTheDocument();
    expect(screen.getByText("CONTRATO")).toBeInTheDocument();
  });

  it("já traz o nome do cliente preenchido", async () => {
    // Quem assina no celular não quer digitar o nome inteiro num campo de
    // texto. O valor continua editável — o documento pode estar num nome
    // ligeiramente diferente.
    mockFetch.mockResolvedValueOnce(jsonResponse(CONTRATO));

    render(<AssinarPage />);

    await waitFor(() =>
      expect(screen.getByLabelText("Seu nome completo")).toHaveValue(
        "Maria Aparecida da Silva",
      ),
    );
  });

  it("não deixa assinar antes de o contrato ser lido até o fim", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(CONTRATO));

    render(<AssinarPage />);
    await screen.findByText(/Cláusula primeira/);

    await userEvent.click(screen.getByRole("checkbox"));

    expect(screen.getByRole("button", { name: "Assinar contrato" })).toBeDisabled();
    expect(screen.getByText(/Role o contrato até o fim/)).toBeInTheDocument();
  });

  it("rolar até o fim e aceitar libera o botão", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(CONTRATO));

    render(<AssinarPage />);
    await screen.findByText(/Cláusula primeira/);

    rolarAteOFim(oContrato());
    await userEvent.click(screen.getByRole("checkbox"));

    expect(screen.getByRole("button", { name: "Assinar contrato" })).toBeEnabled();
  });

  it("o aceite é obrigatório mesmo depois de ler tudo", async () => {
    // Assinar é ato. Caixa desmarcada assinaria por quem só abriu a página.
    mockFetch.mockResolvedValueOnce(jsonResponse(CONTRATO));

    render(<AssinarPage />);
    await screen.findByText(/Cláusula primeira/);

    rolarAteOFim(oContrato());

    expect(screen.getByRole("button", { name: "Assinar contrato" })).toBeDisabled();
  });

  it("assina e mostra a confirmação com data e nome", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(CONTRATO))
      .mockResolvedValueOnce(
        jsonResponse({
          ...CONTRATO,
          ja_assinado: true,
          assinado_em: "2026-08-21T04:34:00",
          assinado_por: "Maria Aparecida da Silva",
        }),
      );

    render(<AssinarPage />);
    await screen.findByText(/Cláusula primeira/);

    rolarAteOFim(oContrato());
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: "Assinar contrato" }));

    expect(await screen.findByText("Assinatura registrada.")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Assinar contrato" }),
    ).not.toBeInTheDocument();
  });

  it("link vencido explica o que fazer, sem parecer defeito", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "Contrato not found" }, 404));

    render(<AssinarPage />);

    expect(await screen.findByText("Link indisponível")).toBeInTheDocument();
    expect(screen.getByText(/pedindo um link novo/)).toBeInTheDocument();
  });

  it("quem já assinou e volta ao link vê que assinou", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({
        ...CONTRATO,
        ja_assinado: true,
        assinado_em: "2026-08-21T04:34:00",
        assinado_por: "Maria Aparecida da Silva",
      }),
    );

    render(<AssinarPage />);

    expect(await screen.findByText("Assinatura registrada.")).toBeInTheDocument();
    expect(screen.getByText("Contrato assinado")).toBeInTheDocument();
  });

  it("oferece desenhar e digitar", async () => {
    // Assinar com o dedo sai um garrancho e muita gente desiste. As duas
    // opções são o que Autentique e DocuSign fazem.
    mockFetch.mockResolvedValueOnce(jsonResponse(CONTRATO));

    render(<AssinarPage />);
    await screen.findByText(/Cláusula primeira/);

    expect(screen.getByRole("tab", { name: "Desenhar" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Digitar" })).toBeInTheDocument();
    // Desenhar é o padrão: é o que se parece com assinar.
    expect(screen.getByRole("tab", { name: "Desenhar" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("trocar de modo descarta o traço anterior", async () => {
    // Manter um desenho invisível enquanto a pessoa escolhe uma letra faria
    // ela assinar com o que não está vendo.
    // Uma resposta só: este teste não chega a assinar. Enfileirar a segunda
    // deixava-a pendurada na fila e o teste **seguinte** abria a página já
    // como "assinado" — falha que só aparece na suíte inteira.
    mockFetch.mockResolvedValueOnce(jsonResponse(CONTRATO));

    render(<AssinarPage />);
    await screen.findByText(/Cláusula primeira/);

    await userEvent.click(screen.getByRole("tab", { name: "Digitar" }));
    expect(screen.getByRole("tab", { name: "Digitar" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.queryByLabelText("Área para assinar")).not.toBeInTheDocument();
  });

  it("assinar continua possível sem nenhum desenho", async () => {
    // O que prova a assinatura é a trilha, não o rabisco. Navegador sem
    // canvas, mouse ruim, mão trêmula — a pessoa ainda assina.
    mockFetch
      .mockResolvedValueOnce(jsonResponse(CONTRATO))
      .mockResolvedValueOnce(
        jsonResponse({ ...CONTRATO, ja_assinado: true, assinado_por: "Maria" }),
      );

    render(<AssinarPage />);
    await screen.findByText(/Cláusula primeira/);

    rolarAteOFim(oContrato());
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: "Assinar contrato" }));

    expect(await screen.findByText("Assinatura registrada.")).toBeInTheDocument();
  });

  it("a página não manda cabeçalho de autorização", async () => {
    // Quem abre é o cliente do escritório, que não tem conta. Se algum dia o
    // `api.ts` for usado aqui por engano, o token de quem gerou o link iria
    // junto para uma página pública.
    mockFetch.mockResolvedValueOnce(jsonResponse(CONTRATO));

    render(<AssinarPage />);
    await screen.findByText(/Cláusula primeira/);

    const [, init] = mockFetch.mock.calls[0];
    expect(init?.headers?.Authorization).toBeUndefined();
  });
});
