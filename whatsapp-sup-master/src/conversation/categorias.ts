import { Prisma } from '../generated/prisma/client';
import { log } from '../log';
import { Entrada, MAX_CORPO_MENSAGEM, normalizar } from './flows';

/**
 * O menu numerado de assuntos, e a navegação na árvore de `Categoria`.
 *
 * A regra que este arquivo existe para concentrar: O NÚMERO QUE O USUÁRIO DIGITA
 * NÃO É NADA GUARDADO NO BANCO. Ele é a posição dentro da lista de irmãs ATIVAS,
 * calculada na hora de montar o menu - 1..N, sem buracos. A coluna `ordem` diz
 * só a sequência; desativar a segunda de seis não pode fazer o menu pular do 1
 * para o 3, e reordenar no painel não pode exigir renumerar nada.
 *
 * O que vai para o banco é sempre o `id` da categoria, resolvido aqui.
 */

export type NoDoMenu = { id: number; rotulo: string };
export type OpcaoMenu = { numero: number; id: number; rotulo: string };

/** Escolha já resolvida contra o menu oferecido. */
export type Escolha = { tipo: 'no'; id: number } | { tipo: 'voltar' };

// Prefixo dos ids de botão/lista deste menu. Protocolo interno, como
// `editar_descricao`: não é reconhecido se for DIGITADO (ver `interpretarEscolha`).
export const PREFIXO_OPCAO = 'cat_';
export const ID_VOLTAR = 'cat_voltar';

const NOTA_SEM_VOLTAR = 'Responda com o número da opção.';
const NOTA_COM_VOLTAR = 'Responda com o número da opção, ou 0 para voltar.';

/** Separador do caminho na árvore ("SUPORTE > PDV"). */
const SEPARADOR = ' / ';

// Teto de profundidade ao subir a árvore. A API impede criar ciclo (ver
// internal/categorias.ts), mas o banco é um arquivo que alguém pode editar com
// SQL crua - e um ciclo aqui viraria laço infinito dentro da transação que
// atende a mensagem do usuário.
const MAX_PROFUNDIDADE = 10;

export const CABECALHO_RAIZ = 'Olá! Para abrir seu chamado, escolha o assunto do atendimento:';

export const CABECALHO_FILHAS = 'Agora escolha a opção mais específica:';

/**
 * As opções do nível atual: as filhas de `paiId` (ou as raízes, se nulo) que
 * podem ser OFERECIDAS na conversa.
 *
 * Dois filtros, e nenhum dos dois é o mesmo que o outro:
 *   - `ativa`: o assunto saiu de circulação. Some de todo lugar de escolha.
 *   - `visivelNoWhatsapp`: o assunto é de USO INTERNO. Continua vivo e no
 *     seletor do painel - a TI classifica chamado com ele -, mas o cliente
 *     nunca o vê no menu.
 *
 * Esta é a ÚNICA porta pela qual um assunto entra na conversa: o handler usa a
 * mesma lista para montar o menu e para interpretar o número recebido. É o que
 * garante que um assunto interno não seja escolhível nem digitando o número que
 * ele "teria" - a posição 3 é sempre a terceira opção OFERECIDA, e a whitelist
 * de `interpretarEscolha` é feita destas mesmas opções.
 *
 * Um pai fora do menu esconde a subárvore inteira sem precisar de cascata: a
 * navegação desce um nível por vez, e um nó que nunca é oferecido nunca vira o
 * `paiId` consultado aqui.
 *
 * `ordem` empata com frequência - o painel deixa criar duas categorias na mesma
 * posição -, e sem o desempate por `id` a numeração do menu mudaria de uma
 * mensagem para a outra sem nada ter sido alterado.
 */
export async function filhasNoMenu(
  tx: Prisma.TransactionClient,
  paiId: number | null
): Promise<NoDoMenu[]> {
  return tx.categoria.findMany({
    where: { paiId, ativa: true, visivelNoWhatsapp: true },
    orderBy: [{ ordem: 'asc' }, { id: 'asc' }],
    select: { id: true, rotulo: true },
  });
}

/**
 * O nó onde a conversa PAROU ainda pode ser oferecido?
 *
 * Existe por causa da conversa que está no meio da árvore quando alguém mexe no
 * painel. `filhasNoMenu` filtra as FILHAS, e o nó atual não passa por ele - a
 * pessoa já desceu. Sem esta checagem, marcar "SUPORTE" como de uso interno não
 * alcançaria quem já estava dentro de "SUPORTE": as filhas dele continuam com a
 * coluna `true`, e seguiriam sendo oferecidas por horas, até a sessão expirar.
 *
 * Sobe até a raiz e não olha só o nó: a marcação de um avô vale para o ramo
 * inteiro pelo mesmo motivo - ninguém alcança o que está embaixo de uma opção
 * que não é oferecida.
 *
 * Vale para `ativa` também, e não por simetria decorativa: desativar um
 * guarda-chuva no painel tinha exatamente o mesmo furo.
 *
 * `null` (a raiz) é sempre oferecível - é onde todo mundo começa. Um nó que
 * sumiu do banco devolve `false`: sem saber onde está, o certo é recomeçar.
 *
 * Estourar `MAX_PROFUNDIDADE` devolve `true`, e aqui o padrão é o OPOSTO do de
 * `criariaCiclo` de propósito. Lá, recusar a escrita não custa nada a ninguém;
 * aqui, `false` jogaria a conversa de volta para a raiz a CADA mensagem, e uma
 * árvore funda demais (ou um ciclo gravado com SQL crua) viraria um loop na cara
 * de quem só queria abrir um chamado. Não mexer é o neutro.
 */
export async function noAindaOferecivel(
  tx: Prisma.TransactionClient,
  id: number | null
): Promise<boolean> {
  let atual: number | null = id;

  for (let i = 0; i < MAX_PROFUNDIDADE && atual !== null; i++) {
    const no: { ativa: boolean; visivelNoWhatsapp: boolean; paiId: number | null } | null =
      await tx.categoria.findUnique({
        where: { id: atual },
        select: { ativa: true, visivelNoWhatsapp: true, paiId: true },
      });

    if (no === null) return false;
    if (!no.ativa || !no.visivelNoWhatsapp) return false;
    atual = no.paiId;
  }

  return true;
}

export function opcoesDoMenu(filhas: NoDoMenu[]): OpcaoMenu[] {
  return filhas.map((c, i) => ({ numero: i + 1, id: c.id, rotulo: c.rotulo }));
}

/**
 * O menu como TEXTO, que é a versão que manda.
 *
 * Já foi "a versão que manda" em contraste com linhas interativas; hoje é a
 * única versão que existe. A Evolution envia texto puro, então o rótulo inteiro
 * cabe e responder com o número é o caminho, não o remendo para quando o botão
 * não renderiza.
 *
 * Se a lista não couber no corpo, as últimas opções ficam de fora do TEXTO. Isso
 * grita no log em vez de acontecer calado, porque uma opção invisível é uma
 * opção que ninguém escolhe. Com o teto em 4096 (e não mais nos 1024 da mensagem
 * interativa da Meta) isso deixou de ser um risco próximo: são dezenas de
 * assuntos de folga.
 */
export function textoDoMenu(cabecalho: string, opcoes: OpcaoMenu[], podeVoltar: boolean): string {
  const nota = podeVoltar ? NOTA_COM_VOLTAR : NOTA_SEM_VOLTAR;
  const espaco = MAX_CORPO_MENSAGEM - `${cabecalho}\n\n\n\n${nota}`.length;

  const linhas: string[] = [];
  let usado = 0;
  for (const o of opcoes) {
    const linha = `${o.numero}. ${o.rotulo}`;
    const custo = linha.length + (linhas.length > 0 ? 1 : 0);
    if (usado + custo > espaco) {
      log.error(
        { cabidas: linhas.length, total: opcoes.length },
        'Menu de assuntos não coube no corpo da mensagem; opções ficaram de fora'
      );
      break;
    }
    linhas.push(linha);
    usado += custo;
  }

  return `${cabecalho}\n\n${linhas.join('\n')}\n\n${nota}`;
}

/**
 * Resolve o que chegou contra as opções que ACABARAM de ser oferecidas.
 *
 * Devolver `null` significa "não reconheci" - nunca um palpite. Três formas são
 * aceitas, e todas passam pela mesma whitelist:
 *   - o número da opção (o caminho principal, e o que o texto pede);
 *   - o toque na linha da lista, que devolve o id interno `cat_<id>`;
 *   - o rótulo digitado por extenso, porque muita gente responde "MUDANÇA DE
 *     CNPJ" em vez de "3".
 *
 * A whitelist contra `opcoes` não é zelo: o WhatsApp mantém os botões antigos
 * clicáveis no histórico da conversa. Sem ela, tocar num menu de três mensagens
 * atrás escolheria um assunto que não está mais sendo oferecido - ou, pior, um
 * nó de OUTRO ramo da árvore.
 */
export function interpretarEscolha(
  entrada: Entrada,
  opcoes: OpcaoMenu[],
  podeVoltar: boolean
): Escolha | null {
  if (entrada.tipo === 'botao') {
    if (entrada.id === ID_VOLTAR) return podeVoltar ? { tipo: 'voltar' } : null;
    if (!entrada.id.startsWith(PREFIXO_OPCAO)) return null;

    const id = Number(entrada.id.slice(PREFIXO_OPCAO.length));
    return opcoes.some((o) => o.id === id) ? { tipo: 'no', id } : null;
  }

  if (entrada.tipo !== 'texto') return null;

  const t = normalizar(entrada.valor);
  if (podeVoltar && (t === '0' || t === 'voltar')) return { tipo: 'voltar' };

  // Até três dígitos: um número de menu tem no máximo dois na prática, e o teto
  // evita tratar um CNPJ digitado por engano como escolha de opção.
  if (/^[0-9]{1,3}$/.test(t)) {
    const porNumero = opcoes.find((o) => o.numero === Number(t));
    return porNumero ? { tipo: 'no', id: porNumero.id } : null;
  }

  const porRotulo = opcoes.find((o) => normalizar(o.rotulo) === t);
  return porRotulo ? { tipo: 'no', id: porRotulo.id } : null;
}

/**
 * O caminho da categoria até a raiz, para mostrar na confirmação.
 *
 * Reconstruído da árvore a cada leitura, e não guardado no `Chamado`: mudar o
 * pai de uma categoria no painel não pode reescrever chamado nenhum, e o rótulo
 * é editável. O que o chamado guarda é o id da folha - só isso.
 */
export async function caminhoDaCategoria(
  tx: Prisma.TransactionClient,
  id: number | null
): Promise<string | null> {
  if (id === null) return null;

  const partes: string[] = [];
  let atual: number | null = id;

  for (let i = 0; i < MAX_PROFUNDIDADE && atual !== null; i++) {
    const no: { rotulo: string; paiId: number | null } | null = await tx.categoria.findUnique({
      where: { id: atual },
      select: { rotulo: true, paiId: true },
    });
    // Categoria apagada entre a escolha e a leitura. Devolve o que já tem em vez
    // de estourar: a confirmação mostrar o caminho incompleto é melhor do que a
    // conversa morrer.
    if (no === null) break;

    partes.unshift(no.rotulo);
    atual = no.paiId;
  }

  return partes.length > 0 ? partes.join(SEPARADOR) : null;
}

/** O pai de um nó, para o "voltar" subir um nível. */
export async function paiDe(tx: Prisma.TransactionClient, id: number): Promise<number | null> {
  const no = await tx.categoria.findUnique({ where: { id }, select: { paiId: true } });
  return no?.paiId ?? null;
}
