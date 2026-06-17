"use client";

import { useState } from "react";
import { shortenURL, type ShortenResponse } from "@/lib/api";

interface Props {
  onShortened?: () => void;
}

export default function ShortenForm({ onShortened }: Props) {
  const [input, setInput] = useState("");
  const [result, setResult] = useState<ShortenResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setCopied(false);

    const trimmed = input.trim();
    if (!trimmed) return;

    setLoading(true);
    try {
      const data = await shortenURL(trimmed);
      setResult(data);
      setInput("");
      onShortened?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (!result) return;
    navigator.clipboard.writeText(result.short_url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6 space-y-4">
      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          type="url"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="https://exemplo.com/url-muito-longa"
          required
          className="flex-1 bg-[#0d1117] border border-[#30363d] rounded-lg px-4 py-2.5
                     text-[#c9d1d9] placeholder-[#8b949e] text-sm
                     focus:outline-none focus:border-[#58a6ff] transition-colors"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-[#238636] hover:bg-[#2ea043] disabled:opacity-50
                     text-white text-sm font-medium px-5 py-2.5 rounded-lg
                     transition-colors whitespace-nowrap"
        >
          {loading ? "Encurtando..." : "Encurtar"}
        </button>
      </form>

      {error && (
        <p className="text-red-400 text-sm">{error}</p>
      )}

      {result && (
        <div className="flex items-center gap-3 bg-[#0d1117] border border-[#30363d] rounded-lg px-4 py-3">
          <a
            href={result.short_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 text-[#58a6ff] hover:text-[#79b8ff] text-sm font-mono truncate"
          >
            {result.short_url}
          </a>
          <button
            onClick={handleCopy}
            className="text-xs text-[#8b949e] hover:text-[#c9d1d9] border border-[#30363d]
                       hover:border-[#58a6ff] rounded px-3 py-1 transition-colors whitespace-nowrap"
          >
            {copied ? "Copiado!" : "Copiar"}
          </button>
        </div>
      )}
    </div>
  );
}
