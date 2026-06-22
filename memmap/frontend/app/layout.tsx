import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MemMap — Second Brain",
  description:
    "Editor de notas com grafo de conhecimento interativo. Extraia entidades automaticamente com NLP e visualize as conexões.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className="bg-[#0d1117] text-[#e6edf3] antialiased">
        {children}
      </body>
    </html>
  );
}
