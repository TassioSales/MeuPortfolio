"use client";

import { create } from "zustand";
import * as authApi from "@/lib/auth";
import { ApiError } from "@/lib/api";
import type { User } from "@/types";

interface AuthState {
  user: User | null;
  /** true enquanto a sessão inicial ainda não foi resolvida. */
  isLoading: boolean;
  error: string | null;

  login: (email: string, senha: string) => Promise<void>;
  register: (nome: string, email: string, senha: string) => Promise<void>;
  logout: () => void;
  /** Recupera a sessão a partir do token em cookie (chamado no mount). */
  loadSession: () => Promise<void>;
  clearError: () => void;
}

function messageFrom(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return fallback;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  error: null,

  login: async (email, senha) => {
    set({ isLoading: true, error: null });
    try {
      const user = await authApi.login(email, senha);
      set({ user, isLoading: false });
    } catch (error) {
      set({
        user: null,
        isLoading: false,
        error: messageFrom(error, "Não foi possível entrar. Tente novamente."),
      });
      throw error;
    }
  },

  register: async (nome, email, senha) => {
    set({ isLoading: true, error: null });
    try {
      await authApi.register(nome, email, senha);
      // Registro não devolve token — autentica em seguida para já entrar logado.
      const user = await authApi.login(email, senha);
      set({ user, isLoading: false });
    } catch (error) {
      set({
        isLoading: false,
        error: messageFrom(error, "Não foi possível criar a conta."),
      });
      throw error;
    }
  },

  logout: () => {
    authApi.logout();
    set({ user: null, error: null, isLoading: false });
  },

  loadSession: async () => {
    if (!authApi.hasStoredSession()) {
      set({ user: null, isLoading: false });
      return;
    }

    try {
      const user = await authApi.getCurrentUser();
      set({ user, isLoading: false });
    } catch {
      // Token inválido/expirado e sem refresh possível: sessão descartada.
      authApi.logout();
      set({ user: null, isLoading: false });
    }
  },

  clearError: () => set({ error: null }),
}));

/**
 * Hook de autenticação usado pelos componentes.
 *
 * `isAuthenticated` é derivado do usuário carregado, não do cookie, para
 * refletir apenas sessões que o backend confirmou.
 */
export function useAuth() {
  const state = useAuthStore();
  return { ...state, isAuthenticated: state.user !== null };
}
