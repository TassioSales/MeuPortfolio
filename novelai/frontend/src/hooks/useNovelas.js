import { useQuery } from '@tanstack/react-query'
import { getNovelas, getNovela, getEpisodios, getTrending, getRecomendacoes, buscar, getGeneros } from '../lib/api'

export function useNovelas(params = {}) {
  return useQuery({
    queryKey: ['novelas', params],
    queryFn: () => getNovelas(params),
  })
}

export function useNovela(id) {
  return useQuery({
    queryKey: ['novela', id],
    queryFn: () => getNovela(id),
    enabled: !!id,
  })
}

export function useEpisodios(novelaId) {
  return useQuery({
    queryKey: ['episodios', novelaId],
    queryFn: () => getEpisodios(novelaId),
    enabled: !!novelaId,
  })
}

export function useTrending(limit = 20) {
  return useQuery({
    queryKey: ['trending', limit],
    queryFn: () => getTrending(limit),
  })
}

export function useRecomendacoes(userId, limit = 20) {
  return useQuery({
    queryKey: ['recomendacoes', userId, limit],
    queryFn: () => getRecomendacoes(userId, limit),
  })
}

export function useBusca(params) {
  return useQuery({
    queryKey: ['busca', params],
    queryFn: () => buscar(params),
    enabled: !!(params?.q || params?.genero),
  })
}

export function useGeneros() {
  return useQuery({
    queryKey: ['generos'],
    queryFn: getGeneros,
    staleTime: Infinity,
  })
}
