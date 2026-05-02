"use client";

import { useCallback, useRef } from "react";

type ToneOptions = {
  frequency: number;
  duration?: number;
  type?: OscillatorType;
  gain?: number;
  slideTo?: number;
};

export function useSoundFx() {
  const contextRef = useRef<AudioContext | null>(null);

  const unlock = useCallback(() => {
    if (!contextRef.current) {
      contextRef.current = new AudioContext();
    }
    if (contextRef.current.state === "suspended") {
      void contextRef.current.resume();
    }
    return contextRef.current;
  }, []);

  const tone = useCallback((options: ToneOptions) => {
    const context = unlock();
    const now = context.currentTime;
    const oscillator = context.createOscillator();
    const volume = context.createGain();
    const duration = options.duration ?? 0.08;

    oscillator.type = options.type ?? "sine";
    oscillator.frequency.setValueAtTime(options.frequency, now);
    if (options.slideTo) {
      oscillator.frequency.exponentialRampToValueAtTime(options.slideTo, now + duration);
    }

    volume.gain.setValueAtTime(0.0001, now);
    volume.gain.exponentialRampToValueAtTime(options.gain ?? 0.045, now + 0.01);
    volume.gain.exponentialRampToValueAtTime(0.0001, now + duration);

    oscillator.connect(volume);
    volume.connect(context.destination);
    oscillator.start(now);
    oscillator.stop(now + duration + 0.02);
  }, [unlock]);

  return {
    paint: () => tone({ frequency: 520, duration: 0.05, type: "square", gain: 0.025, slideTo: 720 }),
    select: () => tone({ frequency: 360, duration: 0.06, type: "triangle", gain: 0.03, slideTo: 540 }),
    clear: () => tone({ frequency: 240, duration: 0.16, type: "sawtooth", gain: 0.035, slideTo: 120 }),
    mode: () => tone({ frequency: 300, duration: 0.08, type: "sine", gain: 0.035, slideTo: 620 }),
  };
}
