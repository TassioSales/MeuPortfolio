"use client";

import { useEffect, useMemo, useState } from "react";

const COOLDOWN_MS = 3000;

type CooldownDialProps = {
  cooldownUntil: number;
};

export function CooldownDial({ cooldownUntil }: CooldownDialProps) {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 50);
    return () => clearInterval(timer);
  }, []);

  const remaining = Math.max(0, cooldownUntil - now);
  const progress = 1 - remaining / COOLDOWN_MS;
  const label = remaining > 0 ? `${Math.ceil(remaining / 1000)}s` : "Ready";

  const style = useMemo(
    () => ({
      background: `conic-gradient(#22d3ee ${Math.max(0, progress) * 360}deg, rgba(148, 163, 184, 0.18) 0deg)`,
    }),
    [progress],
  );

  return (
    <div className="flex items-center gap-3">
      <div className="grid h-12 w-12 place-items-center rounded-full p-[3px] shadow-neon" style={style}>
        <div className="grid h-full w-full place-items-center rounded-full bg-slate-950 text-[11px] font-bold text-slate-100">
          {label}
        </div>
      </div>
      <div>
        <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Cooldown</p>
        <p className="text-sm font-semibold text-slate-100">
          {remaining > 0 ? "Pixel locked" : "Paint enabled"}
        </p>
      </div>
    </div>
  );
}
