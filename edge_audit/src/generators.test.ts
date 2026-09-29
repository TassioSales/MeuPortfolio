import { Project } from "ts-morph";
import { describe, expect, it } from "vitest";

import { inputsForType } from "./generators.ts";

function typeOf(annotation: string) {
  const project = new Project({ useInMemoryFileSystem: true });
  const file = project.createSourceFile("t.ts", `declare const value: ${annotation};`);
  return file.getVariableDeclarationOrThrow("value").getType();
}

function labels(annotation: string): readonly string[] {
  return (inputsForType(typeOf(annotation)) ?? []).map((input) => input.label);
}

describe("inputsForType", () => {
  it("cobre string vazia, espaço e string longa", () => {
    expect(labels("string")).toContain('""');
    expect(labels("string")).toContain('" "');
    expect(labels("string")).toHaveLength(5);
  });

  it("cobre NaN e os dois infinitos para number", () => {
    expect(labels("number")).toEqual(
      expect.arrayContaining(["NaN", "Infinity", "-Infinity", "0", "-0"])
    );
  });

  it("gera os dois booleanos", () => {
    expect(labels("boolean")).toEqual(["true", "false"]);
  });

  it("gera array vazio, array com undefined e array grande", () => {
    expect(labels("string[]")).toEqual(["[]", "[undefined]", "Array(100)"]);
  });

  it("gera data inválida", () => {
    expect(labels("Date")).toContain('new Date("invalido")');
  });

  it("gera objeto vazio, circular e com __proto__ quando o tipo não exige propriedade", () => {
    expect(labels("object")).toEqual(["{}", "{ self: <circular> }", '{ "__proto__": {...} }']);
  });

  it("monta o objeto circular de verdade", () => {
    const circular = inputsForType(typeOf("object"))?.[1]?.value as Record<string, unknown>;
    expect(circular["self"]).toBe(circular);
    expect(() => JSON.stringify(circular)).toThrow();
  });

  it("deixa __proto__ como propriedade própria, sem trocar o protótipo", () => {
    const polluted = inputsForType(typeOf("object"))?.[2]?.value as Record<string, unknown>;
    expect(Object.prototype.hasOwnProperty.call(polluted, "__proto__")).toBe(true);
    expect(Object.getPrototypeOf(polluted)).toBe(Object.prototype);
  });

  it("preenche as propriedades obrigatórias em vez de mandar {}", () => {
    const inputs = inputsForType(typeOf("{ a: number; b: string }"));
    expect(inputs).toHaveLength(1);
    expect(inputs?.[0]?.value).toEqual({ a: 0, b: "" });
  });

  it("trata objeto de propriedades todas opcionais como objeto livre", () => {
    expect(labels("{ a?: number }")).toEqual(["{}", "{ self: <circular> }", '{ "__proto__": {...} }']);
  });

  it("cobre um valor por membro da união", () => {
    expect(labels("string | number | null")).toHaveLength(3);
  });

  it("devolve null quando o tipo é uma função, que não dá para sintetizar", () => {
    expect(inputsForType(typeOf("(a: number) => string"))).toBeNull();
  });
});
