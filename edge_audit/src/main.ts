import { run } from "./cli.ts";

const { output, exitCode } = await run(process.argv.slice(2), process.cwd());
process.stdout.write(`${output}\n`);
process.exit(exitCode);
