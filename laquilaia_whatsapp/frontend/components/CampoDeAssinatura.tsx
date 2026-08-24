"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Onde a pessoa assina com o dedo.
 *
 * Juridicamente o rabisco não acrescenta nada — o que prova a assinatura é a
 * trilha: link individual, hora, IP, aparelho e hash do texto. Mas um contrato
 * sem nada escrito na linha da assinatura **não parece assinado**, e quem
 * recebe o PDF fica sem saber se aquilo valeu. Foi a primeira coisa que o dono
 * disse ao abrir o primeiro contrato assinado de verdade.
 *
 * Três detalhes que não são enfeite:
 *
 * - **`touch-none`**, senão arrastar o dedo rola a página em vez de desenhar,
 *   e a pessoa nunca consegue assinar no celular.
 * - **Pointer Events**, não `touch` + `mouse` separados: um só caminho para
 *   dedo, caneta e mouse, e sem o evento duplicado que faz um traço virar dois.
 * - **O canvas é redimensionado com `devicePixelRatio`.** Sem isso o traço sai
 *   borrado no celular, e assinatura borrada num contrato parece defeito.
 */

interface Props {
  onChange: (dataUrl: string | null) => void;
  disabled?: boolean;
}

export function CampoDeAssinatura({ onChange, disabled }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const desenhando = useRef(false);
  const [temTraco, setTemTraco] = useState(false);

  const preparar = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const escala = window.devicePixelRatio || 1;
    const caixa = canvas.getBoundingClientRect();
    canvas.width = Math.round(caixa.width * escala);
    canvas.height = Math.round(caixa.height * escala);

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(escala, escala);
    ctx.lineWidth = 2.2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    // Preto fixo, e não a cor do tema: o traço vai para um PDF de fundo
    // branco. Um traço claro escolhido no tema escuro sairia invisível no
    // documento — defeito que só apareceria depois de assinado.
    ctx.strokeStyle = "#111111";
  }, []);

  useEffect(() => {
    preparar();
    window.addEventListener("resize", preparar);
    return () => window.removeEventListener("resize", preparar);
  }, [preparar]);

  function ponto(e: React.PointerEvent<HTMLCanvasElement>) {
    const caixa = e.currentTarget.getBoundingClientRect();
    return { x: e.clientX - caixa.left, y: e.clientY - caixa.top };
  }

  function comecar(e: React.PointerEvent<HTMLCanvasElement>) {
    if (disabled) return;
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    desenhando.current = true;
    const { x, y } = ponto(e);
    ctx.beginPath();
    ctx.moveTo(x, y);
    // Um ponto só também é assinatura: sem isto, quem toca e solta não deixa
    // marca nenhuma e acha que o campo não funciona.
    ctx.lineTo(x + 0.1, y);
    ctx.stroke();
    setTemTraco(true);
  }

  function mover(e: React.PointerEvent<HTMLCanvasElement>) {
    if (!desenhando.current) return;
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    const { x, y } = ponto(e);
    ctx.lineTo(x, y);
    ctx.stroke();
  }

  function terminar() {
    if (!desenhando.current) return;
    desenhando.current = false;
    const canvas = canvasRef.current;
    if (canvas) onChange(canvas.toDataURL("image/png"));
  }

  function limpar() {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setTemTraco(false);
    onChange(null);
  }

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <label className="text-sm font-medium text-fg-soft">
          Assine com o dedo
        </label>
        {temTraco && (
          <button
            type="button"
            onClick={limpar}
            className="text-xs text-fg-muted underline"
          >
            limpar
          </button>
        )}
      </div>

      <div className="relative mt-1.5">
        <canvas
          ref={canvasRef}
          onPointerDown={comecar}
          onPointerMove={mover}
          onPointerUp={terminar}
          onPointerLeave={terminar}
          onPointerCancel={terminar}
          aria-label="Área para assinar"
          className="h-40 w-full touch-none rounded-lg border-2 border-dashed border-surface-border bg-white"
        />
        {!temTraco && (
          <span
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 flex items-center justify-center text-sm text-ink-400"
          >
            desenhe sua assinatura aqui
          </span>
        )}
        {/* A linha de base ajuda a pessoa a assinar reto — é o que ela vê num
            papel, e sem ela o rabisco sai subindo pelo canto. */}
        <span
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-8 bottom-8 border-b border-ink-200"
        />
      </div>
    </div>
  );
}

export default CampoDeAssinatura;
