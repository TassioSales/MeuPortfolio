import { auditOneFile } from "./worker.ts";

const [filePath, untrustedInput] = process.argv.slice(2);

if (filePath === undefined) {
  process.exit(2);
}

await auditOneFile(filePath, untrustedInput === "1", (line) => {
  process.stdout.write(`${JSON.stringify(line)}\n`);
});
