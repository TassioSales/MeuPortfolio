"use client";

import React, { useState, useEffect } from "react";
import { usePortfolio } from "@/context/PortfolioContext";
import { portfolioService } from "@/services/api";
import { Wallet, Plus, Search, DollarSign, Calendar, Cpu, Briefcase } from "lucide-react";

const WalletBuilder = () => {
  const { registeredAssets, refreshAll, showToast } = usePortfolio();
  
  // Asset Form
  const [formTicker, setFormTicker] = useState("");
  const [formName, setFormName] = useState("");
  const [formType, setFormType] = useState("STOCK");
  const [formCurrency, setFormCurrency] = useState("BRL");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Transaction Form
  const [txAssetId, setTxAssetId] = useState("");
  const [txType, setTxType] = useState("BUY");
  const [txQuantity, setTxQuantity] = useState("");
  const [txPrice, setTxPrice] = useState("");
  const [txDate, setTxDate] = useState(new Date().toISOString().split("T")[0]);

  const [submittingAsset, setSubmittingAsset] = useState(false);
  const [submittingTx, setSubmittingTx] = useState(false);

  useEffect(() => {
    if (formTicker.length > 1) {
      const delay = setTimeout(async () => {
        setIsSearching(true);
        try {
          const res = await portfolioService.searchAssets(formTicker);
          setSearchResults(res.data);
        } catch (err) {
          setSearchResults([]);
        } finally {
          setIsSearching(false);
        }
      }, 500);
      return () => clearTimeout(delay);
    } else {
      setSearchResults([]);
    }
  }, [formTicker]);

  const handleAddAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingAsset(true);
    try {
      await portfolioService.createAsset({
        ticker: formTicker.toUpperCase(),
        name: formName,
        asset_type: formType,
        currency: formCurrency
      });
      showToast(`${formTicker} registered successfully`, "success");
      setFormTicker(""); setFormName("");
      refreshAll();
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Error registering asset", "error");
    } finally {
      setSubmittingAsset(false);
    }
  };

  const handleAddTransaction = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingTx(true);
    try {
      await portfolioService.createTransaction({
        asset_id: parseInt(txAssetId),
        transaction_type: txType,
        quantity: parseFloat(txQuantity),
        price_per_unit: parseFloat(txPrice),
        date: txDate
      });
      showToast("Transaction executed", "success");
      setTxQuantity(""); setTxPrice("");
      refreshAll();
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Error in transaction", "error");
    } finally {
      setSubmittingTx(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="bg-gradient-to-r from-emerald-600/20 to-blue-600/20 border border-emerald-500/20 p-8 rounded-3xl">
        <h2 className="text-3xl font-black text-emerald-400 flex items-center gap-3 mb-2">
          <Wallet size={32} /> Wallet Orchestrator
        </h2>
        <p className="text-neutral-400 font-medium">Manage your institutional positions and assets for ML risk evaluation.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Step 1: Register Asset */}
        <div className="glass p-8 rounded-3xl border-t-4 border-t-emerald-500/50">
          <h3 className="text-xl font-black mb-8 flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-400 text-sm">1</div>
            Asset Registration
          </h3>
          <form onSubmit={handleAddAsset} className="space-y-6">
            <div className="relative">
              <label htmlFor="asset-search-input" className="block text-[10px] uppercase tracking-widest font-black text-neutral-500 mb-2">Smart Search</label>
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-600" size={16} />
                <input 
                  id="asset-search-input"
                  required value={formTicker} onChange={e=>setFormTicker(e.target.value)} 
                  placeholder="Ticker or Name..."
                  title="Search asset by ticker or name"
                  className="w-full bg-neutral-900/50 border border-white/5 rounded-xl pl-12 pr-4 py-3 focus:border-emerald-500/50 focus:outline-none uppercase font-bold transition"
                />
                {isSearching && <Cpu size={16} className="absolute right-4 top-1/2 -translate-y-1/2 text-emerald-500 animate-spin" />}
              </div>
              {searchResults.length > 0 && (
                <div className="absolute z-50 w-full mt-2 glass rounded-xl shadow-2xl overflow-hidden border border-white/10">
                  {searchResults.map((res, i) => (
                    <div key={i} onClick={() => {
                      setFormTicker(res.ticker);
                      setFormName(res.name);
                      setFormType(res.asset_type);
                      setSearchResults([]);
                    }} className="px-4 py-4 hover:bg-white/5 cursor-pointer border-b border-white/5 last:border-0 flex justify-between items-center group">
                      <div>
                        <div className="font-black text-white group-hover:text-emerald-400 transition">{res.ticker}</div>
                        <div className="text-[10px] text-neutral-500 uppercase">{res.name}</div>
                      </div>
                      <span className="text-[9px] bg-white/5 px-2 py-1 rounded-md font-black text-neutral-400 uppercase">{res.asset_type}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div>
              <label htmlFor="asset-name-input" className="block text-[10px] uppercase tracking-widest font-black text-neutral-500 mb-2">Display Name</label>
              <input
                id="asset-name-input"
                required
                value={formName}
                onChange={e=>setFormName(e.target.value)}
                placeholder="Asset display name"
                title="Asset display name"
                className="w-full bg-neutral-900/50 border border-white/5 rounded-xl px-4 py-3 focus:border-emerald-500/50 focus:outline-none font-bold"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="asset-type-select" className="block text-[10px] uppercase tracking-widest font-black text-neutral-500 mb-2">Type</label>
                <select
                  id="asset-type-select"
                  value={formType}
                  onChange={e=>setFormType(e.target.value)}
                  title="Asset type"
                  className="w-full bg-neutral-900/50 border border-white/5 rounded-xl px-4 py-3 focus:border-emerald-500/50 focus:outline-none font-bold"
                >
                  <option value="STOCK">Stock / Equity</option>
                  <option value="FII">FII / REIT</option>
                  <option value="CRYPTO">Crypto</option>
                  <option value="ETF">ETF</option>
                </select>
              </div>
              <div>
                <label htmlFor="asset-currency-select" className="block text-[10px] uppercase tracking-widest font-black text-neutral-500 mb-2">Currency</label>
                <select
                  id="asset-currency-select"
                  value={formCurrency}
                  onChange={e=>setFormCurrency(e.target.value)}
                  title="Asset currency"
                  className="w-full bg-neutral-900/50 border border-white/5 rounded-xl px-4 py-3 focus:border-emerald-500/50 focus:outline-none font-bold"
                >
                  <option value="BRL">BRL (R$)</option>
                  <option value="USD">USD ($)</option>
                </select>
              </div>
            </div>

            <button type="submit" disabled={submittingAsset} className="w-full bg-neutral-100 hover:bg-white text-black font-black py-4 rounded-xl transition-all shadow-xl hover:shadow-white/10 active:scale-[0.98]">
              {submittingAsset ? <Plus className="animate-spin mx-auto" /> : "REGISTER ASSET"}
            </button>
          </form>
        </div>

        {/* Step 2: Trade Entry */}
        <div className="glass p-8 rounded-3xl border-t-4 border-t-purple-500/50">
          <h3 className="text-xl font-black mb-8 flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-purple-500/10 flex items-center justify-center text-purple-400 text-sm">2</div>
            Trade Execution
          </h3>
          <form onSubmit={handleAddTransaction} className="space-y-6">
            <div>
              <label htmlFor="transaction-asset-select" className="block text-[10px] uppercase tracking-widest font-black text-neutral-500 mb-2">Select Asset</label>
              <select
                id="transaction-asset-select"
                required
                value={txAssetId}
                onChange={e=>setTxAssetId(e.target.value)}
                title="Select registered asset"
                className="w-full bg-neutral-900/50 border border-white/5 rounded-xl px-4 py-3 focus:border-purple-500/50 focus:outline-none font-bold"
              >
                <option value="">-- Choose registered asset --</option>
                {registeredAssets.map(a => <option key={a.id} value={a.id}>{a.ticker} - {a.name}</option>)}
              </select>
            </div>

            <div>
              <label className="block text-[10px] uppercase tracking-widest font-black text-neutral-500 mb-2">Order Side</label>
              <div className="grid grid-cols-2 gap-4">
                <button 
                  type="button" onClick={()=>setTxType("BUY")}
                  className={`py-3 rounded-xl border font-black transition ${txType === 'BUY' ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400' : 'bg-white/5 border-white/5 text-neutral-500 hover:bg-white/10'}`}
                >BUY</button>
                <button 
                  type="button" onClick={()=>setTxType("SELL")}
                  className={`py-3 rounded-xl border font-black transition ${txType === 'SELL' ? 'bg-red-500/20 border-red-500/50 text-red-400' : 'bg-white/5 border-white/5 text-neutral-500 hover:bg-white/10'}`}
                >SELL</button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="transaction-quantity-input" className="block text-[10px] uppercase tracking-widest font-black text-neutral-500 mb-2">Quantity</label>
                <input
                  id="transaction-quantity-input"
                  required
                  type="number"
                  step="any"
                  value={txQuantity}
                  onChange={e=>setTxQuantity(e.target.value)}
                  placeholder="0"
                  title="Transaction quantity"
                  className="w-full bg-neutral-900/50 border border-white/5 rounded-xl px-4 py-3 focus:border-purple-500/50 focus:outline-none font-bold"
                />
              </div>
              <div>
                <label htmlFor="transaction-price-input" className="block text-[10px] uppercase tracking-widest font-black text-neutral-500 mb-2">Unit Price</label>
                <div className="relative">
                  <DollarSign className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-600" size={14} />
                  <input
                    id="transaction-price-input"
                    required
                    type="number"
                    step="any"
                    value={txPrice}
                    onChange={e=>setTxPrice(e.target.value)}
                    placeholder="0.00"
                    title="Transaction unit price"
                    className="w-full bg-neutral-900/50 border border-white/5 rounded-xl pl-10 pr-4 py-3 focus:border-purple-500/50 focus:outline-none font-bold"
                  />
                </div>
              </div>
            </div>

            <button type="submit" disabled={submittingTx} className="w-full bg-purple-600 hover:bg-purple-500 text-white font-black py-4 rounded-xl transition-all shadow-xl shadow-purple-500/20 active:scale-[0.98]">
              {submittingTx ? <Plus className="animate-spin mx-auto" /> : "EXECUTE TRADE"}
            </button>
          </form>
        </div>
      </div>

      <div className="glass p-8 rounded-3xl">
        <h3 className="text-xl font-black mb-6 flex items-center gap-3">
          <Briefcase className="text-blue-500" /> Infrastructure Registry
        </h3>
        <div className="flex flex-wrap gap-3">
          {registeredAssets.map(a => (
            <div key={a.id} className="bg-white/5 border border-white/5 px-4 py-3 rounded-xl flex items-center gap-3 hover:border-blue-500/30 transition group">
              <span className="font-black text-white group-hover:text-blue-400 transition">{a.ticker}</span>
              <span className="text-[10px] font-black bg-white/5 text-neutral-500 px-2 py-1 rounded-md uppercase tracking-wider">{a.asset_type}</span>
            </div>
          ))}
          {registeredAssets.length === 0 && <span className="text-neutral-500 text-sm font-medium">No assets registered in the SQLite layer.</span>}
        </div>
      </div>
    </div>
  );
};

export default WalletBuilder;
