"use client";

import { useCallback, useEffect, useState } from "react";
import * as metricsApi from "@/lib/metrics";
import { messageFrom } from "./useAgents";
import type {
  MetricsPeriod,
  MetricsSummary,
  ResponseTimeMetrics,
  TimeseriesPoint,
} from "@/types";

/** Quantos dias a série cobre para cada período do seletor. */
const DIAS_POR_PERIODO: Record<MetricsPeriod, number> = {
  day: 7,
  week: 14,
  month: 30,
};

export function useMetrics(agentId: string, period: MetricsPeriod) {
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [responseTime, setResponseTime] = useState<ResponseTimeMetrics | null>(null);
  const [pontos, setPontos] = useState<TimeseriesPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // As três chamadas são independentes: em paralelo, não em sequência.
      const [resumo, tempo, serie] = await Promise.all([
        metricsApi.getSummary(agentId, period),
        metricsApi.getResponseTime(agentId, period),
        metricsApi.getTimeseries(agentId, DIAS_POR_PERIODO[period]),
      ]);
      setSummary(resumo);
      setResponseTime(tempo);
      setPontos(serie.pontos);
    } catch (err) {
      setError(messageFrom(err, "Não foi possível carregar as métricas."));
    } finally {
      setIsLoading(false);
    }
  }, [agentId, period]);

  useEffect(() => {
    void load();
  }, [load]);

  return { summary, responseTime, pontos, isLoading, error, reload: load };
}
