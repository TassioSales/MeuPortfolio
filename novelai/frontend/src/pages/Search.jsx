import { useState, useCallback, useRef } from 'react'
import { Search as SearchIcon, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useBusca, useGeneros } from '../hooks/useNovelas'
import NovelaCard from '../components/NovelaCard'
import { useTrending } from '../hooks/useNovelas'

export default function Search() {
  const [query, setQuery] = useState('')
  const [generoSel, setGeneroSel] = useState('')
  const navigate = useNavigate()
  const inputRef = useRef(null)

  const { data: generos = [] } = useGeneros()
  const { data: trending = [] } = useTrending(12)

  const searchParams = (query.length >= 2 || generoSel)
    ? { q: query || undefined, genero: generoSel || undefined, por_pagina: 30 }
    : null

  const { data, isLoading } = useBusca(searchParams)
  const resultados = data?.items || []
  const total = data?.total || 0

  const handleClear = useCallback(() => {
    setQuery('')
    setGeneroSel('')
    inputRef.current?.focus()
  }, [])

  const isSearching = !!searchParams

  return (
    <div className="min-h-screen pt-20 pb-20 container mx-auto px-6 max-w-7xl">
      {/* Search bar */}
      <div className="max-w-2xl mx-auto mb-10">
        <div className="relative">
          <SearchIcon size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-novelai-muted" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar novelas, gêneros, atores..."
            className="input pl-12 pr-12 py-4 text-lg"
            autoFocus
          />
          {(query || generoSel) && (
            <button
              onClick={handleClear}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-novelai-muted hover:text-white transition-colors"
            >
              <X size={20} />
            </button>
          )}
        </div>
      </div>

      {/* Gêneros (filtros rápidos) */}
      <div className="flex gap-3 flex-wrap justify-center mb-10">
        {generos.slice(0, 10).map((g) => (
          <button
            key={g}
            onClick={() => setGeneroSel(generoSel === g ? '' : g)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
              generoSel === g
                ? 'bg-novelai-accent text-white'
                : 'bg-novelai-card border border-novelai-border text-novelai-muted hover:text-white hover:border-white/30'
            }`}
          >
            {g}
          </button>
        ))}
      </div>

      {/* Resultados */}
      {isSearching ? (
        <div>
          <p className="text-novelai-muted text-sm mb-6">
            {isLoading ? 'Buscando...' : `${total} resultados${query ? ` para "${query}"` : ''}${generoSel ? ` em ${generoSel}` : ''}`}
          </p>

          {isLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {Array.from({ length: 12 }).map((_, i) => (
                <div key={i} className="skeleton rounded-xl" style={{ paddingBottom: '150%' }} />
              ))}
            </div>
          ) : resultados.length === 0 ? (
            <div className="text-center py-20 text-novelai-muted">
              <SearchIcon size={48} className="mx-auto mb-4 opacity-30" />
              <p className="text-xl text-white">Nada encontrado</p>
              <p className="text-sm mt-2">Tente outros termos ou gêneros</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {resultados.map((n) => (
                <NovelaCard key={n.id} novela={n} />
              ))}
            </div>
          )}
        </div>
      ) : (
        <div>
          <h2 className="text-xl font-bold text-white mb-6">Em alta agora</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {trending.map((n) => (
              <NovelaCard key={n.id} novela={n} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
