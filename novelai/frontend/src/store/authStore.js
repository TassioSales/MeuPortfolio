import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { login as apiLogin, register as apiRegister, getMe } from '../lib/api'

export const useAuthStore = create(
  persist(
    (set, get) => ({
      token: null,
      refreshToken: null,
      user: null,
      isLoading: false,
      error: null,

      login: async (email, password) => {
        set({ isLoading: true, error: null })
        try {
          const data = await apiLogin({ email, password })
          localStorage.setItem('novelai_token', data.access_token)
          localStorage.setItem('novelai_refresh', data.refresh_token)
          const me = await getMe()
          set({ token: data.access_token, refreshToken: data.refresh_token, user: me, isLoading: false })
          return true
        } catch (e) {
          set({ error: e.response?.data?.detail || 'Erro ao fazer login', isLoading: false })
          return false
        }
      },

      register: async (nome, email, password) => {
        set({ isLoading: true, error: null })
        try {
          const data = await apiRegister({ nome, email, password })
          localStorage.setItem('novelai_token', data.access_token)
          localStorage.setItem('novelai_refresh', data.refresh_token)
          const me = await getMe()
          set({ token: data.access_token, refreshToken: data.refresh_token, user: me, isLoading: false })
          return true
        } catch (e) {
          set({ error: e.response?.data?.detail || 'Erro ao criar conta', isLoading: false })
          return false
        }
      },

      logout: () => {
        localStorage.removeItem('novelai_token')
        localStorage.removeItem('novelai_refresh')
        set({ token: null, refreshToken: null, user: null })
      },

      refreshUser: async () => {
        try {
          const me = await getMe()
          set({ user: me })
        } catch {
          get().logout()
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'novelai-auth',
      partialize: (s) => ({ token: s.token, refreshToken: s.refreshToken, user: s.user }),
    }
  )
)
