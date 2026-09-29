// Reproduz o caso que derrubava a própria ferramenta: uma função que recebe um tamanho e não o
// limita entra em loop infinito com Infinity, consumindo memória até o processo morrer.

const CHARACTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

/** Trava com Infinity: o laço nunca termina e a string cresce sem limite. */
export function loopForever(length = 12): string {
  let result = "";
  for (let i = 0; i < length; i++) {
    result += CHARACTERS.charAt(i % CHARACTERS.length);
  }
  return result;
}
