"use client";

import { create } from "zustand";
import * as authApi from "@/lib/auth";
import { ApiError } from "@/lib/api";
import type { User } from "@/types";

interface AuthState {
  user: User | null;
  /** true enquanto a sessão inicial ainda não foi resolvida. */
  isLoading: boolean;
  /**
   * A sessão não pôde ser confirmada porque o servidor não respondeu.
   *
   * Diferente de "não tem sessão": os cookies continuam lá e válidos. Quem lê
   * isto (o layout do painel) precisa oferecer uma nova tentativa em vez de
   * mandar para o login — mandar seria pior que inútil, porque o middleware vê
   * o cookie e devolve para o painel, e a pessoa fica no pingue-pongue.
   */
  servidorForaDoAr: boolean;
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
  servidorForaDoAr: false,
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
      set({ user: null, isLoading: false, servidorForaDoAr: false });
      return;
    }

    try {
      const user = await authApi.getCurrentUser();
      set({ user, isLoading: false, servidorForaDoAr: false });
    } catch (error) {
      // Só o servidor encerra sessão.
      //
      // Aqui se chamava `logout()` para qualquer erro — e `logout()` apaga os
      // cookies. Bastava o backend estar reiniciando, um 502 do proxy ou o
      // wi-fi piscar para a sessão ser destruída no cliente, com token válido
      // por sete dias. Quem estava com o painel aberto durante um
      // `docker compose up -d backend` era deslogado por isso.
      //
      // 401 aqui já passou pela renovação do `api.ts` e falhou: aí sim acabou.
      // Qualquer outra coisa é problema de rede, e o que ela pede é tentar de
      // novo, não recomeçar a sessão.
      if (error instanceof ApiError && error.status === 401) {
        authApi.logout();
        set({ user: null, isLoading: false, servidorForaDoAr: false });
        return;
      }

      set({
        user: null,
        isLoading: false,
        servidorForaDoAr: true,
        error: messageFrom(error, "Não foi possível falar com o servidor."),
      });
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
