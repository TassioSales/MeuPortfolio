import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import { pathToFileURL } from "node:url";

import { ts } from "ts-morph";

/**
 * Loads a pure module's exports by stripping its types and importing the result.
 *
 * Erasing the types is enough because the caller has already established the module imports
 * nothing that runs, so the emitted JavaScript has no dependencies left to resolve.
 */
export async function loadModuleExports(
  filePath: string,
  sourceText: string
): Promise<Record<string, unknown>> {
  const directory = mkdtempSync(join(tmpdir(), "edge-audit-"));
  const emittedPath = join(directory, `${basename(filePath).replace(/\.tsx?$/, "")}.mjs`);

  try {
    const emitted = ts.transpileModule(sourceText, {
      compilerOptions: {
        target: ts.ScriptTarget.ES2023,
        module: ts.ModuleKind.ESNext,
      },
      fileName: filePath,
    });
    writeFileSync(emittedPath, emitted.outputText, "utf8");
    return (await import(pathToFileURL(emittedPath).href)) as Record<string, unknown>;
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}
