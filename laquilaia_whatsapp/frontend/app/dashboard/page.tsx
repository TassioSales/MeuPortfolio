"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

interface QuickLink {
  href: string;
  title: string;
  description: string;
  icon: string;
  available: boolean;
}

const QUICK_LINKS: QuickLink[] = [
  {
    href: "/dashboard/agents",
    title: "Agentes",
    description: "Crie e edite os prompts dos seus agentes de IA.",
    icon: "🤖",
    available: false,
  },
  {
    href: "/dashboard/chat-test",
    title: "Chat de teste",
    description: "Converse com o agente antes de publicá-lo no WhatsApp.",
    icon: "💬",
    available: false,
  },
  {
    href: "/dashboard/kanban",
    title: "Kanban CRM",
    description: "Acompanhe os leads pelo funil de qualificação.",
    icon: "🗂️",
    available: false,
  },
  {
    href: "/dashboard/metrics",
    title: "Métricas",
    description: "Taxa de qualificação, tempo de resposta e KPIs.",
    icon: "📈",
    available: false,
  },
];

export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900">
          Olá, {user?.nome ?? "por aqui"} 👋
        </h1>
        <p className="mt-1 text-sm text-gray-600">
          Este é o painel da sua conta. As áreas abaixo são liberadas conforme as próximas
          fases do projeto forem entregues.
        </p>
      </header>

      <section aria-label="Atalhos" className="grid gap-4 sm:grid-cols-2">
        {QUICK_LINKS.map((link) => {
          const card = (
            <>
              <span aria-hidden="true" className="text-2xl">
                {link.icon}
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
