import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Trilha — AI Career Coach",
  description: "Sua trilha de carreira com IA.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
