import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./hooks/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      boxShadow: {
        neon: "0 0 28px rgba(34, 211, 238, 0.24)",
        danger: "0 0 26px rgba(244, 63, 94, 0.24)",
      },
    },
  },
  plugins: [],
};

export default config;
