"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import {
  IconeAgente,
  IconeConversa,
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
}

const QUICK_LINKS: QuickLink[] = [
  {
    href: "/dashboard/agents",
    title: "Agentes",
    description: "O prompt da triagem e os limites do atendimento.",
    Icone: IconeAgente,
    available: true,
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

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-ink-900">
          Olá, {user?.nome ?? "por aqui"}
        </h1>
        <p className="mt-1 text-sm text-gray-600">
          O agente atende no WhatsApp, faz a triagem e prepara a análise do caso.
          Por aqui você acompanha e ajusta.
        </p>
      </header>

      <section aria-label="Atalhos" className="grid gap-4 sm:grid-cols-2">
        {QUICK_LINKS.map((link) => {
          const card = (
            <>
              <span className="rounded-lg bg-ink-50 p-2 text-ink-700">
                <link.Icone />
              </span>
              <div>
                <h2 className="text-sm font-medium text-gray-900">{link.title}</h2>
                <p className="mt-0.5 text-sm text-gray-600">{link.description}</p>
                {!link.available && (
                  <span className="mt-2 inline-block rounded-full bg-surface-muted px-2 py-0.5 text-xs text-gray-500">
                    Em breve
                  </span>
                )}
              </div>
            </>
          );

          const className =
            "flex items-start gap-4 rounded-xl border border-surface-border bg-white p-5";

          return link.available ? (
            <Link
              key={link.href}
              href={link.href}
              className={`${className} transition-colors hover:border-brand-300 hover:bg-brand-50/40`}
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
