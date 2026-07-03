"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Map, Play, BarChart2, Users, LogOut, TrendingUp, ChevronRight, BookOpen } from "lucide-react";
import { clsx } from "clsx";
import { useAuthStore } from "@/lib/stores/authStore";
import { useCareerStore } from "@/lib/stores/careerStore";

const NAV = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/dashboard/my-path", label: "Meu Caminho", icon: Map },
  { href: "/dashboard/courses", label: "Cursos", icon: BookOpen },
  { href: "/dashboard/simulation", label: "Simulação", icon: Play },
  { href: "/dashboard/analytics", label: "Analytics", icon: BarChart2 },
  { href: "/dashboard/mentorship", label: "Mentoria", icon: Users },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const { roadmap } = useCareerStore();
  const pct = roadmap?.progress_pct ?? 0;

  return (
    <aside className="w-60 min-h-screen flex flex-col border-r border-border bg-surface shrink-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-accent-gradient flex items-center justify-center shadow-accent-sm">
            <TrendingUp size={16} className="text-surface" />
          </div>
          <div>
            <span className="font-bold text-base text-text-primary tracking-tight leading-none block">TRILHA</span>
            <span className="text-[10px] text-text-muted leading-none">AI Career Coach</span>
          </div>
        </div>
      </div>

      {/* User profile */}
      {user && (
        <div className="px-4 py-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-accent/15 border border-accent/30 flex items-center justify-center text-accent font-bold text-sm shrink-0 shadow-accent-sm">
              {user.name.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-text-primary truncate leading-tight">{user.name}</p>
              <p className="text-xs text-text-muted truncate mt-0.5">{user.current_role}</p>
            </div>
          </div>

          {/* Mini progress */}
          <div className="mt-3">
            <div className="flex justify-between text-[10px] text-text-muted mb-1">
              <span>Progresso</span>
              <span className="text-accent font-semibold">{pct.toFixed(0)}%</span>
            </div>
            <div className="h-1.5 bg-surface-high rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{ width: `${pct}%`, background: "linear-gradient(90deg,#00e87a,#00b85e)" }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 px-3 py-3 space-y-0.5">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all group",
                active
                  ? "bg-accent/12 text-accent font-semibold border border-accent/20 shadow-accent-sm"
                  : "text-text-muted hover:text-text-primary hover:bg-surface-high"
              )}
            >
              <Icon size={15} className={active ? "text-accent" : "text-text-dim group-hover:text-text-muted transition-colors"} />
              <span className="flex-1">{label}</span>
              {active && <ChevronRight size={12} className="text-accent/60" />}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-3 pb-4 space-y-1 border-t border-border pt-3">
        <div className="px-3 py-2.5 rounded-xl bg-surface-high border border-border">
          <p className="text-[10px] text-text-muted uppercase tracking-wider mb-0.5">Meta</p>
          <p className="text-xs font-semibold text-text-primary truncate">{user?.target_role ?? "..."}</p>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-2.5 px-3 py-2 w-full text-sm text-text-muted hover:text-red-400 transition-colors rounded-xl hover:bg-surface-high"
        >
          <LogOut size={14} />
          Sair
        </button>
      </div>
    </aside>
  );
}
