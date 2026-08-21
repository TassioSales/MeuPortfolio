/**
 * A tela de modelos de contrato e a emissão no dossiê.
 *
 * O que ela precisa acertar é o aviso: a variável escrita errada tem de
 * aparecer **na hora de salvar o modelo**, com o nome dela. Descobrir isso na
 * hora de gerar o contrato do cliente é tarde — alguém já prometeu o
 * documento, e o que sai é um buraco no meio de um instrumento jurídico.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ContratosPage from "@/app/dashboard/contratos/page";
import { ContratoDoLead } from "@/components/ContratoDoLead";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";
import type { Contrato, DadosDoContrato, ModeloDeContrato } from "@/types";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}

const VARIAVEIS = [
  { nome: "cliente.nome", descricao: "Nome completo do cliente" },
  { nome: "escritorio.oab", descricao: "OAB do responsável" },
];

const MODELO: ModeloDeContrato = {
  id: "m1",
  nome: "Honorários trabalhista",
  corpo: "# CONTRATO\n{{cliente.nome}}",
  ativo: true,
  data_atualizacao: "2026-08-20T10:00:00",
};

const DADOS_VAZIOS: DadosDoContrato = {
  cpf: null,
  rg: null,
  nacionalidade: null,
  estado_civil: null,
  profissao: null,
  endereco: null,
  cep: null,
  cidade: null,
  uf: null,
};

const CONTRATO: Contrato = {
  id: "k1",
  lead_id: "lead-1",
  modelo_id: "m1",
  corpo: "# CONTRATO\nTássio Sales",
  status: "gerado",
  link_assinatura: null,
  token_expira_em: null,
  data_envio: null,
  data_assinatura: null,
  assinado_nome: null,
  hash_documento: null,
  data_criacao: "2026-08-20T14:30:00",
};

beforeEach(() => setStoredToken("token-abc"));
afterEach(() => clearStoredTokens());

describe("modelos de contrato", () => {
  it("lista os modelos e marca qual está em uso", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse([MODELO]))
      .mockResolvedValueOnce(jsonResponse(VARIAVEIS));

    render(<ContratosPage />);

    expect(await screen.findByText("Honorários trabalhista")).toBeInTheDocument();
    expect(screen.getByText("em uso")).toBeInTheDocument();
  });

  it("mostra as lacunas disponíveis, vindas do backend", async () => {
    // A lista não é escrita na tela de propósito: duas listas — a do editor e
    // a do preenchimento — divergiriam.
    mockFetch
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(VARIAVEIS));

    render(<ContratosPage />);

    expect(await screen.findByText("{{cliente.nome}}")).toBeInTheDocument();
    expect(screen.getByText("OAB do responsável")).toBeInTheDocument();
  });

  it("sem nenhum modelo, explica o que fazer em vez de ficar em branco", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(VARIAVEIS));

    render(<ContratosPage />);

    expect(await screen.findByText(/Nenhum modelo ainda/)).toBeInTheDocument();
  });

  it("a variável escrita errada é apontada pelo nome, ao salvar", async () => {
    // O motivo de o backend recusar em vez de aceitar em silêncio. A mensagem
    // dele nomeia a variável, e a tela não pode trocá-la por um texto genérico.
    mockFetch
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(VARIAVEIS))
      .mockResolvedValueOnce(
        jsonResponse(
          { detail: "Variáveis que o sistema não sabe preencher: cliente.cpj" },
          422,
        ),
      );

    render(<ContratosPage />);
    await screen.findByText(/Nenhum modelo ainda/);

    await userEvent.click(screen.getByRole("button", { name: "Novo modelo" }));
    await userEvent.type(screen.getByLabelText("Nome do modelo"), "Teste");
    await userEvent.type(
      screen.getByLabelText("Texto do contrato"),
      "Eu, {{cliente.cpj}}.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("cliente.cpj");
  });

  it("cria um modelo e volta para a lista", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(VARIAVEIS))
      .mockResolvedValueOnce(jsonResponse(MODELO, 201))
      .mockResolvedValueOnce(jsonResponse([MODELO]))
      .mockResolvedValueOnce(jsonResponse(VARIAVEIS));

    render(<ContratosPage />);
    await screen.findByText(/Nenhum modelo ainda/);

    await userEvent.click(screen.getByRole("button", { name: "Novo modelo" }));
    await userEvent.type(screen.getByLabelText("Nome do modelo"), "Padrão");
    await userEvent.type(screen.getByLabelText("Texto do contrato"), "# CONTRATO");
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    expect(await screen.findByText("Honorários trabalhista")).toBeInTheDocument();
  });

  it("avisa que ativar um desativa o outro", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(VARIAVEIS));

    render(<ContratosPage />);
    await screen.findByText(/Nenhum modelo ainda/);
    await userEvent.click(screen.getByRole("button", { name: "Novo modelo" }));

    expect(screen.getByText(/desativa o anterior/)).toBeInTheDocument();
  });
});

describe("contrato no dossiê", () => {
  it("nasce fechado — quem abre um card quase sempre quer o parecer", () => {
    render(<ContratoDoLead leadId="lead-1" />);

    expect(screen.getByRole("button", { name: /Contrato/ })).toBeInTheDocument();
    expect(screen.queryByLabelText("CPF")).not.toBeInTheDocument();
  });

  it("aberto, mostra os campos e os contratos já emitidos", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(DADOS_VAZIOS))
      .mockResolvedValueOnce(jsonResponse([CONTRATO]));

    render(<ContratoDoLead leadId="lead-1" />);
    await userEvent.click(screen.getByRole("button", { name: /Contrato/ }));

    expect(await screen.findByLabelText("CPF")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abrir PDF" })).toBeInTheDocument();
  });

  it("avisa que campo em branco vira lacuna, e não some do contrato", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(DADOS_VAZIOS))
      .mockResolvedValueOnce(jsonResponse([]));

    render(<ContratoDoLead leadId="lead-1" />);
    await userEvent.click(screen.getByRole("button", { name: /Contrato/ }));

    expect(await screen.findByText(/linha a preencher/)).toBeInTheDocument();
  });

  it("gerar salva os dados antes, para o documento não sair sem o que está na tela", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(DADOS_VAZIOS))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse({ ...DADOS_VAZIOS, cpf: "12345678901" }))
      .mockResolvedValueOnce(jsonResponse(CONTRATO, 201));

    render(<ContratoDoLead leadId="lead-1" />);
    await userEvent.click(screen.getByRole("button", { name: /Contrato/ }));
    await screen.findByLabelText("CPF");

    await userEvent.type(screen.getByLabelText("CPF"), "12345678901");
    await userEvent.click(screen.getByRole("button", { name: "Gerar contrato" }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Abrir PDF" })).toBeInTheDocument(),
    );

    const chamadas = mockFetch.mock.calls.map(([url, init]) => [url, init?.method]);
    const gravou = chamadas.findIndex(([u, m]) => String(u).endsWith("/dados") && m === "PUT");
    const gerou = chamadas.findIndex(
      ([u, m]) => String(u).endsWith("/contratos/leads/lead-1") && m === "POST",
    );
    expect(gravou).toBeGreaterThanOrEqual(0);
    expect(gerou).toBeGreaterThan(gravou);
  });

  it("sem modelo em uso, o erro diz o que conferir", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(DADOS_VAZIOS))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(DADOS_VAZIOS))
      .mockResolvedValueOnce(jsonResponse({ detail: "Modelo not found" }, 404));

    render(<ContratoDoLead leadId="lead-1" />);
    await userEvent.click(screen.getByRole("button", { name: /Contrato/ }));
    await screen.findByLabelText("CPF");

    await userEvent.click(screen.getByRole("button", { name: "Gerar contrato" }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});
