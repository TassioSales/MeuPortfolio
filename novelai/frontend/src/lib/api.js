import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('novelai_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    if (error.response?.status === 401) {
      const refresh = localStorage.getItem('novelai_refresh')
      if (refresh) {
        try {
          const { data } = await axios.post(`${API_BASE}/api/auth/refresh`, {
            refresh_token: refresh,
          })
          localStorage.setItem('novelai_token', data.access_token)
          localStorage.setItem('novelai_refresh', data.refresh_token)
          error.config.headers.Authorization = `Bearer ${data.access_token}`
          return api.request(error.config)
        } catch {
          localStorage.removeItem('novelai_token')
          localStorage.removeItem('novelai_refresh')
          window.location.href = '/'
        }
      }
    }
    return Promise.reject(error)
  }
)

// ─── Novelas ────────────────────────────────────────────────────────────────────
export const getNovelas = (params) => api.get('/api/novelas', { params }).then((r) => r.data)
export const getNovela = (id) => api.get(`/api/novelas/${id}`).then((r) => r.data)
export const getEpisodios = (novelaId) => api.get(`/api/novelas/${novelaId}/episodios`).then((r) => r.data)
export const getComentarios = (novelaId, params) => api.get(`/api/novelas/${novelaId}/comentarios`, { params }).then((r) => r.data)

// ─── Stream ─────────────────────────────────────────────────────────────────────
export const getStream = (episodeId) => api.get(`/api/stream/${episodeId}`).then((r) => r.data)

// ─── Busca ──────────────────────────────────────────────────────────────────────
export const buscar = (params) => api.get('/api/busca', { params }).then((r) => r.data)

// ─── Recomendações ──────────────────────────────────────────────────────────────
export const getTrending = (limit = 20) => api.get('/api/recomendacoes/trending', { params: { limit } }).then((r) => r.data)
export const getRecomendacoes = (userId, limit = 20) => api.get('/api/recomendacoes', { params: { user_id: userId, limit } }).then((r) => r.data)

// ─── Gêneros ────────────────────────────────────────────────────────────────────
export const getGeneros = () => api.get('/api/generos').then((r) => r.data)

// ─── Auth ───────────────────────────────────────────────────────────────────────
export const login = (data) => api.post('/api/auth/login', data).then((r) => r.data)
export const register = (data) => api.post('/api/auth/register', data).then((r) => r.data)
export const getMe = () => api.get('/api/auth/me').then((r) => r.data)

// ─── Usuário ────────────────────────────────────────────────────────────────────
export const getHistorico = () => api.get('/api/usuarios/historico').then((r) => r.data)
export const updateHistorico = (episodeId, posicao) =>
  api.post('/api/usuarios/historico', { posicao_segundos: posicao }, { params: { episode_id: episodeId } }).then((r) => r.data)
export const getFavoritos = () => api.get('/api/usuarios/favoritos').then((r) => r.data)
export const toggleFavorito = (novelaId) =>
  api.post('/api/usuarios/favoritos/toggle', { novela_id: novelaId }).then((r) => r.data)
export const salvarPreferencias = (data) => api.put('/api/usuarios/preferencias', data).then((r) => r.data)

// ─── Comentários ────────────────────────────────────────────────────────────────
export const criarComentario = (episodeId, texto) =>
  api.post(`/api/usuarios/episodios/${episodeId}/comentarios`, { texto }).then((r) => r.data)
export const deletarComentario = (id) => api.delete(`/api/usuarios/comentarios/${id}`).then((r) => r.data)

// ─── Rating ─────────────────────────────────────────────────────────────────────
export const darRating = (episodeId, estrelas) =>
  api.post(`/api/usuarios/episodios/${episodeId}/rating`, { estrelas }).then((r) => r.data)

export default api
