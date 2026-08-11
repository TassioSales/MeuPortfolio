"use client";

import { useEffect } from "react";
import { Button } from "@/components/Button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Erro não tratado na UI:", error);
  }, [error]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-center">
      <span aria-hidden="true" className="text-4xl">
        ⚠️
      </span>
      <h1 className="text-xl font-semibold text-gray-900">Algo deu errado</h1>
      <p className="max-w-sm text-sm text-gray-600">
        {error.message || "Ocorreu um erro inesperado ao renderizar a página."}
      </p>
      <Button onClick={reset}>Tentar novamente</Button>
    </main>
  );
}
