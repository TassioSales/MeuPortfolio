import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'DevMetrics — GitHub Analytics Dashboard',
  description: 'Analyze GitHub profiles with AI-powered insights',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#0d1117] text-[#e6edf3]">
        {children}
      </body>
    </html>
  )
}
