import type { Metadata } from "next";

import "@/app/globals.css";
import { AppShell } from "@/components/app-shell";

export const metadata: Metadata = {
  title: "Fuel Analytics Platform",
  description: "Dashboard profissional para analise e previsao de combustiveis no Brasil",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}

