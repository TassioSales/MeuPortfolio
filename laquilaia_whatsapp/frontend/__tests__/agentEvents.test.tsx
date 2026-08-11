/**
 * Testes do canal de tempo real no cliente.
 */
import { renderHook, act, waitFor } from "@testing-library/react";
import { useAgentEvents, type AgentEvent } from "@/hooks/useAgentEvents";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";

/** WebSocket falso: o jsdom não implementa o de verdade. */
class FakeWebSocket {
  static instances: FakeWebSocket[] = [];

  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: ((e: { code: number }) => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  close() {
    this.closed = true;
  }

  // Auxiliares do teste
  simulateOpen() {
    this.onopen?.();
  }
  simulateMessage(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }
  simulateRawMessage(data: string) {
    this.onmessage?.({ data });
  }
  simulateClose(code = 1006) {
    this.onclose?.({ code });
  }
}

beforeEach(() => {
  FakeWebSocket.instances = [];
  (global as any).WebSocket = FakeWebSocket;
  setStoredToken("token-abc");
  jest.useFakeTimers();
});

afterEach(() => {
  jest.useRealTimers();
  clearStoredTokens();
});

describe("useAgentEvents", () => {
  it("conecta no canal do agente levando o token na query", () => {
    renderHook(() => useAgentEvents("agent-1", jest.fn()));

    const url = FakeWebSocket.instances[0].url;
    expect(url).toContain("/ws/agents/agent-1");
    // O navegador não deixa definir cabeçalhos ao abrir um WebSocket.
    expect(url).toContain("token=token-abc");
  });

  it("usa ws:// derivado da URL da API", () => {
    renderHook(() => useAgentEvents("agent-1", jest.fn()));

    expect(FakeWebSocket.instances[0].url.startsWith("ws://")).toBe(true);
  });

  it("não conecta sem agente selecionado", () => {
    renderHook(() => useAgentEvents(null, jest.fn()));

    expect(FakeWebSocket.instances).toHaveLength(0);
  });

  it("não conecta sem sessão", () => {
    clearStoredTokens();

    renderHook(() => useAgentEvents("agent-1", jest.fn()));

    expect(FakeWebSocket.instances).toHaveLength(0);
  });

  it("entrega o evento recebido ao callback", async () => {
    const onEvent = jest.fn();
    renderHook(() => useAgentEvents("agent-1", onEvent));

    act(() => {
      FakeWebSocket.instances[0].simulateOpen();
      FakeWebSocket.instances[0].simulateMessage({
        type: "lead_moved",
        lead_id: "lead-1",
        column_id: "col-2",
        status_funil: "qualificado",
      });
    });

    expect(onEvent).toHaveBeenCalledWith({
      type: "lead_moved",
      lead_id: "lead-1",
      column_id: "col-2",
      status_funil: "qualificado",
    });
  });

  it("marca conectado ao abrir e desconectado ao fechar", async () => {
    const { result } = renderHook(() => useAgentEvents("agent-1", jest.fn()));

    act(() => FakeWebSocket.instances[0].simulateOpen());
    await waitFor(() => expect(result.current.isConnected).toBe(true));

    act(() => FakeWebSocket.instances[0].simulateClose());
    await waitFor(() => expect(result.current.isConnected).toBe(false));
  });

  it("frame malformado não derruba a página", () => {
    const onEvent = jest.fn();
    renderHook(() => useAgentEvents("agent-1", onEvent));

    act(() => {
      FakeWebSocket.instances[0].simulateOpen();
      FakeWebSocket.instances[0].simulateRawMessage("isto não é json");
    });

    expect(onEvent).not.toHaveBeenCalled();
  });

  it("reconecta depois de uma queda", () => {
    renderHook(() => useAgentEvents("agent-1", jest.fn()));

    act(() => {
      FakeWebSocket.instances[0].simulateOpen();
      FakeWebSocket.instances[0].simulateClose(1006);
    });
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it("não reconecta quando a conexão foi recusada por autorização", () => {
    renderHook(() => useAgentEvents("agent-1", jest.fn()));

    // 1008 = policy violation: insistir só repetiria a recusa.
    act(() => FakeWebSocket.instances[0].simulateClose(1008));
    act(() => {
      jest.advanceTimersByTime(60000);
    });

    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it("espera cada vez mais entre tentativas", () => {
    renderHook(() => useAgentEvents("agent-1", jest.fn()));

    act(() => FakeWebSocket.instances[0].simulateClose(1006));
    act(() => jest.advanceTimersByTime(1000));
    expect(FakeWebSocket.instances).toHaveLength(2);

    act(() => FakeWebSocket.instances[1].simulateClose(1006));
    // A segunda espera é maior: 1s não basta para a terceira tentativa.
    act(() => jest.advanceTimersByTime(1000));
    expect(FakeWebSocket.instances).toHaveLength(2);

    act(() => jest.advanceTimersByTime(1000));
    expect(FakeWebSocket.instances).toHaveLength(3);
  });

  it("fecha o socket ao desmontar", () => {
    const { unmount } = renderHook(() => useAgentEvents("agent-1", jest.fn()));
    const socket = FakeWebSocket.instances[0];

    unmount();

    expect(socket.closed).toBe(true);
  });

  it("trocar o callback não reabre a conexão", () => {
    const { rerender } = renderHook<
      { isConnected: boolean },
      { cb: (event: AgentEvent) => void }
    >(({ cb }) => useAgentEvents("agent-1", cb), {
      initialProps: { cb: jest.fn() },
    });

    rerender({ cb: jest.fn() });

    expect(FakeWebSocket.instances).toHaveLength(1);
  });
});
