import { useState, useCallback } from 'react'
import { useNovelas, useGeneros } from '../hooks/useNovelas'
import NovelaCard from '../components/NovelaCard'
import { Filter, ChevronDown, Grid, List } from 'lucide-react'
import clsx from 'clsx'

const SORT_OPTIONS = [
  { value: 'recente', label: 'Mais recentes' },
  { value: 'trending', label: 'Em alta' },
  { value: 'rating', label: 'Melhor avaliados' },
  { value: 'titulo', label: 'A-Z' },
]

const IDIOMAS = ['Todos', 'pt', 'en', 'es', 'ja', 'ko', 'zh']

export default function Browse() {
  const [filtros, setFiltros] = useState({ sort: 'trending', pagina: 1, por_pagina: 24 })
  const [generoSel, setGeneroSel] = useState('')
  const [idiomaSel, setIdiomaSel] = useState('')
  const [viewMode, setViewMode] = useState('grid')
  const [showFilters, setShowFilters] = useState(false)

  const { data: generos = [] } = useGeneros()
  const { data, isLoading } = useNovelas({
    ...filtros,
    genero: generoSel || undefined,
    idioma: idiomaSel && idiomaSel !== 'Todos' ? idiomaSel : undefined,
  })

  const novelas = data?.items || []
  const total = data?.total || 0
  const totalPaginas = data?.total_paginas || 1

  const setSort = useCallback((sort) => setFiltros((f) => ({ ...f, sort, pagina: 1 })), [])
  const setPagina = useCallback((p) => setFiltros((f) => ({ ...f, pagina: p })), [])

  return (
    <div className="min-h-screen pt-20 pb-20 container mx-auto px-6 max-w-7xl">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-white">Biblioteca</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={clsx('btn-secondary flex items-center gap-2 py-2', showFilters && 'ring-1 ring-novelai-accent')}
          >
            <Filter size={16} />
            Filtros
          </button>
          <div className="flex items-center bg-novelai-card border border-novelai-border rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode('grid')}
              className={clsx('p-2.5', viewMode === 'grid' ? 'bg-novelai-accent text-white' : 'text-novelai-muted hover:text-white')}
            >
              <Grid size={18} />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={clsx('p-2.5', viewMode === 'list' ? 'bg-novelai-accent text-white' : 'text-novelai-muted hover:text-white')}
            >
              <List size={18} />
            </button>
          </div>
        </div>
      </div>

      {/* Filtros */}
      {showFilters && (
        <div className="card p-5 mb-8 animate-fade-in">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="text-sm text-novelai-muted mb-2 block">Ordenar por</label>
              <select
                value={filtros.sort}
                onChange={(e) => setSort(e.target.value)}
                className="input text-sm"
              >
                {SORT_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-novelai-muted mb-2 block">Gênero</label>
              <select
                value={generoSel}
                onChange={(e) => setGeneroSel(e.target.value)}
                className="input text-sm"
              >
                <option value="">Todos os gêneros</option>
                {generos.map((g) => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-novelai-muted mb-2 block">Idioma</label>
              <select
                value={idiomaSel}
                onChange={(e) => setIdiomaSel(e.target.value)}
                className="input text-sm"
              >
                {IDIOMAS.map((i) => (
                  <option key={i} value={i}>{i === 'pt' ? 'Português' : i === 'en' ? 'Inglês' : i === 'es' ? 'Espanhol' : i}</option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={() => { setGeneroSel(''); setIdiomaSel(''); setFiltros({ sort: 'trending', pagina: 1, por_pagina: 24 }) }}
                className="btn-secondary w-full py-2 text-sm"
              >
                Limpar filtros
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Resultados */}
      <div className="text-novelai-muted text-sm mb-6">
        {isLoading ? 'Carregando...' : `${total} novelas encontradas`}
      </div>

      {isLoading ? (
        <div className={clsx('grid gap-4', viewMode === 'grid' ? 'grid-cols-2 md:grid-cols-4 lg:grid-cols-6' : 'grid-cols-1')}>
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="skeleton rounded-xl" style={{ paddingBottom: viewMode === 'grid' ? '150%' : '80px' }} />
          ))}
        </div>
      ) : novelas.length === 0 ? (
        <div className="text-center py-20 text-novelai-muted">
          <p className="text-xl">Nenhuma novela encontrada</p>
          <p className="text-sm mt-2">Tente ajustar os filtros</p>
        </div>
      ) : (
        <div className={clsx('grid gap-4', viewMode === 'grid' ? 'grid-cols-2 md:grid-cols-4 lg:grid-cols-6' : 'grid-cols-1 md:grid-cols-2')}>
          {novelas.map((n) => (
            <NovelaCard key={n.id} novela={n} />
          ))}
        </div>
      )}

      {/* Paginação */}
      {totalPaginas > 1 && (
        <div className="flex justify-center items-center gap-2 mt-12">
          <button
            disabled={filtros.pagina === 1}
            onClick={() => setPagina(filtros.pagina - 1)}
            className="btn-secondary py-2 px-4 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Anterior
          </button>
          <span className="text-novelai-muted text-sm">
            Página {filtros.pagina} de {totalPaginas}
          </span>
          <button
            disabled={filtros.pagina === totalPaginas}
            onClick={() => setPagina(filtros.pagina + 1)}
            className="btn-secondary py-2 px-4 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Próxima
          </button>
        </div>
      )}
    </div>
  )
}
