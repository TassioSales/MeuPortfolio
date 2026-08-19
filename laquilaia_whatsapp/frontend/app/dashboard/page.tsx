"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import {
  IconeAgente,
  IconeConversa,
  IconeClientes,
  IconeFunil,
  IconeMetricas,
  IconeTeste,
} from "@/components/icons";

interface QuickLink {
  href: string;
  title: string;
  description: string;
  Icone: (props: { className?: string }) => JSX.Element;
  available: boolean;
  /** Atalhos que levam a telas que o operador não abre (404 no backend). */
  soAdmin?: boolean;
}

const QUICK_LINKS: QuickLink[] = [
  {
    href: "/dashboard/agents",
    title: "Agentes",
    description: "O prompt da triagem e os limites do atendimento.",
    Icone: IconeAgente,
    available: true,
    soAdmin: true,
  },
  {
    href: "/dashboard/conversations",
    title: "Atendimentos",
    description: "As conversas em andamento e o parecer de cada caso.",
    Icone: IconeConversa,
    available: true,
  },
  {
    href: "/dashboard/chat-test",
    title: "Chat de teste",
    description: "Converse com o agente antes de soltá-lo no WhatsApp.",
    Icone: IconeTeste,
    available: true,
    soAdmin: true,
  },
  {
    href: "/dashboard/clientes",
    title: "Clientes",
    description: "Todo mundo que já escreveu. Busque por nome, telefone ou e-mail.",
    Icone: IconeClientes,
    available: true,
  },
  {
    href: "/dashboard/kanban",
    title: "Kanban CRM",
    description: "Acompanhe os casos pelo funil, da entrada ao agendamento.",
    Icone: IconeFunil,
    available: true,
  },
  {
    href: "/dashboard/metrics",
    title: "Métricas",
    description: "Volume de atendimentos, taxa de qualificação e tempo de resposta.",
    Icone: IconeMetricas,
    available: true,
  },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const eAdmin = user?.papel === "admin";
  const atalhos = QUICK_LINKS.filter((link) => eAdmin || !link.soAdmin);

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-fg">
          Olá, {user?.nome ?? "por aqui"}
        </h1>
        <p className="mt-1 text-sm text-fg-muted">
          O agente atende no WhatsApp, faz a triagem e prepara a análise do caso.
          Por aqui você acompanha e ajusta.
        </p>
      </header>

      <section aria-label="Atalhos" className="grid gap-4 sm:grid-cols-2">
        {atalhos.map((link) => {
          const card = (
            <>
              <span className="rounded-lg bg-ink-50 p-2 text-ink-700 dark:bg-ink-900 dark:text-ink-100">
                <link.Icone />
              </span>
              <div>
                <h2 className="text-sm font-medium text-fg">{link.title}</h2>
                <p className="mt-0.5 text-sm text-fg-muted">{link.description}</p>
                {!link.available && (
                  <span className="mt-2 inline-block rounded-full bg-surface-muted px-2 py-0.5 text-xs text-fg-muted">
                    Em breve
                  </span>
                )}
              </div>
            </>
          );

          const className =
            "flex items-start gap-4 rounded-xl border border-surface-border bg-surface p-5";

          return link.available ? (
            <Link
              key={link.href}
              href={link.href}
              className={`${className} transition-colors hover:border-brand-300 hover:bg-brand-50 dark:bg-brand-900/40/40`}
            >
              {card}
            </Link>
          ) : (
            <div key={link.href} aria-disabled="true" className={`${className} opacity-70`}>
              {card}
            </div>
          );
        })}
      </section>
    </div>
  );
}
