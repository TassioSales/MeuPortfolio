"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import {
  CHAVE_DO_TEMA,
  aplicarTema,
  lerTemaSalvo,
  type Tema,
} from "@/lib/tema";

/**
 * Claro, escuro ou o do sistema.
 *
 * Três botões visíveis em vez de um interruptor: com interruptor não há como
 * voltar para "seguir o sistema" depois de tocar uma vez, e é o estado padrão.
 *
 * Os ícones vão junto do texto lido por leitor de tela. Sol e lua sozinhos são
 * ambíguos — sol pode significar "está claro" ou "clique para clarear", e as
 * duas leituras aparecem em produtos reais.
 */

const OPCOES: { valor: Tema; rotulo: string; Icone: () => JSX.Element }[] = [
  { valor: "claro", rotulo: "Claro", Icone: IconeSol },
  { valor: "escuro", rotulo: "Escuro", Icone: IconeLua },
  { valor: "sistema", rotulo: "Sistema", Icone: IconeSistema },
];

export function SeletorDeTema({ className }: { className?: string }) {
  // Nasce em "sistema" e é corrigido no primeiro efeito: o servidor não tem
  // como saber o que está no `localStorage` do navegador, e chutar aqui daria
  // erro de hidratação.
  const [tema, setTema] = useState<Tema>("sistema");

  useEffect(() => {
    setTema(lerTemaSalvo());
  }, []);

  // Enquanto for "sistema", a tela acompanha a mudança do sistema em tempo
  // real — inclusive a que acontece sozinha ao anoitecer.
  useEffect(() => {
    if (tema !== "sistema" || !window.matchMedia) return;

    const consulta = window.matchMedia("(prefers-color-scheme: dark)");
    const aoMudar = () => aplicarTema("sistema");
    consulta.addEventListener("change", aoMudar);
    return () => consulta.removeEventListener("change", aoMudar);
  }, [tema]);

  function escolher(novo: Tema) {
    setTema(novo);
    aplicarTema(novo);
    try {
      window.localStorage.setItem(CHAVE_DO_TEMA, novo);
    } catch {
      // Navegação privada pode recusar a escrita. O tema vale nesta sessão;
      // não valer na próxima é melhor que quebrar a tela.
    }
  }

  return (
    <div
      role="radiogroup"
      aria-label="Tema"
      className={cn(
        "flex items-center gap-0.5 rounded-lg border border-surface-border p-0.5",
        className,
      )}
    >
      {OPCOES.map(({ valor, rotulo, Icone }) => (
        <button
          key={valor}
          type="button"
          role="radio"
          aria-checked={tema === valor}
          title={rotulo}
          onClick={() => escolher(valor)}
          className={cn(
            "rounded-md p-1.5 transition-colors",
            tema === valor
              ? "bg-surface-muted text-fg"
              : "text-fg-muted hover:text-fg",
          )}
        >
          <Icone />
          <span className="sr-only">{rotulo}</span>
        </button>
      ))}
    </div>
  );
}

function Base({ children }: { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

function IconeSol() {
  return (
    <Base>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </Base>
  );
}

function IconeLua() {
  return (
    <Base>
      <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z" />
    </Base>
  );
}

function IconeSistema() {
  return (
    <Base>
      <rect x="3" y="4" width="18" height="12" rx="2" />
      <path d="M8 20h8M12 16v4" />
    </Base>
  );
}

export default SeletorDeTema;
