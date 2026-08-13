import type { Metadata } from "next";
import "./globals.css";
import { SCRIPT_ANTI_PISCADA } from "@/lib/tema";

export const metadata: Metadata = {
  title: "AdvogAi — triagem jurídica no WhatsApp",
  description:
    "Agente de triagem jurídica no WhatsApp: entende o caso, coleta o que importa e entrega ao advogado uma análise preliminar.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <head>
        {/* Antes da primeira pintura: sem isto a página nasce clara e vira
            escura quando o React monta — um flash branco na cara de quem
            escolheu escuro justamente para não levar um. */}
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_ANTI_PISCADA }} />
      </head>
      <body className="font-sans">{children}</body>
    </html>
  );
}
