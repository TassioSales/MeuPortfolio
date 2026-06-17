"use client";

import { useState } from "react";
import type { ShortURL } from "@/lib/api";

interface Props {
  url: ShortURL;
}

const SHORT_BASE =
  typeof window !== "undefined"
    ? window.location.origin
    : "http://localhost:3000";

export default function URLCard({ url }: Props) {
  const [copied, setCopied] = useState(false);
  const shortURL = `${SHORT_BASE}/r/${url.short_code}`;

  const handleCopy = () => {
    navigator.clipboard.writeText(shortURL).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-lg px-4 py-3 flex items-center gap-4">
      <div className="flex-1 min-w-0">
        <a
          href={shortURL}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#58a6ff] hover:text-[#79b8ff] text-sm font-mono"
        >
          /r/{url.short_code}
        </a>
        <p className="text-[#8b949e] text-xs truncate mt-0.5">{url.original_url}</p>
      </div>

      <span className="text-[#8b949e] text-xs whitespace-nowrap">
        {url.click_count} clique{url.click_count !== 1 ? "s" : ""}
      </span>

      <button
        onClick={handleCopy}
        className="text-xs text-[#8b949e] hover:text-[#c9d1d9] border border-[#30363d]
                   hover:border-[#58a6ff] rounded px-3 py-1 transition-colors whitespace-nowrap"
      >
        {copied ? "Copiado!" : "Copiar"}
      </button>
    </div>
  );
}
