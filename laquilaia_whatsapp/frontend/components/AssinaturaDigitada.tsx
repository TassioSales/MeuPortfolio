"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * A assinatura gerada a partir do nome, para quem não quer desenhar.
 *
 * É o que Autentique e DocuSign oferecem ao lado do desenho, e existe por um
 * motivo prático: assinar com o dedo numa tela sai um garrancho, e muita gente
 * desiste ou fica com vergonha do resultado. Digitar e escolher a letra é o
 * caminho que a maioria prefere.
 *
 * **O resultado é o mesmo PNG do desenho.** O nome é pintado num `<canvas>` e
 * sai pelo mesmo caminho — o backend não sabe (nem precisa saber) se o traço
 * veio de um dedo ou de uma fonte, e não há um segundo formato para validar,
 * guardar e desenhar no PDF.
 *
 * **Não é falsificação.** O sistema não assina por ninguém: a pessoa digita o
 * próprio nome, escolhe como ele aparece e confirma. O que sustenta a
 * assinatura continua sendo a trilha — link individual, hora, IP, aparelho e
 * hash do texto.
 */

interface Props {
  nome: string;
  onChange: (dataUrl: string | null) => void;
}

const ESTILOS = [
  { id: "elegante", rotulo: "Clássica", classe: "font-assinatura-elegante", css: "var(--fonte-assinatura-elegante), cursive" },
  { id: "solta", rotulo: "Solta", classe: "font-assinatura-solta", css: "var(--fonte-assinatura-solta), cursive" },
  { id: "caneta", rotulo: "Caneta", classe: "font-assinatura-caneta", css: "var(--fonte-assinatura-caneta), cursive" },
] as const;

/** Alto o bastante para o traço não sair serrilhado quando o PDF for ampliado. */
const LARGURA = 900;
const ALTURA = 260;

export function AssinaturaDigitada({ nome, onChange }: Props) {
  const [estilo, setEstilo] = useState<string>(ESTILOS[0].id);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const pintar = useCallback(async () => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const limpo = nome.trim();
    ctx.clearRect(0, 0, LARGURA, ALTURA);
    if (!limpo) {
      onChange(null);
      return;
    }

    const escolhido = ESTILOS.find((e) => e.id === estilo) ?? ESTILOS[0];
    // Sem esperar a fonte, o primeiro desenho sai na fonte de reserva e o
    // cliente assina com um nome em Times — que não parece assinatura
    // nenhuma. O `catch` cobre navegador sem a API: aí pinta com o que tiver.
    try {
      await document.fonts.load(`72px ${escolhido.css}`, limpo);
      await document.fonts.ready;
    } catch {
      /* segue com a reserva */
    }

    // Encolhe até caber: um nome como "Tassio Lucian de Jesus Sales" estoura a
    // largura no tamanho cheio, e cortar o nome de alguém num contrato é pior
    // que uma letra menor.
    let tamanho = 84;
    ctx.fillStyle = "#111111";
    ctx.textBaseline = "middle";
    do {
      ctx.font = `${tamanho}px ${escolhido.css}`;
      if (ctx.measureText(limpo).width <= LARGURA - 80) break;
      tamanho -= 4;
    } while (tamanho > 28);

    ctx.textAlign = "center";
    ctx.fillText(limpo, LARGURA / 2, ALTURA / 2);
    onChange(canvas.toDataURL("image/png"));
  }, [nome, estilo, onChange]);

  useEffect(() => {
    void pintar();
  }, [pintar]);

  return (
    <div>
      <p className="text-sm font-medium text-fg-soft">Escolha como sua assinatura aparece</p>

      <div
        role="radiogroup"
        aria-label="Estilo da assinatura"
        className="mt-2 flex flex-col gap-2"
      >
        {ESTILOS.map((opcao) => (
          <button
            key={opcao.id}
            type="button"
            role="radio"
            aria-checked={estilo === opcao.id}
            onClick={() => setEstilo(opcao.id)}
            className={[
              "flex items-center justify-between rounded-lg border-2 bg-white px-4 py-3 text-left transition-colors",
              estilo === opcao.id
                ? "border-ink-900"
                : "border-surface-border hover:border-ink-300",
            ].join(" ")}
          >
            <span
              className={`${opcao.classe} truncate text-3xl leading-tight text-ink-950`}
            >
              {nome.trim() || "Seu nome"}
            </span>
            <span className="ml-3 shrink-0 text-xs text-ink-400">{opcao.rotulo}</span>
          </button>
        ))}
      </div>

      {/* Fora da tela: é daqui que sai o PNG, no tamanho grande, sem que a
          pessoa veja um segundo desenho do mesmo nome. */}
      <canvas
        ref={canvasRef}
        width={LARGURA}
        height={ALTURA}
        aria-hidden="true"
        className="pointer-events-none absolute -left-[9999px] h-0 w-0"
      />

      {!nome.trim() && (
        <p className="mt-2 text-xs text-fg-muted">
          Preencha seu nome completo acima para ver as opções.
        </p>
      )}
    </div>
  );
}

export default AssinaturaDigitada;
