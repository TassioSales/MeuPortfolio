import { join } from "node:path";

import { Project } from "ts-morph";

import { impurityReason } from "./purity.ts";
import { formatJson, formatTable } from "./report.ts";
import { auditFileInChild, type SpawnDeps } from "./spawn.ts";
import type { Finding, Skipped } from "./types.ts";

interface Options {
  readonly patterns: readonly string[];
  readonly json: boolean;
  readonly help: boolean;
  readonly untrustedInput: boolean;
}

export function parseArguments(argv: readonly string[]): Options {
  const patterns: string[] = [];
  let json = false;
  let help = false;
  let untrustedInput = false;

  for (const argument of argv) {
    if (argument === "--json") {
      json = true;
    } else if (argument === "--untrusted-input") {
      untrustedInput = true;
    } else if (argument === "--help" || argument === "-h") {
      help = true;
    } else if (argument.startsWith("-")) {
      throw new Error(`Opção desconhecida: ${argument}`);
    } else {
      patterns.push(argument);
    }
  }

  return { patterns, json, help, untrustedInput };
}

const USAGE = `edge-audit — audita funções utilitárias TypeScript em casos-limite

Uso:
  edge-audit "<glob>" [...] [--json] [--untrusted-input]

Exemplo:
  edge-audit "src/**/*.ts"

Opções:
  --json              saída em JSON, incluindo a lista de alvos pulados
  --untrusted-input   também passa null e undefined a parâmetros cujo tipo proíbe.
                      Use quando a biblioteca é publicada e pode ser chamada de
                      JavaScript, onde o tipo declarado não é garantia nenhuma.
  --help              esta mensagem

Só audita módulos puros: arquivos cujos imports são todos de tipo. Qualquer
arquivo que importe algo em tempo de execução é pulado, e o motivo aparece no
relatório.`;

/** Files whose functions can be reached, and the ones that cannot, decided without running anything. */
export function planFiles(patterns: readonly string[]): { auditable: readonly string[]; skipped: readonly Skipped[] } {
  const project = new Project({ compilerOptions: { allowJs: false, strict: true }, skipAddingFilesFromTsConfig: true });
  project.addSourceFilesAtPaths(patterns);

  const auditable: string[] = [];
  const skipped: Skipped[] = [];

  for (const sourceFile of project.getSourceFiles()) {
    const filePath = sourceFile.getFilePath();
    if (/\.(test|spec|d)\.tsx?$/.test(filePath)) {
      continue;
    }
    const impurity = impurityReason(sourceFile);
    if (impurity !== null) {
      skipped.push({ target: filePath, reason: impurity });
      continue;
    }
    auditable.push(filePath);
  }

  return { auditable, skipped };
}

export async function run(
  argv: readonly string[],
  cwd: string,
  deps?: Partial<SpawnDeps>
): Promise<{ output: string; exitCode: number }> {
  const options = parseArguments(argv);

  if (options.help || options.patterns.length === 0) {
    return { output: USAGE, exitCode: options.help ? 0 : 1 };
  }

  const spawnDeps: SpawnDeps = {
    workerEntry: deps?.workerEntry ?? join(import.meta.dirname, "worker-main.js"),
    execPath: deps?.execPath ?? process.execPath,
    ...(deps?.budgetMs === undefined ? {} : { budgetMs: deps.budgetMs }),
  };

  const plan = planFiles(options.patterns);
  const findings: Finding[] = [];
  const skipped: Skipped[] = [...plan.skipped];
  let functionsChecked = 0;
  let callsMade = 0;

  for (const filePath of plan.auditable) {
    const outcome = await auditFileInChild(filePath, options.untrustedInput, spawnDeps);
    findings.push(...outcome.findings);
    skipped.push(...outcome.skipped);
    functionsChecked += outcome.functionsChecked;
    callsMade += outcome.callsMade;
  }

  const result = { findings, skipped, functionsChecked, callsMade };
  return {
    output: options.json ? formatJson(result) : formatTable(result, cwd),
    exitCode: findings.length > 0 ? 1 : 0,
  };
}
