import { useState } from 'react'
import { User, Settings, LogOut, Save } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { salvarPreferencias } from '../lib/api'
import { useNavigate } from 'react-router-dom'

const QUALIDADES = ['480p', '720p', '1080p']
const IDIOMAS = [
  { value: 'pt', label: 'Português' },
  { value: 'en', label: 'Inglês' },
  { value: 'es', label: 'Espanhol' },
  { value: 'ja', label: 'Japonês' },
]
const LEGENDAS = [
  { value: 'off', label: 'Desativado' },
  { value: 'pt', label: 'Português' },
  { value: 'en', label: 'Inglês' },
  { value: 'es', label: 'Espanhol' },
]

export default function Profile() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const [prefs, setPrefs] = useState({
    idioma_preferido: user?.idioma_preferido || 'pt',
    qualidade_padrao: user?.qualidade_padrao || '720p',
    legendas_padrao: user?.legendas_padrao || 'off',
  })
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      await salvarPreferencias(prefs)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch {
      // silent
    } finally {
      setSaving(false)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <div className="min-h-screen pt-20 pb-20 container mx-auto px-6 max-w-2xl">
      <h1 className="text-3xl font-bold text-white mb-10">Perfil</h1>

      {/* Avatar e nome */}
      <div className="card p-6 mb-6 flex items-center gap-6">
        <div className="w-20 h-20 rounded-full bg-novelai-accent/20 flex items-center justify-center flex-shrink-0">
          {user?.foto_url ? (
            <img src={user.foto_url} alt="" className="w-full h-full rounded-full object-cover" />
          ) : (
            <User size={36} className="text-novelai-accent" />
          )}
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">{user?.nome}</h2>
          <p className="text-novelai-muted text-sm mt-1">{user?.email}</p>
          {user?.role === 'admin' && (
            <span className="badge bg-novelai-accent/20 text-novelai-accent mt-2 inline-block">Admin</span>
          )}
        </div>
      </div>

      {/* Preferências */}
      <div className="card p-6 mb-6">
        <h3 className="text-white font-semibold mb-6 flex items-center gap-2">
          <Settings size={18} />
          Preferências
        </h3>

        <div className="space-y-5">
          <div>
            <label className="text-sm text-novelai-muted block mb-2">Qualidade padrão</label>
            <div className="flex gap-3">
              {QUALIDADES.map((q) => (
                <button
                  key={q}
                  onClick={() => setPrefs((p) => ({ ...p, qualidade_padrao: q }))}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    prefs.qualidade_padrao === q
                      ? 'bg-novelai-accent text-white'
                      : 'bg-novelai-border text-novelai-muted hover:text-white'
                  }`}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-sm text-novelai-muted block mb-2">Idioma preferido</label>
            <select
              value={prefs.idioma_preferido}
              onChange={(e) => setPrefs((p) => ({ ...p, idioma_preferido: e.target.value }))}
              className="input max-w-xs"
            >
              {IDIOMAS.map((i) => (
                <option key={i.value} value={i.value}>{i.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-sm text-novelai-muted block mb-2">Legendas padrão</label>
            <select
              value={prefs.legendas_padrao}
              onChange={(e) => setPrefs((p) => ({ ...p, legendas_padrao: e.target.value }))}
              className="input max-w-xs"
            >
              {LEGENDAS.map((l) => (
                <option key={l.value} value={l.value}>{l.label}</option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-primary mt-8 flex items-center gap-2"
        >
          <Save size={16} />
          {saving ? 'Salvando...' : saved ? 'Salvo!' : 'Salvar preferências'}
        </button>
      </div>

      {/* Logout */}
      <button
        onClick={handleLogout}
        className="w-full card p-4 flex items-center gap-3 text-red-400 hover:text-red-300 hover:border-red-500/40 transition-colors"
      >
        <LogOut size={18} />
        Sair da conta
      </button>
    </div>
  )
}
