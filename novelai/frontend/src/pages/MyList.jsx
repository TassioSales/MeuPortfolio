import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getHistorico, getFavoritos } from '../lib/api'
import NovelaCard from '../components/NovelaCard'
import { History, Heart, Clock } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'

function formatProgress(pos, dur) {
  if (!dur) return null
  const pct = Math.min(100, (pos / dur) * 100)
  return pct.toFixed(0)
}

export default function MyList() {
  const [tab, setTab] = useState('historico')
  const navigate = useNavigate()

  const { data: historico = [], isLoading: loadingH } = useQuery({
    queryKey: ['historico'],
    queryFn: getHistorico,
  })

  const { data: favoritos = [], isLoading: loadingF } = useQuery({
    queryKey: ['favoritos'],
    queryFn: getFavoritos,
  })

  return (
    <div className="min-h-screen pt-20 pb-20 container mx-auto px-6 max-w-7xl">
      <h1 className="text-3xl font-bold text-white mb-8">Minha Lista</h1>

      {/* Tabs */}
      <div className="flex gap-6 border-b border-novelai-border mb-10">
        {[
          { id: 'historico', label: 'Continuando', icon: History },
          { id: 'favoritos', label: 'Favoritos', icon: Heart },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={clsx(
              'pb-3 flex items-center gap-2 text-sm font-semibold transition-colors',
              tab === id
                ? 'text-white border-b-2 border-novelai-accent'
                : 'text-novelai-muted hover:text-white'
            )}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>

      {tab === 'historico' && (
        <div>
          {loadingH ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="skeleton rounded-xl aspect-video" />
              ))}
            </div>
          ) : historico.length === 0 ? (
            <EmptyState icon={<History size={48} />} title="Sem histórico" desc="Comece a assistir para ver aqui" cta="Explorar novelas" onCta={() => navigate('/browse')} />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {historico.map((h) => (
                <button
                  key={h.episode_id}
                  onClick={() => navigate(`/watch/${h.episode_id}`)}
                  className="card flex gap-4 p-4 hover:border-novelai-accent transition-colors text-left group"
                >
                  <div className="relative w-28 h-20 flex-shrink-0 rounded-lg overflow-hidden bg-novelai-border">
                    {h.novela?.poster_url && (
                      <img src={h.novela.poster_url} alt="" className="w-full h-full object-cover" />
                    )}
                    <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                      <div className="w-8 h-8 bg-novelai-accent rounded-full flex items-center justify-center">
                        ▶
                      </div>
                    </div>
                    {/* Progress bar */}
                    {h.episodio?.duracao_segundos > 0 && (
                      <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/20">
                        <div
                          className="h-full bg-novelai-accent"
                          style={{ width: `${formatProgress(h.posicao_segundos, h.episodio.duracao_segundos)}%` }}
                        />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium text-sm truncate">{h.novela?.titulo}</p>
                    <p className="text-novelai-muted text-xs mt-1 truncate">EP {h.episodio?.numero} — {h.episodio?.titulo}</p>
                    <div className="flex items-center gap-1 text-novelai-muted text-xs mt-2">
                      <Clock size={12} />
                      <span>{new Date(h.assistido_em).toLocaleDateString('pt-BR')}</span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'favoritos' && (
        <div>
          {loadingF ? (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="skeleton rounded-xl" style={{ paddingBottom: '150%' }} />
              ))}
            </div>
          ) : favoritos.length === 0 ? (
            <EmptyState icon={<Heart size={48} />} title="Sem favoritos" desc="Favorite episódios para salvá-los aqui" cta="Explorar novelas" onCta={() => navigate('/browse')} />
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {favoritos.map((f) => (
                <NovelaCard key={f.id} novela={f} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function EmptyState({ icon, title, desc, cta, onCta }) {
  return (
    <div className="text-center py-20 text-novelai-muted">
      <div className="flex justify-center mb-4 opacity-40">{icon}</div>
      <p className="text-xl text-white font-semibold">{title}</p>
      <p className="text-sm mt-2 mb-6">{desc}</p>
      <button onClick={onCta} className="btn-primary">{cta}</button>
    </div>
  )
}
