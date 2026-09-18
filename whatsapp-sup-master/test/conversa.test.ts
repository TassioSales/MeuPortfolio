import './env';
import assert from 'node:assert/strict';
import test, { beforeEach } from 'node:test';
import { Categoria, Estado, Sessao, capturarEnvios, criarFakePrisma } from './fake-prisma';

const dbClient = require('../src/db/client');
const { processarMensagem } = require('../src/conversation/handler');
const { handleIncomingMessage } = require('../src/whatsapp/webhook');
const { _resetThrottle } = require('../src/whatsapp/throttle');
const { MAX_CORPO_MENSAGEM } = require('../src/conversation/flows');
const { contarSessoesExpiradas, limparSessoesExpiradas } = require('../src/conversation/sessoes');

const TEL = '5511998877665';
const captura = capturarEnvios();

function preparar(
  sessaoInicial?: Partial<Sessao> & { telefone: string },
  categorias: Partial<Categoria>[] = []
): Estado {
  const estado = criarFakePrisma(sessaoInicial, categorias);
  dbClient.prisma = estado.prisma;
  captura.reset();
  return estado;
}

const emConfirmacao = {
  telefone: TEL,
  etapa: 'confirmacao',
  nome: 'Natan',
  resumo: 'Sistema fora do ar',
  descricao: 'Desde as 9h não consigo acessar.',
  criadoEm: new Date('2026-01-01'),
};

const texto = (valor: string) => ({ tipo: 'texto' as const, valor });
const botao = (id: string) => ({ tipo: 'botao' as const, id });

// --- payloads da Evolution -----------------------------------------------
//
// O envelope é `{ event, instance, data }`, com UMA mensagem em `data` — a Meta
// agrupava em entry[] -> changes[] -> messages[]. O bot também aceita lista em
// `data`, e é o que os testes de lote usam.

const jid = (telefone: string) => `${telefone}@s.whatsapp.net`;

const evento = (data: unknown) => ({ event: 'messages.upsert', instance: 'teste', data });

const msgTexto = (de: string, valor: string, id: string) => ({
  key: { remoteJid: jid(de), fromMe: false, id },
  message: { conversation: valor },
  messageType: 'conversation',
});

/** `tipo` é o nome do Baileys: `audioMessage`, `imageMessage`... */
const msgMidia = (de: string, tipo: string, id: string) => ({
  key: { remoteJid: jid(de), fromMe: false, id },
  message: { [tipo]: { mimetype: 'application/octet-stream' } },
  messageType: tipo,
});

beforeEach(() => _resetThrottle());

// --- fluxo feliz ---------------------------------------------------------

test('fluxo completo: nome -> resumo -> descrição -> confirmação -> chamado', async () => {
  const e = preparar();

  // Primeiro contato só responde a saudação; ver o teste seguinte.
  await processarMensagem(TEL, texto('oi'), 'w0');

  await processarMensagem(TEL, texto('Natan'), 'w1');
  assert.equal(e.sessoes.get(TEL)!.nome, 'Natan');
  assert.equal(e.sessoes.get(TEL)!.etapa, 'resumo');

  await processarMensagem(TEL, texto('Sistema fora do ar'), 'w2');
  assert.equal(e.sessoes.get(TEL)!.etapa, 'descricao');

  await processarMensagem(TEL, texto('Desde as 9h não consigo acessar.'), 'w3');
  assert.equal(e.sessoes.get(TEL)!.etapa, 'confirmacao');
  assert.match(captura.ultimoTexto(), /Confirma a abertura/);

  await processarMensagem(TEL, botao('confirmar'), 'w4');
  assert.equal(e.chamados.length, 1);
  assert.equal(e.chamados[0].situacao, 'aberto');
  assert.equal(e.chamados[0].nome, 'Natan');
  assert.equal(e.sessoes.has(TEL), false, 'sessão deve ser apagada ao confirmar');
});

test('primeiro contato recebe a saudação, e a mensagem não vira o nome', async () => {
  const e = preparar();

  // Quem chega no WhatsApp escreve "oi", não o próprio nome. Este texto era
  // gravado como NOME e o formulário inteiro deslizava um campo: o nome ia
  // para o resumo, o resumo para a descrição. A pergunta da etapa `nome` só
  // era alcançável por expiração, mídia ou edição.
  await processarMensagem(TEL, texto('oi'), 'w1');

  assert.match(captura.ultimoTexto(), /qual é o seu nome/i);
  assert.equal(e.sessoes.get(TEL)!.nome, null, 'a saudação não pode virar valor de campo');
  assert.equal(e.sessoes.get(TEL)!.etapa, 'nome', 'continua esperando o nome');

  await processarMensagem(TEL, texto('Natan'), 'w2');

  assert.equal(e.sessoes.get(TEL)!.nome, 'Natan');
  assert.equal(e.sessoes.get(TEL)!.etapa, 'resumo');
});

test('a saudação não é repetida na segunda mensagem', async () => {
  const e = preparar();
  await processarMensagem(TEL, texto('oi'), 'w1');
  await processarMensagem(TEL, texto('bom dia'), 'w2');

  // A segunda mensagem já é resposta: vira o nome, mesmo sendo outra saudação.
  // Insistir em "isso não parece um nome" seria adivinhar conteúdo, que é
  // exatamente o que este projeto não faz.
  assert.equal(e.sessoes.get(TEL)!.nome, 'bom dia');
  assert.equal(e.sessoes.get(TEL)!.etapa, 'resumo');
});

// --- #6 ------------------------------------------------------------------

test('#6 mensagens de saída são registradas com remetente=sistema', async () => {
  const e = preparar();
  await processarMensagem(TEL, texto('Natan'), 'w1');

  const entradas = e.mensagens.filter((m) => m.remetente === 'usuario');
  const saidas = e.mensagens.filter((m) => m.remetente === 'sistema');
  assert.equal(entradas.length, 1);
  assert.equal(saidas.length, 1);
  assert.equal(saidas[0].texto, captura.ultimoTexto());
});

test('#6 a mensagem de chamado aberto já nasce vinculada ao chamado', async () => {
  const e = preparar(emConfirmacao);
  await processarMensagem(TEL, botao('confirmar'), 'w1');

  const saida = e.mensagens.find((m) => m.remetente === 'sistema');
  assert.equal(saida.chamadoId, e.chamados[0].id);
});

// --- #7 ------------------------------------------------------------------

test('#7 digitar um id interno de botão não dispara o comando', async () => {
  const e = preparar(emConfirmacao);
  await processarMensagem(TEL, texto('editar_descricao'), 'w1');

  assert.equal(e.sessoes.get(TEL)!.etapa, 'confirmacao');
  assert.match(captura.ultimoTexto(), /use os botões/i);
});

test('#7 clicar no botão de edição entra no campo certo', async () => {
  const e = preparar(emConfirmacao);
  await processarMensagem(TEL, botao('editar_descricao'), 'w1');

  assert.equal(e.sessoes.get(TEL)!.etapa, 'descricao');
  assert.equal(e.sessoes.get(TEL)!.editando, true);
});

test('#7 as palavras humanas ainda funcionam digitadas', async () => {
  for (const palavra of ['confirmar', 'SIM', ' Ok ']) {
    const e = preparar(emConfirmacao);
    await processarMensagem(TEL, texto(palavra), `w-${palavra}`);
    assert.equal(e.chamados.length, 1, `"${palavra}" deveria confirmar`);
  }
});

test('#7 editar um campo volta direto para a confirmação', async () => {
  const e = preparar({ ...emConfirmacao, etapa: 'resumo', editando: true });
  await processarMensagem(TEL, texto('Outro resumo'), 'w1');

  assert.equal(e.sessoes.get(TEL)!.resumo, 'Outro resumo');
  assert.equal(e.sessoes.get(TEL)!.etapa, 'confirmacao');
  assert.equal(e.sessoes.get(TEL)!.editando, false);
});

// --- #8 ------------------------------------------------------------------

test('#8 id de campo fora da whitelist é recusado sem quebrar', async () => {
  const e = preparar(emConfirmacao);
  await processarMensagem(TEL, botao('editar_situacao'), 'w1');

  assert.equal(e.sessoes.get(TEL)!.etapa, 'confirmacao');
  assert.match(captura.ultimoTexto(), /não reconheci/i);
});

// --- #9 ------------------------------------------------------------------

test('#9 todas as mensagens de um lote são processadas, não só a primeira', async () => {
  const e = preparar();
  const msg = (i: number) =>
    msgTexto(`55119988776${String(i).padStart(2, '0')}`, `mensagem ${i}`, `id.${i}`);

  await handleIncomingMessage(evento([msg(1), msg(2), msg(3), msg(4), msg(5)]));

  assert.equal(e.mensagens.filter((m) => m.remetente === 'usuario').length, 5);
});

test('#9 evento que não é de mensagem não faz nada', async () => {
  const e = preparar();
  // `connection.update`, `messages.update`, presença, recibo de leitura: a
  // Evolution manda tudo pelo mesmo webhook quando não se filtra o evento. Ler
  // um recibo como se fosse conversa é o que esta checagem impede.
  await handleIncomingMessage({
    event: 'connection.update',
    instance: 'teste',
    data: { state: 'open' },
  });
  assert.equal(e.mensagens.length, 0);
});

test('a própria mensagem do bot (fromMe) é ignorada', async () => {
  const e = preparar();
  // A Evolution notifica TAMBÉM o que nós acabamos de enviar. Sem o descarte,
  // cada resposta do bot viraria entrada nova e a conversa entraria em laço.
  await handleIncomingMessage(
    evento({
      key: { remoteJid: jid(TEL), fromMe: true, id: 'eco' },
      message: { conversation: 'Qual é o seu nome?' },
      messageType: 'conversation',
    })
  );
  assert.equal(e.mensagens.length, 0);
  assert.equal(e.sessoes.has(TEL), false);
});

test('mensagem de grupo é descartada', async () => {
  const e = preparar();
  // O bot é conversa de um para um. Uma sessão indexada pelo id de um grupo
  // misturaria as respostas de todo mundo no mesmo formulário.
  await handleIncomingMessage(
    evento({
      key: { remoteJid: '120363000000000000@g.us', fromMe: false, id: 'g1' },
      message: { conversation: 'oi' },
      messageType: 'conversation',
    })
  );
  assert.equal(e.mensagens.length, 0);
});

test('telefone em formato inválido é descartado', async () => {
  const e = preparar();
  await handleIncomingMessage(evento(msgTexto('not-a-phone', 'oi', 'w')));
  assert.equal(e.mensagens.length, 0);
});

// --- #10 -----------------------------------------------------------------

test('#10 entrega repetida do mesmo wamid não avança o fluxo', async () => {
  const e = preparar();
  await processarMensagem(TEL, texto('Natan'), 'wamid.dup');
  const etapa = e.sessoes.get(TEL)!.etapa;
  const envios = captura.enviados.length;

  await processarMensagem(TEL, texto('Natan'), 'wamid.dup');

  assert.equal(e.sessoes.get(TEL)!.etapa, etapa);
  assert.equal(captura.enviados.length, envios, 'não deve responder de novo');
});

test('#10 ler a etapa e gravar a resposta acontece dentro de UMA transação', async () => {
  const e = preparar();
  await processarMensagem(TEL, texto('Natan'), 'w1');

  // A serialização entre mensagens simultâneas do mesmo telefone vem de a
  // transação existir: no Postgres havia um `pg_advisory_xact_lock` para
  // observar, no SQLite o mutex é do adaptador e não aparece em SQL nenhuma.
  // Sobra conferir que a transação foi aberta - e que foi UMA, porque abrir
  // duas em sequência devolveria a corrida que o lock resolvia.
  assert.equal(e.transacoes.abertas, 1);

  // E que as escritas caíram DENTRO dela: gravar a entrada, avançar a etapa e
  // enfileirar a resposta fora da transação devolveria a corrida - duas
  // mensagens simultâneas leriam a mesma etapa.
  assert.deepEqual(e.transacoes.escritas, [
    'mensagem.create:usuario',
    // `create` e não `update`: este é o primeiro contato do telefone, então a
    // sessão nasce aqui dentro (ver `decidir` em conversation/handler.ts).
    'sessaoConversa.create',
    // Este teste não semeia categoria nenhuma, então a etapa de assunto é pulada
    // - e pular é uma ESCRITA, porque grava a etapa seguinte. Ela cai dentro da
    // mesma transação, que é o que este teste existe para provar.
    'sessaoConversa.update',
    'mensagem.create:sistema',
  ]);
});

// --- #11 -----------------------------------------------------------------

test('#11 só as mensagens desta conversa são vinculadas ao chamado', async () => {
  const e = preparar(emConfirmacao);
  await processarMensagem(TEL, botao('confirmar'), 'w1');

  const where = e.updateManyArgs[0].where;
  assert.equal(where.chamadoId, null);
  assert.equal(where.timestamp.gte.getTime(), emConfirmacao.criadoEm.getTime());
});

// --- #12 -----------------------------------------------------------------

test('#12 confirmar com campo nulo repergunta em vez de estourar', async () => {
  const e = preparar({ ...emConfirmacao, descricao: null });
  await processarMensagem(TEL, botao('confirmar'), 'w1');

  assert.equal(e.chamados.length, 0);
  assert.equal(e.sessoes.get(TEL)!.etapa, 'descricao');
  assert.match(captura.ultimoTexto(), /descri/i);
});

// --- #13 -----------------------------------------------------------------

test('#13 áudio recebe resposta explicando a limitação', async () => {
  const e = preparar();
  await handleIncomingMessage(evento(msgMidia(TEL, 'audioMessage', 'w1')));

  assert.match(captura.ultimoTexto(), /só consigo ler mensagens de texto/i);
  assert.match(captura.ultimoTexto(), /qual é o seu nome/i, 'deve repetir a pergunta atual');
  assert.equal(e.sessoes.get(TEL)!.nome, null, 'mídia não pode virar valor de campo');
});

test('#13 mídia fica registrada no histórico da conversa', async () => {
  const e = preparar();
  await handleIncomingMessage(evento(msgMidia(TEL, 'imageMessage', 'w1')));

  const entrada = e.mensagens.find((m) => m.remetente === 'usuario');
  assert.match(entrada.texto, /imagem/);
});

test('#13 mídia na confirmação não confirma nem cancela nada', async () => {
  const e = preparar(emConfirmacao);
  await processarMensagem(TEL, { tipo: 'midia', formato: 'áudio' }, 'w1');

  assert.equal(e.chamados.length, 0);
  assert.equal(e.sessoes.get(TEL)!.etapa, 'confirmacao');
});

// --- #14 -----------------------------------------------------------------

test('#14 sessão parada além do TTL recomeça do zero', async () => {
  const doisDiasAtras = new Date(Date.now() - 48 * 60 * 60 * 1000);
  const e = preparar({ ...emConfirmacao, atualizadoEm: doisDiasAtras });

  await processarMensagem(TEL, texto('oi'), 'w1');

  assert.equal(e.sessoes.get(TEL)!.etapa, 'nome');
  assert.equal(e.sessoes.get(TEL)!.resumo, null);
  assert.match(captura.ultimoTexto(), /começar de novo/i);
});

test('#14 sessão recente continua de onde parou', async () => {
  const e = preparar({ ...emConfirmacao, atualizadoEm: new Date(Date.now() - 60_000) });
  await processarMensagem(TEL, texto('oi qualquer coisa'), 'w1');

  assert.equal(e.sessoes.get(TEL)!.etapa, 'confirmacao');
});

// --- #15 -----------------------------------------------------------------

test('#15 "cancelar" digitado encerra a conversa em qualquer etapa', async () => {
  for (const etapa of ['nome', 'resumo', 'descricao', 'confirmacao']) {
    const e = preparar({ ...emConfirmacao, etapa });
    await processarMensagem(TEL, texto('cancelar'), `w-${etapa}`);

    assert.equal(e.sessoes.has(TEL), false, `deveria cancelar na etapa ${etapa}`);
    assert.equal(e.chamados.length, 0);
    assert.match(captura.ultimoTexto(), /cancelei/i);
  }
});

test('#15 botão Cancelar na confirmação também encerra', async () => {
  const e = preparar(emConfirmacao);
  await processarMensagem(TEL, botao('cancelar'), 'w1');
  assert.equal(e.sessoes.has(TEL), false);
});

test('#15 "cancelar" sem nada em andamento não diz que cancelou algo', async () => {
  const e = preparar(); // nenhuma sessão existente
  await processarMensagem(TEL, texto('cancelar'), 'w1');

  assert.equal(e.chamados.length, 0);
  assert.match(captura.ultimoTexto(), /não tem nenhuma abertura/i);
});

test('#15 "cancelar" dentro de uma frase NÃO cancela', async () => {
  const e = preparar({ ...emConfirmacao, etapa: 'descricao' });
  await processarMensagem(TEL, texto('preciso cancelar meu pedido no site'), 'w1');

  assert.equal(e.sessoes.has(TEL), true);
  assert.equal(e.sessoes.get(TEL)!.descricao, 'preciso cancelar meu pedido no site');
});

// --- sessões abandonadas (LGPD) ------------------------------------------

test('sessão abandonada além do TTL é descartada pela varredura', async () => {
  const e = preparar({
    ...emConfirmacao,
    atualizadoEm: new Date(Date.now() - 48 * 60 * 60 * 1000),
  });

  assert.equal(await contarSessoesExpiradas(), 1);
  assert.equal(await limparSessoesExpiradas(), 1);
  assert.equal(e.sessoes.size, 0, 'nome, resumo e descrição não podem ficar no banco para sempre');
});

test('sessão ativa não é descartada pela varredura', async () => {
  const e = preparar({ ...emConfirmacao, atualizadoEm: new Date(Date.now() - 60_000) });

  assert.equal(await contarSessoesExpiradas(), 0);
  assert.equal(await limparSessoesExpiradas(), 0);
  assert.equal(e.sessoes.size, 1);
});

// --- normalização de texto ----------------------------------------------

test('acento não impede o reconhecimento do comando ("não" -> editar)', async () => {
  const e = preparar(emConfirmacao);
  await processarMensagem(TEL, texto('não'), 'w1');

  assert.equal(e.chamados.length, 0, '"não" na confirmação não pode abrir chamado');
  // O menu de correção deixou de ser uma segunda tela: "editar" digitado agora
  // só reapresenta o menu único, com as opções de correção já visíveis.
  assert.match(captura.ultimoTexto(), /escolha o que deseja corrigir/i);
  assert.ok(
    captura.ultimasOpcoes().some((o) => /resumo/i.test(o.texto)),
    'as opções de correção vêm no mesmo menu'
  );
});

// --- limites e formatação ------------------------------------------------

test('resposta acima do limite do campo recebe aviso amigável', async () => {
  const e = preparar({ telefone: TEL, etapa: 'resumo', nome: 'Natan' });
  await processarMensagem(TEL, texto('x'.repeat(500)), 'w1');

  assert.equal(e.sessoes.get(TEL)!.resumo, null);
  assert.match(captura.ultimoTexto(), /200 caracteres/);
});

test('resposta curta demais é recusada', async () => {
  const e = preparar({ telefone: TEL, etapa: 'nome' });
  await processarMensagem(TEL, texto('a'), 'w1');
  assert.equal(e.sessoes.get(TEL)!.nome, null);
  assert.match(captura.ultimoTexto(), /mais detalhada/i);
});

test('descrição longa não estoura o limite do corpo interativo', async () => {
  preparar({ ...emConfirmacao, descricao: 'x'.repeat(2000) });
  await processarMensagem(TEL, botao('editar'), 'w0');

  const e2 = preparar({
    ...emConfirmacao,
    descricao: 'x'.repeat(2000),
    etapa: 'descricao',
    editando: true,
  });
  await processarMensagem(TEL, texto('y'.repeat(2000)), 'w1');

  const corpo = captura.ultimoTexto();
  assert.ok(
    corpo.length <= MAX_CORPO_MENSAGEM,
    `corpo tem ${corpo.length}, máximo ${MAX_CORPO_MENSAGEM}`
  );
  assert.equal(
    e2.sessoes.get(TEL)!.descricao!.length,
    2000,
    'o texto completo continua salvo no banco'
  );
});

// --- reentrega x cota por telefone ---------------------------------------

const LIMITE_POR_MINUTO = Number(process.env.MSGS_POR_MINUTO_POR_TELEFONE ?? 20);

const loteDe = (id: string) => evento(msgTexto(TEL, 'oi', id));

test('reentrega da Meta não consome a cota do telefone', async () => {
  const e = preparar();

  await handleIncomingMessage(loteDe('wamid.a'));

  // A Meta entrega "pelo menos uma vez": a mesma mensagem pode voltar várias
  // vezes. Todas são descartadas como duplicata - não podem gastar a cota.
  for (let i = 0; i < LIMITE_POR_MINUTO * 2; i++) {
    await handleIncomingMessage(loteDe('wamid.a'));
  }

  await handleIncomingMessage(loteDe('wamid.b'));

  const gravadas = e.mensagens.filter((m) => m.remetente === 'usuario');
  assert.equal(gravadas.length, 2, 'só as duas mensagens distintas foram gravadas');
  assert.ok(
    gravadas.some((m) => m.whatsappMessageId === 'wamid.b'),
    'a mensagem nova não pode ser barrada por cota gasta em reentrega'
  );
});

test('a cota continua valendo para mensagens de verdade', async () => {
  const e = preparar();

  // Uma a mais que o limite, todas com wamid distinto: nenhuma é duplicata.
  for (let i = 0; i <= LIMITE_POR_MINUTO; i++) {
    await handleIncomingMessage(loteDe(`wamid.real.${i}`));
  }

  const gravadas = e.mensagens.filter((m) => m.remetente === 'usuario');
  assert.equal(gravadas.length, LIMITE_POR_MINUTO, 'a que passou do limite foi descartada');
});

// --- resposta a menu antigo ----------------------------------------------
//
// O bot não manda mais botão nem lista: com a Evolution, menu é texto numerado.
// Mas uma conversa que estava no meio da virada pode ter um menu interativo
// ANTIGO na tela, e a resposta dele ainda chega. Ler esses dois formatos é o que
// impede essa pessoa de ficar sem resposta.

const respostaDeBotao = (selectedButtonId: string) =>
  evento({
    key: { remoteJid: jid(TEL), fromMe: false, id: 'w-botao' },
    message: { buttonsResponseMessage: { selectedButtonId } },
    messageType: 'buttonsResponseMessage',
  });

const respostaDeLista = (selectedRowId: string) =>
  evento({
    key: { remoteJid: jid(TEL), fromMe: false, id: 'w-lista' },
    message: { listResponseMessage: { singleSelectReply: { selectedRowId } } },
    messageType: 'listResponseMessage',
  });

test('resposta a botão antigo continua valendo', async () => {
  const e = preparar(emConfirmacao);
  await handleIncomingMessage(respostaDeBotao('editar_resumo'));

  assert.equal(e.sessoes.get(TEL)!.etapa, 'resumo');
  assert.equal(e.sessoes.get(TEL)!.editando, true);
});

test('escolha em lista antiga vale como clique de botão', async () => {
  const e = preparar(emConfirmacao);
  await handleIncomingMessage(respostaDeLista('editar_resumo'));

  assert.equal(e.sessoes.get(TEL)!.etapa, 'resumo');
  assert.equal(e.sessoes.get(TEL)!.editando, true);
});

test('resposta interativa sem id conhecido continua caindo em "só texto"', async () => {
  const e = preparar(emConfirmacao);

  await handleIncomingMessage(
    evento({
      key: { remoteJid: jid(TEL), fromMe: false, id: 'w-nfm' },
      message: { interactiveResponseMessage: {} },
      messageType: 'interactiveResponseMessage',
    })
  );

  assert.equal(e.sessoes.get(TEL)!.etapa, 'confirmacao', 'o fluxo não avança');
  assert.ok(captura.ultimoTexto().includes('só consigo ler mensagens de texto'));
});

// --- o menu numerado -----------------------------------------------------

test('responder com o NÚMERO confirma o chamado', async () => {
  const e = preparar(emConfirmacao);
  // Sem categoria ativa, a opção 1 é "Confirmar e abrir o chamado".
  await processarMensagem(TEL, texto('1'), 'w-num');

  assert.equal(e.chamados.length, 1);
  assert.equal(e.sessoes.has(TEL), false);
});

test('responder com o NÚMERO escolhe o campo a corrigir', async () => {
  const e = preparar(emConfirmacao);

  // A sessão começa em `confirmacao`, mas nenhuma mensagem foi ENVIADA ainda —
  // então não há menu para ler. Pedir o menu é o primeiro passo.
  await processarMensagem(TEL, texto('editar'), 'w-menu');
  const opcoes = captura.ultimasOpcoes();

  // Descobre a posição do campo pelo rótulo, em vez de fixar o número: a lista
  // muda de tamanho conforme haja ou não categoria ativa, e fixar o índice aqui
  // seria repetir a regra de montagem num segundo lugar.
  const posicao = opcoes.findIndex((o) => /resumo/i.test(o.texto)) + 1;
  assert.ok(posicao > 0, 'o menu deve oferecer a correção do resumo');

  await processarMensagem(TEL, texto(String(posicao)), 'w-num2');

  assert.equal(e.sessoes.get(TEL)!.etapa, 'resumo');
  assert.equal(e.sessoes.get(TEL)!.editando, true);
});

test('número fora da faixa não confirma nada', async () => {
  const e = preparar(emConfirmacao);
  // O risco concreto: cair na opção 1 por engano abriria o chamado.
  await processarMensagem(TEL, texto('99'), 'w-num3');

  assert.equal(e.chamados.length, 0);
  assert.equal(e.sessoes.get(TEL)!.etapa, 'confirmacao');
});

test('número com texto em volta não é escolha de menu', async () => {
  const e = preparar(emConfirmacao);
  await processarMensagem(TEL, texto('1 por favor'), 'w-num4');

  assert.equal(e.chamados.length, 0, 'não pode confirmar');
});
