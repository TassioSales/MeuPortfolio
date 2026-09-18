import crypto from 'node:crypto';
import { config } from '../config';
import { caminhoDoBanco } from '../db/caminho';
import { prisma } from '../db/client';
import { varrerPendentes } from '../whatsapp/outbox';
import { corpoTexto } from '../whatsapp/client';
import { Prisma } from '../generated/prisma/client';

/**
 * Confere, contra o ARQUIVO SQLite de verdade, as garantias que os dublês em
 * memória não conseguem provar.
 *
 * O README listava essas quatro como "vale um teste manual antes de ir para
 * produção". Este script é esse teste manual, automatizado:
 *
 *   0. como a data é gravada, e que ela é comparável com o `now()` do banco em
 *      SQL crua - o lugar que já quebrou o varredor da outbox duas vezes;
 *   1. duas mensagens simultâneas do mesmo telefone não se atropelando;
 *   2. índice único do `whatsappMessageId` derrubando entrega repetida;
 *   3. dois PATCH simultâneos no mesmo chamado gerando UMA notificação;
 *   4. a SQL de reserva da outbox, com a espera crescente entre tentativas;
 *   5. a recuperação de uma pendente depois de a Evolution voltar;
 *   6. o ON DELETE CASCADE do histórico de situação - sem ele a retenção (LGPD)
 *      passa a falhar na FK ao apagar chamados antigos;
 *   7. a árvore de assuntos - `_count`, `orderBy` em lista, `paiId: null` e o
 *      ON DELETE SET NULL que faz apagar categoria não apagar chamado.
 *
 * A lista acima e os números impressos no console são a mesma coisa dita duas
 * vezes; o item 5 faltava aqui e as duas metades ficaram fora de passo até esta
 * revisão.
 *
 * Nos itens 1 e 3 o que era um lock explícito do Postgres (`pg_advisory_xact_lock`
 * e `SELECT ... FOR UPDATE`) virou uma propriedade do SQLite: um escritor por
 * banco, e transações serializadas pelo mutex do adaptador. O que se verifica
 * aqui é o EFEITO observável, que não mudou - e é justamente por não ter mudado
 * que estas checagens continuam valendo a pena.
 *
 * Precisa do servidor rodando (`npm run dev`) e do banco migrado.
 * Não faz parte do build de produção (ver `exclude` no tsconfig.json).
 */

const ALVO = process.env.ALVO ?? `http://127.0.0.1:${config.port}`;
const EVOLUTION = config.evolutionUrl;

let falhas = 0;

function afirmar(condicao: boolean, descricao: string, detalhe = ''): void {
  console.log(`  ${condicao ? 'OK  ' : 'FALHOU'} ${descricao}${detalhe ? ` — ${detalhe}` : ''}`);
  if (!condicao) falhas += 1;
}

// --- utilidades ----------------------------------------------------------

/** Telefone novo por execução, para uma rodada nunca herdar estado da anterior. */
function telefoneNovo(sufixo: number): string {
  return `55119${String(Date.now()).slice(-7)}${sufixo}`;
}

const envelope = (mensagens: unknown[]) => ({
  event: 'messages.upsert',
  instance: config.evolutionInstancia,
  // Lista, e não objeto: a Evolution manda uma mensagem por requisição, mas o
  // bot aceita lote — e é o lote que estas checagens exercitam.
  data: mensagens,
});

const msgTexto = (de: string, texto: string, id: string) => ({
  key: { remoteJid: `${de}@s.whatsapp.net`, fromMe: false, id },
  message: { conversation: texto },
  messageType: 'conversation',
});

async function postarWebhook(payload: unknown): Promise<number> {
  // O segredo vai no caminho. Ver whatsapp/signature.ts.
  const res = await fetch(`${ALVO}/webhook/${config.webhookSegredo}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return res.status;
}

/** Liga/desliga a falha simulada na Evolution de mentira. Silencioso se não for ela. */
async function controlarEvolution(status: number, vezes = 1): Promise<boolean> {
  if (!/127\.0\.0\.1|localhost/.test(EVOLUTION)) return false;
  try {
    const res = await fetch(`${EVOLUTION}/_controle`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ status, vezes }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

async function limpar(telefone: string): Promise<void> {
  await prisma.mensagem.deleteMany({ where: { telefone } });
  await prisma.sessaoConversa.deleteMany({ where: { telefone } });
  await prisma.chamado.deleteMany({ where: { telefone } });
}

/**
 * Abre a conversa e para na etapa `nome`.
 *
 * Já foi uma mensagem só; hoje são duas, e a diferença é o menu de assuntos.
 * O primeiro contato devolve a saudação — a mensagem que abre a conversa não é
 * resposta a pergunta nenhuma (ver `decidir` em conversation/handler.ts) —, e
 * essa saudação agora É o menu numerado. As checagens daqui querem observar
 * respostas que AVANÇAM o estado a partir de `nome`, então gastam a saudação e
 * a escolha do assunto aqui, em vez de contá-las como etapa.
 *
 * A escolha é sempre a opção 1, num laço, porque a árvore pode ter
 * sub-assuntos: desce pela primeira opção até a etapa deixar de ser `categoria`.
 * Sem nenhuma categoria ativa cadastrada, a etapa já sai de `categoria` na
 * própria saudação e o laço não roda nenhuma volta.
 */
async function abrirConversa(telefone: string): Promise<void> {
  await postarWebhook(envelope([msgTexto(telefone, 'oi', `wamid.OI-${telefone}-${Date.now()}`)]));

  for (let i = 0; i < 5; i++) {
    const sessao = await prisma.sessaoConversa.findUnique({ where: { telefone } });
    if (sessao?.etapa !== 'categoria') return;

    await postarWebhook(
      envelope([msgTexto(telefone, '1', `wamid.CAT-${telefone}-${i}-${Date.now()}`)])
    );
  }
}

// --- 0. gravação e comparação de data ------------------------------------

async function testarDataComparavel(): Promise<void> {
  console.log('\n0) data: gravada em UTC e comparável com o now() do banco em SQL crua');
  const tel = telefoneNovo(0);
  await limpar(tel);

  const agora = new Date();
  const linha = await prisma.mensagem.create({
    data: { telefone: tel, remetente: 'sistema', texto: 'data', timestamp: agora },
  });

  // Primeiro o FORMATO, porque é dele que todo o resto depende. O Prisma grava
  // data no SQLite como TEXTO, e a SQL de reserva da outbox só funciona se esse
  // texto trouxer o deslocamento explícito - é o que `unixepoch()` usa para
  // saber que aquilo é UTC. Se um dia o adaptador passar a gravar em outro
  // formato (ele tem uma opção `timestampFormat`), esta é a checagem que acusa.
  const [cru] = await prisma.$queryRaw<{ texto: string; tipo: string }[]>`
    SELECT CAST("timestamp" AS TEXT) AS texto, typeof("timestamp") AS tipo
      FROM "Mensagem" WHERE id = ${linha.id}`;
  afirmar(cru.tipo === 'text', 'a coluna de data guarda TEXTO', `typeof=${cru.tipo}`);
  afirmar(
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}\+00:00$/.test(cru.texto),
    'o texto é ISO-8601 com offset +00:00 (sempre UTC)',
    cru.texto
  );

  // E agora a prova que importa: uma data escrita AGORA não pode aparecer no
  // futuro para o `now()` do banco. Este é o ponto exato que já derrubou o
  // varredor da outbox duas vezes - antes por fuso de sessão no Postgres, e
  // aqui pelo risco de comparar as duas pontas como TEXTO (`datetime('now')`
  // devolve `2026-08-27 19:57:00`, com espaço e sem offset, e o `T` da coluna é
  // maior que o espaço em comparação de string). Round-trip pelo Prisma NÃO
  // mostra nada disso: ele converte na leitura e a data parece certa.
  const [comparado] = await prisma.$queryRaw<{ futuro: number; distanciaSeg: number }[]>`
    SELECT unixepoch("timestamp", 'subsec') > unixepoch('now', 'subsec')            AS futuro,
           abs(unixepoch('now', 'subsec') - unixepoch("timestamp", 'subsec'))       AS "distanciaSeg"
      FROM "Mensagem" WHERE id = ${linha.id}`;

  afirmar(Number(comparado.futuro) === 0, 'uma data recém-gravada não está no futuro para o now()');
  afirmar(
    Number(comparado.distanciaSeg) < 60,
    'a data gravada bate com o now() do banco (sem deslocamento de fuso)',
    `diferença=${Math.round(Number(comparado.distanciaSeg))}s`
  );

  await limpar(tel);
}

// --- 1. serialização por telefone ----------------------------------------

async function testarSerializacaoPorTelefone(): Promise<void> {
  console.log('\n1) serialização: duas mensagens simultâneas do mesmo telefone');
  const tel = telefoneNovo(1);
  await limpar(tel);
  await abrirConversa(tel);

  // Linha de base: a saudação já gravou uma entrada, e o que se mede aqui é o
  // efeito das duas mensagens simultâneas.
  const entradasAntes = await prisma.mensagem.count({
    where: { telefone: tel, remetente: 'usuario' },
  });

  const agora = Date.now();
  // Se as duas transações rodassem sobrepostas, as duas leriam etapa='nome' e
  // uma sobrescreveria o trabalho da outra. No Postgres o que impedia isso era
  // o `pg_advisory_xact_lock`; aqui é o mutex do adaptador (ver db/client.ts).
  // O que se observa é o mesmo: nenhuma mensagem se perde.
  const [a, b] = await Promise.all([
    postarWebhook(envelope([msgTexto(tel, 'Natan', `wamid.LOCK-A-${agora}`)])),
    postarWebhook(envelope([msgTexto(tel, 'Estoque fora do ar', `wamid.LOCK-B-${agora}`)])),
  ]);

  const sessao = await prisma.sessaoConversa.findUnique({ where: { telefone: tel } });
  const entradas =
    (await prisma.mensagem.count({ where: { telefone: tel, remetente: 'usuario' } })) -
    entradasAntes;

  afirmar(a === 200 && b === 200, 'as duas requisições responderam 200', `${a} e ${b}`);
  afirmar(entradas === 2, 'as duas entradas foram gravadas', `gravadas: ${entradas}`);
  afirmar(
    sessao?.etapa === 'descricao',
    'o fluxo avançou DUAS etapas (nenhuma mensagem se perdeu)',
    `etapa=${sessao?.etapa}`
  );
  afirmar(
    Boolean(sessao?.nome) && Boolean(sessao?.resumo),
    'nome e resumo foram preenchidos',
    `nome=${JSON.stringify(sessao?.nome)} resumo=${JSON.stringify(sessao?.resumo)}`
  );

  await limpar(tel);
}

// --- 2. índice único do wamid -------------------------------------------

async function testarWamidUnico(): Promise<void> {
  console.log('\n2) índice único: reentrega do mesmo id de mensagem');
  const tel = telefoneNovo(2);
  await limpar(tel);
  await abrirConversa(tel);

  const wamid = `wamid.DUP-${Date.now()}`;
  const payload = envelope([msgTexto(tel, 'Natan', wamid)]);

  await postarWebhook(payload);
  const etapaDepoisDa1a = (await prisma.sessaoConversa.findUnique({ where: { telefone: tel } }))
    ?.etapa;
  const saidasDepoisDa1a = await prisma.mensagem.count({
    where: { telefone: tel, remetente: 'sistema' },
  });
  const entradasDepoisDa1a = await prisma.mensagem.count({
    where: { telefone: tel, remetente: 'usuario' },
  });

  await postarWebhook(payload); // mesma mensagem, de novo

  const sessao = await prisma.sessaoConversa.findUnique({ where: { telefone: tel } });
  const entradas = await prisma.mensagem.count({ where: { telefone: tel, remetente: 'usuario' } });
  const saidas = await prisma.mensagem.count({ where: { telefone: tel, remetente: 'sistema' } });

  afirmar(
    entradas === entradasDepoisDa1a,
    'a entrada repetida NÃO foi gravada duas vezes',
    `entradas: ${entradas} (era ${entradasDepoisDa1a})`
  );
  afirmar(
    sessao?.etapa === etapaDepoisDa1a,
    'a etapa não avançou de novo',
    `${etapaDepoisDa1a} -> ${sessao?.etapa}`
  );
  afirmar(saidas === saidasDepoisDa1a, 'o bot não respondeu duas vezes', `saídas: ${saidas}`);

  await limpar(tel);
}

// --- 3. dois PATCH simultâneos no mesmo chamado --------------------------

async function testarPatchSimultaneo(): Promise<void> {
  console.log('\n3) dois PATCH simultâneos no mesmo chamado: uma notificação só');
  const tel = telefoneNovo(3);
  await limpar(tel);

  const chamado = await prisma.chamado.create({
    data: { nome: 'Teste', telefone: tel, resumo: 'r', descricao: 'd', situacao: 'aberto' },
  });

  const patch = () =>
    fetch(`${ALVO}/internal/chamados/${chamado.id}/situacao`, {
      method: 'PATCH',
      headers: {
        authorization: `Bearer ${config.internalApiToken}`,
        'content-type': 'application/json',
      },
      body: JSON.stringify({ situacao: 'resolvido', notificarUsuario: true }),
    }).then((r) => r.json() as Promise<{ anterior?: string; notificado?: boolean }>);

  // Se a leitura da situação anterior e a gravação da nova não estivessem na
  // MESMA transação, as duas leriam `aberto`, as duas considerariam que houve
  // mudança e as duas notificariam o usuário. No Postgres havia um
  // `SELECT ... FOR UPDATE` para travar a linha; no SQLite a transação basta,
  // porque duas nunca se sobrepõem.
  const [x, y] = await Promise.all([patch(), patch()]);
  const viramAberto = [x, y].filter((r) => r.anterior === 'aberto').length;
  const notificacoes = await prisma.mensagem.count({
    where: { telefone: tel, remetente: 'sistema' },
  });

  afirmar(
    viramAberto === 1,
    'só UM PATCH viu a situação anterior como "aberto"',
    `viram: ${viramAberto}`
  );
  afirmar(
    notificacoes === 1,
    'o usuário foi notificado UMA vez só',
    `notificações: ${notificacoes}`
  );

  await limpar(tel);
}

// --- 4. reserva da outbox com espera crescente --------------------------

async function testarReservaOutbox(): Promise<void> {
  console.log('\n4) reserva da outbox: uma instrução só + espera crescente');
  const tel = telefoneNovo(4);
  await limpar(tel);

  const agora = Date.now();
  const emSegundos = (s: number) => new Date(agora - s * 1000);
  const payload = corpoTexto(tel, 'oi') as Prisma.InputJsonValue;

  const criar = (
    rotulo: string,
    tentativas: number,
    ultimaSegundos: number | null,
    idadeSeg: number
  ) =>
    prisma.mensagem.create({
      data: {
        telefone: tel,
        remetente: 'sistema',
        texto: rotulo,
        payload,
        enviadaEm: null,
        tentativas,
        timestamp: emSegundos(idadeSeg),
        ultimaTentativaEm: ultimaSegundos === null ? null : emSegundos(ultimaSegundos),
      },
    });

  // A regra: coalesce(ultimaTentativaEm, timestamp) < now() - 30s * 2^tentativas
  const nuncaTentada = await criar('elegivel-nunca-tentada', 0, null, 120); // 30s exigidos: elegível
  const recemCriada = await criar('nova-demais', 0, null, 5); // 30s exigidos: NÃO
  const esperaCurta = await criar('espera-nao-venceu', 1, 40, 300); // 60s exigidos: NÃO
  const esperaVencida = await criar('espera-venceu', 1, 90, 300); // 60s exigidos: elegível
  const noTeto = await criar('esgotou-tentativas', config.enviosMaxTentativas, 3600, 7200); // NÃO

  // Falha simulada: mantém as linhas pendentes, então o que se observa é apenas
  // o efeito da RESERVA (tentativas +1 e ultimaTentativaEm marcado).
  const controlou = await controlarEvolution(503, 50);
  if (!controlou) console.log('     (aviso: Evolution de mentira não respondeu ao /_controle)');

  await varrerPendentes(50);
  await controlarEvolution(0);

  const reler = async (id: number) =>
    prisma.mensagem.findUniqueOrThrow({
      where: { id },
      select: { tentativas: true, ultimaTentativaEm: true },
    });

  const r1 = await reler(nuncaTentada.id);
  const r2 = await reler(recemCriada.id);
  const r3 = await reler(esperaCurta.id);
  const r4 = await reler(esperaVencida.id);
  const r5 = await reler(noTeto.id);

  afirmar(
    r1.tentativas === 1,
    'pendente antiga nunca tentada foi reservada',
    `tentativas=${r1.tentativas}`
  );
  afirmar(
    r2.tentativas === 0,
    'pendente com menos de 30s NÃO foi reservada',
    `tentativas=${r2.tentativas}`
  );
  afirmar(
    r3.tentativas === 1,
    'espera de 60s ainda não vencida: NÃO reservada',
    `tentativas=${r3.tentativas}`
  );
  afirmar(r4.tentativas === 2, 'espera de 60s vencida: reservada', `tentativas=${r4.tentativas}`);
  afirmar(
    r5.tentativas === config.enviosMaxTentativas,
    'no teto de tentativas: NÃO reservada',
    `tentativas=${r5.tentativas}`
  );
  afirmar(r1.ultimaTentativaEm !== null, 'a reserva marcou ultimaTentativaEm');

  await limpar(tel);
}

// --- 5. recuperação de ponta a ponta ------------------------------------

async function testarRecuperacaoOutbox(): Promise<void> {
  console.log('\n5) recuperação: Evolution fora -> pendente -> varredor entrega');
  const tel = telefoneNovo(5);
  await limpar(tel);

  // Sonda em modo normal: se não é a Evolution de mentira, nada aqui faz sentido.
  if (!(await controlarEvolution(0))) {
    console.log('     pulado: exige a Evolution de mentira (npm run dev:evolution)');
    return;
  }

  // A saudação do primeiro contato sai com a Evolution ainda de pé; o que precisa
  // ficar pendente é a resposta que avança o estado.
  await abrirConversa(tel);
  await controlarEvolution(503, 50);

  await postarWebhook(envelope([msgTexto(tel, 'Natan', `wamid.REC-${Date.now()}`)]));

  const pendente = await prisma.mensagem.findFirst({
    where: { telefone: tel, remetente: 'sistema' },
    orderBy: { id: 'desc' },
  });
  afirmar(pendente !== null, 'a resposta foi gravada na outbox mesmo com a Evolution fora');
  afirmar(
    pendente?.enviadaEm === null,
    'ficou pendente em vez de sumir',
    `tentativas=${pendente?.tentativas}`
  );

  const sessao = await prisma.sessaoConversa.findUnique({ where: { telefone: tel } });
  afirmar(
    sessao?.etapa === 'resumo',
    'o estado da conversa avançou de qualquer forma',
    `etapa=${sessao?.etapa}`
  );

  // Evolution de volta: força a espera a vencer e chama o varredor.
  await controlarEvolution(0);
  await prisma.mensagem.update({
    where: { id: pendente!.id },
    data: { ultimaTentativaEm: new Date(Date.now() - 10 * 60 * 1000) },
  });

  const entregues = await varrerPendentes(50);
  const final = await prisma.mensagem.findUniqueOrThrow({ where: { id: pendente!.id } });

  afirmar(entregues >= 1, 'o varredor entregou o pendente', `entregues=${entregues}`);
  afirmar(final.enviadaEm !== null, 'a linha foi marcada como enviada');

  await limpar(tel);
}

// --- 6. histórico de situação e o cascade dele --------------------------

async function testarHistoricoSituacao(): Promise<void> {
  console.log('\n6) histórico de situação: gravação e ON DELETE CASCADE');
  const tel = telefoneNovo(6);
  await limpar(tel);

  const chamado = await prisma.chamado.create({
    data: { nome: 'Teste', telefone: tel, resumo: 'r', descricao: 'd', situacao: 'aberto' },
  });

  const patch = (situacao: string, autor?: string) =>
    fetch(`${ALVO}/internal/chamados/${chamado.id}/situacao`, {
      method: 'PATCH',
      headers: {
        authorization: `Bearer ${config.internalApiToken}`,
        'content-type': 'application/json',
      },
      body: JSON.stringify({ situacao, ...(autor ? { autor } : {}) }),
    }).then((r) => r.status);

  await patch('em_andamento', 'Verificador');
  await patch('resolvido');
  await patch('resolvido'); // repetição: não é evento de atendimento

  const linhas = await prisma.mudancaSituacao.findMany({
    where: { chamadoId: chamado.id },
    orderBy: { criadoEm: 'asc' },
  });

  afirmar(linhas.length === 2, 'só as mudanças reais viraram linha', `linhas: ${linhas.length}`);
  afirmar(
    linhas[0]?.de === 'aberto' && linhas[0]?.para === 'em_andamento',
    'a primeira linha registra o de/para correto'
  );
  afirmar(linhas[0]?.autor === 'Verificador', 'o autor informado foi gravado');
  afirmar(linhas[1]?.autor === null, 'sem autor, a coluna fica nula');

  // A prova que dublê em memória não dá: o cascade é do banco. E no SQLite ele
  // depende de `PRAGMA foreign_keys` estar ligado NA CONEXÃO - se estiver
  // desligado, apagar o chamado não estoura erro nenhum, só deixa o histórico
  // órfão em silêncio. `prepararBanco` (src/db/client.ts) confere isso no boot;
  // esta checagem é a que prova o efeito.
  await prisma.chamado.delete({ where: { id: chamado.id } });
  const sobraram = await prisma.mudancaSituacao.count({ where: { chamadoId: chamado.id } });
  afirmar(sobraram === 0, 'apagar o chamado levou o histórico junto', `sobraram: ${sobraram}`);

  await limpar(tel);
}

// --- 6. árvore de assuntos e marcos de SLA -------------------------------

/**
 * O que o dublê em memória NÃO consegue provar sobre `Categoria` e o SLA:
 *
 *   - `_count` sobre uma relação — o painel usa para saber, antes de tentar, que
 *     excluir vai levar 409;
 *   - `orderBy` em LISTA (`[{ ordem }, { id }]`), o desempate de onde sai a
 *     numeração do menu do WhatsApp;
 *   - `paiId: null`, que em SQL é `IS NULL` e não `= NULL` — errado, o menu
 *     voltaria vazio e a conversa pularia a pergunta sem ninguém entender;
 *   - o índice único de `codigo` derrubando um código repetido de verdade;
 *   - `visivelNoWhatsapp: true` de fato filtrando. No SQLite não existe tipo
 *     booleano: a coluna é INTEGER e o filtro tem de virar `= 1`. O dublê
 *     compara `true === true` em JavaScript e passaria de qualquer jeito;
 *   - o `ON DELETE SET NULL` de Categoria -> Chamado. Este é o mais importante:
 *     é a razão de a API recusar o DELETE de uma categoria em uso, e o dublê
 *     não o imita.
 */
async function testarArvoreDeAssuntos(): Promise<void> {
  console.log('\n7) assuntos: _count, ordenação, paiId nulo, código único e SET NULL');

  const marca = Date.now();
  const raiz = await prisma.categoria.create({
    data: { codigo: `zz_raiz_${marca}`, nome: 'VERIFICAÇÃO', rotulo: 'VERIFICAÇÃO', ordem: 9998 },
  });
  const filha = await prisma.categoria.create({
    data: { codigo: `zz_filha_${marca}`, nome: 'FILHA', rotulo: 'FILHA', ordem: 1, paiId: raiz.id },
  });

  const tel = telefoneNovo(6);
  await limpar(tel);
  const chamado = await prisma.chamado.create({
    data: {
      nome: 'Teste',
      telefone: tel,
      resumo: 'r',
      descricao: 'd',
      situacao: 'aberto',
      categoriaId: raiz.id,
    },
  });

  const contagem = await prisma.categoria.findUnique({
    where: { id: raiz.id },
    select: { _count: { select: { chamados: true, filhas: true } } },
  });
  afirmar(
    contagem?._count.chamados === 1,
    '_count.chamados conta o chamado que aponta para ela',
    `chamados=${contagem?._count.chamados}`
  );
  afirmar(
    contagem?._count.filhas === 1,
    '_count.filhas conta o sub-assunto',
    `filhas=${contagem?._count.filhas}`
  );

  const raizes = await prisma.categoria.findMany({
    where: { paiId: null, ativa: true },
    orderBy: [{ ordem: 'asc' }, { id: 'asc' }],
    select: { id: true, ordem: true },
  });
  afirmar(
    raizes.some((c) => c.id === raiz.id),
    'o filtro paiId: null vira IS NULL e devolve a raiz'
  );
  afirmar(!raizes.some((c) => c.id === filha.id), 'a filha NÃO entra na lista de raízes');
  afirmar(
    raizes.every((c, i) => i === 0 || raizes[i - 1].ordem <= c.ordem),
    'orderBy [ordem, id] já devolve ordenado, sem sort do lado do Node'
  );

  // O assunto de uso interno, no banco de verdade. `visivelNoWhatsapp` nasce
  // `true` pelo default da coluna (é o que faz a migração não precisar de UPDATE
  // nas categorias que já existiam), e o filtro do menu tem de deixar a marcada
  // de fora sem deixar a outra.
  afirmar(
    raiz.visivelNoWhatsapp === true,
    'o default da coluna faz o assunto novo nascer visível no WhatsApp',
    `visivelNoWhatsapp=${raiz.visivelNoWhatsapp}`
  );

  const interna = await prisma.categoria.create({
    data: {
      codigo: `zz_interna_${marca}`,
      nome: 'SÓ TI',
      rotulo: 'SÓ TI',
      ordem: 9997,
      visivelNoWhatsapp: false,
    },
  });
  const oferecidas = await prisma.categoria.findMany({
    where: { paiId: null, ativa: true, visivelNoWhatsapp: true },
    select: { id: true },
  });
  afirmar(
    !oferecidas.some((c) => c.id === interna.id),
    'o assunto de uso interno fica fora da consulta que monta o menu'
  );
  afirmar(
    oferecidas.some((c) => c.id === raiz.id),
    'e o filtro não leva junto quem está visível'
  );
  await prisma.categoria.delete({ where: { id: interna.id } });

  let repetiu = false;
  try {
    await prisma.categoria.create({
      data: { codigo: `zz_raiz_${marca}`, nome: 'OUTRA', rotulo: 'OUTRA', ordem: 9999 },
    });
  } catch (err) {
    repetiu = err instanceof Prisma.PrismaClientKnownRequestError && err.code === 'P2002';
  }
  afirmar(repetiu, 'o índice único do código derruba a segunda inserção com P2002');

  const agora = new Date();
  await prisma.chamado.update({
    where: { id: chamado.id },
    data: { primeiroAtendimentoEm: agora, resolvidoEm: agora },
  });
  const marcos = await prisma.chamado.findUnique({
    where: { id: chamado.id },
    select: { primeiroAtendimentoEm: true, resolvidoEm: true },
  });
  afirmar(
    marcos?.primeiroAtendimentoEm instanceof Date && marcos?.resolvidoEm instanceof Date,
    'os marcos de SLA voltam do SQLite como Date, e não como texto',
    `tipo=${typeof marcos?.resolvidoEm}`
  );

  // Apaga POR FORA da API de propósito: a rota recusaria (409), e o que se
  // observa aqui é o que o banco faria se ela não recusasse.
  await prisma.categoria.delete({ where: { id: filha.id } });
  await prisma.categoria.delete({ where: { id: raiz.id } });

  const orfao = await prisma.chamado.findUnique({
    where: { id: chamado.id },
    select: { categoriaId: true },
  });
  afirmar(
    orfao !== null && orfao.categoriaId === null,
    'ON DELETE SET NULL zera a categoria do chamado em vez de apagar o chamado',
    `categoriaId=${orfao?.categoriaId}`
  );

  await limpar(tel);
}

// --- main ----------------------------------------------------------------

async function main(): Promise<void> {
  console.log('Verificando garantias que só o arquivo SQLite de verdade prova.');
  console.log(`  servidor: ${ALVO}`);
  console.log(`  evolution: ${EVOLUTION}`);
  console.log(`  banco:    ${caminhoDoBanco(config.databaseUrl)}`);

  try {
    const res = await fetch(`${ALVO}/health`, { signal: AbortSignal.timeout(3_000) });
    if (!res.ok) throw new Error(String(res.status));
  } catch {
    console.error(`\nO servidor não respondeu em ${ALVO}/health. Suba com: npm run dev\n`);
    process.exitCode = 1;
    return;
  }

  await testarDataComparavel();
  await testarSerializacaoPorTelefone();
  await testarWamidUnico();
  await testarPatchSimultaneo();
  await testarReservaOutbox();
  await testarRecuperacaoOutbox();
  await testarHistoricoSituacao();
  await testarArvoreDeAssuntos();

  console.log(
    falhas === 0
      ? '\nTudo certo: as garantias de banco se comportaram como o esperado.\n'
      : `\n${falhas} verificação(ões) falharam.\n`
  );
  if (falhas > 0) process.exitCode = 1;
}

main()
  .catch((err) => {
    console.error('Falha na verificação:', err instanceof Error ? err.message : err);
    process.exitCode = 1;
  })
  .finally(async () => {
    await controlarEvolution(0); // nunca deixar a Evolution de mentira em modo falha
    await prisma.$disconnect();
  });
