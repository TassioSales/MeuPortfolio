"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: string;
  /** Fases que ainda não existem ficam visíveis porém desabilitadas. */
  disabled?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Visão geral", icon: "📊" },
  { href: "/dashboard/agents", label: "Agentes", icon: "🤖" },
  { href: "/dashboard/chat-test", label: "Chat de teste", icon: "💬" },
  { href: "/dashboard/kanban", label: "Kanban CRM", icon: "🗂️" },
  { href: "/dashboard/metrics", label: "Métricas", icon: "📈" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-60 shrink-0 border-r border-surface-border bg-white md:block">
      <nav className="flex flex-col gap-1 p-4" aria-label="Navegação principal">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/dashboard"
              ? pathname === item.href
              : pathname.startsWith(item.href);

          if (item.disabled) {
            return (
              <span
                key={item.href}
                aria-disabled="true"
                title="Disponível em uma próxima fase"
                className="flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2 text-sm text-gray-400"
              >
                <span aria-hidden="true">{item.icon}</span>
                {item.label}
              </span>
            );
          }

          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-brand-50 font-medium text-brand-700"
                  : "text-gray-600 hover:bg-surface-muted",
              )}
            >
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

export default Sidebar;
