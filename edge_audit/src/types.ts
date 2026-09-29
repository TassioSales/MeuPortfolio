export interface AdversarialInput {
  readonly label: string;
  readonly value: unknown;
}

/** Which `typeof` results a declared return type admits. `null` means "accept anything". */
export type AcceptedTypeofs = ReadonlySet<string> | null;

export interface FunctionUnderAudit {
  readonly file: string;
  readonly name: string;
  readonly parameterInputs: readonly (readonly AdversarialInput[])[];
  readonly acceptedTypeofs: AcceptedTypeofs;
  readonly returnsNever: boolean;
  readonly returnIsNullable: boolean;
}

export type Rule = "a" | "b" | "c" | "d";

export interface Finding {
  readonly file: string;
  readonly func: string;
  readonly input: string;
  readonly rule: Rule;
  readonly what: string;
}

export interface Skipped {
  readonly target: string;
  readonly reason: string;
}

export interface AuditResult {
  readonly findings: readonly Finding[];
  readonly skipped: readonly Skipped[];
  readonly functionsChecked: number;
  readonly callsMade: number;
}

export const RULE_DESCRIPTIONS: Readonly<Record<Rule, string>> = {
  a: "lançou exceção, e o retorno declarado não é never",
  b: "retornou valor cujo typeof contradiz o retorno declarado",
  c: "retornou string com 'undefined' ou 'NaN' que nenhuma entrada continha",
  d: "não retornou dentro do orçamento de tempo ou de memória",
};
