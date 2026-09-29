import { api } from "./api";
import type {
  MetricsPeriod,
  MetricsSummary,
  ResponseTimeMetrics,
  TimeseriesResponse,
} from "@/types";

/** Endpoints de `backend/app/routers/metrics.py`. */
function metricsPath(agentId: string): string {
  return `/api/v1/agents/${agentId}/metrics`;
}

export async function getSummary(
  agentId: string,
  period: MetricsPeriod,
): Promise<MetricsSummary> {
  return api.get<MetricsSummary>(`${metricsPath(agentId)}?period=${period}`);
}

/**
 * Série diária de atendimentos e leads qualificados.
 *
 * A janela vem em dias, e não como período nomeado, porque o gráfico precisa
 * de mais pontos do que o resumo: "day" no seletor ainda mostra a última
 * semana.
 */
export async function getTimeseries(
  agentId: string,
  dias: number,
): Promise<TimeseriesResponse> {
  return api.get<TimeseriesResponse>(`${metricsPath(agentId)}/timeseries?dias=${dias}`);
}

export async function getResponseTime(
  agentId: string,
  period: MetricsPeriod,
): Promise<ResponseTimeMetrics> {
  return api.get<ResponseTimeMetrics>(
    `${metricsPath(agentId)}/response-time?period=${period}`,
  );
}
