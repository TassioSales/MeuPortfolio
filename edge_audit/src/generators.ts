import type { Type } from "ts-morph";

import type { AdversarialInput } from "./types.ts";

const LONG_STRING_LENGTH = 1_000;
const BIG_ARRAY_LENGTH = 100;

function circularObject(): Record<string, unknown> {
  const object: Record<string, unknown> = { name: "circular" };
  object["self"] = object;
  return object;
}

function prototypePollutingObject(): Record<string, unknown> {
  // Built with JSON.parse so the key lands as own data rather than invoking the
  // Object.prototype setter, which is what an object literal would do here.
  return JSON.parse('{"__proto__": {"polluted": true}, "safe": 1}') as Record<string, unknown>;
}

const STRINGS: readonly AdversarialInput[] = [
  { label: '""', value: "" },
  { label: '" "', value: " " },
  { label: '"0"', value: "0" },
  { label: '"a\\nb"', value: "a\nb" },
  { label: `"x".repeat(${LONG_STRING_LENGTH})`, value: "x".repeat(LONG_STRING_LENGTH) },
];

const NUMBERS: readonly AdversarialInput[] = [
  { label: "0", value: 0 },
  { label: "-0", value: -0 },
  { label: "NaN", value: Number.NaN },
  { label: "Infinity", value: Number.POSITIVE_INFINITY },
  { label: "-Infinity", value: Number.NEGATIVE_INFINITY },
  { label: "Number.MAX_SAFE_INTEGER", value: Number.MAX_SAFE_INTEGER },
];

const BOOLEANS: readonly AdversarialInput[] = [
  { label: "true", value: true },
  { label: "false", value: false },
];

const DATES: readonly AdversarialInput[] = [
  { label: 'new Date("invalido")', value: new Date("invalido") },
  { label: "new Date(0)", value: new Date(0) },
];

const OBJECTS: readonly AdversarialInput[] = [
  { label: "{}", value: {} },
  { label: "{ self: <circular> }", value: circularObject() },
  { label: '{ "__proto__": {...} }', value: prototypePollutingObject() },
];

export const NULLISH: readonly AdversarialInput[] = [
  { label: "undefined", value: undefined },
  { label: "null", value: null },
];

function arraysOf(element: readonly AdversarialInput[]): readonly AdversarialInput[] {
  // The smallest sample fills the big array on purpose: the point is the element count, and the
  // longest sample would multiply into megabytes per value.
  const sample = [...element].sort((a, b) => String(a.value).length - String(b.value).length)[0]?.value;
  return [
    { label: "[]", value: [] },
    { label: "[undefined]", value: [undefined] },
    { label: `Array(${BIG_ARRAY_LENGTH})`, value: Array.from({ length: BIG_ARRAY_LENGTH }, () => sample) },
  ];
}

/**
 * The adversarial values a declared type admits, or `null` when the type cannot be synthesised.
 *
 * Returning `null` is deliberate: a function whose parameters cannot be built is skipped and
 * reported as skipped, rather than called with a guess that would produce a finding the author
 * could not act on.
 */
export function inputsForType(type: Type, depth = 0): readonly AdversarialInput[] | null {
  if (depth > 3) {
    return null;
  }

  if (type.isAny() || type.isUnknown()) {
    return [...NULLISH, ...STRINGS.slice(0, 2), ...NUMBERS.slice(0, 3), ...OBJECTS.slice(0, 2)];
  }
  if (type.isBoolean()) {
    return BOOLEANS;
  }
  if (type.isUnion()) {
    const collected: AdversarialInput[] = [];
    for (const member of type.getUnionTypes()) {
      const memberInputs = inputsForType(member, depth + 1);
      if (memberInputs === null) {
        return null;
      }
      const first = memberInputs[0];
      if (first !== undefined) {
        collected.push(first);
      }
    }
    return collected.length > 0 ? collected : null;
  }
  if (type.isUndefined() || type.isVoid()) {
    return [NULLISH[0] as AdversarialInput];
  }
  if (type.isNull()) {
    return [NULLISH[1] as AdversarialInput];
  }
  if (type.isStringLiteral()) {
    return [{ label: JSON.stringify(type.getLiteralValue()), value: type.getLiteralValue() }];
  }
  if (type.isNumberLiteral() || type.isBooleanLiteral()) {
    return [{ label: type.getText(), value: type.getLiteralValue() ?? type.getText() === "true" }];
  }
  if (type.isString()) {
    return STRINGS;
  }
  if (type.isNumber()) {
    return NUMBERS;
  }
  if (type.isBoolean()) {
    return BOOLEANS;
  }
  if (type.isArray() || type.isTuple()) {
    const element = type.getArrayElementType();
    const elementInputs = element === undefined ? STRINGS : (inputsForType(element, depth + 1) ?? STRINGS);
    return arraysOf(elementInputs);
  }
  if (/\bDate\b/.test(type.getText())) {
    return DATES;
  }
  // The `object` keyword is TypeFlags.NonPrimitive, so isObject() reports false for it.
  if (type.getText() === "object") {
    return OBJECTS;
  }
  if (type.isObject()) {
    // A call signature is a function parameter; synthesising one would mean inventing behaviour.
    if (type.getCallSignatures().length > 0) {
      return null;
    }

    const required = type.getProperties().filter((property) => !property.isOptional());
    if (required.length === 0) {
      return OBJECTS;
    }

    // Required properties are filled from their own types. Feeding `{}` to a parameter that
    // declares them would report a type error the compiler already rejects, not a real defect.
    const complete: Record<string, unknown> = {};
    for (const property of required) {
      const declaration = property.getValueDeclaration();
      if (declaration === undefined) {
        return null;
      }
      const propertyInputs = inputsForType(declaration.getType(), depth + 1);
      const first = propertyInputs?.[0];
      if (first === undefined) {
        return null;
      }
      complete[property.getName()] = first.value;
    }
    return [{ label: `{ ${required.map((p) => p.getName()).join(", ")} }`, value: complete }];
  }

  return null;
}
