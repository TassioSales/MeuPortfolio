import { config } from '../config';
import { Entrada, processarMensagem } from '../conversation/handler';
import { erroSeguro, log } from '../log';
import { OpcoesEnvio } from './client';
import { ehTelefoneValido } from './telefone';
import { devolverMensagem, permitirMensagem } from './throttle';

/**
 * Formato real do payload da Evolution API v2:
 *
 *   {
 *     event: 'messages.upsert',
 *     instance: 'suporte',
 *     data: {
 *       key: { remoteJid: '5511...@s.whatsapp.net', fromMe: false, id: '3EB0...' },
 *       pushName: 'Fulano',
 *       message: { conversation: 'oi' },
 *       messageType: 'conversation'
 *     }
 *   }
 *
 * Três diferenças estruturais em relação ao que a Meta mandava:
 *
 * 1. NÃO HÁ AGRUPAMENTO. A Meta entregava entry[] -> changes[] -> messages[], e
 *    um webhook podia trazer dezenas de mensagens. Aqui é uma mensagem por
 *    requisição — `data` é objeto, não lista. Ainda assim o código aceita lista,
 *    porque algumas configurações de fila entregam em lote.
 * 2. O REMETENTE VEM COMO JID, não como número puro: `5511...@s.whatsapp.net`.
 * 3. O TIPO ESTÁ NA CHAVE DE `message`, não num campo `type`. Uma mensagem de
 *    imagem é `{ imageMessage: {...} }`, e não `{ type: 'image' }`.
 */

function comoArray(valor: unknown): any[] {
  if (Array.isArray(valor)) return valor;
  return valor === null || valor === undefined ? [] : [valor];
}

/**
 * Tipos que o usuário consegue enviar mas o bot ainda não lê.
 *
 * As chaves são os nomes que o Baileys dá a cada tipo de mensagem — é assim que
 * eles chegam, e não como `image`/`audio` da Meta.
 */
const FORMATOS_CONHECIDOS: Record<string, string> = {
  imageMessage: 'imagem',
  audioMessage: 'áudio',
  videoMessage: 'vídeo',
  documentMessage: 'documento',
  documentWithCaptionMessage: 'documento',
  stickerMessage: 'figurinha',
  locationMessage: 'localização',
  liveLocationMessage: 'localização',
  contactMessage: 'contato',
  contactsArrayMessage: 'contato',
  reactionMessage: 'reação',
  pollCreationMessage: 'enquete',
};

/**
 * O número, a partir do JID.
 *
 * `5511999999999@s.whatsapp.net` -> `5511999999999`.
 *
 * Grupo (`@g.us`) e transmissão (`@broadcast`) são recusados aqui, e não mais
 * adiante: o bot é uma conversa de um para um, e uma sessão indexada pelo id de
 * um grupo misturaria as respostas de todo mundo no mesmo formulário.
 */
export function telefoneDoJid(jid: unknown): string | null {
  if (typeof jid !== 'string' || jid === '') return null;
  if (!jid.endsWith('@s.whatsapp.net')) return null;

  const numero = jid.slice(0, -'@s.whatsapp.net'.length);
  return ehTelefoneValido(numero) ? numero : null;
}

function extrairEntrada(dados: any): Entrada | null {
  const message = dados?.message;
  if (!message || typeof message !== 'object') return null;

  // Texto simples e texto com contexto (resposta a outra mensagem, link com
  // prévia) chegam em chaves diferentes e valem o mesmo para nós.
  const texto =
    typeof message.conversation === 'string'
      ? message.conversation
      : typeof message.extendedTextMessage?.text === 'string'
        ? message.extendedTextMessage.text
        : null;

  if (texto !== null) {
    if (texto === '') return null;
    return { tipo: 'texto', valor: texto.slice(0, config.maxCaracteresMensagem) };
  }

  // Resposta a botão ou a lista ainda pode chegar de um menu antigo, enviado
  // antes da migração. O id vem no mesmo lugar em que nós o colocamos, então
  // continua valendo como clique — é o que impede uma conversa em andamento na
  // virada de ficar sem resposta.
  const idInterativo =
    message.buttonsResponseMessage?.selectedButtonId ??
    message.listResponseMessage?.singleSelectReply?.selectedRowId;
  if (typeof idInterativo === 'string' && idInterativo !== '') {
    return { tipo: 'botao', id: idInterativo.slice(0, config.maxCaracteresMensagem) };
  }

  // O tipo é a primeira chave de `message` que reconhecemos. `messageType` do
  // nível de cima diz quase sempre a mesma coisa, mas nem sempre: em mensagem
  // encaminhada ou citada ele vem como `extendedTextMessage` enquanto o conteúdo
  // real é outro. A chave é a fonte mais confiável.
  for (const chave of Object.keys(message)) {
    if (chave in FORMATOS_CONHECIDOS) return { tipo: 'midia', formato: FORMATOS_CONHECIDOS[chave] };
  }

  const tipoBruto = typeof dados?.messageType === 'string' ? dados.messageType : '';
  if (tipoBruto !== '') {
    return { tipo: 'midia', formato: FORMATOS_CONHECIDOS[tipoBruto] ?? tipoBruto };
  }

  return null;
}

/** Retorna true quando a mensagem foi de fato processada. */
async function processarUma(dados: any, opts: OpcoesEnvio): Promise<boolean> {
  // A PRÓPRIA MENSAGEM DO BOT VOLTA COMO EVENTO.
  //
  // A Evolution notifica tudo o que passa pela instância, inclusive o que nós
  // acabamos de enviar. Sem esta linha, cada resposta do bot seria lida como
  // entrada nova, avançaria a etapa sozinha e geraria outra resposta — um laço
  // que só para quando a sessão expira. A Meta nunca fez isso; é a armadilha
  // número um de quem migra.
  if (dados?.key?.fromMe === true) return false;

  const telefone = telefoneDoJid(dados?.key?.remoteJid);
  if (telefone === null) return false;

  const entrada = extrairEntrada(dados);
  if (!entrada) return false;

  // Descarta em silêncio: responder "você está enviando rápido demais" a quem
  // faz flood só gera mais tráfego de saída.
  if (!(await permitirMensagem(telefone))) return false;

  // O id da mensagem no WhatsApp. Continua sendo a chave de idempotência, agora
  // vindo de `key.id` em vez do `wamid` da Meta.
  const idMensagem = typeof dados?.key?.id === 'string' ? dados.key.id : undefined;

  // Reentrega: a mensagem é descartada, então a cota consumida logo acima volta.
  // Sem isso, uma rajada de reentregas comia o limite de um usuário legítimo com
  // mensagens que nem chegaram a ser processadas.
  if ((await processarMensagem(telefone, entrada, idMensagem, opts)) === 'duplicata') {
    await devolverMensagem(telefone);
    return false;
  }

  return true;
}

export type ResultadoRecebimento = {
  processadas: number;
  /** Telefones cuja mensagem estourou - são os únicos que merecem um aviso. */
  falharam: string[];
};

/**
 * Só os eventos que trazem mensagem de entrada.
 *
 * A Evolution manda muito mais que isso no mesmo webhook quando configurada sem
 * filtro: atualização de conexão, presença, recibo de leitura, chamada. Todos
 * com `data` de formato diferente. Filtrar pelo evento é o que evita tentar ler
 * um recibo como se fosse conversa.
 */
const EVENTO_MENSAGEM = 'messages.upsert';

function ehEventoDeMensagem(payload: any): boolean {
  const evento = payload?.event;
  if (typeof evento !== 'string') return false;
  // A Evolution usa ponto em alguns lugares e underline em outros, dependendo
  // da versão e de como o webhook foi cadastrado.
  return evento.replace(/_/g, '.').toLowerCase() === EVENTO_MENSAGEM;
}

/** Extrai os remetentes do payload sem depender do resto do pipeline. */
export function telefonesDoPayload(payload: any): string[] {
  const encontrados = new Set<string>();
  if (!ehEventoDeMensagem(payload)) return [];

  for (const dados of comoArray(payload?.data)) {
    if (dados?.key?.fromMe === true) continue;
    const telefone = telefoneDoJid(dados?.key?.remoteJid);
    if (telefone !== null) encontrados.add(telefone);
  }
  return [...encontrados];
}

export async function handleIncomingMessage(
  payload: any,
  opts: OpcoesEnvio = {}
): Promise<ResultadoRecebimento> {
  let processadas = 0;
  const falharam = new Set<string>();

  if (!ehEventoDeMensagem(payload)) return { processadas: 0, falharam: [] };

  for (const dados of comoArray(payload?.data)) {
    try {
      // Sequencial de propósito: mensagens do mesmo usuário precisam ser
      // processadas na ordem em que chegaram.
      if (await processarUma(dados, opts)) processadas++;
    } catch (err) {
      // Uma mensagem que estoura NÃO pode levar as outras do lote embora.
      log.error(erroSeguro(err), 'Falha ao processar mensagem recebida');
      const telefone = telefoneDoJid(dados?.key?.remoteJid);
      if (telefone !== null) falharam.add(telefone);
    }
  }

  return { processadas, falharam: [...falharam] };
}
