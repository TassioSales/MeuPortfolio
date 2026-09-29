import { api } from "./api";
import type { Agent, AgentInput, AgentUpdateInput } from "@/types";

/** Endpoints de `backend/app/routers/agents.py`. */
const AGENTS = "/api/v1/agents";

export async function listAgents(): Promise<Agent[]> {
  return api.get<Agent[]>(AGENTS);
}

export async function getAgent(agentId: string): Promise<Agent> {
  return api.get<Agent>(`${AGENTS}/${agentId}`);
}

export async function createAgent(data: AgentInput): Promise<Agent> {
  return api.post<Agent>(AGENTS, data);
}

export async function updateAgent(
  agentId: string,
  data: AgentUpdateInput,
): Promise<Agent> {
  return api.put<Agent>(`${AGENTS}/${agentId}`, data);
}

export async function deleteAgent(agentId: string): Promise<void> {
  await api.delete(`${AGENTS}/${agentId}`);
}
