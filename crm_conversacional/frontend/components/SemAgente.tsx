"use client";

import Link from "next/link";
import { EmptyState } from "./EmptyState";
import { useAuth } from "@/hooks/useAuth";

/**
 * A tela de quem chegou e não há agente configurado.
 *
 * O texto muda com o papel, e não é firula. A versão única dizia "Crie um para
 * começar" com um botão "Ir para Agentes" — e o operador não pode criar agente
 * nem abrir aquela tela: o backend responde 404 nela. Era um convite para uma
 * porta trancada, dado justamente a quem não tem a chave.
 *
 * Para o operador, a informação útil é outra: não é ele que resolve, e ele
 * precisa saber a quem pedir.
 */
export function SemAgente({
  icone,
  titulo,
  paraOAdmin,
}: {
  icone: string;
  titulo: string;
  /** O que o administrador lê — ele é quem pode agir. */
  paraOAdmin: string;
}) {
  const { user } = useAuth();
  const eAdmin = user?.papel === "admin";

  if (!eAdmin) {
    return (
      <EmptyState
        icon={icone}
        title={titulo}
        description="O escritório ainda não configurou o agente que atende no WhatsApp. Peça isso a um administrador — assim que ele existir, os atendimentos aparecem aqui."
      />
    );
  }

  return (
    <EmptyState
      icon={icone}
      title={titulo}
      description={paraOAdmin}
      action={
        <Link
          href="/dashboard/agents"
          className="rounded-lg bg-ink-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-ink-800 dark:bg-ink-100 dark:text-ink-950 dark:hover:bg-white"
        >
          Ir para Agentes
        </Link>
      }
    />
  );
}

export default SemAgente;
