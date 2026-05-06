"use client";

import React, { useState } from "react";
import { usePortfolio } from "@/context/PortfolioContext";
import TickerTape from "@/components/layout/TickerTape";
import ExecutiveBrief from "@/components/dashboard/ExecutiveBrief";
import DashboardStats from "@/components/dashboard/DashboardStats";
import AssetTable from "@/components/dashboard/AssetTable";
import AllocationChart from "@/components/dashboard/AllocationChart";
import MarketRadar from "@/components/radar/MarketRadar";
import WalletBuilder from "@/components/wallet/WalletBuilder";
import ChatBot from "@/components/ai/ChatBot";
import {
  Briefcase, Radar, Wallet, Activity, ShieldAlert, CheckCircle2
} from "lucide-react";

export default function Home() {
  const { toast, apiStatus, errorMessage, refreshAll } = usePortfolio();
  const [activeTab, setActiveTab] = useState<"portfolio" | "radar" | "wallet">("portfolio");
  const [selectedRadarTicker, setSelectedRadarTicker] = useState<string | null>(null);

  const handleSelectAsset = (ticker: string) => {
    setSelectedRadarTicker(ticker);
    setActiveTab("radar");
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-white font-sans selection:bg-purple-500/30">
      
      <TickerTape />

      <div className="max-w-7xl mx-auto p-4 md:p-8 space-y-12">
        {toast && (
          <div className={`fixed top-14 right-8 p-4 rounded-2xl shadow-2xl z-[60] transition-all font-black flex items-center gap-3 animate-in slide-in-from-right duration-300 ${toast.type === 'success' ? 'bg-emerald-600 border border-emerald-400/20' : 'bg-red-600 border border-red-400/20'}`}>
            {toast.type === 'success' && <CheckCircle2 size={20} />} {toast.msg}
          </div>
        )}

        {/* Header Section */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div>
            <div className="flex items-center gap-4 mb-2">
              <h1 className="text-5xl font-black tracking-tighter text-gradient">
                WealthMap
              </h1>
              <span className="px-3 py-1 bg-white/5 border border-white/10 text-white text-[10px] font-black rounded-full uppercase tracking-widest shadow-xl">
                Enterprise v2.0
              </span>
            </div>
            <p className="text-neutral-500 text-sm font-medium flex items-center gap-2">
              <Activity size={16} className="text-blue-500" />
              Professional portfolio intelligence, risk monitoring and allocation control
            </p>
          </div>
          
          <div className="flex bg-neutral-900/50 p-1.5 rounded-2xl border border-white/5 backdrop-blur-xl">
            <button 
              onClick={() => setActiveTab("portfolio")} 
              className={`px-6 py-3 rounded-xl font-black text-xs transition-all flex items-center gap-2 ${activeTab === "portfolio" ? "bg-white text-black shadow-2xl" : "text-neutral-500 hover:text-white"}`}
            >
              <Briefcase size={16} /> OVERVIEW
            </button>
            <button 
              onClick={() => setActiveTab("radar")} 
              className={`px-6 py-3 rounded-xl font-black text-xs transition-all flex items-center gap-2 ${activeTab === "radar" ? "bg-white text-black shadow-2xl" : "text-neutral-500 hover:text-white"}`}
            >
              <Radar size={16} /> RADAR
            </button>
            <button 
              onClick={() => setActiveTab("wallet")} 
              className={`px-6 py-3 rounded-xl font-black text-xs transition-all flex items-center gap-2 ${activeTab === "wallet" ? "bg-emerald-500 text-white shadow-2xl shadow-emerald-500/20" : "text-neutral-500 hover:text-white"}`}
            >
              <Wallet size={16} /> BUILDER
            </button>
          </div>
        </header>

        {apiStatus === "offline" && (
          <section className="glass border border-red-500/30 bg-red-500/10 rounded-2xl p-5 flex flex-col md:flex-row gap-4 md:items-center md:justify-between">
            <div className="flex items-start gap-3">
              <ShieldAlert className="text-red-400 mt-0.5" size={22} />
              <div>
                <h2 className="font-black text-red-100">Backend desconectado</h2>
                <p className="text-sm text-red-100/70 mt-1">
                  A API em `localhost:8000` nao respondeu. Rode `start_wealthmap.bat` ou confira a janela WealthMap Backend.
                  {errorMessage ? ` Detalhe: ${errorMessage}` : ""}
                </p>
              </div>
            </div>
            <button
              onClick={refreshAll}
              className="px-5 py-3 rounded-xl bg-red-500 hover:bg-red-400 text-white font-black text-xs transition"
            >
              TENTAR NOVAMENTE
            </button>
          </section>
        )}

        {/* Tab Content */}
        <main className="min-h-[600px]">
          {activeTab === "portfolio" && (
            <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <ExecutiveBrief />
              <DashboardStats />
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2">
                  <AssetTable onSelectAsset={handleSelectAsset} />
                </div>
                <div className="lg:col-span-1">
                  <AllocationChart />
                </div>
              </div>
            </div>
          )}

          {activeTab === "radar" && (
            <MarketRadar initialTicker={selectedRadarTicker} />
          )}

          {activeTab === "wallet" && (
            <WalletBuilder />
          )}
        </main>

        {/* Footer */}
        <footer className="pt-12 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-4 text-neutral-600">
          <div className="text-[10px] font-black uppercase tracking-widest">
            WealthMap Quants Layer © 2026
          </div>
          <div className="flex gap-6 items-center">
            <span className="flex items-center gap-1.5 text-[10px] font-black">
              <div className={`w-1 h-1 rounded-full ${apiStatus === "online" ? "bg-emerald-500" : "bg-red-500"}`}></div>
              API {apiStatus === "online" ? "STABLE" : "OFFLINE"}
            </span>
            <span className="flex items-center gap-1.5 text-[10px] font-black">
              <div className="w-1 h-1 rounded-full bg-emerald-500"></div> WS CONNECTED
            </span>
          </div>
        </footer>
      </div>

      <ChatBot />
    </div>
  );
}
