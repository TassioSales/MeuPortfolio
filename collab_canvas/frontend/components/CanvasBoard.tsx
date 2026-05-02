"use client";

import { MouseEvent, useEffect, useRef } from "react";

type CanvasBoardProps = {
  pixels: string[][];
  width: number;
  height: number;
  selectedColor: string;
  disabled: boolean;
  onDraw: (x: number, y: number, color: string) => void;
};

const CANVAS_SIZE = 720;

export function CanvasBoard({
  pixels,
  width,
  height,
  selectedColor,
  disabled,
  onDraw,
}: CanvasBoardProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) {
      return;
    }

    const cellWidth = canvas.width / width;
    const cellHeight = canvas.height / height;

    context.clearRect(0, 0, canvas.width, canvas.height);
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, canvas.width, canvas.height);
    for (let y = 0; y < height; y += 1) {
      for (let x = 0; x < width; x += 1) {
        context.fillStyle = pixels[y]?.[x] ?? "#ffffff";
        context.fillRect(Math.floor(x * cellWidth), Math.floor(y * cellHeight), Math.ceil(cellWidth), Math.ceil(cellHeight));
      }
    }

    context.strokeStyle = "rgba(15, 23, 42, 0.09)";
    context.lineWidth = 1;
    for (let x = 0; x <= width; x += 5) {
      const lineX = Math.floor(x * cellWidth) + 0.5;
      context.beginPath();
      context.moveTo(lineX, 0);
      context.lineTo(lineX, canvas.height);
      context.stroke();
    }
    for (let y = 0; y <= height; y += 5) {
      const lineY = Math.floor(y * cellHeight) + 0.5;
      context.beginPath();
      context.moveTo(0, lineY);
      context.lineTo(canvas.width, lineY);
      context.stroke();
    }
  }, [height, pixels, width]);

  const handleClick = (event: MouseEvent<HTMLCanvasElement>) => {
    if (disabled) {
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const rect = canvas.getBoundingClientRect();
    const scaleX = width / rect.width;
    const scaleY = height / rect.height;
    const x = Math.floor((event.clientX - rect.left) * scaleX);
    const y = Math.floor((event.clientY - rect.top) * scaleY);
    onDraw(x, y, selectedColor);
  };

  return (
    <div className="relative w-full max-w-[min(76vh,760px)]">
      <div className="pointer-events-none absolute -inset-3 rounded-xl bg-cyan-300/10 blur-2xl" />
      <canvas
        aria-label="CollabCanvas board"
        className="relative aspect-square w-full cursor-crosshair rounded-lg border border-cyan-300/40 bg-white shadow-neon"
        height={CANVAS_SIZE}
        onClick={handleClick}
        ref={canvasRef}
        width={CANVAS_SIZE}
      />
      <div className="pointer-events-none absolute inset-0 rounded-lg ring-1 ring-white/10" />
    </div>
  );
}
