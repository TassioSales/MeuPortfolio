import readline from 'node:readline';
import { config } from '../config';
import { caminhoDoBanco } from '../db/caminho';
import { prisma } from '../db/client';

/**
 * Simulador da Evolution, só para desenvolvimento.
 *
 * Monta o payload que a Evolution entrega (`messages.upsert`, envelope Baileys) e
 * posta em `/webhook/<segredo>` — ou seja, entra pelo mesmo caminho e com a mesma
 * autenticação que a Evolution de verdade usaria. Com isso dá para exercitar a
 * conversa completa sem instância conectada e sem número de WhatsApp.
 *
 * As respostas do bot são lidas da tabela `Mensagem`: como a linha de saída é
 * gravada DENTRO da transação, ela já existe quando o webhook devolve 200. Isso
 * dá uma conversa em um terminal só, e de quebra mostra o estado do outbox
 * (entregue ou pendente).
 *
 * Não faz parte do build de produção (ver `exclude` no tsconfig.json).
 */

// O segredo vai no CAMINHO, como a Evolution será configurada para chamar.
const ALVO = process.env.ALVO ?? `http://127.0.0.1:${config.port}/webhook/${config.webhookSegredo}`;
const TELEFONE_PADRAO = process.env.TELEFONE ?? '5511999990000';

let seq = 0;
function idMensagem(): string {
  seq += 1;
  return `SIM${Date.now().toString(36)}${seq}`;
}

const jid = (telefone: string) => `${telefone}@s.whatsapp.net`;

// --- payloads ------------------------------------------------------------

/**
 * O envelope da Evolution: um evento, uma instância, UMA mensagem em `data`.
 *
 * A Meta agrupava (entry[] -> changes[] -> messages[]) e um webhook podia trazer
 * dezenas. Aqui `data` é objeto. O bot aceita lista também, e o cenário de lote
 * abaixo exercita esse caminho.
 */
const envelope = (dados: unknown) => ({
  event: 'messages.upsert',
  instance: config.evolutionInstancia,
  data: dados,
});

const msgTexto = (de: string, texto: string, id = idMensagem()) => ({
  key: { remoteJid: jid(de), fromMe: false, id },
  pushName: 'Simulador',
  message: { conversation: texto },
  messageType: 'conversation',
  messageTimestamp: Math.floor(Date.now() / 1000),
});

/**
 * Resposta a botão — de um menu ANTIGO, enviado antes da migração.
 *
 * O bot não manda mais botão nenhum, mas ainda lê a resposta: é o que impede uma
 * conversa que estava no meio da virada de ficar sem resposta.
 */
const msgBotao = (de: string, botaoId: string, id = idMensagem()) => ({
  key: { remoteJid: jid(de), fromMe: false, id },
  pushName: 'Simulador',
  message: {
    buttonsResponseMessage: { selectedButtonId: botaoId, selectedDisplayText: botaoId },
  },
  messageType: 'buttonsResponseMessage',
  messageTimestamp: Math.floor(Date.now() / 1000),
});

/** `tipo` é o nome do Baileys: `imageMessage`, `audioMessage`... */
const msgMidia = (de: string, tipo: string, id = idMensagem()) => ({
  key: { remoteJid: jid(de), fromMe: false, id },
  pushName: 'Simulador',
  message: { [tipo]: { mimetype: 'application/octet-stream', fileLength: '1234' } },
  messageType: tipo,
  messageTimestamp: Math.floor(Date.now() / 1000),
});

/** A própria mensagem do bot voltando como evento. O bot tem de IGNORAR. */
const msgDoBot = (para: string, texto: string, id = idMensagem()) => ({
  key: { remoteJid: jid(para), fromMe: true, id },
  message: { conversation: texto },
  messageType: 'conversation',
  messageTimestamp: Math.floor(Date.now() / 1000),
});

// --- envio ---------------------------------------------------------------

async function postar(payload: unknown, alvoForcado?: string): Promise<number> {
  const corpo = JSON.stringify(payload);

  try {
    const res = await fetch(alvoForcado ?? ALVO, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: corpo,
    });
    return res.status;
  } catch (err) {
    console.error(
      `\nNão consegui falar com ${ALVO}. O servidor está rodando (npm run dev)?\n` +
        `  ${err instanceof Error ? err.message : String(err)}\n`
    );
    process.exitCode = 1;
    return 0;
  }
}

// --- diagnóstico de banco ------------------------------------------------

/**
 * Traduz falha de acesso ao banco para instrução acionável.
 *
 * Sem isso, um banco sem tabelas derrubava o simulador com um despejo de erro do
 * Prisma, que não diz o que fazer.
 *
 * A lista encurtou junto com a troca do Postgres pelo SQLite, e o motivo é o
 * próprio ponto: sem servidor, não existe senha errada, host errado, porta
 * fechada nem "o banco não existe" - o arquivo é criado quando falta. O que
 * sobra é sistema de arquivos e schema.
 */
function explicarErroDeBanco(err: unknown): string {
  const msg = err instanceof Error ? err.message : String(err);
  const codigo = (err as { errorCode?: unknown })?.errorCode;
  const url = process.env.DATABASE_URL ?? '';

  if (url === '') return 'DATABASE_URL não está definida. Copie o .env.example para .env.';

  // A mensagem completa desta já explica o que fazer (ver src/db/caminho.ts);
  // reescrevê-la aqui só a encurtaria.
  if (/aponta para um servidor/.test(msg)) return msg;

  if (/no such table/i.test(msg) || codigo === 'P2021') {
    return 'o arquivo do banco existe mas está sem as tabelas. Rode:  npm run prisma:deploy';
  }

  if (/unable to open database file/i.test(msg)) {
    return (
      `não consegui abrir o arquivo do banco (${caminhoDoBanco(url)}).\n` +
      '  Confira se o diretório existe e se o usuário atual pode escrever nele.'
    );
  }

  if (/SQLITE_READONLY/i.test(msg)) {
    return (
      `o arquivo do banco está somente-leitura (${caminhoDoBanco(url)}).\n` +
      '  Confira a permissão do arquivo e do diretório.'
    );
  }

  if (/SQLITE_BUSY/i.test(msg) || codigo === 'P2034') {
    return (
      'outro processo está com o lock de escrita do banco.\n' +
      '  SQLite aceita um escritor por vez: feche o outro servidor, o `sqlite3` ou\n' +
      '  o `npm run retencao` que esteja rodando.'
    );
  }

  if (/SQLITE_CORRUPT|file is not a database/i.test(msg)) {
    return (
      `o arquivo em ${caminhoDoBanco(url)} não é um banco SQLite válido.\n` +
      '  Se ele veio de um dump de Postgres, não serve: ver docs/WA Banco de dados.md.'
    );
  }

  return msg;
}

/** Confere o banco antes de começar, para falhar com instrução em vez de stack. */
async function bancoOk(): Promise<boolean> {
  try {
    await prisma.$queryRaw`SELECT 1`;
    return true;
  } catch (err) {
    console.error(`\nNão consegui falar com o banco:\n  ${explicarErroDeBanco(err)}\n`);
    return false;
  }
}

/** Idem para o servidor: uma checagem no /health em vez de N erros de conexão. */
async function servidorOk(): Promise<boolean> {
  // ALVO termina em /webhook/<segredo>; o /health mora na raiz.
  const base = ALVO.replace(/\/webhook(\/.*)?$/, '');
  try {
    const res = await fetch(`${base}/health`, { signal: AbortSignal.timeout(3_000) });
    if (res.ok) return true;
    console.error(`\nO servidor respondeu ${res.status} em ${base}/health.\n`);
  } catch {
    console.error(`\nO servidor não respondeu em ${base}/health.\n  Suba com:  npm run dev\n`);
  }
  return false;
}

// --- leitura das respostas ----------------------------------------------

async function ultimoIdDeMensagem(): Promise<number> {
  const m = await prisma.mensagem.findFirst({ orderBy: { id: 'desc' }, select: { id: true } });
  return m?.id ?? 0;
}

function renderizarSaida(m: { texto: string; enviadaEm: Date | null; payload: unknown }): string {
  const situacao = m.enviadaEm ? 'entregue' : 'PENDENTE no outbox';
  const payload = m.payload as any;
  const botoes = payload?.interactive?.action?.buttons;

  const linhas = [`bot [${situacao}]:`];
  for (const l of m.texto.split('\n')) linhas.push(`  ${l}`);
  if (Array.isArray(botoes)) {
    linhas.push(`  ${botoes.map((b: any) => `[ ${b.reply?.title} ]`).join(' ')}`);
    linhas.push(
      `  (responda com: /botao ${botoes.map((b: any) => b.reply?.id).join(' | /botao ')})`
    );
  }
  return linhas.join('\n');
}

async function mostrarRespostas(telefone: string, depoisDoId: number): Promise<void> {
  const saidas = await prisma.mensagem.findMany({
    where: { telefone, remetente: 'sistema', id: { gt: depoisDoId } },
    orderBy: { id: 'asc' },
    select: { texto: true, enviadaEm: true, payload: true },
  });

  if (saidas.length === 0) {
    console.log(
      'bot: (nenhuma resposta — descartada pelo limite por telefone, ou entrega repetida)'
    );
    return;
  }
  for (const s of saidas) console.log(renderizarSaida(s as any));
}

/** Manda uma mensagem e imprime o que o bot respondeu. */
async function trocar(telefone: string, mensagem: unknown): Promise<void> {
  const antes = await ultimoIdDeMensagem();
  const status = await postar(envelope([mensagem]));
  if (status !== 200) {
    console.log(`webhook respondeu ${status}`);
    return;
  }
  await mostrarRespostas(telefone, antes);
}

async function mostrarEstado(telefone: string): Promise<void> {
  const sessao = await prisma.sessaoConversa.findUnique({ where: { telefone } });
  const chamados = await prisma.chamado.findMany({
    where: { telefone },
    orderBy: { id: 'desc' },
    take: 3,
  });
  const pendentes = await prisma.mensagem.count({
    where: { telefone, remetente: 'sistema', enviadaEm: null },
  });

  console.log('\n--- estado ------------------------------------------');
  console.log(
    sessao
      ? `sessão: etapa=${sessao.etapa} editando=${sessao.editando}\n` +
          `        nome=${JSON.stringify(sessao.nome)} resumo=${JSON.stringify(sessao.resumo)}\n` +
          `        descricao=${JSON.stringify(sessao.descricao)}`
      : 'sessão: (nenhuma)'
  );
  for (const c of chamados) {
    console.log(`chamado #${c.id}: ${c.situacao} — ${c.resumo}`);
  }
  console.log(`saídas pendentes no outbox: ${pendentes}`);
  console.log('-----------------------------------------------------\n');
}

// --- modo conversa -------------------------------------------------------

const AJUDA_CHAT = `
Digite uma mensagem e pressione Enter. Comandos:
  /botao <id>     clica um botão (ex: /botao confirmar, /botao editar_descricao)
  /audio          manda um áudio (formato não suportado pelo bot)
  /imagem         manda uma imagem
  /estado         mostra sessão, chamados e pendências do outbox
  /repetir        reenvia a última mensagem com o MESMO wamid (entrega duplicada)
  /ajuda          esta lista
  /sair           encerra
`;

async function conversar(telefone: string): Promise<void> {
  console.log(`Conversando como ${telefone} contra ${ALVO}`);
  console.log(AJUDA_CHAT);

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  let ultimaMensagem: any = null;

  process.stdout.write(`${telefone}> `);
  for await (const linha of rl) {
    const entrada = linha.trim();

    if (entrada === '') {
      process.stdout.write(`${telefone}> `);
      continue;
    }
    if (entrada === '/sair') break;

    // Um comando que falha (banco fora, servidor caído) não pode encerrar a
    // conversa: você corrige o problema em outra janela e continua daqui.
    try {
      if (entrada === '/ajuda') {
        console.log(AJUDA_CHAT);
      } else if (entrada === '/estado') {
        await mostrarEstado(telefone);
      } else if (entrada === '/repetir') {
        if (!ultimaMensagem) console.log('(nada para repetir ainda)');
        else await trocar(telefone, ultimaMensagem); // mesmo wamid de propósito
      } else if (entrada.startsWith('/botao ')) {
        ultimaMensagem = msgBotao(telefone, entrada.slice('/botao '.length).trim());
        await trocar(telefone, ultimaMensagem);
      } else if (entrada === '/audio' || entrada === '/imagem') {
        ultimaMensagem = msgMidia(telefone, entrada === '/audio' ? 'audio' : 'image');
        await trocar(telefone, ultimaMensagem);
      } else if (entrada.startsWith('/')) {
        console.log(`comando desconhecido: ${entrada}`);
      } else {
        ultimaMensagem = msgTexto(telefone, entrada);
        await trocar(telefone, ultimaMensagem);
      }
    } catch (err) {
      console.error(`erro: ${explicarErroDeBanco(err)}`);
    }

    process.stdout.write(`${telefone}> `);
  }

  rl.close();
}

// --- cenários prontos ----------------------------------------------------

async function cenarioLote(telefone: string): Promise<void> {
  console.log('Enviando 3 mensagens de 3 telefones diferentes em UM webhook...');
  const base = telefone.slice(0, -2);
  const antes = await ultimoIdDeMensagem();

  const status = await postar(
    envelope([
      msgTexto(`${base}01`, 'Primeira'),
      msgTexto(`${base}02`, 'Segunda'),
      msgTexto(`${base}03`, 'Terceira'),
    ])
  );

  console.log(`webhook respondeu ${status}`);
  const criadas = await prisma.mensagem.count({ where: { id: { gt: antes } } });
  console.log(`linhas criadas em Mensagem: ${criadas} (esperado 6: 3 entradas + 3 respostas)`);
}

async function cenarioDuplicada(telefone: string): Promise<void> {
  const msg = msgTexto(telefone, 'Mensagem que vai ser entregue duas vezes');
  console.log('Primeira entrega:');
  await trocar(telefone, msg);
  console.log('\nSegunda entrega (mesmo wamid) — não deve avançar o fluxo nem responder de novo:');
  await trocar(telefone, msg);
}

async function cenarioSegredo(): Promise<void> {
  const corpo = envelope([msgTexto(TELEFONE_PADRAO, 'deveria ser recusada')]);
  const raiz = ALVO.replace(/\/webhook(\/.*)?$/, '');

  // 404, e não 401, de propósito: quem erra o segredo não fica sabendo que
  // existe um /webhook ali. Ver o notFoundHandler em src/app.ts.
  console.log(`sem segredo    -> ${await postar(corpo, `${raiz}/webhook`)}   (esperado 404)`);
  console.log(
    `segredo errado -> ${await postar(corpo, `${raiz}/webhook/nao-e-esse`)}   (esperado 404)`
  );
  console.log(`segredo certo  -> ${await postar(corpo)}   (esperado 200)`);
}

const USO = `
Simulador da Evolution — exercita o /webhook sem instância configurada.

  npm run dev:simular                          conversa interativa
  npm run dev:simular -- chat 5511999990000    conversa com outro telefone
  npm run dev:simular -- texto "Meu problema"  manda um texto e sai
  npm run dev:simular -- botao confirmar       clica um botão e sai
  npm run dev:simular -- audio                 manda áudio (formato não suportado)
  npm run dev:simular -- lote                  3 mensagens em um webhook só
  npm run dev:simular -- duplicada             mesma mensagem duas vezes (idempotência)
  npm run dev:simular -- segredo               confere que segredo errado é recusado
  npm run dev:simular -- estado                mostra sessão, chamados e outbox

Variáveis: ALVO (padrão ${ALVO}), TELEFONE (padrão ${TELEFONE_PADRAO})
`;

async function main(): Promise<void> {
  const [comando = 'chat', ...resto] = process.argv.slice(2);

  // Cada comando depende de coisas diferentes; checar só o necessário evita
  // exigir banco para conferir assinatura, ou servidor para inspecionar o
  // banco. E uma checagem no começo vale mais que N erros de conexão no meio.
  const soBanco = new Set(['estado']);
  const soServidor = new Set(['segredo']);

  if (!soServidor.has(comando) && !(await bancoOk())) {
    process.exitCode = 1;
    return;
  }
  if (!soBanco.has(comando) && !(await servidorOk())) {
    process.exitCode = 1;
    return;
  }

  switch (comando) {
    case 'chat':
      await conversar(resto[0] ?? TELEFONE_PADRAO);
      break;
    case 'texto':
      await trocar(TELEFONE_PADRAO, msgTexto(TELEFONE_PADRAO, resto.join(' ') || 'oi'));
      break;
    case 'botao':
      await trocar(TELEFONE_PADRAO, msgBotao(TELEFONE_PADRAO, resto[0] ?? 'confirmar'));
      break;
    case 'audio':
    case 'imagem':
      await trocar(
        TELEFONE_PADRAO,
        msgMidia(TELEFONE_PADRAO, comando === 'audio' ? 'audio' : 'image')
      );
      break;
    case 'lote':
      await cenarioLote(TELEFONE_PADRAO);
      break;
    case 'duplicada':
      await cenarioDuplicada(TELEFONE_PADRAO);
      break;
    case 'segredo':
      await cenarioSegredo();
      break;
    case 'estado':
      await mostrarEstado(resto[0] ?? TELEFONE_PADRAO);
      break;
    default:
      console.log(USO);
      process.exitCode = 1;
  }
}

main()
  .catch((err) => {
    console.error('Falha no simulador:', err instanceof Error ? err.message : err);
    process.exitCode = 1;
  })
  .finally(() => prisma.$disconnect());
