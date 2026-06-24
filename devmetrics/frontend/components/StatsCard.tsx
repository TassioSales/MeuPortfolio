import { BookOpen, Star, GitFork, Code2 } from 'lucide-react'

type IconType = 'repo' | 'star' | 'fork' | 'lang'

interface StatsCardProps {
  icon: IconType
  label: string
  value: number | string
  delay?: number
}

const config: Record<IconType, { icon: React.ReactNode; color: string; bg: string }> = {
  repo: {
    icon: <BookOpen className="w-5 h-5" />,
    color: '#388bfd',
    bg: 'rgba(56,139,253,0.12)',
  },
  star: {
    icon: <Star className="w-5 h-5" />,
    color: '#e3b341',
    bg: 'rgba(227,179,65,0.12)',
  },
  fork: {
    icon: <GitFork className="w-5 h-5" />,
    color: '#3fb950',
    bg: 'rgba(63,185,80,0.12)',
  },
  lang: {
    icon: <Code2 className="w-5 h-5" />,
    color: '#a371f7',
    bg: 'rgba(163,113,247,0.12)',
  },
}

export default function StatsCard({ icon, label, value, delay = 0 }: StatsCardProps) {
  const { icon: iconEl, color, bg } = config[icon]

  return (
    <div
      className="card card-accent p-5 animate-fade-in"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center mb-4"
        style={{ background: bg, color }}
      >
        {iconEl}
      </div>
      <div className="text-[26px] font-bold mb-1" style={{ color: 'var(--text)' }}>
        {typeof value === 'number' ? value.toLocaleString('pt-BR') : value}
      </div>
      <div className="text-[12px] font-medium uppercase tracking-wide" style={{ color: 'var(--muted)' }}>
        {label}
      </div>
    </div>
  )
}
