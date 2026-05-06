"use client";

import React, { useState, useRef, useEffect } from "react";
import { aiService } from "@/services/api";
import { Send, Bot, Cpu, Sparkles, X } from "lucide-react";

const ChatBot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<{ role: "user" | "ai"; content: string }[]>([
    { role: "ai", content: "Olá, eu sou o WealthMap AI. Posso analisar risco, concentração, diversificação e próximos movimentos da sua carteira." }
  ]);
  const [loading, setLoading] = useState(false);
  const [aiStatus, setAiStatus] = useState<{ provider: string; model: string } | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    aiService.status()
      .then((res) => setAiStatus(res.data))
      .catch(() => setAiStatus({ provider: "local", model: "local-rules" }));
  }, []);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);

    try {
      const res = await aiService.chat(userMsg);
      setMessages(prev => [...prev, { role: "ai", content: res.data.reply }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: "ai", content: "Sorry, I encountered an error processing your request." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating Button */}
      <button 
        onClick={() => setIsOpen(true)}
        aria-label="Abrir assistente WealthMap AI"
        title="Abrir assistente WealthMap AI"
        className={`fixed bottom-8 right-8 w-16 h-16 rounded-full bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center text-white shadow-2xl shadow-purple-500/40 hover:scale-110 transition-all z-40 group ${isOpen ? 'scale-0 opacity-0' : 'scale-100 opacity-100'}`}
      >
        <span className="sr-only">Abrir assistente WealthMap AI</span>
        <Sparkles className="group-hover:rotate-12 transition-transform" />
      </button>

      {/* Chat Window */}
      <div className={`fixed bottom-8 right-8 w-[400px] h-[600px] glass rounded-3xl flex flex-col z-50 transition-all duration-500 origin-bottom-right shadow-[0_0_50px_rgba(0,0,0,0.5)] border border-white/10 ${isOpen ? 'scale-100 opacity-100' : 'scale-0 opacity-0 pointer-events-none'}`}>
        {/* Header */}
        <div className="p-6 border-b border-white/10 flex justify-between items-center bg-white/5 rounded-t-3xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center">
              <Bot className="text-purple-400" size={20} />
            </div>
            <div>
              <h4 className="font-black text-sm tracking-tight">WealthMap AI</h4>
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                <span className="text-[10px] font-black text-emerald-500 uppercase tracking-widest">
                  {aiStatus?.provider === "mistral" ? `Mistral ${aiStatus.model}` : "Local fallback"}
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            aria-label="Fechar assistente WealthMap AI"
            title="Fechar assistente WealthMap AI"
            className="text-neutral-500 hover:text-white transition"
          >
            <span className="sr-only">Fechar assistente WealthMap AI</span>
            <X size={20} />
          </button>
        </div>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] p-4 rounded-2xl text-xs leading-relaxed ${
                msg.role === 'user' 
                  ? 'bg-purple-600 text-white font-bold rounded-tr-none' 
                  : 'bg-white/5 border border-white/5 text-neutral-200 font-medium rounded-tl-none'
              }`}>
                {msg.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-white/5 border border-white/5 p-4 rounded-2xl rounded-tl-none">
                <Cpu className="animate-spin text-purple-500" size={16} />
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="p-6 border-t border-white/10">
          <div className="relative">
            <input 
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              placeholder="Pergunte sobre risco, concentração, rebalanceamento..."
              className="w-full bg-neutral-900 border border-white/5 rounded-2xl pl-4 pr-12 py-4 text-xs focus:outline-none focus:border-purple-500/50 transition font-bold"
            />
            <button 
              onClick={handleSend}
              aria-label="Enviar mensagem"
              title="Enviar mensagem"
              className="absolute right-3 top-1/2 -translate-y-1/2 p-2 bg-purple-600 text-white rounded-xl hover:bg-purple-500 transition"
            >
              <span className="sr-only">Enviar mensagem</span>
              <Send size={14} />
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default ChatBot;
