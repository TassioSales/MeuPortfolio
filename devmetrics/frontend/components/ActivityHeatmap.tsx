'use client'

interface ActivityHeatmapProps {
  username: string
}

export default function ActivityHeatmap({ username }: ActivityHeatmapProps) {
  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Activity</h3>
      <p className="text-[#8b949e] text-sm">
        View {username}&apos;s full contribution history on{' '}
        <a
          href={`https://github.com/${username}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#388bfd] hover:underline"
        >
          GitHub
        </a>
      </p>
    </div>
  )
}
