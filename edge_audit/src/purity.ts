import type { SourceFile } from "ts-morph";

/**
 * A module qualifies for auditing only when nothing it imports can run.
 *
 * This is the constraint that makes the whole approach possible: with every import erased at
 * compile time, the transpiled file has no runtime dependencies, so it can be loaded and its
 * functions called without reaching a database, the network or the filesystem. Auditing a module
 * that imports a live dependency would mean executing that dependency with hostile arguments.
 */
export function impurityReason(sourceFile: SourceFile): string | null {
  for (const declaration of sourceFile.getImportDeclarations()) {
    const specifier = declaration.getModuleSpecifierValue();

    if (declaration.isTypeOnly()) {
      continue;
    }
    if (declaration.getNamedImports().length > 0 && declaration.getNamedImports().every((n) => n.isTypeOnly())) {
      continue;
    }
    // A bare `import "./side-effect"` has no clause at all and exists only to run the module.
    return `importa "${specifier}" em tempo de execução`;
  }

  for (const declaration of sourceFile.getExportDeclarations()) {
    if (!declaration.isTypeOnly() && declaration.getModuleSpecifierValue() !== undefined) {
      return `reexporta "${declaration.getModuleSpecifierValue()}" em tempo de execução`;
    }
  }

  return null;
}
