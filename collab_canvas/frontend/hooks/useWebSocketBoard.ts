"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ConnectionStatus, ServerMessage } from "@/types/board";

const DEFAULT_SIZE = 100;
const LOCAL_COOLDOWN_MS = 3000;

function createEmptyBoard(size = DEFAULT_SIZE) {
  return Array.from({ length: size }, () => Array.from({ length: size }, () => "#ffffff"));
}

function getWebSocketUrl() {
  if (process.env.NEXT_PUBLIC_WS_URL) {
    return process.env.NEXT_PUBLIC_WS_URL;
  }

  if (typeof window === "undefined") {
    return "ws://localhost:8080/ws";
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.hostname}:8080/ws`;
}

export function useWebSocketBoard() {
  const [pixels, setPixels] = useState<string[][]>(() => createEmptyBoard());
  const [width, setWidth] = useState(DEFAULT_SIZE);
  const [height, setHeight] = useState(DEFAULT_SIZE);
  const [users, setUsers] = useState(0);
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [cooldownUntil, setCooldownUntil] = useState(0);
  const [lastError, setLastError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptRef = useRef(0);

  const wsUrl = useMemo(getWebSocketUrl, []);

  const applyDraw = useCallback((x: number, y: number, color: string) => {
    setPixels((current) => {
      if (!current[y] || current[y][x] === undefined) {
        return current;
      }

      const next = current.map((row) => [...row]);
      next[y][x] = color;
      return next;
    });
  }, []);

  useEffect(() => {
    let disposed = false;

    const connect = () => {
      setStatus("connecting");
      const socket = new WebSocket(wsUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        reconnectAttemptRef.current = 0;
        setStatus("online");
        setLastError(null);
      };

      socket.onmessage = (event) => {
        const message = JSON.parse(event.data) as ServerMessage;

        if (message.type === "init") {
          setWidth(message.width);
          setHeight(message.height);
          setPixels(message.pixels);
          setUsers(message.users ?? 0);
          return;
        }

        if (message.type === "presence") {
          setUsers(message.users);
          return;
        }

        if (message.type === "draw") {
          applyDraw(message.payload.x, message.payload.y, message.payload.color);
          return;
        }

        if (message.type === "cooldown") {
          setCooldownUntil(Date.now() + message.retryAfterMs);
          return;
        }

        if (message.type === "error") {
          setLastError(message.payload.message);
        }
      };

      socket.onclose = () => {
        if (disposed) {
          return;
        }

        setStatus("offline");
        reconnectAttemptRef.current += 1;
        const delay = Math.min(4000, 500 * reconnectAttemptRef.current);
        reconnectTimerRef.current = setTimeout(connect, delay);
      };

      socket.onerror = () => {
        setLastError("Connection error");
        socket.close();
      };
    };

    connect();

    return () => {
      disposed = true;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      socketRef.current?.close();
    };
  }, [applyDraw, wsUrl]);

  const sendDraw = useCallback((x: number, y: number, color: string) => {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setLastError("Board is offline");
      return false;
    }

    const now = Date.now();
    if (cooldownUntil > now) {
      return false;
    }

    socket.send(JSON.stringify({ action: "draw", x, y, color }));
    setCooldownUntil(now + LOCAL_COOLDOWN_MS);
    return true;
  }, [cooldownUntil]);

  return {
    pixels,
    width,
    height,
    users,
    status,
    cooldownUntil,
    lastError,
    sendDraw,
  };
}
