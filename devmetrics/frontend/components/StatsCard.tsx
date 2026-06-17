import { BookOpen, Star, GitFork, Code2 } from 'lucide-react'

type IconType = 'repo' | 'star' | 'fork' | 'lang'

interface StatsCardProps {
  icon: IconType
  label: string
  value: number | string
}

const icons: Record<IconType, React.ReactNode> = {
  repo: <BookOpen className="w-5 h-5 text-[#388bfd]" />,
  star: <Star className="w-5 h-5 text-[#e3b341]" />,
  fork: <GitFork className="w-5 h-5 text-[#3fb950]" />,
  lang: <Code2 className="w-5 h-5 text-[#a371f7]" />,
}

export default function StatsCard({ icon, label, value }: StatsCardProps) {
  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        {icons[icon]}
        <span className="text-xs text-[#8b949e] font-medium uppercase tracking-wide">{label}</span>
      </div>
      <div className="text-2xl font-bold text-white">
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
    </div>
  )
}
