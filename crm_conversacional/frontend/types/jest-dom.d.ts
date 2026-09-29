/**
 * Registra os matchers do jest-dom (`toBeInTheDocument`, `toHaveValue`, ...)
 * no tipo `expect` do Jest — sem isto o `tsc` não os reconhece nos testes.
 */
import "@testing-library/jest-dom";
