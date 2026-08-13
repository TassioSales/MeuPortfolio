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
        // Azul-tinta da barra lateral e das telas de entrada.
        //
        // O painel era branco de ponta a ponta e parecia ferramenta interna de
        // startup — o que ele é, mas não é o que o escritório mostra. A tinta
        // dá o peso institucional sem virar tema escuro: o conteúdo continua
        // claro, só a moldura é escura.
        //
        // A escala `brand` continua onde estava, de propósito: ela é a cor dos
        // botões e das colunas do Kanban, e os hexes dos gráficos passaram pelo
        // validador de contraste e daltonismo. Moldura nova não é motivo para
        // revalidar paleta de dados.
        ink: {
          50: "#f5f7fa",
          100: "#e6ebf2",
          200: "#c8d3e2",
          300: "#9badc4",
          400: "#6b81a0",
          500: "#4a5f7d",
          600: "#354867",
          700: "#25344c",
          800: "#182335",
          900: "#0f1826",
          950: "#080e18",
        },
        // Latão. É o único ponto quente da interface, reservado para a marca e
        // para o item ativo da navegação — um acento que aparece em tudo deixa
        // de ser acento.
        brass: {
          200: "#f0dfae",
          300: "#e2c87f",
          400: "#d3ae54",
          500: "#bf9436",
          600: "#9c7729",
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
