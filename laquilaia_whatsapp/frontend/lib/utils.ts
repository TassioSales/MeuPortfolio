import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Compõe classes do Tailwind resolvendo conflitos.
 *
 * `clsx` resolve os condicionais e o `twMerge` desempata classes da mesma
 * propriedade — sem ele, `cn("p-2", "p-4")` deixaria as duas no atributo e
 * quem vence passaria a depender da ordem no CSS gerado.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
