import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // ── New design system ──────────────────────────────────────
        bg:       "#070C14",  // near-black background
        surface:  "#0D1623",  // dark navy card surface
        surface2: "#12213A",  // elevated card surface
        panel:    "#0A111D",  // sidebar/panel bg
        line:     "#1A2B3D",  // dividers
        amber:    "#F59E0B",  // brand color — fuel / energy / heat
        "amber-dim": "#92400E",
        emerald:  "#10B981",  // price drop — good news
        rose:     "#F43F5E",  // price rise — danger
        blue:     "#60A5FA",  // neutral data
        purple:   "#A78BFA",  // forecast / prediction
        text:     "#E2E8F0",  // primary text
        muted:    "#64748B",  // secondary text
        dim:      "#334155",  // very dim text
        // ── Backward compat aliases ────────────────────────────────
        ink:      "#070C14",  // was #05090f → maps to new bg
        accent:   "#36d6a7",  // keep exact value
        coral:    "#ff7b72",
        sky:      "#6bb8ff",
        iris:     "#8b7dff",
        mist:     "#8ea4b8",
        glass:          "rgba(255, 255, 255, 0.03)",
        "glass-border": "rgba(255, 255, 255, 0.08)",
      },
      boxShadow: {
        panel:  "0 24px 50px -12px rgba(0, 0, 0, 0.6)",
        glow:   "0 0 24px rgba(245, 158, 11, 0.20)",   // amber glow
        "glow-emerald": "0 0 20px rgba(16, 185, 129, 0.18)",
        "glow-rose":    "0 0 20px rgba(244,  63,  94, 0.18)",
        float:  "0 30px 80px -30px rgba(7, 12, 20, 0.9)",
        card:   "0 1px 3px rgba(0,0,0,0.4), 0 4px 16px rgba(0,0,0,0.3)",
      },
      fontFamily: {
        display: ["Space Grotesk", "sans-serif"],
        body:    ["Inter", "sans-serif"],
        mono:    ["DM Mono", "monospace"],
      },
      backgroundImage: {
        // Keep for opt-in use (e.g. .grid-bg)
        grid: "linear-gradient(rgba(142,164,184,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(142,164,184,0.04) 1px, transparent 1px)",
      },
      borderRadius: {
        card: "0.75rem",
        pill: "9999px",
      },
      keyframes: {
        "fade-up": {
          "0%":   { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "slide-in-left": {
          "0%":   { opacity: "0", transform: "translateX(-10px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        "num-in": {
          "0%":   { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "ticker-scroll": {
          "0%":   { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
        "row-in": {
          "0%":   { opacity: "0", transform: "translateX(-4px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
      },
      animation: {
        "fade-up":        "fade-up 0.35s ease-out both",
        "slide-in-left":  "slide-in-left 0.30s ease-out both",
        "num-in":         "num-in 0.35s ease-out both",
        "ticker-scroll":  "ticker-scroll 40s linear infinite",
        "row-in":         "row-in 0.25s ease-out both",
      },
    },
  },
  plugins: [],
};

export default config;
