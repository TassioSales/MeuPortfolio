import { useNavigate } from 'react-router-dom'
import { Play, Star } from 'lucide-react'
import clsx from 'clsx'

export default function NovelaCard({ novela, className }) {
  const navigate = useNavigate()

  if (!novela) return null

  return (
    <div
      onClick={() => navigate(`/novelas/${novela.id}`)}
      className={clsx('novela-card cursor-pointer relative rounded-xl overflow-hidden group', className)}
    >
      {/* Poster */}
      <div className="relative aspect-[2/3] bg-novelai-border">
        {novela.poster_url ? (
          <img
            src={novela.poster_url}
            alt={novela.titulo}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-novelai-muted text-xs text-center p-2">
            {novela.titulo}
          </div>
        )}

        {/* Overlay on hover */}
        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <div className="w-12 h-12 bg-novelai-accent rounded-full flex items-center justify-center shadow-lg">
            <Play size={22} className="text-white ml-0.5" fill="white" />
          </div>
        </div>

        {/* Rating badge */}
        {novela.rating_medio > 0 && (
          <div className="absolute top-2 right-2 bg-black/70 backdrop-blur-sm rounded-md px-1.5 py-0.5 flex items-center gap-1">
            <Star size={10} className="text-yellow-400" fill="currentColor" />
            <span className="text-white text-xs font-semibold">{novela.rating_medio.toFixed(1)}</span>
          </div>
        )}

        {/* IA badge */}
        {novela.origem === 'gerada_ia' && (
          <div className="absolute top-2 left-2 bg-purple-600/80 backdrop-blur-sm rounded-md px-1.5 py-0.5">
            <span className="text-white text-xs font-medium">IA</span>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-2">
        <p className="text-white text-xs font-medium truncate">{novela.titulo}</p>
        {novela.genero?.length > 0 && (
          <p className="text-novelai-muted text-xs truncate mt-0.5">{novela.genero[0]}</p>
        )}
      </div>
    </div>
  )
}
