"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  CheckCircle2,
  Database,
  Flame,
  LayoutDashboard,
  Scale,
  Settings,
  TrendingUp,
  Trophy,
  XCircle,
} from "lucide-react";

import { FuelTicker } from "@/components/fuel-ticker";
import { cn } from "@/lib/utils";
import { useSettingsStore } from "@/lib/store";

const navLinks = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/historico", label: "Histórico", icon: Activity },
  { href: "/previsoes", label: "Previsões", icon: TrendingUp },
  { href: "/comparacoes", label: "Comparações", icon: Scale },
  { href: "/rankings", label: "Rankings", icon: Trophy },
  { href: "/explorer", label: "Explorer", icon: Database },
  { href: "/configuracoes", label: "Config", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { mistralKey } = useSettingsStore();

  return (
    <div className="min-h-screen" style={{ backgroundColor: "#070C14" }}>
      {/* Sticky Header */}
      <header
        className="sticky top-0 z-50 flex h-16 items-center border-b px-6"
        style={{
          background: "rgba(7, 12, 20, 0.92)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderColor: "rgba(255, 255, 255, 0.06)",
        }}
      >
        {/* Logo */}
        <div className="flex shrink-0 items-center gap-2.5 mr-8">
          <Flame
            className="h-5 w-5"
            style={{ color: "#F59E0B" }}
          />
          <div className="flex flex-col leading-none">
            <span
              className="text-lg font-bold text-white tracking-tight"
              style={{ fontFamily: "'Space Grotesk', sans-serif" }}
            >
              FUEL INTEL
            </span>
            <span
              className="text-[10px] tracking-widest uppercase"
              style={{ color: "#64748B", fontFamily: "'Inter', sans-serif" }}
            >
              BR Analytics
            </span>
          </div>
        </div>

        {/* Tab Navigation */}
        <nav className="flex flex-1 items-center gap-1 overflow-x-auto no-scrollbar">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const active =
              link.href === "/"
                ? pathname === "/"
                : pathname === link.href || pathname.startsWith(`${link.href}/`);

            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "inline-flex shrink-0 items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-all duration-200",
                  active
                    ? "border text-amber"
                    : "text-muted hover:text-text",
                )}
                style={
                  active
                    ? {
                        backgroundColor: "rgba(245, 158, 11, 0.15)",
                        borderColor: "rgba(245, 158, 11, 0.30)",
                        color: "#F59E0B",
                        fontFamily: "'Inter', sans-serif",
                      }
                    : {
                        color: "#64748B",
                        fontFamily: "'Inter', sans-serif",
                      }
                }
                onMouseEnter={(e) => {
                  if (!active) {
                    (e.currentTarget as HTMLAnchorElement).style.backgroundColor =
                      "rgba(255, 255, 255, 0.05)";
                    (e.currentTarget as HTMLAnchorElement).style.color = "#E2E8F0";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!active) {
                    (e.currentTarget as HTMLAnchorElement).style.backgroundColor =
                      "transparent";
                    (e.currentTarget as HTMLAnchorElement).style.color = "#64748B";
                  }
                }}
              >
                <Icon className="h-3.5 w-3.5" />
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Right: API key status + settings */}
        <div className="flex shrink-0 items-center gap-3 ml-4">
          <Link
            href="/configuracoes"
            title={mistralKey ? "Mistral configurado" : "API Key não configurada"}
            className="flex items-center transition-opacity hover:opacity-80"
          >
            {mistralKey ? (
              <CheckCircle2 className="h-4 w-4" style={{ color: "#10B981" }} />
            ) : (
              <XCircle className="h-4 w-4" style={{ color: "#F43F5E" }} />
            )}
          </Link>
          <Link
            href="/configuracoes"
            className="flex h-8 w-8 items-center justify-center rounded-full transition-colors"
            style={{ color: "#64748B" }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.backgroundColor =
                "rgba(255, 255, 255, 0.06)";
              (e.currentTarget as HTMLAnchorElement).style.color = "#E2E8F0";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.backgroundColor = "transparent";
              (e.currentTarget as HTMLAnchorElement).style.color = "#64748B";
            }}
          >
            <Settings className="h-4 w-4" />
          </Link>
        </div>
      </header>

      {/* Ticker Bar */}
      <FuelTicker />

      {/* Main Content */}
      <main className="mx-auto max-w-[1600px] px-6 py-8">
        {children}
      </main>
    </div>
  );
}
