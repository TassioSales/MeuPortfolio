import { timingSafeEqual } from 'node:crypto';

/**
 * A autenticação do webhook, depois da saída da Meta.
 *
 * O QUE SE PERDEU
 *
 * A Meta assinava cada webhook com HMAC-SHA256 sobre os bytes crus do corpo. Era
 * uma prova de duas coisas ao mesmo tempo: que o remetente conhecia o segredo E
 * que o corpo não foi alterado no caminho. A Evolution não assina nada — ela faz
 * um POST comum no endereço cadastrado.
 *
 * O QUE ENTROU NO LUGAR
 *
 * Um segredo no CAMINHO: a Evolution é configurada para chamar
 * `/webhook/<segredo>`, e o valor é comparado aqui em tempo constante.
 *
 * Isto prova só a primeira das duas coisas. Não há integridade do corpo: quem
 * estiver no meio do caminho pode alterar o JSON sem que se perceba. Em troca,
 * funciona em qualquer versão da Evolution, sem depender de ela suportar
 * cabeçalho customizado no webhook — o que varia entre versões.
 *
 * POR QUE ISSO IMPORTA TANTO
 *
 * Um `/webhook` aberto não significa "aceita chamado falso". Quem postasse ali
 * faria o bot ENVIAR mensagem para qualquer número, e isso termina com o número
 * banido pelo WhatsApp. É a mesma ameaça que definia o desenho anterior, e a
 * razão de este módulo continuar existindo em vez de a rota ficar sem guarda.
 *
 * CONSEQUÊNCIAS OPERACIONAIS, que precisam ser conhecidas:
 *
 *   - A URL inteira, segredo incluso, aparece em log de acesso de proxy e de
 *     servidor. Com a Cloudflare na frente, ela está nos logs dela.
 *   - Trocar o segredo exige reconfigurar o webhook na Evolution, senão as
 *     mensagens passam a ser recusadas em silêncio (401) e ninguém recebe
 *     resposta.
 *   - HTTPS é obrigatório. Em HTTP o segredo trafega em claro na primeira linha
 *     da requisição.
 */
export function comparacaoSegura(a: string, b: string): boolean {
  const bufA = Buffer.from(a, 'utf8');
  const bufB = Buffer.from(b, 'utf8');

  // `timingSafeEqual` exige o mesmo tamanho, e estourar aqui já vazaria a
  // informação de que os tamanhos diferem. A comparação de tamanho antes é
  // aceitável: ela revela o comprimento do segredo, não o conteúdo.
  if (bufA.length !== bufB.length) return false;

  return timingSafeEqual(bufA, bufB);
}

/**
 * O segredo apresentado na URL confere?
 *
 * Recebe o valor já extraído do caminho. String vazia, ausente ou de outro
 * tamanho falha — e falha do mesmo jeito, sem dizer qual dos casos foi.
 */
export function segredoValido(apresentado: unknown, esperado: string): boolean {
  if (typeof apresentado !== 'string' || apresentado === '') return false;
  if (esperado === '') return false;
  return comparacaoSegura(apresentado, esperado);
}
