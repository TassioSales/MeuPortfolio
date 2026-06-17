import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0d1117",
        surface: "#161b22",
        border: "#30363d",
        accent: "#58a6ff",
        "accent-hover": "#79b8ff",
        muted: "#8b949e",
        text: "#c9d1d9",
      },
    },
  },
  plugins: [],
};

export default config;
