import { describe, expect, it } from "vitest";

import { auditFunction, combinations, MAX_CALLS_PER_FUNCTION } from "./audit.ts";
import type { AdversarialInput, FunctionUnderAudit } from "./types.ts";

const input = (label: string, value: unknown): AdversarialInput => ({ label, value });

function target(overrides: Partial<FunctionUnderAudit> = {}): FunctionUnderAudit {
  return {
    file: "/f.ts",
    name: "fn",
    parameterInputs: [[input('""', "")]],
    acceptedTypeofs: new Set(["string"]),
    returnsNever: false,
    returnIsNullable: false,
    ...overrides,
  };
}

describe("combinations", () => {
  it("faz o produto cartesiano", () => {
    const rows = combinations([[input("a", 1), input("b", 2)], [input("c", 3)]], 100);
    expect(rows.map((row) => row.map((i) => i.label).join(""))).toEqual(["ac", "bc"]);
  });

  it("respeita o limite em vez de explodir", () => {
    const many = Array.from({ length: 10 }, (_, i) => input(String(i), i));
    const rows = combinations([many, many, many, many], MAX_CALLS_PER_FUNCTION);
    expect(rows.length).toBeLessThanOrEqual(MAX_CALLS_PER_FUNCTION);
  });

  it("devolve uma linha vazia para função sem parâmetro", () => {
    expect(combinations([], 100)).toEqual([[]]);
  });
});

describe("console do código auditado", () => {
  it("não deixa a função auditada escrever no relatório", () => {
    const written: string[] = [];
    const original = console.log;
    console.log = ((...args: unknown[]) => written.push(args.join(" "))) as typeof console.log;
    try {
      auditFunction(target(), (value) => {
        console.log("ruido do alvo");
        return String(value);
      });
    } finally {
      console.log = original;
    }
    expect(written).toEqual([]);
  });

  it("restaura o console mesmo quando a função lança", () => {
    const before = console.log;
    auditFunction(target(), () => {
      throw new Error("x");
    });
    expect(console.log).toBe(before);
  });
});

describe("função que precisa de navegador", () => {
  it("não reporta ReferenceError de global do navegador, e diz qual global", () => {
    const { findings, needsBrowser } = auditFunction(target(), () => {
      throw new ReferenceError("window is not defined");
    });
    expect(findings).toEqual([]);
    expect(needsBrowser).toBe("window");
  });

  it("continua reportando ReferenceError que não é de navegador", () => {
    const { findings, needsBrowser } = auditFunction(target(), () => {
      throw new ReferenceError("minhaVariavel is not defined");
    });
    expect(needsBrowser).toBeNull();
    expect(findings).toHaveLength(1);
  });
});

describe("regra a — exceção", () => {
  it("reporta exceção quando o retorno não é never", () => {
    const { findings } = auditFunction(target(), () => {
      throw new TypeError("quebrou");
    });
    expect(findings).toHaveLength(1);
    expect(findings[0]?.rule).toBe("a");
    expect(findings[0]?.what).toBe("TypeError: quebrou");
  });

  it("não reporta exceção quando o retorno declarado é never", () => {
    const { findings } = auditFunction(target({ returnsNever: true }), () => {
      throw new Error("esperado");
    });
    expect(findings).toEqual([]);
  });
});

describe("regra b — retorno contradiz o tipo", () => {
  it("reporta undefined onde string foi prometida", () => {
    const { findings } = auditFunction(target(), () => undefined);
    expect(findings[0]?.rule).toBe("b");
    expect(findings[0]?.what).toContain("devolveu undefined");
  });

  it("reporta null quando o retorno não é anulável", () => {
    const { findings } = auditFunction(target({ acceptedTypeofs: new Set(["object"]) }), () => null);
    expect(findings[0]?.what).toBe("retorno não é anulável, devolveu null");
  });

  it("aceita null quando o retorno é anulável", () => {
    const seen = auditFunction(
      target({ acceptedTypeofs: new Set(["object", "undefined"]), returnIsNullable: true }),
      () => null
    );
    expect(seen.findings).toEqual([]);
  });

  it("não reporta nada quando o retorno é any", () => {
    expect(auditFunction(target({ acceptedTypeofs: null }), () => 42).findings).toEqual([]);
  });
});

describe("regra c — valor ausente interpolado", () => {
  it("reporta string com undefined que não veio da entrada", () => {
    const { findings } = auditFunction(target(), () => "user@undefined");
    expect(findings[0]?.rule).toBe("c");
    expect(findings[0]?.what).toContain('contendo "undefined"');
  });

  it("reporta string com NaN", () => {
    const { findings } = auditFunction(target(), () => "R$ NaN");
    expect(findings[0]?.rule).toBe("c");
  });

  it("não reporta quando o texto veio da própria entrada", () => {
    const passesThrough = auditFunction(
      target({ parameterInputs: [[input('"undefined"', "undefined")]] }),
      (value) => String(value)
    );
    expect(passesThrough.findings).toEqual([]);
  });
});

describe("deduplicação", () => {
  it("junta 200 chamadas que falham igual em uma falha só", () => {
    const many = Array.from({ length: 50 }, (_, i) => input(String(i), i));
    const { findings, calls } = auditFunction(
      target({ parameterInputs: [many, many] }),
      () => {
        throw new Error("sempre o mesmo");
      }
    );
    expect(calls).toBe(MAX_CALLS_PER_FUNCTION);
    expect(findings).toHaveLength(1);
  });
});
