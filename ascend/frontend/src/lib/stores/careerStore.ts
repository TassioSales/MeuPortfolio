"use client";
import { create } from "zustand";
import { api, type CareerPathResponse, type AnalyticsSummary } from "@/lib/api";

interface CareerState {
  roadmap: CareerPathResponse | null;
  analytics: AnalyticsSummary | null;
  loading: boolean;
  fetchRoadmap: () => Promise<void>;
  fetchAnalytics: () => Promise<void>;
  updateMilestone: (index: number, status: string, minutes?: number) => Promise<void>;
}

export const useCareerStore = create<CareerState>((set, get) => ({
  roadmap: null,
  analytics: null,
  loading: false,
  fetchRoadmap: async () => {
    set({ loading: true });
    try {
      const [roadmap, analytics] = await Promise.all([
        api.career.getRoadmap(),
        api.analytics.getSummary(),
      ]);
      set({ roadmap, analytics });
    } finally {
      set({ loading: false });
    }
  },
  fetchAnalytics: async () => {
    const analytics = await api.analytics.getSummary();
    set({ analytics });
  },
  updateMilestone: async (index, status, minutes = 0) => {
    await api.career.updateMilestone(index, status, minutes);
    await get().fetchRoadmap();
  },
}));
