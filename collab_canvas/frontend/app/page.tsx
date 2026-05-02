"use client";

import { useMemo, useState } from "react";
import { Activity, Eraser, Radio, Sparkles, Users, WifiOff } from "lucide-react";
import { CanvasBoard } from "@/components/CanvasBoard";
import { ColorPalette } from "@/components/ColorPalette";
import { CooldownDial } from "@/components/CooldownDial";
import { useSoundFx } from "@/hooks/useSoundFx";
import { useWebSocketBoard } from "@/hooks/useWebSocketBoard";

export default function Home() {
  const [selectedColor, setSelectedColor] = useState("#22d3ee");
  const [mode, setMode] = useState<"multiplayer" | "single">("multiplayer");
  const [localPixels, setLocalPixels] = useState(() => createLocalBoard());
  const sound = useSoundFx();
  const board = useWebSocketBoard();
  const {
    pixels,
    width,
    height,
    users,
    status,
    cooldownUntil,
    lastError,
    sendDraw,
  } = board;

  const activePixels = mode === "single" ? localPixels : pixels;
  const activeStatus = mode === "single" ? "solo" : status;
  const isCoolingDown = mode === "multiplayer" && cooldownUntil > Date.now();
  const statusTone = useMemo(() => {
    if (status === "online") {
      return "text-emerald-300";
    }
    if (status === "connecting") {
      return "text-amber-300";
    }
    return "text-rose-300";
  }, [status]);

  const handleDraw = (x: number, y: number, color: string) => {
    if (mode === "single") {
      setLocalPixels((current) => {
        const next = current.map((row) => [...row]);
        if (next[y]?.[x] !== undefined) {
          next[y][x] = color;
        }
        return next;
      });
      sound.paint();
      return;
    }

    if (sendDraw(x, y, color)) {
      sound.paint();
    }
  };

  const clearSingleBoard = () => {
    setLocalPixels(createLocalBoard());
    sound.clear();
  };

  const changeMode = (nextMode: "multiplayer" | "single") => {
    setMode(nextMode);
    sound.mode();
  };

  const selectColor = (color: string) => {
    setSelectedColor(color);
    sound.select();
  };

  return (
    <main className="min-h-screen px-4 py-5 text-slate-100 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-5">
        <header className="flex flex-col gap-4 border-b border-white/10 pb-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.36em] text-cyan-300">Pixel art arena</p>
            <h1 className="mt-2 text-3xl font-black tracking-normal text-white sm:text-5xl">CollabCanvas</h1>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="panel flex h-11 items-center gap-2 rounded-lg px-4">
              {mode === "single" ? <Sparkles size={18} /> : status === "online" ? <Radio size={18} /> : <WifiOff size={18} />}
              <span className={`text-sm font-bold uppercase ${mode === "single" ? "text-cyan-300" : statusTone}`}>{activeStatus}</span>
            </div>
            <div className="panel flex h-11 items-center gap-2 rounded-lg px-4">
              {mode === "single" ? <Users size={18} className="text-cyan-300" /> : <Activity size={18} className="text-cyan-300" />}
              <span className="text-sm font-bold">{mode === "single" ? 1 : users}</span>
              <span className="text-sm text-slate-400">{mode === "single" ? "player" : "online"}</span>
            </div>
          </div>
        </header>

        <section className="grid items-start gap-5 lg:grid-cols-[300px_minmax(0,1fr)]">
          <aside className="panel rounded-lg p-4">
            <div className="space-y-5">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Mode</p>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <button
                    className={`rounded-md border px-3 py-2 text-sm font-bold transition ${mode === "multiplayer" ? "border-cyan-300 bg-cyan-300/15 text-cyan-100 shadow-neon" : "border-white/10 bg-white/5 text-slate-300"}`}
                    onClick={() => changeMode("multiplayer")}
                    type="button"
                  >
                    Multi
                  </button>
                  <button
                    className={`rounded-md border px-3 py-2 text-sm font-bold transition ${mode === "single" ? "border-cyan-300 bg-cyan-300/15 text-cyan-100 shadow-neon" : "border-white/10 bg-white/5 text-slate-300"}`}
                    onClick={() => changeMode("single")}
                    type="button"
                  >
                    Solo
                  </button>
                </div>
              </div>

              <div className="h-px bg-white/10" />

              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Palette</p>
                <div className="mt-3">
                  <ColorPalette selectedColor={selectedColor} onSelect={selectColor} />
                </div>
              </div>

              <div className="h-px bg-white/10" />

              {mode === "multiplayer" ? (
                <CooldownDial cooldownUntil={cooldownUntil} />
              ) : (
                <button
                  className="flex w-full items-center justify-center gap-2 rounded-md border border-white/10 bg-white/5 px-3 py-3 text-sm font-bold text-slate-200 transition hover:border-cyan-300/70 hover:text-cyan-100"
                  onClick={clearSingleBoard}
                  type="button"
                >
                  <Eraser size={17} />
                  Clear Solo Board
                </button>
              )}

              {mode === "multiplayer" && lastError ? (
                <div className="rounded-lg border border-rose-400/25 bg-rose-950/40 p-3 text-sm text-rose-100 shadow-danger">
                  {lastError}
                </div>
              ) : null}
            </div>
          </aside>

          <section className="flex min-h-[calc(100vh-180px)] items-center justify-center">
            <CanvasBoard
              disabled={mode === "multiplayer" && (status !== "online" || isCoolingDown)}
              height={height}
              onDraw={handleDraw}
              pixels={activePixels}
              selectedColor={selectedColor}
              width={width}
            />
          </section>
        </section>
      </div>
    </main>
  );
}

function createLocalBoard(size = 100): string[][] {
  return Array.from({ length: size }, (_, y) =>
    Array.from({ length: size }, (_, x) => {
      if ((x + y) % 17 === 0) {
        return "#ecfeff";
      }
      return "#ffffff";
    }),
  );
}
