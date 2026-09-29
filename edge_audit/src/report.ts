import { RULE_DESCRIPTIONS, type AuditResult } from "./types.ts";

function column(values: readonly string[], header: string): number {
  return Math.max(header.length, ...values.map((value) => value.length));
}

function pad(value: string, width: number): string {
  return value.padEnd(width, " ");
}

export function formatTable(result: AuditResult, rootDirectory: string): string {
  if (result.findings.length === 0) {
    return [
      `Nenhuma falha encontrada. ${result.functionsChecked} funções auditadas, ${result.callsMade} chamadas.`,
      ...(result.skipped.length > 0 ? [`${result.skipped.length} alvos pulados (rode com --json para ver quais).`] : []),
    ].join("\n");
  }

  const rows = result.findings.map((finding) => ({
    file: finding.file.startsWith(rootDirectory) ? finding.file.slice(rootDirectory.length + 1) : finding.file,
    func: finding.func,
    input: finding.input.length > 46 ? `${finding.input.slice(0, 43)}...` : finding.input,
    rule: finding.rule,
    what: finding.what,
  }));

  const widths = {
    file: column(rows.map((row) => row.file), "ARQUIVO"),
    func: column(rows.map((row) => row.func), "FUNÇÃO"),
    input: column(rows.map((row) => row.input), "ENTRADA"),
    rule: 5,
  };

  const lines = [
    [pad("ARQUIVO", widths.file), pad("FUNÇÃO", widths.func), pad("ENTRADA", widths.input), pad("REGRA", widths.rule), "O QUE ACONTECEU"].join("  "),
    "-".repeat(widths.file + widths.func + widths.input + widths.rule + 25),
    ...rows.map((row) =>
      [pad(row.file, widths.file), pad(row.func, widths.func), pad(row.input, widths.input), pad(row.rule, widths.rule), row.what].join("  ")
    ),
    "",
    `${result.findings.length} falhas em ${result.functionsChecked} funções auditadas (${result.callsMade} chamadas).`,
    "",
    "Regras:",
    ...(Object.entries(RULE_DESCRIPTIONS) as readonly [keyof typeof RULE_DESCRIPTIONS, string][]).map(
      ([rule, description]) => `  ${rule}) ${description}`
    ),
  ];

  if (result.skipped.length > 0) {
    lines.push("", `${result.skipped.length} alvos pulados (rode com --json para ver quais).`);
  }

  return lines.join("\n");
}

export function formatJson(result: AuditResult): string {
  return JSON.stringify(result, null, 2);
}
