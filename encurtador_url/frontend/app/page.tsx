"use client";

import { useState, useEffect, useCallback } from "react";
import ShortenForm from "@/components/ShortenForm";
import URLCard from "@/components/URLCard";
import { listURLs, type ShortURL } from "@/lib/api";

export default function HomePage() {
  const [urls, setUrls] = useState<ShortURL[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchURLs = useCallback(async () => {
    try {
      const data = await listURLs();
      setUrls(data);
    } catch {
      // API may not be running yet — silently ignore.
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchURLs();
  }, [fetchURLs]);

  return (
    <div className="space-y-10">
      {/* Hero */}
      <div className="text-center space-y-3">
        <h1 className="text-4xl font-bold text-[#c9d1d9]">
          Encurte seus links
        </h1>
        <p className="text-[#8b949e] text-lg">
          Cole uma URL longa e obtenha um link curto em segundos.
        </p>
      </div>

      {/* Shorten form */}
      <ShortenForm onShortened={fetchURLs} />

      {/* Recent URLs */}
      <section>
        <h2 className="text-xl font-semibold text-[#c9d1d9] mb-4">
          Links recentes
        </h2>
        {loading ? (
          <p className="text-[#8b949e]">Carregando...</p>
        ) : urls.length === 0 ? (
          <p className="text-[#8b949e]">Nenhum link criado ainda.</p>
        ) : (
          <div className="space-y-3">
            {urls.slice(0, 10).map((url) => (
              <URLCard key={url.short_code} url={url} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
