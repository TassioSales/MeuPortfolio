import { useParams, useNavigate } from 'react-router-dom'
import { Play, Star, Clock, Globe, Heart, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import { useNovela, useEpisodios } from '../hooks/useNovelas'
import Comments from '../components/Comments'
import NovelaCard from '../components/NovelaCard'
import { useTrending } from '../hooks/useNovelas'
import { toggleFavorito } from '../lib/api'
import { useAuthStore } from '../store/authStore'
import clsx from 'clsx'

function formatDuration(sec) {
  if (!sec) return '—'
  const m = Math.floor(sec / 60)
  const h = Math.floor(m / 60)
  if (h > 0) return `${h}h ${m % 60}m`
  return `${m}m`
}

export default function Details() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [showAllEps, setShowAllEps] = useState(false)
  const [activeTab, setActiveTab] = useState('episodios')

  const { token } = useAuthStore()
  const [isFav, setIsFav] = useState(false)
  const [favLoading, setFavLoading] = useState(false)

  const { data: novela, isLoading } = useNovela(id)
  const { data: episodios = [] } = useEpisodios(id)
  const { data: similares = [] } = useTrending(8)

  const visibleEps = showAllEps ? episodios : episodios.slice(0, 6)

  const handleFavoritar = async () => {
    if (!token || favLoading) return
    setFavLoading(true)
    try {
      const res = await toggleFavorito(id)
      setIsFav(res.favorito)
    } catch {
      // silent
    } finally {
      setFavLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen pt-20">
        <div className="h-96 skeleton" />
        <div className="container mx-auto px-6 max-w-7xl mt-8 space-y-4">
          <div className="skeleton h-10 w-64 rounded" />
          <div className="skeleton h-4 w-full rounded" />
          <div className="skeleton h-4 w-3/4 rounded" />
        </div>
      </div>
    )
  }

  if (!novela) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center text-novelai-muted">
        Novela não encontrada
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      {/* Backdrop */}
      <div className="relative h-[55vh] min-h-[350px]">
        <img
          src={novela.backdrop_url || novela.poster_url || '/placeholder.jpg'}
          alt={novela.titulo}
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 hero-gradient" />
        <div className="absolute inset-0 hero-gradient-bottom" />
      </div>

      <div className="relative z-10 -mt-40 container mx-auto px-6 max-w-7xl pb-20">
        <div className="flex flex-col md:flex-row gap-8">
          {/* Poster */}
          <div className="flex-shrink-0 w-48 md:w-64">
            <img
              src={novela.poster_url || '/placeholder.jpg'}
              alt={novela.titulo}
              className="w-full rounded-xl shadow-2xl"
            />
          </div>

          {/* Info */}
          <div className="flex-1 pt-8">
            {novela.genero?.length > 0 && (
              <div className="flex gap-2 mb-3 flex-wrap">
                {novela.genero.map((g) => (
                  <span key={g} className="badge-accent">{g}</span>
                ))}
                {novela.origem === 'gerada_ia' && (
                  <span className="badge bg-purple-500/20 text-purple-400">Gerada com IA</span>
                )}
              </div>
            )}

            <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-4">{novela.titulo}</h1>

            <div className="flex items-center gap-6 text-novelai-muted text-sm mb-6 flex-wrap">
              {novela.rating_medio > 0 && (
                <div className="flex items-center gap-1 text-yellow-400">
                  <Star size={16} fill="currentColor" />
                  <span className="text-white font-semibold">{novela.rating_medio.toFixed(1)}</span>
                  <span className="text-novelai-muted">({novela.total_votos} votos)</span>
                </div>
              )}
              {novela.ano && <span>{novela.ano}</span>}
              {novela.idioma && (
                <div className="flex items-center gap-1">
                  <Globe size={14} />
                  <span>{novela.idioma.toUpperCase()}</span>
                </div>
              )}
              {novela.total_episodios && (
                <span>{novela.total_episodios} episódios</span>
              )}
              <span>{novela.views?.toLocaleString()} visualizações</span>
            </div>

            {novela.descricao && (
              <p className="text-white/80 text-base leading-relaxed mb-8 max-w-2xl">
                {novela.descricao}
              </p>
            )}

            <div className="flex gap-4 flex-wrap">
              {episodios[0] && (
                <button
                  onClick={() => navigate(`/watch/${episodios[0].id}`)}
                  className="btn-primary flex items-center gap-2"
                >
                  <Play size={20} fill="currentColor" />
                  Assistir EP 1
                </button>
              )}
              {token && (
                <button
                  onClick={handleFavoritar}
                  disabled={favLoading}
                  className={clsx(
                    'btn-secondary flex items-center gap-2',
                    isFav && 'text-novelai-accent border-novelai-accent'
                  )}
                >
                  <Heart size={20} fill={isFav ? 'currentColor' : 'none'} />
                  {isFav ? 'Favoritado' : 'Favoritar'}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="mt-12">
          <div className="flex gap-6 border-b border-novelai-border mb-8">
            {['episodios', 'comentarios'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={clsx(
                  'pb-3 text-sm font-semibold capitalize transition-colors',
                  activeTab === tab
                    ? 'text-white border-b-2 border-novelai-accent'
                    : 'text-novelai-muted hover:text-white'
                )}
              >
                {tab === 'episodios' ? 'Episódios' : 'Comentários'}
              </button>
            ))}
          </div>

          {activeTab === 'episodios' && (
            <div className="space-y-3">
              {visibleEps.map((ep) => (
                <button
                  key={ep.id}
                  onClick={() => navigate(`/watch/${ep.id}`)}
                  className="w-full card p-4 flex items-center gap-4 hover:border-novelai-accent transition-colors text-left group"
                >
                  <div className="w-14 h-14 rounded-lg bg-novelai-border flex items-center justify-center flex-shrink-0 group-hover:bg-novelai-accent transition-colors">
                    <Play size={22} className="text-white" fill="white" />
                  </div>
                  {ep.thumbnail_url && (
                    <img src={ep.thumbnail_url} alt="" className="w-24 h-14 object-cover rounded hidden sm:block" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium truncate">
                      {ep.numero}. {ep.titulo}
                    </p>
                    {ep.descricao && (
                      <p className="text-novelai-muted text-sm line-clamp-1 mt-1">{ep.descricao}</p>
                    )}
                  </div>
                  {ep.duracao_segundos > 0 && (
                    <div className="flex items-center gap-1 text-novelai-muted text-sm flex-shrink-0">
                      <Clock size={14} />
                      {formatDuration(ep.duracao_segundos)}
                    </div>
                  )}
                </button>
              ))}

              {episodios.length > 6 && (
                <button
                  onClick={() => setShowAllEps(!showAllEps)}
                  className="w-full text-novelai-muted hover:text-white py-4 flex items-center justify-center gap-2 transition-colors"
                >
                  {showAllEps ? <><ChevronUp size={16} /> Ver menos</> : <><ChevronDown size={16} /> Ver todos os {episodios.length} episódios</>}
                </button>
              )}

              {episodios.length === 0 && (
                <p className="text-novelai-muted text-center py-10">Nenhum episódio disponível</p>
              )}
            </div>
          )}

          {activeTab === 'comentarios' && (
            <Comments novelaId={id} episodeId={episodios[0]?.id} />
          )}
        </div>

        {/* Similares */}
        {similares.length > 0 && (
          <div className="mt-16">
            <h2 className="text-xl font-bold text-white mb-6">Você também pode gostar</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {similares.filter((s) => s.id !== id).slice(0, 6).map((n) => (
                <NovelaCard key={n.id} novela={n} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
