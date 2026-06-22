import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0a0e1a',
        panel: '#111827',
        border: '#1f2937',
        accent: '#3b82f6',
        positive: '#10b981',
        negative: '#ef4444',
        muted: '#6b7280',
        text: '#f9fafb',
      },
    },
  },
}

export default config
