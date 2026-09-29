import { readFileSync } from "node:fs";

import { Project } from "ts-morph";

import { analyzeFile } from "./analyze.ts";
import { auditFunction } from "./audit.ts";
import { loadModuleExports } from "./execute.ts";
import type { Finding, Skipped } from "./types.ts";

export type WorkerLine =
  | { readonly type: "start"; readonly func: string }
  | { readonly type: "done"; readonly func: string; readonly findings: readonly Finding[]; readonly calls: number }
  | { readonly type: "skipped"; readonly skipped: Skipped };

/**
 * Audits one file and reports progress as it goes, one JSON object per line.
 *
 * The `start` line before each call matters more than it looks: a function that never returns takes
 * this process down with it, and the parent identifies the culprit as the one function that started
 * without finishing. Without it, a hang would be indistinguishable from a crash anywhere in the file.
 */
export async function auditOneFile(filePath: string, untrustedInput: boolean, emit: (line: WorkerLine) => void): Promise<void> {
  const project = new Project({ compilerOptions: { strict: true }, skipAddingFilesFromTsConfig: true });
  const sourceFile = project.addSourceFileAtPath(filePath);
  const analyzed = analyzeFile(sourceFile, { untrustedInput });

  for (const skipped of analyzed.skipped) {
    emit({ type: "skipped", skipped });
  }
  if (analyzed.functions.length === 0) {
    return;
  }

  const exports = await loadModuleExports(filePath, readFileSync(filePath, "utf8"));

  for (const target of analyzed.functions) {
    const implementation = exports[target.name];
    if (typeof implementation !== "function") {
      emit({ type: "skipped", skipped: { target: `${target.name} (${filePath})`, reason: "export não é função em tempo de execução" } });
      continue;
    }
    emit({ type: "start", func: target.name });
    const result = auditFunction(target, implementation as (...args: readonly unknown[]) => unknown);
    emit({ type: "done", func: target.name, findings: result.findings, calls: result.calls });
    if (result.needsBrowser !== null) {
      emit({
        type: "skipped",
        skipped: { target: `${target.name} (${filePath})`, reason: `precisa de navegador: usa ${result.needsBrowser}` },
      });
    }
  }
}
