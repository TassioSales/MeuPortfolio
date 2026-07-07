import { useState } from 'react'
import { X, Eye, EyeOff } from 'lucide-react'
import { useAuthStore } from '../store/authStore'

export default function AuthModal({ mode, onClose, onSwitchMode }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [nome, setNome] = useState('')
  const [showPass, setShowPass] = useState(false)
  const { login, register, isLoading, error, clearError } = useAuthStore()

  const isLogin = mode === 'login'

  const handleSubmit = async (e) => {
    e.preventDefault()
    clearError()
    const ok = isLogin ? await login(email, password) : await register(nome, email, password)
    if (ok) onClose()
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative card p-8 w-full max-w-md animate-slide-up">
        <button onClick={onClose} className="absolute top-4 right-4 text-novelai-muted hover:text-white transition-colors">
          <X size={20} />
        </button>

        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-white">{isLogin ? 'Entrar' : 'Criar conta'}</h2>
          <p className="text-novelai-muted text-sm mt-2">
            {isLogin ? 'Acesse sua conta NovelAI' : 'Comece a assistir gratuitamente'}
          </p>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-lg px-4 py-3 mb-6">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div>
              <label className="text-sm text-novelai-muted block mb-1.5">Nome</label>
              <input
                type="text"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Seu nome"
                className="input"
                required
                minLength={2}
              />
            </div>
          )}

          <div>
            <label className="text-sm text-novelai-muted block mb-1.5">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="seu@email.com"
              className="input"
              required
            />
          </div>

          <div>
            <label className="text-sm text-novelai-muted block mb-1.5">Senha</label>
            <div className="relative">
              <input
                type={showPass ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Mínimo 8 caracteres"
                className="input pr-12"
                required
                minLength={8}
              />
              <button
                type="button"
                onClick={() => setShowPass(!showPass)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-novelai-muted hover:text-white transition-colors"
              >
                {showPass ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <button type="submit" disabled={isLoading} className="btn-primary w-full mt-6">
            {isLoading ? 'Aguarde...' : isLogin ? 'Entrar' : 'Criar conta'}
          </button>
        </form>

        <p className="text-center text-novelai-muted text-sm mt-6">
          {isLogin ? 'Não tem conta?' : 'Já tem conta?'}{' '}
          <button
            onClick={() => { clearError(); onSwitchMode(isLogin ? 'register' : 'login') }}
            className="text-novelai-accent hover:underline font-medium"
          >
            {isLogin ? 'Criar agora' : 'Entrar'}
          </button>
        </p>
      </div>
    </div>
  )
}
