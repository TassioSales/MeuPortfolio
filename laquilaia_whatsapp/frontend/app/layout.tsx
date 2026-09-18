import type { Metadata } from "next";
import { Caveat, Dancing_Script, Great_Vibes } from "next/font/google";
import "./globals.css";
import { SCRIPT_ANTI_PISCADA } from "@/lib/tema";

/**
 * As letras de assinatura, para quem prefere digitar a desenhar.
 *
 * Carregadas aqui e não na página porque o `next/font` precisa ser chamado no
 * escopo de módulo. O custo é zero para quem não usa: o `next/font` **baixa a
 * fonte na build e a serve do nosso próprio domínio**, então em tempo de
 * execução não há requisição ao Google — nem para quem só abre o painel.
 */
const cursivaElegante = Great_Vibes({
  weight: "400",
  subsets: ["latin"],
  variable: "--fonte-assinatura-elegante",
  display: "swap",
});
const cursivaSolta = Dancing_Script({
  weight: "600",
  subsets: ["latin"],
  variable: "--fonte-assinatura-solta",
  display: "swap",
});
const cursivaCaneta = Caveat({
  weight: "600",
  subsets: ["latin"],
  variable: "--fonte-assinatura-caneta",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AdvogAi — triagem jurídica no WhatsApp",
  description:
    "Agente de triagem jurídica no WhatsApp: entende o caso, coleta o que importa e entrega ao advogado uma análise preliminar.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="pt-BR"
      suppressHydrationWarning
      className={`${cursivaElegante.variable} ${cursivaSolta.variable} ${cursivaCaneta.variable}`}
    >
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
