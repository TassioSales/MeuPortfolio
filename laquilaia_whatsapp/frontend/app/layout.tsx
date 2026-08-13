import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AdvogAi — triagem jurídica no WhatsApp",
  description:
    "Agente de triagem jurídica no WhatsApp: entende o caso, coleta o que importa e entrega ao advogado uma análise preliminar.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="font-sans">{children}</body>
    </html>
  );
}
