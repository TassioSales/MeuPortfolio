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
        ink: "#05090f",
        panel: "#0a131f",
        line: "#162b3d",
        accent: "#36d6a7",
        amber: "#f4b860",
        coral: "#ff7b72",
        sky: "#6bb8ff",
        iris: "#8b7dff",
        mist: "#8ea4b8",
        glass: "rgba(255, 255, 255, 0.03)",
        "glass-border": "rgba(255, 255, 255, 0.08)",
      },
      boxShadow: {
        panel: "0 24px 50px -12px rgba(0, 0, 0, 0.5)",
        glow: "0 0 20px rgba(54, 214, 167, 0.15)",
        float: "0 30px 80px -30px rgba(8, 17, 26, 0.9)",
      },
      fontFamily: {
        display: ["Space Grotesk", "sans-serif"],
        body: ["Plus Jakarta Sans", "sans-serif"],
      },
      backgroundImage: {
        grid: "linear-gradient(rgba(142,164,184,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(142,164,184,0.04) 1px, transparent 1px)",
      },
    },
  },
  plugins: [],
};

export default config;
