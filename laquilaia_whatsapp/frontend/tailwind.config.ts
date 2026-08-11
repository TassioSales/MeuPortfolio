import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#d9e6ff",
          200: "#bcd3ff",
          300: "#8eb6ff",
          400: "#588dff",
          500: "#3164ff",
          600: "#1b41f5",
          700: "#152fe1",
          800: "#1829b6",
          900: "#1a298f",
        },
        surface: {
          DEFAULT: "#ffffff",
          muted: "#f7f8fa",
          border: "#e4e7ec",
        },
      },
      fontFamily: {
        sans: ["system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
