"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { portfolioService, analyticsService } from "@/services/api";

interface PortfolioContextType {
  portfolio: any[];
  registeredAssets: any[];
  riskData: any;
  loading: boolean;
  apiStatus: "online" | "offline";
  errorMessage: string | null;
  refreshAll: () => Promise<void>;
  showToast: (msg: string, type: "success" | "error") => void;
  toast: { msg: string; type: "success" | "error" } | null;
}

const PortfolioContext = createContext<PortfolioContextType | undefined>(undefined);

export const PortfolioProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [portfolio, setPortfolio] = useState<any[]>([]);
  const [registeredAssets, setRegisteredAssets] = useState<any[]>([]);
  const [riskData, setRiskData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [apiStatus, setApiStatus] = useState<"online" | "offline">("online");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" } | null>(null);

  const showToast = useCallback((msg: string, type: "success" | "error") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  const refreshAll = async () => {
    setLoading(true);
    try {
      const [pRes, aRes, rRes] = await Promise.all([
        portfolioService.getPortfolio(),
        portfolioService.getAssets(),
        analyticsService.getRisk(),
      ]);
      setPortfolio(pRes.data);
      setRegisteredAssets(aRes.data);
      setRiskData(rRes.data);
      setApiStatus("online");
      setErrorMessage(null);
    } catch (error: any) {
      console.error("Error refreshing data:", error);
      setApiStatus("offline");
      setErrorMessage(error?.message || "Nao foi possivel conectar ao backend");
      showToast("Backend offline na porta 8000", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshAll();
  }, []);

  return (
    <PortfolioContext.Provider
      value={{
        portfolio,
        registeredAssets,
        riskData,
        loading,
        apiStatus,
        errorMessage,
        refreshAll,
        showToast,
        toast,
      }}
    >
      {children}
    </PortfolioContext.Provider>
  );
};

export const usePortfolio = () => {
  const context = useContext(PortfolioContext);
  if (context === undefined) {
    throw new Error("usePortfolio must be used within a PortfolioProvider");
  }
  return context;
};
