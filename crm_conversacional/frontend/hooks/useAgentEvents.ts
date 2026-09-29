"use client";

import { useEffect, useRef, useState } from "react";
import { getStoredToken } from "@/lib/tokens";
import { API_URL } from "@/lib/api";

/** Nomes definidos em `backend/app/ws/manager.py` — mudar exige mudar os dois lados. */
export type AgentEvent =
  | { type: "lead_moved"; lead_id: string; column_id: string; status_funil: string }
  | { type: "new_message"; conversation_id: string; phone_number: string };

/** ws:// para http://, wss:// para https://. */
function websocketUrl(agentId: string, token: string): string {
  const base = API_URL.replace(/^http/, "ws");
  return `${base}/ws/agents/${agentId}?token=${encodeURIComponent(token)}`;
}

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

/**
 * Escuta os eventos de um agente.
 *
 * O `onEvent` é guardado em ref para que trocar o callback não derrube e
 * reabra o socket a cada render.
 */
export function useAgentEvents(
  agentId: string | null,
  onEvent: (event: AgentEvent) => void,
) {
  const [isConnected, setIsConnected] = useState(false);
  const callbackRef = useRef(onEvent);
  callbackRef.current = onEvent;

  useEffect(() => {
    if (!agentId) return;

    const token = getStoredToken();
    if (!token) return;

    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;
    let cancelled = false;

    function connect() {
      if (cancelled) return;

      socket = new WebSocket(websocketUrl(agentId!, token!));

      socket.onopen = () => {
        attempt = 0;
        setIsConnected(true);
      };

      socket.onmessage = (message) => {
        try {
          callbackRef.current(JSON.parse(message.data) as AgentEvent);
        } catch {
          // Frame malformado não pode derrubar a página.
        }
      };

      socket.onclose = (event) => {
        setIsConnected(false);
        if (cancelled) return;

        // 1008 é recusa de autorização: reconectar só repetiria a recusa.
        if (event.code === 1008) return;

        // Backoff exponencial com teto, para não martelar o servidor.
        const delay = Math.min(RECONNECT_BASE_MS * 2 ** attempt, RECONNECT_MAX_MS);
        attempt += 1;
        reconnectTimer = setTimeout(connect, delay);
      };

      socket.onerror = () => {
        // O `onclose` sempre vem em seguida e cuida da reconexão.
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
      setIsConnected(false);
    };
  }, [agentId]);

  return { isConnected };
}
