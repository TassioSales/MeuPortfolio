import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getComentarios, criarComentario, deletarComentario } from '../lib/api'
import { useAuthStore } from '../store/authStore'
import { Send, Trash2, MessageCircle } from 'lucide-react'

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m atrás`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h atrás`
  return `${Math.floor(hrs / 24)}d atrás`
}

export default function Comments({ novelaId, episodeId }) {
  const [text, setText] = useState('')
  const { user, token } = useAuthStore()
  const queryClient = useQueryClient()

  const { data: comentarios = [], isLoading } = useQuery({
    queryKey: ['comentarios', novelaId],
    queryFn: () => getComentarios(novelaId),
  })

  const addMutation = useMutation({
    mutationFn: ({ texto }) => criarComentario(episodeId, texto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comentarios', novelaId] })
      setText('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => deletarComentario(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['comentarios', novelaId] }),
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!text.trim() || !episodeId) return
    addMutation.mutate({ texto: text.trim() })
  }

  return (
    <div>
      {/* Formulário */}
      {token ? (
        <form onSubmit={handleSubmit} className="mb-8">
          <div className="flex gap-3 items-start">
            <div className="w-9 h-9 rounded-full bg-novelai-accent/20 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-novelai-accent font-bold text-sm">
                {user?.nome?.charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="flex-1">
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Adicione um comentário..."
                rows={3}
                className="input resize-none"
                maxLength={2000}
              />
              <div className="flex justify-between items-center mt-2">
                <span className="text-novelai-muted text-xs">{text.length}/2000</span>
                <button
                  type="submit"
                  disabled={!text.trim() || addMutation.isPending || !episodeId}
                  className="btn-primary py-2 px-4 text-sm flex items-center gap-2 disabled:opacity-50"
                >
                  <Send size={14} />
                  {addMutation.isPending ? 'Enviando...' : 'Comentar'}
                </button>
              </div>
            </div>
          </div>
        </form>
      ) : (
        <div className="card p-6 text-center mb-8">
          <MessageCircle size={32} className="mx-auto mb-3 text-novelai-muted" />
          <p className="text-novelai-muted text-sm">Faça login para comentar</p>
        </div>
      )}

      {/* Lista */}
      {isLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex gap-3">
              <div className="skeleton w-9 h-9 rounded-full flex-shrink-0" />
              <div className="flex-1 space-y-2">
                <div className="skeleton h-4 w-32 rounded" />
                <div className="skeleton h-3 w-full rounded" />
              </div>
            </div>
          ))}
        </div>
      ) : comentarios.length === 0 ? (
        <div className="text-center py-12 text-novelai-muted">
          <MessageCircle size={36} className="mx-auto mb-3 opacity-30" />
          <p>Seja o primeiro a comentar!</p>
        </div>
      ) : (
        <div className="space-y-6">
          <p className="text-novelai-muted text-sm">{comentarios.length} comentário{comentarios.length !== 1 ? 's' : ''}</p>
          {comentarios.map((c) => (
            <div key={c.id} className="flex gap-3">
              <div className="w-9 h-9 rounded-full bg-novelai-accent/10 flex items-center justify-center flex-shrink-0">
                {c.usuario_foto ? (
                  <img src={c.usuario_foto} className="w-full h-full rounded-full object-cover" alt="" />
                ) : (
                  <span className="text-novelai-accent font-bold text-sm">
                    {c.usuario_nome?.charAt(0).toUpperCase()}
                  </span>
                )}
              </div>
              <div className="flex-1">
                <div className="flex items-baseline gap-3">
                  <span className="text-white font-medium text-sm">{c.usuario_nome}</span>
                  <span className="text-novelai-muted text-xs">{timeAgo(c.criado_em)}</span>
                </div>
                <p className="text-white/80 text-sm mt-1 leading-relaxed">{c.texto}</p>
              </div>
              {user?.id === c.user_id && (
                <button
                  onClick={() => deleteMutation.mutate(c.id)}
                  className="text-novelai-muted hover:text-red-400 transition-colors p-1 self-start"
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
