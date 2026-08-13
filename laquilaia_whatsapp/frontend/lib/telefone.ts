/**
 * Telefone: como mostrar e como abrir.
 *
 * O número chega do WhatsApp com DDI colado e sem separador —
 * `5561999887234`. Assim ele é ilegível na tela e inútil como link: quem lê
 * precisa contar dígitos para achar o DDD, e quem quer responder precisa
 * copiar, abrir o WhatsApp e colar.
 */

/** Só os dígitos, que é o que o `wa.me` aceita. */
export function digitos(telefone: string): string {
  return (telefone ?? "").replace(/\D/g, "");
}

/**
 * `5561999887234` → `+55 61 99988-7234`.
 *
 * Fora do padrão brasileiro (DDI 55 com 10 ou 11 dígitos locais), devolve o
 * número como veio: inventar formato para um telefone estrangeiro é pior que
 * não formatar — quebra o número em grupos errados e ele deixa de ser
 * reconhecível para quem mora lá.
 */
export function formatarTelefone(telefone: string): string {
  const d = digitos(telefone);

  if (d.startsWith("55") && (d.length === 12 || d.length === 13)) {
    const ddd = d.slice(2, 4);
    const local = d.slice(4);
    const corte = local.length === 9 ? 5 : 4;
    return `+55 ${ddd} ${local.slice(0, corte)}-${local.slice(corte)}`;
  }

  return telefone;
}

/**
 * O link que abre a conversa no WhatsApp.
 *
 * `wa.me` e não `tel:`: o contato veio pelo WhatsApp e é por lá que o
 * escritório responde. Vazio quando não há dígitos — link para `wa.me/` abre
 * uma página de erro do WhatsApp, o que é pior que não ter link.
 */
export function linkDoWhatsapp(telefone: string): string | null {
  const d = digitos(telefone);
  return d.length >= 10 ? `https://wa.me/${d}` : null;
}
