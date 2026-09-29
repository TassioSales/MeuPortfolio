import { Project } from "ts-morph";
import { describe, expect, it } from "vitest";

import { impurityReason } from "./purity.ts";

function reasonFor(source: string): string | null {
  const project = new Project({ useInMemoryFileSystem: true });
  return impurityReason(project.createSourceFile("m.ts", source));
}

describe("impurityReason", () => {
  it("aceita arquivo sem import", () => {
    expect(reasonFor("export const x = 1;")).toBeNull();
  });

  it("aceita import type", () => {
    expect(reasonFor('import type { A } from "./a";\nexport const x = 1;')).toBeNull();
  });

  it("aceita import de named type-only", () => {
    expect(reasonFor('import { type A } from "./a";\nexport const x = 1;')).toBeNull();
  });

  it("recusa import de valor", () => {
    expect(reasonFor('import { readFileSync } from "node:fs";')).toBe('importa "node:fs" em tempo de execução');
  });

  it("recusa import só por efeito colateral", () => {
    expect(reasonFor('import "./setup";')).toBe('importa "./setup" em tempo de execução');
  });

  it("recusa reexport de valor", () => {
    expect(reasonFor('export { a } from "./a";')).toBe('reexporta "./a" em tempo de execução');
  });
});
