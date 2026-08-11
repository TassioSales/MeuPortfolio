/**
 * Testes da camada de agentes (lib/agents + store useAgentsStore).
 */
import * as agentsApi from "@/lib/agents";
import { useAgentsStore } from "@/hooks/useAgents";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";
import type { Agent } from "@/types";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

const AGENT: Agent = {
  id: "agent-1",
  user_id: "user-1",
  nome: "Qualificador",
  descricao: "Qualifica leads no WhatsApp",
  system_prompt: "Você é um assistente...",
  temperatura: 0.7,
  max_tokens: 1024,
  status: "ativo",
  data_criacao: "2026-08-11T00:00:00Z",
  data_atualizacao: "2026-08-11T00:00:00Z",
};

const AGENT_INPUT = {
  nome: "Qualificador",
  descricao: "Qualifica leads no WhatsApp",
  system_prompt: "Você é um assistente...",
  temperatura: 0.7,
  max_tokens: 1024,
};

describe("lib/agents", () => {
  beforeEach(() => setStoredToken("token-abc"));
  afterEach(() => clearStoredTokens());

  it("listAgents chama GET /api/v1/agents", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse([AGENT]));

    const agents = await agentsApi.listAgents();

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/agents");
    expect(init.method).toBe("GET");
    expect(agents).toEqual([AGENT]);
  });

  it("createAgent envia o corpo esperado pelo schema AgentCreate", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(AGENT, 201));

    await agentsApi.createAgent(AGENT_INPUT);

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/agents");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual(AGENT_INPUT);
  });

  it("updateAgent usa PUT no id do agente", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ ...AGENT, nome: "Novo nome" }));

    await agentsApi.updateAgent("agent-1", { nome: "Novo nome" });

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/agents/agent-1");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body)).toEqual({ nome: "Novo nome" });
  });

  it("deleteAgent usa DELETE no id do agente", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "deleted" }));

    await agentsApi.deleteAgent("agent-1");

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/agents/agent-1");
    expect(init.method).toBe("DELETE");
  });
});

describe("useAgentsStore", () => {
  beforeEach(() => {
    setStoredToken("token-abc");
    useAgentsStore.setState({ agents: [], isLoading: true, error: null });
  });
  afterEach(() => clearStoredTokens());

  it("fetchAgents popula a lista e desliga o loading", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse([AGENT]));

    await useAgentsStore.getState().fetchAgents();

    const state = useAgentsStore.getState();
    expect(state.agents).toEqual([AGENT]);
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });

  it("fetchAgents guarda a mensagem do backend quando falha", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "Error listing agents" }, 500));

    await useAgentsStore.getState().fetchAgents();

    const state = useAgentsStore.getState();
    expect(state.error).toBe("Error listing agents");
    expect(state.isLoading).toBe(false);
    expect(state.agents).toEqual([]);
  });

  it("createAgent insere o novo agente no topo da lista", async () => {
    const existente = { ...AGENT, id: "agent-0", nome: "Antigo" };
    useAgentsStore.setState({ agents: [existente], isLoading: false });
    mockFetch.mockResolvedValueOnce(jsonResponse(AGENT, 201));

    await useAgentsStore.getState().createAgent(AGENT_INPUT);

    expect(useAgentsStore.getState().agents.map((a) => a.id)).toEqual([
      "agent-1",
      "agent-0",
    ]);
  });

  it("createAgent propaga o erro sem alterar a lista", async () => {
    useAgentsStore.setState({ agents: [AGENT], isLoading: false });
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ detail: "System prompt cannot be empty" }, 400),
    );

    await expect(
      useAgentsStore.getState().createAgent({ ...AGENT_INPUT, system_prompt: "" }),
    ).rejects.toMatchObject({ message: "System prompt cannot be empty" });

    expect(useAgentsStore.getState().agents).toEqual([AGENT]);
  });

  it("updateAgent troca apenas o agente alvo", async () => {
    const outro = { ...AGENT, id: "agent-2", nome: "Outro" };
    useAgentsStore.setState({ agents: [AGENT, outro], isLoading: false });
    mockFetch.mockResolvedValueOnce(jsonResponse({ ...AGENT, nome: "Renomeado" }));

    await useAgentsStore.getState().updateAgent("agent-1", { nome: "Renomeado" });

    const agents = useAgentsStore.getState().agents;
    expect(agents[0].nome).toBe("Renomeado");
    expect(agents[1].nome).toBe("Outro");
  });

  it("removeAgent tira o agente da lista", async () => {
    const outro = { ...AGENT, id: "agent-2" };
    useAgentsStore.setState({ agents: [AGENT, outro], isLoading: false });
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "deleted" }));

    await useAgentsStore.getState().removeAgent("agent-1");

    expect(useAgentsStore.getState().agents.map((a) => a.id)).toEqual(["agent-2"]);
  });

  it("removeAgent mantém a lista intacta quando a API falha", async () => {
    useAgentsStore.setState({ agents: [AGENT], isLoading: false });
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "Agent not found" }, 404));

    await expect(useAgentsStore.getState().removeAgent("agent-1")).rejects.toMatchObject({
      status: 404,
    });

    expect(useAgentsStore.getState().agents).toEqual([AGENT]);
  });
});
