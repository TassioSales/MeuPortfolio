"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/Button";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import { FullPageLoader } from "@/components/LoadingSpinner";
import { useAuth } from "@/hooks/useAuth";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, isLoading, servidorForaDoAr, loadSession } = useAuth();

  // O middleware só confere se o cookie existe; aqui o backend valida o token.
  useEffect(() => {
    void loadSession();
  }, [loadSession]);

  useEffect(() => {
    // Servidor fora do ar não é sessão encerrada: os cookies continuam
    // válidos, e mandar para o login faria o middleware devolver para cá —
    // pingue-pongue em vez de mensagem.
    if (!isLoading && !user && !servidorForaDoAr) router.replace("/login");
  }, [isLoading, user, servidorForaDoAr, router]);

  if (!isLoading && !user && servidorForaDoAr) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
        <h1 className="text-lg font-medium text-fg">
          Não foi possível falar com o servidor
        </h1>
        <p className="max-w-sm text-sm text-fg-muted">
          Sua sessão continua válida. Se o backend acabou de reiniciar, ele
          costuma levar alguns segundos para responder.
        </p>
        <Button onClick={() => void loadSession()}>Tentar de novo</Button>
      </div>
    );
  }

  if (isLoading || !user) {
    return <FullPageLoader label="Verificando sessão..." />;
  }

  // A lateral vai de topo a base, e a barra superior fica só sobre o conteúdo.
  // Na ordem inversa sobrava uma tira branca por cima da lateral escura, com a
  // marca começando abaixo dela — parece corte, não composição.
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Navbar />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
