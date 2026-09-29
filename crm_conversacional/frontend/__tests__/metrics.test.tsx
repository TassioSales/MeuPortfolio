/**
 * Testes das métricas: camada de API, hook e renderização dos gráficos.
 */
import { render, screen, waitFor, renderHook } from "@testing-library/react";
import * as metricsApi from "@/lib/metrics";
import { useMetrics } from "@/hooks/useMetrics";
import { FunilChart } from "@/components/charts/FunilChart";
import { StatTile } from "@/components/charts/StatTile";
import { formatSeconds, formatDayShort } from "@/components/charts/theme";
import { setStoredToken, clearStoredTokens } from "@/lib/tokens";
import type { LeadDistribution } from "@/types";

const mockFetch = global.fetch as jest.Mock;

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

const DISTRIBUICAO: LeadDistribution = {
  novo: 4,
  em_qualificacao: 3,
  qualificado: 2,
  agendado: 1,
  arquivado: 0,
  total: 10,
};

const SUMMARY = {
  agent_id: "agent-1",
  periodo: "week",
  atendimentos_totais: 12,
  taxa_qualificacao: 20,
  tempo_medio_resposta_seg: 95,
  leads_por_status: DISTRIBUICAO,
  timestamp: "2026-08-11T00:00:00Z",
};

const RESPONSE_TIME = {
  tempo_medio_seg: 95,
  p50_seg: 60,
  p95_seg: 240,
  min_seg: 10,
  max_seg: 300,
  total_trocas: 40,
  timestamp: "2026-08-11T00:00:00Z",
};

const TIMESERIES = {
  agent_id: "agent-1",
  dias: 3,
  pontos: [
    { data: "2026-08-09", atendimentos: 2, leads_qualificados: 1 },
    { data: "2026-08-10", atendimentos: 5, leads_qualificados: 0 },
    { data: "2026-08-11", atendimentos: 5, leads_qualificados: 1 },
  ],
};

beforeEach(() => setStoredToken("token-abc"));
afterEach(() => clearStoredTokens());

describe("lib/metrics", () => {
  it("getSummary passa o período na query", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(SUMMARY));

    await metricsApi.getSummary("agent-1", "week");

    expect(mockFetch.mock.calls[0][0]).toContain(
      "/api/v1/agents/agent-1/metrics?period=week",
    );
  });

  it("getTimeseries passa a quantidade de dias", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(TIMESERIES));

    await metricsApi.getTimeseries("agent-1", 14);

    expect(mockFetch.mock.calls[0][0]).toContain("/metrics/timeseries?dias=14");
  });

  it("getResponseTime bate no endpoint de tempo de resposta", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(RESPONSE_TIME));

    await metricsApi.getResponseTime("agent-1", "day");

    expect(mockFetch.mock.calls[0][0]).toContain("/metrics/response-time?period=day");
  });
});

describe("useMetrics", () => {
  it("busca resumo, tempo de resposta e série em paralelo", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(SUMMARY))
      .mockResolvedValueOnce(jsonResponse(RESPONSE_TIME))
      .mockResolvedValueOnce(jsonResponse(TIMESERIES));

    const { result } = renderHook(() => useMetrics("agent-1", "week"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.summary?.atendimentos_totais).toBe(12);
    expect(result.current.responseTime?.p95_seg).toBe(240);
    expect(result.current.pontos).toHaveLength(3);
    expect(mockFetch).toHaveBeenCalledTimes(3);
  });

  it("guarda o erro quando alguma chamada falha", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse({ detail: "Agent not found" }, 404))
      .mockResolvedValueOnce(jsonResponse(RESPONSE_TIME))
      .mockResolvedValueOnce(jsonResponse(TIMESERIES));

    const { result } = renderHook(() => useMetrics("agent-1", "week"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBe("Agent not found");
  });

  it("o período escolhido define a janela da série", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(SUMMARY))
      .mockResolvedValueOnce(jsonResponse(RESPONSE_TIME))
      .mockResolvedValueOnce(jsonResponse(TIMESERIES));

    renderHook(() => useMetrics("agent-1", "month"));

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(3));
    const urlSerie = mockFetch.mock.calls.find((c) =>
      String(c[0]).includes("timeseries"),
    )![0];
    expect(urlSerie).toContain("dias=30");
  });
});

describe("FunilChart", () => {
  it("mostra cada etapa com o número, não só a barra", () => {
    render(<FunilChart distribuicao={DISTRIBUICAO} />);

    // O valor em texto garante que a leitura não depende de cor.
    expect(screen.getByText("Novo lead")).toBeInTheDocument();
    expect(screen.getByLabelText("Novo lead: 4")).toBeInTheDocument();
    expect(screen.getByLabelText("Arquivado: 0")).toBeInTheDocument();
  });

  it("mostra o total no subtítulo", () => {
    render(<FunilChart distribuicao={DISTRIBUICAO} />);

    expect(screen.getByText(/10 leads no total/)).toBeInTheDocument();
  });

  it("aguenta o funil vazio sem dividir por zero", () => {
    const vazio: LeadDistribution = {
      novo: 0,
      em_qualificacao: 0,
      qualificado: 0,
      agendado: 0,
      arquivado: 0,
      total: 0,
    };

    render(<FunilChart distribuicao={vazio} />);

    expect(screen.getByText(/0 leads no total/)).toBeInTheDocument();
  });
});

describe("StatTile", () => {
  it("mostra rótulo, valor e contexto", () => {
    render(<StatTile label="Atendimentos" value="12" hint="no período" />);

    expect(screen.getByText("Atendimentos")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("no período")).toBeInTheDocument();
  });

  it("acompanha a variação de um ícone, não só da cor", () => {
    render(<StatTile label="Taxa" value="20%" delta={5.2} />);

    expect(screen.getByText("▲")).toBeInTheDocument();
    expect(screen.getByText("5.2%")).toBeInTheDocument();
  });

  it("em métricas onde cair é bom, a queda é o resultado positivo", () => {
    const { container } = render(
      <StatTile label="Tempo" value="1.5min" delta={-10} lowerIsBetter />,
    );

    expect(screen.getByText("▼")).toBeInTheDocument();
    expect(container.querySelector(".text-green-700")).toBeInTheDocument();
  });
});

describe("formatação", () => {
  it("formata segundos em unidade legível", () => {
    expect(formatSeconds(45)).toBe("45s");
    expect(formatSeconds(95)).toBe("1.6min");
    expect(formatSeconds(4800)).toBe("1h20");
  });

  it("trata ausência de dado sem mostrar 0s", () => {
    expect(formatSeconds(0)).toBe("—");
    expect(formatSeconds(NaN)).toBe("—");
  });

  it("encurta a data para o eixo", () => {
    expect(formatDayShort("2026-08-11")).toBe("11/08");
  });
});
