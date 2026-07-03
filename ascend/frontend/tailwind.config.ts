import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        accent: "#00e87a",
        "accent-dim": "#00b85e",
        "accent-glow": "rgba(0,232,122,0.15)",
        surface: "#0f1219",
        "surface-raised": "#161b27",
        "surface-high": "#1e2536",
        "surface-card": "#1a2030",
        border: "#252d40",
        "border-bright": "#3a4560",
        "text-primary": "#eef2ff",
        "text-muted": "#6b7594",
        "text-dim": "#3d4a66",
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "glow": "glow 2s ease-in-out infinite alternate",
      },
      boxShadow: {
        "accent-sm": "0 0 16px rgba(0,232,122,0.12)",
        "accent-md": "0 0 32px rgba(0,232,122,0.18)",
        "card": "0 4px 24px rgba(0,0,0,0.4), 0 1px 0 rgba(255,255,255,0.04) inset",
        "card-hover": "0 8px 32px rgba(0,0,0,0.5), 0 1px 0 rgba(255,255,255,0.06) inset",
      },
      backgroundImage: {
        "accent-gradient": "linear-gradient(135deg, #00e87a, #00b85e)",
        "surface-gradient": "linear-gradient(180deg, #161b27 0%, #0f1219 100%)",
      },
      keyframes: {
        glow: {
          "0%": { boxShadow: "0 0 16px rgba(0,232,122,0.1)" },
          "100%": { boxShadow: "0 0 32px rgba(0,232,122,0.25)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
