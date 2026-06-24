import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'DevMetrics — Analytics GitHub com IA',
  description: 'Analise perfis do GitHub com insights gerados por Inteligência Artificial',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  )
}
