import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VoxBR — Transcrição de Áudio com IA",
  description:
    "Plataforma de transcrição de áudio com Whisper + resumo inteligente com Mistral AI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen bg-[#0a0e1a] text-gray-100">{children}</body>
    </html>
  );
}
