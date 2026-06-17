import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Encurtador URL",
  description: "A fast, simple URL shortener built with Go and Next.js",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen bg-[#0d1117] text-[#c9d1d9]">
        <nav className="border-b border-[#30363d] bg-[#161b22]">
          <div className="mx-auto max-w-5xl px-4 py-3 flex items-center gap-6">
            <Link
              href="/"
              className="text-lg font-bold text-[#58a6ff] hover:text-[#79b8ff] transition-colors"
            >
              Encurtador URL
            </Link>
            <Link
              href="/"
              className="text-sm text-[#8b949e] hover:text-[#c9d1d9] transition-colors"
            >
              Home
            </Link>
            <Link
              href="/dashboard"
              className="text-sm text-[#8b949e] hover:text-[#c9d1d9] transition-colors"
            >
              Dashboard
            </Link>
          </div>
        </nav>
        <main className="mx-auto max-w-5xl px-4 py-10">{children}</main>
      </body>
    </html>
  );
}
