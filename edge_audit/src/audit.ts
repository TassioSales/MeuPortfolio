import type { AdversarialInput, Finding, FunctionUnderAudit, Rule } from "./types.ts";

export const MAX_CALLS_PER_FUNCTION = 200;

/** Bounded cartesian product: stops at `limit` rather than materialising every combination. */
export function combinations(
  perParameter: readonly (readonly AdversarialInput[])[],
  limit: number
): readonly (readonly AdversarialInput[])[] {
  let rows: AdversarialInput[][] = [[]];

  for (const inputs of perParameter) {
    const next: AdversarialInput[][] = [];
    for (const row of rows) {
      for (const input of inputs) {
        if (next.length >= limit) {
          return next;
        }
        next.push([...row, input]);
      }
    }
    rows = next;
  }

  return rows;
}

function describe(row: readonly AdversarialInput[]): string {
  return `(${row.map((input) => input.label).join(", ")})`;
}

function looksLikeMissingValue(returned: string, row: readonly AdversarialInput[]): string | null {
  for (const token of ["undefined", "NaN"] as const) {
    if (!returned.includes(token)) {
      continue;
    }
    // Provenance has to be textual. A caller that passes the string "undefined" and gets it back
    // is being served correctly, but a caller that passes the number NaN and gets "R$ NaN" on a
    // receipt is not: the function was handed a value it should have refused, and printed it.
    const cameFromInput = row.some((input) => typeof input.value === "string" && input.value.includes(token));
    if (!cameFromInput) {
      return token;
    }
  }
  return null;
}

const BROWSER_GLOBALS = ["window", "document", "navigator", "localStorage", "sessionStorage", "location"] as const;

/**
 * A ReferenceError naming a browser global means the function needs a DOM, not that it is broken.
 *
 * Reporting it as a defect would bury the real findings: a utilities folder in a web app holds
 * plenty of functions that only ever run in the browser, and every one of them would light up.
 */
function requiredBrowserGlobal(error: unknown): string | null {
  if (!(error instanceof ReferenceError)) {
    return null;
  }
  return BROWSER_GLOBALS.find((global) => error.message.startsWith(`${global} is not defined`)) ?? null;
}

export interface FunctionAuditResult {
  readonly findings: readonly Finding[];
  readonly calls: number;
  /** Set when the function turned out to need a browser, which makes it unauditable here. */
  readonly needsBrowser: string | null;
}

const CONSOLE_METHODS = ["log", "info", "warn", "error", "debug", "trace"] as const;

/**
 * Silences the audited code while it runs.
 *
 * Utility functions that log on a failed parse are common, and 200 hostile calls to one of them
 * would bury the report under the target's own output. Restoring in `finally` matters: a throwing
 * call must not leave the console muted for the rest of the run.
 */
function withSilencedConsole<T>(body: () => T): T {
  const saved = CONSOLE_METHODS.map((method) => [method, console[method]] as const);
  for (const method of CONSOLE_METHODS) {
    console[method] = () => undefined;
  }
  try {
    return body();
  } finally {
    for (const [method, original] of saved) {
      console[method] = original;
    }
  }
}

export function auditFunction(
  target: FunctionUnderAudit,
  implementation: (...args: readonly unknown[]) => unknown
): FunctionAuditResult {
  const findings: Finding[] = [];
  const seen = new Set<string>();
  let calls = 0;
  let needsBrowser: string | null = null;

  const record = (rule: Rule, input: string, what: string, cause: string): void => {
    // One finding per distinct failure mode: 200 calls hitting the same bug is still one bug.
    // Keyed on the cause rather than on `what`, which embeds the values of this particular call.
    const key = `${rule}:${cause}`;
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    findings.push({ file: target.file, func: target.name, input, rule, what });
  };

  for (const row of combinations(target.parameterInputs, MAX_CALLS_PER_FUNCTION)) {
    calls += 1;
    let returned: unknown;

    try {
      returned = withSilencedConsole(() => implementation(...row.map((input) => input.value)));
    } catch (error) {
      const browserGlobal = requiredBrowserGlobal(error);
      if (browserGlobal !== null) {
        needsBrowser = browserGlobal;
        break;
      }
      if (!target.returnsNever) {
        const name = error instanceof Error ? error.constructor.name : typeof error;
        const message = error instanceof Error ? error.message : String(error);
        record("a", describe(row), `${name}: ${message.slice(0, 120)}`, name);
      }
      continue;
    }

    const actual = typeof returned;
    const accepted = target.acceptedTypeofs;
    if (accepted !== null && !accepted.has(actual)) {
      record("b", describe(row), `retorno declarado admite ${[...accepted].join("|")}, devolveu ${actual}`, `b:${actual}`);
    } else if (returned === null && accepted !== null && !target.returnIsNullable) {
      record("b", describe(row), "retorno não é anulável, devolveu null", "b:null");
    }

    if (typeof returned === "string") {
      const token = looksLikeMissingValue(returned, row);
      if (token !== null) {
        record("c", describe(row), `devolveu ${JSON.stringify(returned.slice(0, 60))} contendo "${token}"`, `c:${token}`);
      }
    }
  }

  return { findings: needsBrowser === null ? findings : [], calls, needsBrowser };
}
