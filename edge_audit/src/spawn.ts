import { spawn } from "node:child_process";

import type { Finding, Skipped } from "./types.ts";
import type { WorkerLine } from "./worker.ts";

export const CALL_BUDGET_MS = 15_000;
export const CALL_BUDGET_MB = 512;

export interface FileOutcome {
  readonly findings: readonly Finding[];
  readonly skipped: readonly Skipped[];
  readonly functionsChecked: number;
  readonly callsMade: number;
}

export interface SpawnDeps {
  readonly workerEntry: string;
  readonly execPath: string;
  readonly budgetMs?: number;
}

/**
 * Audits one file in a child process, so a function that hangs or exhausts memory is a finding
 * rather than the end of the run.
 *
 * `randomString(Infinity)` is the case that forced this: it loops forever appending to a string.
 * Auditing in-process meant the tool died on exactly the defect it had just found.
 */
export function auditFileInChild(
  filePath: string,
  untrustedInput: boolean,
  deps: SpawnDeps
): Promise<FileOutcome> {
  return new Promise((resolve) => {
    const child = spawn(
      deps.execPath,
      [`--max-old-space-size=${CALL_BUDGET_MB}`, deps.workerEntry, filePath, untrustedInput ? "1" : "0"],
      { stdio: ["ignore", "pipe", "ignore"] }
    );

    const findings: Finding[] = [];
    const skipped: Skipped[] = [];
    const started = new Set<string>();
    const finished = new Set<string>();
    let callsMade = 0;
    let buffer = "";
    let settled = false;

    const timer = setTimeout(() => child.kill("SIGKILL"), deps.budgetMs ?? CALL_BUDGET_MS);

    const consume = (line: string): void => {
      if (line.trim() === "") {
        return;
      }
      let parsed: WorkerLine;
      try {
        parsed = JSON.parse(line) as WorkerLine;
      } catch {
        return;
      }
      if (parsed.type === "start") {
        started.add(parsed.func);
      } else if (parsed.type === "done") {
        finished.add(parsed.func);
        findings.push(...parsed.findings);
        callsMade += parsed.calls;
      } else {
        skipped.push(parsed.skipped);
      }
    };

    child.stdout.on("data", (chunk: Buffer) => {
      buffer += chunk.toString("utf8");
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        consume(line);
      }
    });

    const settle = (): void => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timer);
      consume(buffer);

      for (const func of started) {
        if (!finished.has(func)) {
          findings.push({
            file: filePath,
            func,
            input: "(não identificada: o processo morreu durante a chamada)",
            rule: "d",
            what: `não retornou em ${(deps.budgetMs ?? CALL_BUDGET_MS) / 1000}s ou passou de ${CALL_BUDGET_MB} MB`,
          });
        }
      }

      resolve({ findings, skipped, functionsChecked: finished.size + (started.size - finished.size), callsMade });
    };

    child.on("close", settle);
    child.on("error", (error) => {
      skipped.push({ target: filePath, reason: `não consegui rodar o worker: ${error.message}` });
      settle();
    });
  });
}
