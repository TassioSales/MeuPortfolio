import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { parseArguments, run } from "./cli.ts";

const FIXTURES = join(import.meta.dirname, "..", "fixtures");
const WORKER = join(import.meta.dirname, "..", "dist", "worker-main.js");
const DEPS = { workerEntry: WORKER, execPath: process.execPath, budgetMs: 20_000 };

describe("parseArguments", () => {
  it("separa globs de flags", () => {
    expect(parseArguments(["src/**/*.ts", "--json"])).toEqual({
      patterns: ["src/**/*.ts"],
      json: true,
      help: false,
      untrustedInput: false,
    });
  });

  it("liga a entrada não confiável", () => {
    expect(parseArguments(["x.ts", "--untrusted-input"]).untrustedInput).toBe(true);
  });

  it("recusa opção desconhecida", () => {
    expect(() => parseArguments(["--nope"])).toThrow("Opção desconhecida: --nope");
  });
});

describe("run", () => {
  it("acha as falhas do fixture quebrado e sai com código 1", async () => {
    const { output, exitCode } = await run([join(FIXTURES, "pure-broken.ts")], FIXTURES, DEPS);
    expect(exitCode).toBe(1);
    expect(output).toContain("extractBaseEmail");
    expect(output).toContain("serialize");
    expect(output).toContain("totalWithTax");
  });

  it("pula função de navegador dizendo qual global ela usa", async () => {
    const { output } = await run([join(FIXTURES, "pure-broken.ts"), "--json"], FIXTURES, DEPS);
    const parsed = JSON.parse(output) as { findings: { func: string }[]; skipped: { reason: string }[] };
    expect(parsed.findings.map((f) => f.func)).not.toContain("currentPath");
    expect(parsed.skipped.some((s) => s.reason === "precisa de navegador: usa location")).toBe(true);
  });

  it("por padrão não passa null a parâmetro que declara string", async () => {
    // O compilador já impede essa chamada dentro de um projeto TypeScript.
    const { output } = await run([join(FIXTURES, "pure-broken.ts")], FIXTURES, DEPS);
    expect(output).not.toContain("stripMarkdown");
  });

  it("com --untrusted-input pega o que quebra com null", async () => {
    const { output, exitCode } = await run(
      [join(FIXTURES, "pure-broken.ts"), "--untrusted-input"],
      FIXTURES,
      DEPS
    );
    expect(exitCode).toBe(1);
    expect(output).toContain("stripMarkdown");
  });

  it("NÃO pega bug semântico com tipo correto — limitação conhecida e documentada", async () => {
    // "@sms.cal.com" é string válida, sem undefined nem NaN: nenhuma regra se aplica.
    // Este teste existe para que a limitação apareça se alguém tentar escondê-la.
    const { output, exitCode } = await run([join(FIXTURES, "pure-undetectable.ts")], FIXTURES, DEPS);
    expect(exitCode).toBe(0);
    expect(output).toContain("Nenhuma falha encontrada");
  });

  it("sai com código 0 no fixture correto", async () => {
    const { output, exitCode } = await run([join(FIXTURES, "pure-ok.ts")], FIXTURES, DEPS);
    expect(exitCode).toBe(0);
    expect(output).toContain("Nenhuma falha encontrada");
  });

  it("pula arquivo que importa em tempo de execução, dizendo o motivo", async () => {
    const { output, exitCode } = await run([join(FIXTURES, "impure.ts"), "--json"], FIXTURES, DEPS);
    expect(exitCode).toBe(0);
    const parsed = JSON.parse(output) as { skipped: { reason: string }[]; functionsChecked: number };
    expect(parsed.functionsChecked).toBe(0);
    expect(parsed.skipped[0]?.reason).toBe('importa "node:fs" em tempo de execução');
  });

  it("audita arquivo cujo único import é de tipo", async () => {
    const { exitCode } = await run([join(FIXTURES, "type-only-import.ts"), "--json"], FIXTURES, DEPS);
    expect(exitCode).toBe(0);
  });

  it("mostra o uso e sai com 1 quando não recebe glob", async () => {
    const { output, exitCode } = await run([], FIXTURES, DEPS);
    expect(exitCode).toBe(1);
    expect(output).toContain("Uso:");
  });

  it("sai com 0 no --help", async () => {
    expect((await run(["--help"], FIXTURES, DEPS)).exitCode).toBe(0);
  });
});

describe("regra d — função que não termina", () => {
  it("reporta a função que travou em vez de morrer junto", async () => {
    const { output, exitCode } = await run(
      [join(FIXTURES, "pure-hangs.ts")],
      FIXTURES,
      { ...DEPS, budgetMs: 4_000 }
    );
    expect(exitCode).toBe(1);
    expect(output).toContain("loopForever");
    expect(output).toContain("d");
  }, 30_000);
});
