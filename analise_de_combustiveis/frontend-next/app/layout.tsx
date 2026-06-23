import type { Metadata, Viewport } from "next";

import "@/app/globals.css";
import { AppShell } from "@/components/app-shell";

export const metadata: Metadata = {
  title: "Fuel Intel — Análise de Combustíveis Brasil",
  description:
    "Plataforma profissional de análise, acompanhamento e previsão de preços de combustíveis no Brasil. Dados ANP processados em tempo real.",
  keywords: ["combustíveis", "gasolina", "etanol", "diesel", "ANP", "preços", "Brasil"],
  authors: [{ name: "Fuel Intel" }],
};

export const viewport: Viewport = {
  themeColor: "#070C14",
  colorScheme: "dark",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className="dark">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
