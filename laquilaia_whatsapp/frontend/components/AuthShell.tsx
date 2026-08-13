import type { ReactNode } from "react";
import { Logo, Marca } from "./Logo";
import { SeletorDeTema } from "./SeletorDeTema";

/**
 * A moldura das telas de entrar e criar conta.
 *
 * Eram um formulário solto no meio de um fundo cinza — a primeira tela do
 * produto não dizia de quem ela é. Aqui a metade escura carrega a marca e o
 * que o sistema faz; a clara fica só com o formulário.
 *
 * A metade escura some abaixo de `lg` em vez de empilhar. Empilhada, ela
 * empurraria os campos para fora da primeira dobra no celular, e a tela de
 * login existe para digitar e-mail e senha, não para ler.
 */

interface AuthShellProps {
  titulo: string;
  subtitulo: string;
  children: ReactNode;
  /** Linha final: o link para a outra tela. */
  rodape: ReactNode;
}

export function AuthShell({ titulo, subtitulo, children, rodape }: AuthShellProps) {
  return (
    <main className="flex min-h-screen">
      <section className="hidden w-[46%] max-w-xl flex-col justify-between bg-ink-900 p-12 text-white lg:flex">
        <Logo size={32} className="text-white" />

        <div>
          <p className="text-3xl font-semibold leading-snug tracking-tight">
            A triagem do escritório,
            <br />
            <span className="text-brass-300">no WhatsApp.</span>
          </p>
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-ink-300">
            O agente entende o caso, coleta o que importa e entrega ao advogado
            uma análise preliminar — com teses, jurisprudência e o porte do caso.
          </p>
        </div>

        <p className="text-xs text-ink-400">
          A análise é insumo interno do escritório. O cliente nunca a recebe.
        </p>
      </section>

      <section className="relative flex flex-1 items-center justify-center px-6 py-12">
        <SeletorDeTema className="absolute right-6 top-6" />
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <Marca size={34} className="text-fg lg:hidden" />
            <h1 className="mt-3 text-2xl font-semibold tracking-tight text-fg">
              {titulo}
            </h1>
            <p className="mt-1 text-sm text-fg-muted">{subtitulo}</p>
          </div>

          {children}

          <p className="mt-6 text-sm text-fg-muted">{rodape}</p>
        </div>
      </section>
    </main>
  );
}

export default AuthShell;
