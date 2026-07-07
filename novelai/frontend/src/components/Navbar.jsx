import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Search, Bell, User, LogOut, List, Settings, X, Menu } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import clsx from 'clsx'
import AuthModal from './AuthModal'

export default function Navbar() {
  const [showAuth, setShowAuth] = useState(false)
  const [authMode, setAuthMode] = useState('login')
  const [showMenu, setShowMenu] = useState(false)
  const [showMobile, setShowMobile] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const menuRef = useRef(null)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, token, logout } = useAuthStore()

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    const handleClick = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setShowMenu(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  useEffect(() => setShowMobile(false), [location.pathname])

  const NAV_LINKS = [
    { to: '/', label: 'Início' },
    { to: '/browse', label: 'Novelas' },
    { to: '/busca', label: 'Buscar' },
  ]

  return (
    <>
      <nav
        className={clsx(
          'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
          scrolled || showMobile
            ? 'bg-novelai-bg/95 backdrop-blur-md border-b border-novelai-border'
            : 'bg-gradient-to-b from-black/70 to-transparent'
        )}
      >
        <div className="container mx-auto px-6 max-w-7xl">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2">
              <span className="text-novelai-accent font-extrabold text-2xl tracking-tight">NovelAI</span>
            </Link>

            {/* Desktop nav */}
            <div className="hidden md:flex items-center gap-6">
              {NAV_LINKS.map((l) => (
                <Link
                  key={l.to}
                  to={l.to}
                  className={clsx(
                    'text-sm font-medium transition-colors',
                    location.pathname === l.to ? 'text-white' : 'text-white/70 hover:text-white'
                  )}
                >
                  {l.label}
                </Link>
              ))}
            </div>

            {/* Right actions */}
            <div className="flex items-center gap-3">
              <button onClick={() => navigate('/busca')} className="text-white/80 hover:text-white p-2 transition-colors">
                <Search size={20} />
              </button>

              {token && user ? (
                <div className="relative" ref={menuRef}>
                  <button
                    onClick={() => setShowMenu(!showMenu)}
                    className="flex items-center gap-2 text-white/80 hover:text-white transition-colors"
                  >
                    <div className="w-8 h-8 rounded-full bg-novelai-accent/30 flex items-center justify-center">
                      {user.foto_url ? (
                        <img src={user.foto_url} className="w-full h-full rounded-full object-cover" alt="" />
                      ) : (
                        <User size={16} className="text-novelai-accent" />
                      )}
                    </div>
                  </button>

                  {showMenu && (
                    <div className="absolute right-0 top-12 w-52 card border border-novelai-border shadow-2xl animate-fade-in py-2">
                      <div className="px-4 py-3 border-b border-novelai-border">
                        <p className="text-white font-medium text-sm truncate">{user.nome}</p>
                        <p className="text-novelai-muted text-xs truncate">{user.email}</p>
                      </div>
                      {[
                        { icon: List, label: 'Minha lista', to: '/minha-lista' },
                        { icon: Settings, label: 'Perfil', to: '/perfil' },
                      ].map(({ icon: Icon, label, to }) => (
                        <button
                          key={to}
                          onClick={() => { navigate(to); setShowMenu(false) }}
                          className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-novelai-muted hover:text-white hover:bg-white/5 transition-colors"
                        >
                          <Icon size={16} />
                          {label}
                        </button>
                      ))}
                      {user.role === 'admin' && (
                        <button
                          onClick={() => { navigate('/admin'); setShowMenu(false) }}
                          className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-novelai-accent hover:bg-novelai-accent/10 transition-colors"
                        >
                          <Settings size={16} />
                          Admin
                        </button>
                      )}
                      <div className="border-t border-novelai-border mt-2 pt-2">
                        <button
                          onClick={() => { logout(); setShowMenu(false) }}
                          className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
                        >
                          <LogOut size={16} />
                          Sair
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => { setAuthMode('login'); setShowAuth(true) }}
                    className="text-sm font-medium text-white/80 hover:text-white transition-colors px-3 py-1.5"
                  >
                    Entrar
                  </button>
                  <button
                    onClick={() => { setAuthMode('register'); setShowAuth(true) }}
                    className="btn-primary py-1.5 px-4 text-sm"
                  >
                    Cadastrar
                  </button>
                </div>
              )}

              {/* Mobile toggle */}
              <button
                className="md:hidden text-white/80 hover:text-white p-2"
                onClick={() => setShowMobile(!showMobile)}
              >
                {showMobile ? <X size={20} /> : <Menu size={20} />}
              </button>
            </div>
          </div>

          {/* Mobile menu */}
          {showMobile && (
            <div className="md:hidden pb-4 border-t border-novelai-border pt-4 space-y-1">
              {NAV_LINKS.map((l) => (
                <Link
                  key={l.to}
                  to={l.to}
                  className={clsx(
                    'block px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    location.pathname === l.to ? 'bg-white/10 text-white' : 'text-white/70 hover:text-white hover:bg-white/5'
                  )}
                >
                  {l.label}
                </Link>
              ))}
              {token && (
                <>
                  <Link to="/minha-lista" className="block px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/5">
                    Minha lista
                  </Link>
                  <Link to="/perfil" className="block px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/5">
                    Perfil
                  </Link>
                </>
              )}
            </div>
          )}
        </div>
      </nav>

      {showAuth && <AuthModal mode={authMode} onClose={() => setShowAuth(false)} onSwitchMode={setAuthMode} />}
    </>
  )
}
