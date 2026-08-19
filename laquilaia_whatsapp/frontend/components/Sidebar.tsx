"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";
import { Logo } from "./Logo";
import {
  IconeAcessos,
  IconeAgente,
  IconeClientes,
  IconeConversa,
  IconeEscritorio,
  IconeFinalizados,
  IconeFunil,
  IconeHistorico,
  IconeMetricas,
  IconePainel,
  IconeTeste,
  IconeWhatsapp,
} from "./icons";

interface NavItem {
  href: string;
  label: string;
  Icone: (props: { className?: string }) => JSX.Element;
  /** Fases que ainda não existem ficam visíveis porém desabilitadas. */
  disabled?: boolean;
  /**
   * Telas que só o administrador abre.
   *
   * Escondidas do operador porque o backend responde 404 nelas: deixar o link
   * visível é oferecer uma porta que bate na cara de quem clica. Esconder não
   * é a autorização — ela continua no backend, rota por rota.
   */
  soAdmin?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Visão geral", Icone: IconePainel },
  { href: "/dashboard/agents", label: "Agentes", Icone: IconeAgente, soAdmin: true },
  { href: "/dashboard/whatsapp", label: "WhatsApp", Icone: IconeWhatsapp, soAdmin: true },
  { href: "/dashboard/conversations", label: "Atendimentos", Icone: IconeConversa },
  { href: "/dashboard/chat-test", label: "Chat de teste", Icone: IconeTeste, soAdmin: true },
  { href: "/dashboard/clientes", label: "Clientes", Icone: IconeClientes },
  { href: "/dashboard/kanban", label: "Kanban CRM", Icone: IconeFunil },
  { href: "/dashboard/metrics", label: "Métricas", Icone: IconeMetricas },
  { href: "/dashboard/finalizados", label: "Finalizados", Icone: IconeFinalizados },
  { href: "/dashboard/historico", label: "Histórico", Icone: IconeHistorico },
  { href: "/dashboard/escritorio", label: "Escritório", Icone: IconeEscritorio },
  { href: "/dashboard/usuarios", label: "Acessos", Icone: IconeAcessos, soAdmin: true },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();
  // Enquanto a sessão não carregou, trate como operador: mostrar o link e
  // escondê-lo meio segundo depois pisca a tela, e um menu que muda sozinho
  // parece defeito.
  const eAdmin = user?.papel === "admin";
  const itens = NAV_ITEMS.filter((item) => eAdmin || !item.soAdmin);

  return (
    <aside className="hidden w-60 shrink-0 bg-ink-900 dark:bg-ink-950 md:flex md:flex-col">
      <div className="flex h-16 items-center px-5 text-white">
        <Logo />
      </div>

      <nav className="flex flex-col gap-0.5 px-3 py-2" aria-label="Navegação principal">
        {itens.map(({ href, label, Icone, disabled }) => {
          const isActive =
            href === "/dashboard" ? pathname === href : pathname.startsWith(href);

          if (disabled) {
            return (
              <span
                key={href}
                aria-disabled="true"
                title="Disponível em uma próxima fase"
                className="flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2 text-sm text-ink-500"
              >
                <Icone />
                {label}
              </span>
            );
          }

          return (
            <Link
              key={href}
              href={href}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-ink-800 font-medium text-white"
                  : "text-ink-300 hover:bg-ink-800/60 hover:text-white",
              )}
            >
              {/* A barra de latão marca a página atual sem depender só da cor
                  de fundo, que num tema escuro fica sutil demais. */}
              {isActive && (
                <span
                  aria-hidden="true"
                  className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-brass-400"
                />
              )}
              <Icone className={isActive ? "text-brass-400" : undefined} />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

export default Sidebar;
