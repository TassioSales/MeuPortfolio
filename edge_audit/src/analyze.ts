import { Node, SyntaxKind, type ArrowFunction, type FunctionDeclaration, type FunctionExpression, type SourceFile, type Type } from "ts-morph";

import { inputsForType, NULLISH } from "./generators.ts";
import type { AcceptedTypeofs, AdversarialInput, FunctionUnderAudit, Skipped } from "./types.ts";

/** `typeof` results a declared return type admits; `null` accepts anything. */
function acceptedTypeofs(type: Type, depth = 0): AcceptedTypeofs {
  if (depth > 3 || type.isAny() || type.isUnknown()) {
    return null;
  }
  if (type.isUnion()) {
    const accepted = new Set<string>();
    for (const member of type.getUnionTypes()) {
      const memberAccepted = acceptedTypeofs(member, depth + 1);
      if (memberAccepted === null) {
        return null;
      }
      for (const entry of memberAccepted) {
        accepted.add(entry);
      }
    }
    return accepted;
  }
  if (type.isString() || type.isStringLiteral()) return new Set(["string"]);
  if (type.isNumber() || type.isNumberLiteral()) return new Set(["number"]);
  if (type.isBoolean() || type.isBooleanLiteral()) return new Set(["boolean"]);
  if (type.isVoid() || type.isUndefined()) return new Set(["undefined"]);
  if (type.isNull()) return new Set(["object"]);
  if (type.isObject()) return new Set(["object", "function"]);
  return null;
}

function isNullable(type: Type): boolean {
  return type.isNullable() || type.isUnion()
    ? type.getUnionTypes().some((member) => member.isNull() || member.isUndefined())
    : type.isNull() || type.isUndefined();
}

export interface AnalyzedFile {
  readonly functions: readonly FunctionUnderAudit[];
  readonly skipped: readonly Skipped[];
}

/**
 * Reads every exported function of a source file and turns its signature into the inputs to
 * attack it with. Functions whose parameters cannot be synthesised are reported as skipped.
 */
export interface AnalyzeOptions {
  /**
   * Also pass null and undefined to parameters whose type forbids them.
   *
   * Off by default: inside a TypeScript codebase the compiler already rejects those calls, so a
   * finding would be noise. On for a published library, whose callers may be JavaScript and whose
   * declared types are a promise nobody enforces at the boundary.
   */
  readonly untrustedInput: boolean;
}

export function analyzeFile(sourceFile: SourceFile, options: AnalyzeOptions): AnalyzedFile {
  const file = sourceFile.getFilePath();
  const functions: FunctionUnderAudit[] = [];
  const skipped: Skipped[] = [];

  for (const [name, declarations] of sourceFile.getExportedDeclarations()) {
    for (const declaration of declarations) {
      const signatureNode: FunctionDeclaration | ArrowFunction | FunctionExpression | undefined =
        Node.isFunctionDeclaration(declaration)
          ? declaration
          : Node.isVariableDeclaration(declaration)
            ? (declaration.getInitializerIfKind(SyntaxKind.ArrowFunction) ??
              declaration.getInitializerIfKind(SyntaxKind.FunctionExpression))
            : undefined;

      if (signatureNode === undefined) {
        continue;
      }
      if (signatureNode.isAsync()) {
        skipped.push({ target: `${name} (${file})`, reason: "função assíncrona" });
        continue;
      }

      const parameterInputs: (readonly AdversarialInput[])[] = [];
      let unsupported: string | null = null;

      for (const parameter of signatureNode.getParameters()) {
        if (parameter.isRestParameter()) {
          unsupported = `parâmetro rest "${parameter.getName()}"`;
          break;
        }
        const inputs = inputsForType(parameter.getType());
        if (inputs === null) {
          unsupported = `tipo do parâmetro "${parameter.getName()}" (${parameter.getType().getText()})`;
          break;
        }
        const type = parameter.getType();
        const alreadyNullish = type.isNullable() || parameter.hasQuestionToken();
        parameterInputs.push(
          alreadyNullish
            ? [{ label: "undefined", value: undefined }, ...inputs]
            : options.untrustedInput
              ? [...NULLISH, ...inputs]
              : inputs
        );
      }

      if (unsupported !== null) {
        skipped.push({ target: `${name} (${file})`, reason: `não sei sintetizar o ${unsupported}` });
        continue;
      }

      const returnType = signatureNode.getReturnType();
      functions.push({
        file,
        name,
        parameterInputs,
        acceptedTypeofs: acceptedTypeofs(returnType),
        returnsNever: returnType.isNever(),
        returnIsNullable: isNullable(returnType),
      });
    }
  }

  return { functions, skipped };
}
