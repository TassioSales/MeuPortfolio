import { useNavigate } from 'react-router-dom'
import { Play, Info, Star } from 'lucide-react'
import { useTrending, useRecomendacoes, useNovelas } from '../hooks/useNovelas'
import { useAuthStore } from '../store/authStore'
import Carousel from '../components/Carousel'

export default function Home() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const { data: trending = [] } = useTrending(20)
  const { data: recomendacoes = [] } = useRecomendacoes(user?.id, 20)
  const { data: lancamentos } = useNovelas({ sort: 'recente', por_pagina: 20 })
  const { data: topRated } = useNovelas({ sort: 'rating', por_pagina: 20 })

  const hero = trending[0]

  return (
    <main className="min-h-screen">
      {/* Hero */}
      {hero && (
        <section className="relative h-[85vh] min-h-[500px] flex items-end">
          <div className="absolute inset-0">
            <img
              src={hero.backdrop_url || hero.poster_url || '/placeholder-backdrop.jpg'}
              alt={hero.titulo}
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 hero-gradient" />
            <div className="absolute inset-0 hero-gradient-bottom" />
          </div>

          <div className="relative z-10 container mx-auto px-6 pb-20 max-w-7xl">
            {hero.genero?.length > 0 && (
              <div className="flex gap-2 mb-4">
                {hero.genero.slice(0, 3).map((g) => (
                  <span key={g} className="badge-accent">{g}</span>
                ))}
              </div>
            )}
            <h1 className="text-5xl md:text-7xl font-extrabold text-white mb-4 max-w-2xl leading-tight">
              {hero.titulo}
            </h1>
            {hero.descricao && (
              <p className="text-white/80 text-lg max-w-xl mb-8 line-clamp-3">
                {hero.descricao}
              </p>
            )}
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate(`/novelas/${hero.id}`)}
                className="btn-primary flex items-center gap-2 text-lg"
              >
                <Play size={22} fill="currentColor" />
                Assistir
              </button>
              <button
                onClick={() => navigate(`/novelas/${hero.id}`)}
                className="btn-secondary flex items-center gap-2 text-lg"
              >
                <Info size={22} />
                Mais info
              </button>
              {hero.rating_medio > 0 && (
                <div className="flex items-center gap-1 text-yellow-400 ml-2">
                  <Star size={18} fill="currentColor" />
                  <span className="text-white font-semibold">{hero.rating_medio.toFixed(1)}</span>
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Carousels */}
      <div className="relative z-10 -mt-16 pb-20 space-y-10 container mx-auto px-6 max-w-7xl">
        {trending.length > 0 && (
          <Carousel title="🔥 Em Alta" items={trending} />
        )}

        {recomendacoes.length > 0 && (
          <Carousel title="✨ Recomendado para você" items={recomendacoes} />
        )}

        {lancamentos?.items?.length > 0 && (
          <Carousel title="🆕 Lançamentos" items={lancamentos.items} />
        )}

        {topRated?.items?.length > 0 && (
          <Carousel title="⭐ Mais bem avaliados" items={topRated.items} />
        )}
      </div>
    </main>
  )
}
