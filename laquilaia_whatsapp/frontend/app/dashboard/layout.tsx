"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import { FullPageLoader } from "@/components/LoadingSpinner";
import { useAuth } from "@/hooks/useAuth";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, isLoading, loadSession } = useAuth();

  // O middleware só confere se o cookie existe; aqui o backend valida o token.
  useEffect(() => {
    void loadSession();
  }, [loadSession]);

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

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
