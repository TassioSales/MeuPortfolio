"use client";
import { create } from "zustand";
import { api, type UserProfile } from "@/lib/api";

interface AuthState {
  token: string | null;
  user: UserProfile | null;
  setToken: (token: string) => void;
  loadUser: () => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: typeof window !== "undefined" ? localStorage.getItem("ascend_token") : null,
  user: null,
  setToken: (token) => {
    localStorage.setItem("ascend_token", token);
    set({ token });
  },
  loadUser: async () => {
    try {
      const user = await api.auth.me();
      set({ user });
    } catch {
      set({ token: null, user: null });
      localStorage.removeItem("ascend_token");
    }
  },
  logout: () => {
    localStorage.removeItem("ascend_token");
    set({ token: null, user: null });
  },
}));
