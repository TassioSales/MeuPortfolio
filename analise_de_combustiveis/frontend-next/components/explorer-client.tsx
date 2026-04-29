"use client";

import { useEffect, useState } from "react";
import { Database, Table2 } from "lucide-react";

import { Card } from "@/components/ui/card";
import { getExplorer } from "@/lib/api";
import { ExplorerPayload } from "@/lib/types";

export function ExplorerClient() {
  const [data, setData] = useState<ExplorerPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getExplorer()
      .then((payload) => {
        setData(payload);
        setError(null);
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

  return (
    <main className="space-y-6 pb-10">
      <Card className="bg-white/[0.04]">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-accent">Database Explorer</p>
            <h2 className="mt-3 font-display text-4xl">Warehouse local materializado</h2>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-mist">
              Inspecao rapida das tabelas `raw/staging/curated` e amostras de linhas do banco local.
            </p>
          </div>
          <div className="rounded-3xl border border-white/10 bg-black/10 p-4 text-right">
            <div className="flex items-center gap-2 text-mist">
              <Database className="h-4 w-4" />
              DuckDB
            </div>
            <p className="mt-2 text-sm text-white">{data?.warehouse_path ?? "Carregando..."}</p>
          </div>
        </div>
      </Card>

      {error ? <Card className="border-coral/50 text-coral">Falha ao carregar explorer: {error}</Card> : null}

      <section className="grid gap-6">
        {data?.tables.map((table) => (
          <Card key={table.table} className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="rounded-full bg-white/10 p-2">
                  <Table2 className="h-4 w-4 text-accent" />
                </span>
                <div>
                  <h3 className="font-display text-2xl">{table.table}</h3>
                  <p className="text-sm text-mist">{table.row_count.toLocaleString("pt-BR")} linhas</p>
                </div>
              </div>
            </div>
            <div className="overflow-auto rounded-2xl border border-white/10">
              <table className="min-w-full text-sm">
                <thead className="bg-white/[0.04] text-left text-mist">
                  <tr>
                    {Object.keys(table.sample_rows[0] ?? {}).map((key) => (
                      <th key={key} className="px-4 py-3 font-medium">
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {table.sample_rows.map((row, idx) => (
                    <tr key={idx} className="border-t border-white/5">
                      {Object.values(row).map((value, valueIdx) => (
                        <td key={valueIdx} className="px-4 py-3 text-white/90">
                          {value === null ? "-" : String(value)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        ))}
      </section>
    </main>
  );
}

