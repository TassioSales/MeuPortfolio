"use client";

import { create } from "zustand";
import * as agentsApi from "@/lib/agents";
import { ApiError } from "@/lib/api";
import type { Agent, AgentInput, AgentUpdateInput } from "@/types";

interface AgentsState {
  agents: Agent[];
  isLoading: boolean;
  /** Erro de carregamento da lista (erros de formulário ficam no próprio form). */
  error: string | null;

  fetchAgents: () => Promise<void>;
  createAgent: (data: AgentInput) => Promise<Agent>;
  updateAgent: (agentId: string, data: AgentUpdateInput) => Promise<Agent>;
  removeAgent: (agentId: string) => Promise<void>;
}

export function messageFrom(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return fallback;
}

export const useAgentsStore = create<AgentsState>((set) => ({
  agents: [],
  isLoading: true,
  error: null,

  fetchAgents: async () => {
    set({ isLoading: true, error: null });
    try {
      const agents = await agentsApi.listAgents();
      set({ agents, isLoading: false });
    } catch (error) {
      set({
        isLoading: false,
        error: messageFrom(error, "Não foi possível carregar os agentes."),
      });
    }
  },

  createAgent: async (data) => {
    const agent = await agentsApi.createAgent(data);
    // Insere no topo: o mais recente é o que o usuário acabou de criar.
    set((state) => ({ agents: [agent, ...state.agents] }));
    return agent;
  },

  updateAgent: async (agentId, data) => {
    const updated = await agentsApi.updateAgent(agentId, data);
    set((state) => ({
      agents: state.agents.map((agent) => (agent.id === agentId ? updated : agent)),
    }));
    return updated;
  },

  removeAgent: async (agentId) => {
    await agentsApi.deleteAgent(agentId);
    set((state) => ({ agents: state.agents.filter((agent) => agent.id !== agentId) }));
  },
}));

export function useAgents() {
  return useAgentsStore();
}
