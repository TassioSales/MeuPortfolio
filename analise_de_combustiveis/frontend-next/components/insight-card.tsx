"use client";

import { motion } from "framer-motion";
import { Bot, Sparkles } from "lucide-react";

import { Card } from "@/components/ui/card";
import { InsightPayload } from "@/lib/types";

export function InsightCard({ insight }: { insight: InsightPayload | null }) {
  return (
    <Card className="overflow-hidden">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
      >
        <div className="flex flex-wrap items-center gap-3">
          <p className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/8 px-3 py-1 text-xs uppercase tracking-[0.35em] text-accent">
            <Bot className="h-3.5 w-3.5" />
            Insight Engine
          </p>
          <p className="inline-flex items-center gap-2 rounded-full bg-white/[0.05] px-3 py-1 text-xs text-mist">
            <Sparkles className="h-3.5 w-3.5 text-amber" />
            {insight?.source === "mistral" ? "Narrativa Mistral" : "Narrativa de fallback"}
          </p>
        </div>
        <h3 className="mt-4 font-display text-2xl">{insight?.title ?? "Carregando..."}</h3>
        <p className="mt-4 text-sm leading-7 text-mist">{insight?.summary}</p>
        <div className="mt-5 space-y-2">
          {insight?.bullets?.map((bullet) => (
            <div key={bullet} className="rounded-2xl border border-white/8 bg-white/[0.04] px-4 py-3 text-sm text-white/90">
              {bullet}
            </div>
          ))}
        </div>
      </motion.div>
    </Card>
  );
}
