/**
 * Regras de cor que o tema escuro exige, conferidas no código-fonte.
 *
 * Contraste não se testa renderizando: o jsdom não aplica Tailwind e não sabe
 * o que é legível. O que dá para travar é a **regra** — e as três abaixo são
 * exatamente os defeitos que apareceram na tela, não hipóteses.
 *
 * O leitor pode achar estranho um teste que lê arquivo em vez de renderizar
 * componente. É deliberado: o defeito aqui vive na string de classes, e é lá
 * que ele é pego. Um teste de componente passaria com o campo invisível.
 */

import fs from "fs";
import path from "path";

const RAIZ = path.join(__dirname, "..");

function arquivosTsx(dir: string): string[] {
  const entradas = fs.readdirSync(path.join(RAIZ, dir), { withFileTypes: true });
  return entradas.flatMap((e) => {
    const relativo = path.join(dir, e.name);
    if (e.isDirectory()) return arquivosTsx(relativo);
    return e.name.endsWith(".tsx") ? [relativo] : [];
  });
}

const ARQUIVOS = [...arquivosTsx("components"), ...arquivosTsx("app")];

/**
 * A fonte sem comentários.
 *
 * Sem isto, um comentário explicando por que `bg-gray-50` saiu é acusado como
 * se a classe ainda estivesse lá — e o teste passa a punir justamente quem
 * documentou a correção.
 */
function semComentarios(fonte: string): string {
  return fonte
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n")
    .map((linha) => linha.replace(/(^|\s)\/\/.*$/, "$1"))
    .join("\n");
}

/** As escalas declaradas em `tailwind.config.ts`, com os tons que existem. */
const ESCALAS_PROPRIAS: Record<string, string[]> = (() => {
  const config = fs.readFileSync(path.join(RAIZ, "tailwind.config.ts"), "utf-8");
  const escalas: Record<string, string[]> = {};
  for (const nome of ["brand", "ink"]) {
    const bloco = new RegExp(`${nome}:\\s*\\{([^}]*)\\}`, "s").exec(config);
    if (bloco) {
      const tons: string[] = [];
      const numeros = /(\d+):/g;
      let m: RegExpExecArray | null;
      while ((m = numeros.exec(bloco[1])) !== null) tons.push(m[1]);
      escalas[nome] = tons;
    }
  }
  return escalas;
})();

describe("cores no tema escuro", () => {
  it("todo campo de digitação declara o próprio fundo", () => {
    // Sem classe de fundo o navegador pinta o campo com o padrão dele
    // (branco), enquanto `text-fg` no escuro é claro: texto claro em fundo
    // branco. Foi assim que o campo do playground ficou ilegível — ninguém
    // conseguia ler o que estava digitando.
    const semFundo: string[] = [];

    for (const arquivo of ARQUIVOS) {
      const fonte = semComentarios(fs.readFileSync(path.join(RAIZ, arquivo), "utf-8"));
      // Cada `<input`/`<textarea` até o fechamento da tag.
      //
      // `[\s\S]` em vez da flag `s`, e `exec` em vez de `matchAll`: o
      // `target` do tsconfig é anterior a ES2018 e as duas coisas não
      // compilam. Teste que não compila reprova o `npm run typecheck`, que é
      // parte da CI.
      const tags = /<(input|textarea)\b[^>]*?\/?>/g;
      let m: RegExpExecArray | null;
      while ((m = tags.exec(fonte)) !== null) {
        const tag = m[0];
        if (!/className=/.test(tag)) continue;
        if (!/\bbg-[\w[\]/.-]+/.test(tag)) semFundo.push(`${arquivo}: <${m[1]}>`);
      }
    }

    expect(semFundo).toEqual([]);
  });

  it("tarja clara sempre vem com o par escuro", () => {
    // `bg-red-50` sozinho é uma faixa clarinha no meio de uma tela escura, e
    // quando o texto por cima usa token (`text-fg`, claro no escuro) some de
    // vez. A regra do projeto é token; quando a cor é literal, o par `dark:`
    // é obrigatório.
    const semPar: string[] = [];

    for (const arquivo of ARQUIVOS) {
      const fonte = semComentarios(fs.readFileSync(path.join(RAIZ, arquivo), "utf-8"));
      fonte.split("\n").forEach((linha, i) => {
        const tarjas = /(?<!dark:)\bbg-(\w+)-(50|100)\b/g;
        let m: RegExpExecArray | null;
        while ((m = tarjas.exec(linha)) !== null) {
          const cor = m[1];
          if (!new RegExp(`dark:bg-${cor}-`).test(linha)) {
            semPar.push(`${arquivo}:${i + 1} — ${m[0]}`);
          }
        }
      });
    }

    expect(semPar).toEqual([]);
  });

  it("não usa tom que a escala do projeto não tem", () => {
    // `brand` vai até 900. Um `bg-brand-950` não gera classe nenhuma: o
    // Tailwind ignora em silêncio, o fundo claro fica, e no escuro sobra
    // texto claro sobre fundo claro. O silêncio é o que torna isto perigoso.
    const inexistentes: string[] = [];

    for (const arquivo of ARQUIVOS) {
      const fonte = semComentarios(fs.readFileSync(path.join(RAIZ, arquivo), "utf-8"));
      fonte.split("\n").forEach((linha, i) => {
        for (const [escala, tons] of Object.entries(ESCALAS_PROPRIAS)) {
          const usos = new RegExp(`\\b${escala}-(\\d+)\\b`, "g");
          let m: RegExpExecArray | null;
          while ((m = usos.exec(linha)) !== null) {
            if (!tons.includes(m[1])) {
              inexistentes.push(`${arquivo}:${i + 1} — ${m[0]}`);
            }
          }
        }
      });
    }

    expect(inexistentes).toEqual([]);
  });
});
