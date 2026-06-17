"use client";

import { useState, useEffect, useCallback } from "react";
import ClicksChart from "@/components/ClicksChart";
import { listURLs, getStats, type ShortURL, type DailyStat } from "@/lib/api";

export default function DashboardPage() {
  const [urls, setUrls] = useState<ShortURL[]>([]);
  const [selected, setSelected] = useState<ShortURL | null>(null);
  const [stats, setStats] = useState<DailyStat[]>([]);
  const [loadingURLs, setLoadingURLs] = useState(true);
  const [loadingStats, setLoadingStats] = useState(false);

  const fetchURLs = useCallback(async () => {
    try {
      const data = await listURLs();
      setUrls(data);
    } catch {
      // ignore
    } finally {
      setLoadingURLs(false);
    }
  }, []);

  useEffect(() => {
    fetchURLs();
  }, [fetchURLs]);

  const handleSelect = async (url: ShortURL) => {
    setSelected(url);
    setLoadingStats(true);
    try {
      const data = await getStats(url.short_code);
      setStats(data);
    } catch {
      setStats([]);
    } finally {
      setLoadingStats(false);
    }
  };

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold text-[#c9d1d9]">Dashboard</h1>

      <div className="rounded-lg border border-[#30363d] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[#161b22] text-[#8b949e] text-left">
            <tr>
              <th className="px-4 py-3 font-medium">Código</th>
              <th className="px-4 py-3 font-medium">URL Original</th>
              <th className="px-4 py-3 font-medium text-right">Cliques</th>
              <th className="px-4 py-3 font-medium">Criado em</th>
            </tr>
          </thead>
          <tbody>
            {loadingURLs ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-[#8b949e]">
                  Carregando...
                </td>
              </tr>
            ) : urls.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-[#8b949e]">
                  Nenhum link encontrado.
                </td>
              </tr>
            ) : (
              urls.map((url) => (
                <tr
                  key={url.short_code}
                  onClick={() => handleSelect(url)}
                  className={`border-t border-[#30363d] cursor-pointer transition-colors hover:bg-[#161b22] ${
                    selected?.short_code === url.short_code
                      ? "bg-[#1f2937]"
                      : "bg-[#0d1117]"
                  }`}
                >
                  <td className="px-4 py-3 font-mono text-[#58a6ff]">
                    {url.short_code}
                  </td>
                  <td className="px-4 py-3 text-[#c9d1d9] max-w-xs truncate">
                    {url.original_url}
                  </td>
                  <td className="px-4 py-3 text-right text-[#c9d1d9]">
                    {url.click_count}
                  </td>
                  <td className="px-4 py-3 text-[#8b949e]">
                    {new Date(url.created_at).toLocaleDateString("pt-BR")}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-[#c9d1d9]">
            Cliques — <span className="text-[#58a6ff]">{selected.short_code}</span>
            <span className="ml-2 text-sm text-[#8b949e] font-normal">
              últimos 30 dias
            </span>
          </h2>
          {loadingStats ? (
            <p className="text-[#8b949e]">Carregando estatísticas...</p>
          ) : (
            <ClicksChart data={stats} />
          )}
        </div>
      )}
    </div>
  );
}
