import { useParams, useNavigate, Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { ArrowLeft, SkipForward, List, Heart } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { getStream, getEpisodios } from '../lib/api'
import VideoPlayer from '../components/VideoPlayer'
import { useNovela } from '../hooks/useNovelas'

export default function Player() {
  const { episodeId } = useParams()
  const navigate = useNavigate()
  const [showSidebar, setShowSidebar] = useState(false)
  const [currentNovelaId, setCurrentNovelaId] = useState(null)

  const { data: streamData, isLoading: loadingStream } = useQuery({
    queryKey: ['stream', episodeId],
    queryFn: () => getStream(episodeId),
    enabled: !!episodeId,
  })

  const { data: episodios = [] } = useQuery({
    queryKey: ['episodios', currentNovelaId],
    queryFn: () => getEpisodios(currentNovelaId),
    enabled: !!currentNovelaId,
  })

  const currentIdx = episodios.findIndex((e) => e.id === episodeId)
  const nextEpisodio = episodios[currentIdx + 1]
  const currentEp = episodios[currentIdx]

  useEffect(() => {
    if (currentEp?.novela_id) {
      setCurrentNovelaId(currentEp.novela_id)
    }
  }, [currentEp])

  return (
    <div className="min-h-screen bg-black flex flex-col">
      {/* Player header */}
      <div className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between p-4 bg-gradient-to-b from-black/80 to-transparent">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-white/80 hover:text-white transition-colors"
        >
          <ArrowLeft size={22} />
          <span className="text-sm font-medium hidden sm:block">Voltar</span>
        </button>

        <div className="text-center">
          {currentEp && (
            <p className="text-white font-semibold text-sm">
              EP {currentEp.numero} — {currentEp.titulo}
            </p>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowSidebar(!showSidebar)}
            className="text-white/80 hover:text-white transition-colors p-2"
            title="Episódios"
          >
            <List size={20} />
          </button>
          {nextEpisodio && (
            <button
              onClick={() => navigate(`/watch/${nextEpisodio.id}`)}
              className="text-white/80 hover:text-white transition-colors p-2"
              title="Próximo episódio"
            >
              <SkipForward size={20} />
            </button>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1">
        {/* Video */}
        <div className="flex-1 flex items-center justify-center bg-black">
          {loadingStream ? (
            <div className="flex flex-col items-center gap-4 text-white/60">
              <div className="w-12 h-12 border-2 border-novelai-accent border-t-transparent rounded-full animate-spin" />
              <p>Carregando vídeo...</p>
            </div>
          ) : streamData ? (
            <VideoPlayer
              src={streamData.video_url}
              episodeId={episodeId}
              onEnded={() => nextEpisodio && setTimeout(() => navigate(`/watch/${nextEpisodio.id}`), 3000)}
            />
          ) : (
            <div className="text-white/60 text-center">
              <p className="text-xl mb-2">Vídeo indisponível</p>
              <p className="text-sm">Não foi possível carregar este episódio</p>
            </div>
          )}
        </div>

        {/* Sidebar episódios */}
        {showSidebar && (
          <div className="w-80 bg-novelai-card border-l border-novelai-border overflow-y-auto flex-shrink-0 mt-0">
            <div className="p-4 border-b border-novelai-border">
              <h3 className="text-white font-semibold">Episódios</h3>
            </div>
            <div className="p-3 space-y-2">
              {episodios.map((ep) => (
                <button
                  key={ep.id}
                  onClick={() => navigate(`/watch/${ep.id}`)}
                  className={`w-full text-left p-3 rounded-lg transition-colors ${
                    ep.id === episodeId
                      ? 'bg-novelai-accent/20 border border-novelai-accent/40'
                      : 'hover:bg-white/5'
                  }`}
                >
                  <p className={`font-medium text-sm ${ep.id === episodeId ? 'text-novelai-accent' : 'text-white'}`}>
                    EP {ep.numero}
                  </p>
                  <p className="text-novelai-muted text-xs truncate mt-0.5">{ep.titulo}</p>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Próximo episódio */}
      {nextEpisodio && (
        <div className="p-4 bg-novelai-card border-t border-novelai-border flex items-center justify-between">
          <span className="text-novelai-muted text-sm">A seguir</span>
          <button
            onClick={() => navigate(`/watch/${nextEpisodio.id}`)}
            className="btn-secondary py-2 text-sm flex items-center gap-2"
          >
            <SkipForward size={16} />
            EP {nextEpisodio.numero} — {nextEpisodio.titulo}
          </button>
        </div>
      )}
    </div>
  )
}
