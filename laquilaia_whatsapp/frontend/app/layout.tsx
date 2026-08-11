import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "L'Aquila AI — Agentes de WhatsApp",
  description:
    "Plataforma para gerenciar agentes de IA no WhatsApp, qualificar leads e acompanhar métricas.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="font-sans">{children}</body>
    </html>
  );
}
