import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { BarChart2, Film, Users, Eye, Loader2, Play, CheckCircle, XCircle, Clock, Trash2, Zap, RefreshCw } from 'lucide-react'
import api from '../lib/api'

const adminApi = {
  stats: () => api.get('/api/admin/stats').then((r) => r.data),
  queue: () => api.get('/api/admin/queue').then((r) => r.data),
  gerar: (body) => api.post('/api/admin/generate/episodio', body).then((r) => r.data),
  aprovar: (id) => api.post(`/api/admin/approve/${id}`).then((r) => r.data),
  remover: (id) => api.delete(`/api/admin/videos/${id}`).then((r) => r.data),
  scrape: (canal) => api.post('/api/admin/scrape/manual', null, { params: { canal } }).then((r) => r.data),
  novelas: () => api.get('/api/novelas', { params: { por_pagina: 50 } }).then((r) => r.data),
}

const STATUS_COLORS = {
  pendente: 'text-yellow-400 bg-yellow-400/10',
  processando: 'text-blue-400 bg-blue-400/10',
  concluido: 'text-green-400 bg-green-400/10',
  publicado: 'text-purple-400 bg-purple-400/10',
  erro: 'text-red-400 bg-red-400/10',
}

export default function Admin() {
  const [tab, setTab] = useState('stats')
  const [gerarForm, setGerarForm] = useState({ tema: '', estilo: 'Drama moderno', total_episodios: 1, qualidade: '720p', novela_id: '' })
  const [scrapeCanal, setScrapeCanal] = useState('')
  const queryClient = useQueryClient()

  const { data: stats, isLoading: loadStats } = useQuery({ queryKey: ['admin-stats'], queryFn: adminApi.stats, refetchInterval: 15000 })
  const { data: queue = [], isLoading: loadQueue } = useQuery({ queryKey: ['admin-queue'], queryFn: adminApi.queue, refetchInterval: 5000 })
  const { data: novelasData } = useQuery({ queryKey: ['admin-novelas'], queryFn: adminApi.novelas })
  const novelas = novelasData?.items || []

  const gerarMutation = useMutation({
    mutationFn: adminApi.gerar,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-queue'] })
      setGerarForm((f) => ({ ...f, tema: '', novela_id: '' }))
    },
  })

  const aprovarMutation = useMutation({
    mutationFn: adminApi.aprovar,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-queue'] }),
  })

  const removerMutation = useMutation({
    mutationFn: adminApi.remover,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-novelas'] })
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] })
    },
  })

  const scrapeMutation = useMutation({ mutationFn: () => adminApi.scrape(scrapeCanal) })

  const handleGerar = (e) => {
    e.preventDefault()
    if (!gerarForm.tema.trim()) return
    gerarMutation.mutate({ ...gerarForm, novela_id: gerarForm.novela_id || undefined })
  }

  const TABS = [
    { id: 'stats', label: 'Estatísticas', icon: BarChart2 },
    { id: 'gerar', label: 'Gerar com IA', icon: Zap },
    { id: 'queue', label: `Fila (${queue.length})`, icon: Clock },
    { id: 'novelas', label: 'Novelas', icon: Film },
  ]

  return (
    <div className="min-h-screen pt-20 pb-20 container mx-auto px-6 max-w-6xl">
      <div className="flex items-center gap-3 mb-8">
        <h1 className="text-3xl font-bold text-white">Painel Admin</h1>
        <span className="badge bg-novelai-accent/20 text-novelai-accent">Admin</span>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-novelai-card border border-novelai-border rounded-xl p-1 mb-8 overflow-x-auto">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
              tab === id ? 'bg-novelai-accent text-white' : 'text-novelai-muted hover:text-white'
            }`}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </div>

      {/* Stats */}
      {tab === 'stats' && (
        <div>
          {loadStats ? (
            <div className="flex justify-center py-20"><Loader2 className="animate-spin text-novelai-accent" size={32} /></div>
          ) : stats ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {[
                { icon: Film, label: 'Novelas', value: stats.total_novelas, color: 'text-blue-400' },
                { icon: Play, label: 'Episódios', value: stats.total_episodios, color: 'text-green-400' },
                { icon: Users, label: 'Usuários', value: stats.total_usuarios, color: 'text-purple-400' },
                { icon: Eye, label: 'Visualizações', value: stats.total_views?.toLocaleString(), color: 'text-yellow-400' },
                { icon: Clock, label: 'Gerações pendentes', value: stats.geracoes_pendentes, color: 'text-orange-400' },
                { icon: CheckCircle, label: 'Gerações concluídas', value: stats.geracoes_concluidas, color: 'text-novelai-accent' },
              ].map(({ icon: Icon, label, value, color }) => (
                <div key={label} className="card p-6">
                  <div className={`${color} mb-3`}><Icon size={24} /></div>
                  <p className="text-3xl font-bold text-white">{value ?? '—'}</p>
                  <p className="text-novelai-muted text-sm mt-1">{label}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-novelai-muted text-center py-10">Erro ao carregar estatísticas</p>
          )}

          {/* Scrape manual */}
          <div className="card p-6 mt-8">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
              <RefreshCw size={18} />
              Scraping Manual
            </h3>
            <div className="flex gap-3">
              <input
                type="text"
                value={scrapeCanal}
                onChange={(e) => setScrapeCanal(e.target.value)}
                placeholder="Canal ou URL (opcional)"
                className="input flex-1"
              />
              <button
                onClick={() => scrapeMutation.mutate()}
                disabled={scrapeMutation.isPending}
                className="btn-secondary flex items-center gap-2"
              >
                {scrapeMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                Iniciar
              </button>
            </div>
            {scrapeMutation.isSuccess && (
              <p className="text-green-400 text-sm mt-3">Scraping iniciado em background.</p>
            )}
          </div>
        </div>
      )}

      {/* Gerar com IA */}
      {tab === 'gerar' && (
        <div className="max-w-2xl">
          <div className="card p-8">
            <h2 className="text-xl font-bold text-white mb-2">Gerar Episódio com NVIDIA AI</h2>
            <p className="text-novelai-muted text-sm mb-6">
              Usa os modelos NVIDIA NIM (Mistral, TTS, Geração de Imagem, Vídeo Cosmos, Lip Sync) para criar um episódio completo.
            </p>

            <form onSubmit={handleGerar} className="space-y-5">
              <div>
                <label className="text-sm text-novelai-muted block mb-2">Tema / Sinopse *</label>
                <textarea
                  rows={3}
                  value={gerarForm.tema}
                  onChange={(e) => setGerarForm((f) => ({ ...f, tema: e.target.value }))}
                  placeholder="Ex: Dois rivais no mercado financeiro descobrem que são irmãos separados ao nascer..."
                  className="input resize-none"
                  required
                  minLength={3}
                  maxLength={200}
                />
                <p className="text-novelai-muted text-xs mt-1 text-right">{gerarForm.tema.length}/200</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-novelai-muted block mb-2">Estilo</label>
                  <select
                    value={gerarForm.estilo}
                    onChange={(e) => setGerarForm((f) => ({ ...f, estilo: e.target.value }))}
                    className="input"
                  >
                    {['Drama moderno', 'Romance', 'Suspense', 'Comédia', 'Ficção Científica', 'Mistério'].map((e) => (
                      <option key={e} value={e}>{e}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm text-novelai-muted block mb-2">Qualidade</label>
                  <select
                    value={gerarForm.qualidade}
                    onChange={(e) => setGerarForm((f) => ({ ...f, qualidade: e.target.value }))}
                    className="input"
                  >
                    {['480p', '720p', '1080p'].map((q) => (
                      <option key={q} value={q}>{q}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-novelai-muted block mb-2">Episódios a gerar</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={gerarForm.total_episodios}
                    onChange={(e) => setGerarForm((f) => ({ ...f, total_episodios: parseInt(e.target.value) || 1 }))}
                    className="input"
                  />
                </div>
                <div>
                  <label className="text-sm text-novelai-muted block mb-2">Adicionar à novela (opcional)</label>
                  <select
                    value={gerarForm.novela_id}
                    onChange={(e) => setGerarForm((f) => ({ ...f, novela_id: e.target.value }))}
                    className="input"
                  >
                    <option value="">Nova novela</option>
                    {novelas.map((n) => (
                      <option key={n.id} value={n.id}>{n.titulo}</option>
                    ))}
                  </select>
                </div>
              </div>

              {gerarMutation.isError && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-lg px-4 py-3">
                  Erro ao enfileirar. Verifique o backend e a chave NVIDIA.
                </div>
              )}

              {gerarMutation.isSuccess && (
                <div className="bg-green-500/10 border border-green-500/30 text-green-400 text-sm rounded-lg px-4 py-3">
                  Geração enfileirada! Acompanhe na aba Fila.
                </div>
              )}

              <button
                type="submit"
                disabled={gerarMutation.isPending || !gerarForm.tema.trim()}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                {gerarMutation.isPending ? (
                  <><Loader2 size={16} className="animate-spin" /> Enfileirando...</>
                ) : (
                  <><Zap size={16} /> Gerar Episódio com IA</>
                )}
              </button>
            </form>
          </div>

          <div className="card p-6 mt-6">
            <h3 className="text-white font-semibold mb-3">Pipeline de Geração (NVIDIA NIM)</h3>
            <ol className="space-y-2 text-sm text-novelai-muted">
              {[
                ['Roteiro', 'mistralai/mistral-medium-3.5-128b'],
                ['Voz', 'resemble-ai/chatterbox-multilingual-tts'],
                ['Imagens', 'qwen/qwen-image'],
                ['Vídeo', 'nvidia/cosmos3-nano'],
                ['Lip Sync', 'nvidia/lip-sync'],
                ['Moderação', 'nvidia/nemotron-3-content-safety'],
                ['OCR', 'nvidia/nemotron-ocr-v2'],
                ['Detector IA', 'nvidia/synthetic-video-detector'],
              ].map(([step, model], i) => (
                <li key={i} className="flex gap-3">
                  <span className="text-novelai-accent font-bold w-5 flex-shrink-0">{i + 1}.</span>
                  <span className="text-white">{step}</span>
                  <span className="ml-auto font-mono text-xs text-novelai-muted">{model}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}

      {/* Fila */}
      {tab === 'queue' && (
        <div>
          {loadQueue ? (
            <div className="flex justify-center py-20"><Loader2 className="animate-spin text-novelai-accent" size={32} /></div>
          ) : queue.length === 0 ? (
            <div className="text-center py-20 text-novelai-muted">
              <Clock size={48} className="mx-auto mb-4 opacity-30" />
              <p>Fila vazia</p>
            </div>
          ) : (
            <div className="space-y-3">
              {queue.map((item) => (
                <div key={item.id} className="card p-5 flex items-start gap-4">
                  <div className={`px-2 py-1 rounded text-xs font-medium flex-shrink-0 mt-0.5 ${STATUS_COLORS[item.status] || 'text-novelai-muted bg-novelai-border'}`}>
                    {item.status}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium truncate">{item.parametros?.tema || 'Sem título'}</p>
                    <p className="text-novelai-muted text-xs mt-1">
                      {item.tipo} · {item.parametros?.estilo} · {item.parametros?.qualidade}
                    </p>
                    {item.erro_mensagem && (
                      <p className="text-red-400 text-xs mt-2 truncate">{item.erro_mensagem}</p>
                    )}
                    {item.video_url_resultado && (
                      <p className="text-green-400 text-xs mt-2 truncate">{item.video_url_resultado}</p>
                    )}
                    <p className="text-novelai-muted text-xs mt-1">
                      {new Date(item.criado_em).toLocaleString('pt-BR')}
                    </p>
                  </div>
                  <div className="flex flex-col gap-2 flex-shrink-0">
                    {item.status === 'concluido' && (
                      <button
                        onClick={() => aprovarMutation.mutate(item.id)}
                        disabled={aprovarMutation.isPending}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-green-500/20 text-green-400 hover:bg-green-500/30 rounded-lg text-xs font-medium transition-colors"
                      >
                        <CheckCircle size={14} />
                        Publicar
                      </button>
                    )}
                    {item.status === 'processando' && (
                      <div className="flex items-center gap-1.5 px-3 py-1.5 text-blue-400 text-xs">
                        <Loader2 size={14} className="animate-spin" />
                        Processando...
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Gerenciar novelas */}
      {tab === 'novelas' && (
        <div>
          <div className="space-y-3">
            {novelas.map((n) => (
              <div key={n.id} className="card p-4 flex items-center gap-4">
                {n.poster_url && (
                  <img src={n.poster_url} alt="" className="w-14 h-20 object-cover rounded-lg flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-white font-medium truncate">{n.titulo}</p>
                  <div className="flex gap-3 text-novelai-muted text-xs mt-1 flex-wrap">
                    <span>{n.total_episodios} ep.</span>
                    <span>⭐ {n.rating_medio?.toFixed(1)}</span>
                    <span>{n.views?.toLocaleString()} views</span>
                    {n.origem === 'gerada_ia' && <span className="text-purple-400">IA</span>}
                  </div>
                </div>
                <button
                  onClick={() => {
                    if (window.confirm(`Remover "${n.titulo}" e todos os episódios?`)) {
                      removerMutation.mutate(n.id)
                    }
                  }}
                  disabled={removerMutation.isPending}
                  className="p-2 text-novelai-muted hover:text-red-400 transition-colors flex-shrink-0"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            ))}
            {novelas.length === 0 && (
              <div className="text-center py-20 text-novelai-muted">
                <Film size={48} className="mx-auto mb-4 opacity-30" />
                <p>Nenhuma novela cadastrada</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
