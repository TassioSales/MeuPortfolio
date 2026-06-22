"use client";

import { useEffect, useRef, useState } from "react";
import type { GraphData } from "./types";

/**
 * useGraphSocket connects to the Go API WebSocket endpoint and returns
 * the latest GraphData broadcast. Re-connects automatically on disconnect.
 */
export function useGraphSocket(url: string): GraphData | null {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmounted = useRef(false);

  useEffect(() => {
    unmounted.current = false;

    function connect() {
      if (unmounted.current) return;

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("[MemMap WS] connected");
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data as string) as GraphData;
          setGraphData(data);
        } catch (err) {
          console.error("[MemMap WS] parse error", err);
        }
      };

      ws.onerror = (err) => {
        console.error("[MemMap WS] error", err);
      };

      ws.onclose = () => {
        if (!unmounted.current) {
          console.log("[MemMap WS] disconnected — reconnecting in 3s");
          reconnectTimer.current = setTimeout(connect, 3000);
        }
      };
    }

    connect();

    return () => {
      unmounted.current = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [url]);

  return graphData;
}
