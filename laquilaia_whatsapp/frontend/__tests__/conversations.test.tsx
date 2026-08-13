/**
 * Testes dos atendimentos e da pausa humana: camada de API, hook e painel.
 *
 * O que mais importa aqui é o estado da automação nunca mentir — quem lê a
 * tela decide se vai escrever para o cliente, e mostrar "humano assumiu" antes
 * de o backend confirmar faria o operador falar junto com a IA.
 */
import { render, screen, waitFor } from "@testing-library/react";
import { renderHook, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import * as conversationsApi from "@/lib/conversations";
import { useConversations } from "@/hooks/useConversations";
import { ConversationsPanel } from "@/components/ConversationsPanel";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";
import type { ConversationSummary, ConversationTranscript } from "@/types";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

const CONVERSA: ConversationSummary = {
  id: "conv-1",
  phone_number: "5561999990001",
  status: "ativa",
  ia_ativa: true,
  lead_nome: "Maria Silva",
  lead_status_funil: "qualificado",
  data_ultima_msg: "2026-08-11T12:00:00Z",
  total_mensagens: 2,
  ultima_mensagem: "Claro! Me conta o que você precisa.",
  ultimo_remetente: "assistant",
};

const PAUSADA: ConversationSummary = {
  ...CONVERSA,
  id: "conv-2",
  phone_number: "5561999990002",
  lead_nome: "João Souza",
  status: "pausada",
  ia_ativa: false,
};

const TRANSCRICAO: ConversationTranscript = {
  conversation_id: "conv-1",
  status: "ativa",
  ia_ativa: true,
  phone_number: "5561999990001",
  lead_nome: "Maria Silva",
  analise_preliminar: null,
  casos: [],
  messages: [
    {
      id: "m1",
      remetente: "user",
      conteudo: "Olá, queria saber mais.",
      timestamp: "2026-08-11T11:58:00Z",
    },
    {
      id: "m2",
      remetente: "assistant",
      conteudo: "Claro! Me conta o que você precisa.",
      timestamp: "2026-08-11T12:00:00Z",
    },
  ],
};

// O painel abre um WebSocket pelo useAgentEvents; o jsdom não o implementa.
class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: ((e: { code: number }) => void) | null = null;
  onerror: (() => void) | null = null;
  close = jest.fn();

  constructor(public url: string) {
    FakeWebSocket.instances.push(this);
  }
}

beforeEach(() => {
  setStoredToken("token-abc");
  FakeWebSocket.instances = [];
  (global as unknown as { WebSocket: unknown }).WebSocket = FakeWebSocket;
});
afterEach(() => clearStoredTokens());

describe("lib/conversations", () => {
  it("listConversations busca as conversas do agente", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse([CONVERSA]));

    await conversationsApi.listConversations("agent-1");

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/agents/agent-1/conversations");
    expect(init.method).toBe("GET");
  });

  it("getTranscript busca as mensagens da conversa", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(TRANSCRICAO));

    await conversationsApi.getTranscript("conv-1");

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/conversations/conv-1/messages");
    expect(init.method).toBe("GET");
  });

  it("pauseConversation faz POST em /pause", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ conversation_id: "conv-1", status: "pausada", ia_ativa: false }),
    );

    await conversationsApi.pauseConversation("conv-1");

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/conversations/conv-1/pause");
    expect(init.method).toBe("POST");
  });

  it("resumeConversation faz POST em /resume", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ conversation_id: "conv-1", status: "ativa", ia_ativa: true }),
    );

    await conversationsApi.resumeConversation("conv-1");

    expect(mockFetch.mock.calls[0][0]).toContain("/api/v1/conversations/conv-1/resume");
  });
});

describe("useConversations", () => {
  it("carrega a fila do agente", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse([CONVERSA, PAUSADA]));

    const { result } = renderHook(() => useConversations("agent-1"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.conversations).toHaveLength(2);
  });

  it("abrir uma conversa traz a transcrição", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse([CONVERSA]))
      .mockResolvedValueOnce(jsonResponse(TRANSCRICAO));

    const { result } = renderHook(() => useConversations("agent-1"));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.openConversation("conv-1");
    });

    expect(result.current.transcript?.messages).toHaveLength(2);
    expect(result.current.selectedId).toBe("conv-1");
  });

  it("assumir a conversa marca a IA como parada na transcrição e na fila", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse([CONVERSA]))
      .mockResolvedValueOnce(jsonResponse(TRANSCRICAO))
      .mockResolvedValueOnce(
        jsonResponse({ conversation_id: "conv-1", status: "pausada", ia_ativa: false }),
      );

    const { result } = renderHook(() => useConversations("agent-1"));
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    await act(async () => {
      await result.current.openConversation("conv-1");
    });

    await act(async () => {
      await result.current.togglePause();
    });

    expect(result.current.transcript?.ia_ativa).toBe(false);
    // A lista precisa acompanhar, senão o selo dela continuaria o antigo.
    expect(result.current.conversations[0].ia_ativa).toBe(false);
  });

  it("conversa já pausada chama resume, não pause", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse([PAUSADA]))
      .mockResolvedValueOnce(
        jsonResponse({ ...TRANSCRICAO, conversation_id: "conv-2", ia_ativa: false }),
      )
      .mockResolvedValueOnce(
        jsonResponse({ conversation_id: "conv-2", status: "ativa", ia_ativa: true }),
      );

    const { result } = renderHook(() => useConversations("agent-1"));
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    await act(async () => {
      await result.current.openConversation("conv-2");
    });
    await act(async () => {
      await result.current.togglePause();
    });

    expect(mockFetch.mock.calls[2][0]).toContain("/resume");
    expect(result.current.transcript?.ia_ativa).toBe(true);
  });

  it("se o backend recusa a pausa, o estado não muda", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse([CONVERSA]))
      .mockResolvedValueOnce(jsonResponse(TRANSCRICAO))
      .mockResolvedValueOnce(jsonResponse({ detail: "Conversation not found" }, 404));

    const { result } = renderHook(() => useConversations("agent-1"));
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    await act(async () => {
      await result.current.openConversation("conv-1");
    });
    await act(async () => {
      await result.current.togglePause();
    });

    // Sem atualização otimista: mostrar "assumido" sem confirmação faria o
    // operador escrever achando que a IA parou.
    expect(result.current.transcript?.ia_ativa).toBe(true);
    expect(result.current.error).toBe("Conversation not found");
  });

  it("guarda o erro quando a fila não carrega", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "Agent not found" }, 404));

    const { result } = renderHook(() => useConversations("agent-1"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBe("Agent not found");
    expect(result.current.conversations).toEqual([]);
  });
});

describe("ConversationsPanel", () => {
  it("lista os atendimentos com nome do lead e prévia da última mensagem", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse([CONVERSA, PAUSADA]));

    render(<ConversationsPanel agentId="agent-1" />);

    expect(await screen.findByText("Maria Silva")).toBeInTheDocument();
    expect(screen.getByText("João Souza")).toBeInTheDocument();
    expect(
      screen.getAllByText(/Claro! Me conta o que você precisa/).length,
    ).toBeGreaterThan(0);
  });

  it("mostra por escrito quem está respondendo, não só pela cor", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse([PAUSADA]));

    render(<ConversationsPanel agentId="agent-1" />);

    expect(await screen.findByText("Humano assumiu")).toBeInTheDocument();
  });

  it("abrir um atendimento mostra a conversa e o botão de assumir", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse([CONVERSA]))
      .mockResolvedValueOnce(jsonResponse(TRANSCRICAO));

    render(<ConversationsPanel agentId="agent-1" />);
    await userEvent.click(await screen.findByText("Maria Silva"));

    expect(await screen.findByText("Olá, queria saber mais.")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Assumir conversa" }),
    ).toBeInTheDocument();
  });

  it("assumir troca o botão para devolver e avisa que a IA parou", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse([CONVERSA]))
      .mockResolvedValueOnce(jsonResponse(TRANSCRICAO))
      .mockResolvedValueOnce(
        jsonResponse({ conversation_id: "conv-1", status: "pausada", ia_ativa: false }),
      );

    render(<ConversationsPanel agentId="agent-1" />);
    await userEvent.click(await screen.findByText("Maria Silva"));
    await userEvent.click(await screen.findByRole("button", { name: "Assumir conversa" }));

    expect(
      await screen.findByRole("button", { name: "Devolver para a IA" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/A IA parou de responder/)).toBeInTheDocument();
  });

  it("avisa quando ainda não há atendimentos", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse([]));

    render(<ConversationsPanel agentId="agent-1" />);

    expect(await screen.findByText("Nenhum atendimento ainda")).toBeInTheDocument();
  });

  it("mostra erro e botão de tentar de novo quando a fila falha", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "Agent not found" }, 404));

    render(<ConversationsPanel agentId="agent-1" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Agent not found");
    expect(
      screen.getByRole("button", { name: "Tentar novamente" }),
    ).toBeInTheDocument();
  });
});


describe("Parecer preliminar", () => {
  function abrirConversaCom(analise: string | null) {
    // Duas respostas em sequência: a lista de conversas e a transcrição da
    // que for aberta — é assim que o painel busca.
    mockFetch.mockResolvedValueOnce(jsonResponse([CONVERSA]));
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ ...TRANSCRICAO, analise_preliminar: analise }),
    );
    render(<ConversationsPanel agentId="agent-1" />);
  }

  it("não aparece quando a conversa não tem análise", async () => {
    abrirConversaCom(null);

    await userEvent.click(await screen.findByText("Maria Silva"));

    await waitFor(() =>
      expect(screen.getByText("Olá, queria saber mais.")).toBeInTheDocument(),
    );
    expect(
      screen.queryByText("Análise preliminar do caso"),
    ).not.toBeInTheDocument();
  });

  it("vem fechado, e o conteúdo só aparece depois de abrir", async () => {
    abrirConversaCom(
      "## Resumo\nCliente relata demissão por justa causa.\n\n## Documentos a pedir\n- Atestados médicos",
    );

    await userEvent.click(await screen.findByText("Maria Silva"));

    const gatilho = await screen.findByText("Análise preliminar do caso");
    // Fechado: o cabeçalho existe, o conteúdo não. Quem abre a conversa quer
    // ler a conversa; o parecer é consulta.
    expect(screen.queryByText("Atestados médicos")).not.toBeInTheDocument();

    await userEvent.click(gatilho);

    expect(screen.getByText("Documentos a pedir")).toBeInTheDocument();
    expect(screen.getByText("Atestados médicos")).toBeInTheDocument();
  });

  it("deixa explícito que é interno e que o cliente não recebe", async () => {
    abrirConversaCom("## Resumo\nCaso trabalhista.");

    await userEvent.click(await screen.findByText("Maria Silva"));
    await userEvent.click(await screen.findByText("Análise preliminar do caso"));

    expect(screen.getByText("interno")).toBeInTheDocument();
    expect(screen.getByText(/o cliente nunca a recebe/i)).toBeInTheDocument();
  });
});

describe("Casos do contato", () => {
  const CASO_PROPRIO = {
    id: "caso-1",
    area: "trabalhista",
    resumo: "Cliente relata demissão por justa causa em maio.",
    titular: null,
    score_qualificacao: 90,
    valor_estimado_min: 22000,
    valor_estimado_max: 41500,
    viabilidade: "acima_do_piso",
    data_abertura: "2026-08-10T09:00:00Z",
    analise_preliminar: "## Resumo\nDemissão por justa causa.",
  };

  const CASO_DE_TERCEIRO = {
    id: "caso-2",
    area: "familia",
    resumo: "O contato pergunta pelo divórcio da irmã.",
    titular: "Marina Sales",
    score_qualificacao: 70,
    valor_estimado_min: null,
    valor_estimado_max: null,
    viabilidade: "indeterminado",
    data_abertura: "2026-08-12T09:00:00Z",
    analise_preliminar: "## Resumo\nDivórcio com dois filhos menores.",
  };

  function abrirConversaCom(casos: unknown[]) {
    mockFetch.mockResolvedValueOnce(jsonResponse([CONVERSA]));
    mockFetch.mockResolvedValueOnce(jsonResponse({ ...TRANSCRICAO, casos }));
    render(<ConversationsPanel agentId="agent-1" />);
  }

  it("lista os dois casos com a área de cada um", async () => {
    abrirConversaCom([CASO_DE_TERCEIRO, CASO_PROPRIO]);

    await userEvent.click(await screen.findByText("Maria Silva"));

    expect(await screen.findByText("Casos deste contato (2)")).toBeInTheDocument();
    expect(screen.getByText("Família")).toBeInTheDocument();
    expect(screen.getByText("Trabalhista")).toBeInTheDocument();
  });

  it("destaca quando a parte não é quem manda as mensagens", async () => {
    // É o erro que a separação entre contato e caso existe para evitar: abrir
    // o caso achando que é do titular do WhatsApp.
    abrirConversaCom([CASO_DE_TERCEIRO]);

    await userEvent.click(await screen.findByText("Maria Silva"));

    expect(await screen.findByText("de Marina Sales")).toBeInTheDocument();
  });

  it("mostra a faixa estimada no caso dimensionado", async () => {
    // A faixa aparece junto do veredito, e não o veredito sozinho: "abaixo do
    // piso" sem número é uma etiqueta que ninguém consegue contestar — e
    // contestar é o trabalho de quem lê.
    abrirConversaCom([CASO_PROPRIO]);

    await userEvent.click(await screen.findByText("Maria Silva"));

    expect(await screen.findByText(/R\$\s?22\.000.*R\$\s?41\.500/)).toBeInTheDocument();
  });

  it("caso ainda não dimensionado não ganha tarja nenhuma", async () => {
    // `indeterminado` é o estado normal de quem acabou de chegar. Uma tarja em
    // todo card não informa nada, e sugeriria um veredito que não existe.
    abrirConversaCom([CASO_DE_TERCEIRO]);

    await userEvent.click(await screen.findByText("Maria Silva"));
    await screen.findByText("Família");

    expect(screen.queryByText(/piso/)).not.toBeInTheDocument();
  });

  it("marca o caso abaixo do piso do escritório", async () => {
    abrirConversaCom([
      {
        ...CASO_PROPRIO,
        valor_estimado_min: 400,
        valor_estimado_max: 3500,
        viabilidade: "abaixo_do_piso",
      },
    ]);

    await userEvent.click(await screen.findByText("Maria Silva"));

    const tarja = await screen.findByText(/R\$\s?400.*R\$\s?3\.500/);
    // O texto explica que é estimativa preliminar: sem isso a tarja vira
    // veredito, e ela é só um alerta para o advogado conferir.
    expect(tarja).toHaveAttribute("title", expect.stringContaining("sem documentos"));
  });

  it("o parecer de cada caso só abre quando o caso é aberto", async () => {
    abrirConversaCom([CASO_PROPRIO]);

    await userEvent.click(await screen.findByText("Maria Silva"));

    expect(
      screen.queryByText("Análise preliminar do caso"),
    ).not.toBeInTheDocument();

    await userEvent.click(await screen.findByText("Trabalhista"));

    expect(screen.getByText("Análise preliminar do caso")).toBeInTheDocument();
  });

  it("sem casos, cai no parecer antigo do contato", async () => {
    // Contatos qualificados antes da separação não têm caso arquivado, e o
    // parecer deles não pode sumir da tela por causa disso.
    mockFetch.mockResolvedValueOnce(jsonResponse([CONVERSA]));
    mockFetch.mockResolvedValueOnce(
      jsonResponse({
        ...TRANSCRICAO,
        casos: [],
        analise_preliminar: "## Resumo\nCaso antigo, sem ficha.",
      }),
    );
    render(<ConversationsPanel agentId="agent-1" />);

    await userEvent.click(await screen.findByText("Maria Silva"));

    expect(
      await screen.findByText("Análise preliminar do caso"),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Casos deste contato/)).not.toBeInTheDocument();
  });
});
