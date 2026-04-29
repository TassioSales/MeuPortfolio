"use client";

import { create } from "zustand";

import { FuelName } from "@/lib/types";

interface DashboardState {
  fuel: FuelName;
  state: string;
  city: string;
  compareWith: FuelName;
  startDate: string;
  endDate: string;
  setFuel: (fuel: FuelName) => void;
  setState: (state: string) => void;
  setCity: (city: string) => void;
  setCompareWith: (fuel: FuelName) => void;
  setDateRange: (start: string, end: string) => void;
}

const lastYear = new Date();
lastYear.setFullYear(lastYear.getFullYear() - 1);
const today = new Date();

export const useDashboardStore = create<DashboardState>((set) => ({
  fuel: "gasolina",
  state: "SP",
  city: "",
  compareWith: "etanol",
  startDate: lastYear.toISOString().split("T")[0],
  endDate: today.toISOString().split("T")[0],
  setFuel: (fuel) => set((current) => ({ fuel, compareWith: fuel === current.compareWith ? "etanol" : current.compareWith })),
  setState: (state) => set({ state }),
  setCity: (city) => set({ city }),
  setCompareWith: (compareWith) => set({ compareWith }),
  setDateRange: (startDate, endDate) => set({ startDate, endDate }),
}));
