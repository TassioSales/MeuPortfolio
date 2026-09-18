import './env';
import assert from 'node:assert/strict';
import test, { beforeEach } from 'node:test';
import { Estado, Sessao, capturarEnvios, criarFakePrisma } from './fake-prisma';

const dbClient = require('../src/db/client');
const { processarMensagem } = require('../src/conversation/handler');
const { postarComRetry, corpoTexto, corpoEscolha } = require('../src/whatsapp/client');
const { alertar, _resetAlertas } = require('../src/alerta');
const { despachar, varrerPendentes } = require('../src/whatsapp/outbox');
const { avisarIndisponibilidade, _resetAvisos } = require('../src/whatsapp/indisponibilidade');
const { _resetThrottle } = require('../src/whatsapp/throttle');

const TEL = '5511998877665';
const captura = capturarEnvios();
const MAX_TENTATIVAS = Number(process.env.ENVIOS_MAX_TENTATIVAS ?? 6);

function preparar(sessaoInicial?: Partial<Sessao> & { telefone: string }): Estado {
  const estado = criarFakePrisma(sessaoInicial);
  dbClient.prisma = estado.prisma;
  captura.reset();
  return estado;
}

beforeEach(() => {
  _resetThrottle();
  _resetAvisos();
});

// --- retry / backoff -----------------------------------------------------

test('erro de rede é repetido e a segunda tentativa vale', async () => {
  preparar();
  captura.programar(['erro-de-rede']);

  const r = await postarComRetry(corpoTexto(TEL, 'oi'));

  assert.equal(r.ok, true);
  assert.equal(captura.enviados.length, 2, 'deveria ter tentado duas vezes');
});

test('5xx é repetido; 4xx não', async () => {
  preparar();
  captura.programar([{ status: 503 }]);
  let r = await postarComRetry(corpoTexto(TEL, 'oi'));
  assert.equal(r.ok, true);
  assert.equal(captura.enviados.length, 2);

  captura.reset();
  captura.programar([{ status: 400 }, { status: 200 }]);
  r = await postarComRetry(corpoTexto(TEL, 'oi'));
  assert.equal(r.ok, false);
  assert.equal(r.permanente, true, '400 é permanente');
  assert.equal(captura.enviados.length, 1, 'não deve repetir erro permanente');
});

test('429 é tratado como transitório', async () => {
  preparar();
  captura.programar([{ status: 429 }]);
  const r = await postarComRetry(corpoTexto(TEL, 'oi'));
  assert.equal(r.ok, true);
});

test('desiste depois do teto de tentativas', async () => {
  preparar();
  captura.programar(['erro-de-rede', 'erro-de-rede', 'erro-de-rede', 'erro-de-rede']);

  const r = await postarComRetry(corpoTexto(TEL, 'oi'));

  assert.equal(r.ok, false);
  assert.equal(r.permanente, false);
  assert.equal(captura.enviados.length, Number(process.env.ENVIOS_TENTATIVAS ?? 3));
});

// --- orçamento de tempo do envio síncrono --------------------------------

test('orçamento já vencido não gasta nenhuma tentativa', async () => {
  preparar();
  const r = await postarComRetry(corpoTexto(TEL, 'oi'), { ateMs: Date.now() - 1 });

  assert.equal(r.ok, false);
  assert.equal(captura.enviados.length, 0, 'nem tenta: a Meta já está esperando demais');
});

test('orçamento curto corta o retry em vez de estourar o tempo do webhook', async () => {
  preparar();
  captura.programar(['erro-de-rede', 'erro-de-rede', 'erro-de-rede']);

  // O primeiro backoff é de ~300ms, então não cabe em 50ms: faz uma tentativa e
  // desiste, deixando a linha para o varredor.
  const r = await postarComRetry(corpoTexto(TEL, 'oi'), { ateMs: Date.now() + 50 });

  assert.equal(r.ok, false);
  assert.equal(r.permanente, false, 'transitório: o varredor ainda vai tentar');
  assert.equal(captura.enviados.length, 1);
});

test('tentativas pode ser limitado por chamada', async () => {
  preparar();
  captura.programar(['erro-de-rede', 'erro-de-rede', 'erro-de-rede']);

  await postarComRetry(corpoTexto(TEL, 'oi'), { tentativas: 1 });
  assert.equal(captura.enviados.length, 1);
});

// --- outbox --------------------------------------------------------------

test('a resposta é gravada na outbox dentro da transação, antes do envio', async () => {
  const e = preparar();
  await processarMensagem(TEL, { tipo: 'texto', valor: 'Natan' }, 'w1');

  const saida = e.mensagens.find((m) => m.remetente === 'sistema');
  assert.ok(saida, 'linha de saída deve existir');
  assert.ok(saida.payload, 'payload guardado permite reenvio');
  assert.equal(saida.payload.number, TEL);
  assert.ok(saida.enviadaEm instanceof Date, 'envio deu certo -> marcada como enviada');
});

test('envio que falha deixa a mensagem pendente para o varredor', async () => {
  // Sessão já na etapa `nome`: o que interessa aqui é a resposta que AVANÇA o
  // estado, e o primeiro contato só devolve a saudação.
  const e = preparar({ telefone: TEL, etapa: 'nome' });
  captura.programar(['erro-de-rede', 'erro-de-rede', 'erro-de-rede']);

  await processarMensagem(TEL, { tipo: 'texto', valor: 'Natan' }, 'w1');

  const saida = e.mensagens.find((m) => m.remetente === 'sistema');
  assert.equal(saida.enviadaEm, null, 'continua pendente');
  assert.equal(saida.tentativas, 1);
  assert.equal(e.sessoes.get(TEL)!.etapa, 'resumo', 'o estado avançou mesmo assim');
});

test('falha permanente não fica sendo retentada', async () => {
  const e = preparar();
  captura.programar([{ status: 400 }]);

  await processarMensagem(TEL, { tipo: 'texto', valor: 'Natan' }, 'w1');

  const saida = e.mensagens.find((m) => m.remetente === 'sistema');
  assert.equal(saida.enviadaEm, null);
  assert.equal(
    saida.tentativas,
    Number(process.env.ENVIOS_MAX_TENTATIVAS ?? 6),
    'marcada como desistida'
  );
});

test('despachar marca enviadaEm quando dá certo', async () => {
  const e = preparar();
  const linha = await e.prisma.mensagem.create({
    data: { telefone: TEL, remetente: 'sistema', texto: 'oi', payload: corpoTexto(TEL, 'oi') },
  });

  const ok = await despachar(linha.id, corpoTexto(TEL, 'oi'));

  assert.equal(ok, true);
  assert.ok(e.mensagens.find((m) => m.id === linha.id).enviadaEm instanceof Date);
});

// --- varredor de pendentes ----------------------------------------------

/** Cria uma linha de saída pendente com idade e histórico de tentativas. */
async function pendente(
  e: Estado,
  opts: { idadeMs?: number; tentativas?: number; ultimaTentativaMs?: number } = {}
) {
  const agora = Date.now();
  const linha = await e.prisma.mensagem.create({
    data: {
      telefone: TEL,
      remetente: 'sistema',
      texto: 'oi',
      payload: corpoTexto(TEL, 'oi'),
      enviadaEm: null,
      tentativas: opts.tentativas ?? 0,
      timestamp: new Date(agora - (opts.idadeMs ?? 120_000)),
      ultimaTentativaEm:
        opts.ultimaTentativaMs === undefined ? null : new Date(agora - opts.ultimaTentativaMs),
    },
  });
  return e.mensagens.find((m) => m.id === linha.id);
}

test('o varredor reenvia pendente e marca como enviada', async () => {
  const e = preparar();
  const linha = await pendente(e);

  assert.equal(await varrerPendentes(), 1);
  assert.ok(linha.enviadaEm instanceof Date);
  assert.equal(captura.enviados.length, 1);
});

// Uma linha que ficou pendente ANTES da troca da Meta pela Evolution guarda o
// corpo no formato antigo. Sem reconstrução ela queimaria as seis tentativas
// contra um 400 e morreria — mensagem perdida, e o alerta diria só "desisti".
test('pendente com payload no formato antigo é reconstruída, não descartada', async () => {
  const e = preparar();
  const linha = await e.prisma.mensagem.create({
    data: {
      telefone: TEL,
      remetente: 'sistema',
      texto: 'Mensagem presa desde antes da migração.',
      // Exatamente o que a Meta recebia.
      payload: {
        messaging_product: 'whatsapp',
        recipient_type: 'individual',
        to: TEL,
        type: 'text',
        text: { body: 'Mensagem presa desde antes da migração.' },
      },
      enviadaEm: null,
      tentativas: 0,
      timestamp: new Date(Date.now() - 120_000),
      ultimaTentativaEm: null,
    },
  });

  assert.equal(await varrerPendentes(), 1);

  const enviado = captura.enviados[0];
  assert.equal(enviado.number, TEL, 'o destinatário veio da coluna telefone');
  assert.equal(
    enviado.text,
    'Mensagem presa desde antes da migração.',
    'o texto veio da coluna texto'
  );
  assert.equal(enviado.messaging_product, undefined, 'nada do formato da Meta sobrou');
  assert.equal(enviado.to, undefined, 'nada do formato da Meta sobrou');

  const gravada = e.mensagens.find((m: any) => m.id === linha.id);
  assert.ok(gravada.enviadaEm instanceof Date, 'e a linha foi marcada como entregue');
});

test('o varredor ignora mensagem recém-criada', async () => {
  const e = preparar();
  await pendente(e, { idadeMs: 5_000 });

  assert.equal(await varrerPendentes(), 0, 'os 30s iniciais ainda não passaram');
  assert.equal(captura.enviados.length, 0);
});

test('o varredor espera mais a cada tentativa gasta', async () => {
  const e = preparar();
  // 1 tentativa gasta => precisa esperar 60s. Com 40s, ainda não é a hora.
  await pendente(e, { tentativas: 1, ultimaTentativaMs: 40_000 });
  assert.equal(await varrerPendentes(), 0, 'a espera de 60s não venceu');

  const e2 = preparar();
  const linha = await pendente(e2, { tentativas: 1, ultimaTentativaMs: 90_000 });
  assert.equal(await varrerPendentes(), 1, 'passados 90s, tenta de novo');
  assert.ok(linha.enviadaEm instanceof Date);
});

test('o varredor não pega mensagem que já esgotou as tentativas', async () => {
  const e = preparar();
  await pendente(e, { tentativas: MAX_TENTATIVAS, ultimaTentativaMs: 10 * 60_000 });

  assert.equal(await varrerPendentes(), 0);
  assert.equal(captura.enviados.length, 0);
});

test('a reserva já conta a tentativa, mesmo se o envio falhar', async () => {
  const e = preparar();
  const linha = await pendente(e, { tentativas: 2, ultimaTentativaMs: 10 * 60_000 });
  captura.programar(['erro-de-rede', 'erro-de-rede', 'erro-de-rede']);

  assert.equal(await varrerPendentes(), 0);
  assert.equal(linha.tentativas, 3, 'incrementada na reserva');
  assert.ok(linha.ultimaTentativaEm instanceof Date, 'marca quando tentou, para espaçar a próxima');
  assert.equal(linha.enviadaEm, null);
});

// --- o menu numerado -----------------------------------------------------
//
// Os limites de botão (3) e de lista (10 linhas, títulos de 20 e 24) sumiram
// junto com os formatos interativos. Eles existiam porque a Meta RECUSAVA a
// mensagem inteira ao estourá-los; texto não tem esse teto.
//
// O que ficou no lugar é a garantia que passou a importar: nenhuma opção some.

test('o menu numera todas as opções, sem descartar nenhuma', () => {
  const opcoes = Array.from({ length: 14 }, (_, i) => ({ id: `id${i}`, texto: `Opção ${i + 1}` }));
  const corpo: any = corpoEscolha(TEL, 'Escolha:', opcoes);

  for (let i = 1; i <= 14; i++) {
    assert.ok(corpo.text.includes(`${i}. Opção ${i}`), `a opção ${i} deveria estar no texto`);
  }
});

test('o menu não corta rótulo longo', () => {
  // Com a lista da Meta, um rótulo acima de 24 caracteres era truncado — e era
  // por isso que o menu de assuntos sempre pediu o número.
  const rotulo = 'SUPORTE TÉCNICO AO FRANQUEADO DA REGIÃO METROPOLITANA';
  const corpo: any = corpoEscolha(TEL, 'Escolha:', [{ id: 'a', texto: rotulo }]);

  assert.ok(corpo.text.includes(rotulo), 'o rótulo inteiro precisa aparecer');
});

test('o corpo de envio tem a forma da Evolution', () => {
  const corpo: any = corpoEscolha(TEL, 'Escolha:', [{ id: 'a', texto: 'A' }]);

  assert.equal(corpo.number, TEL);
  assert.equal(typeof corpo.text, 'string');
  assert.equal(corpo.messaging_product, undefined, 'campo da Meta não pode sobrar');
  assert.equal(corpo.interactive, undefined, 'não existe mais mensagem interativa');
});

// --- aviso de indisponibilidade -----------------------------------------

test('quando o processamento estoura, o usuário recebe um aviso', async () => {
  preparar();
  await avisarIndisponibilidade([TEL]);

  assert.equal(captura.enviados.length, 1);
  assert.match(captura.ultimoTexto(), /problema técnico/i);
  assert.match(captura.ultimoTexto(), /não foi registrada/i);
});

test('o aviso não vira looping para o mesmo telefone', async () => {
  preparar();
  for (let i = 0; i < 5; i++) await avisarIndisponibilidade([TEL]);

  assert.equal(captura.enviados.length, 1, 'só o primeiro aviso sai');
});

test('telefones diferentes recebem cada um o seu aviso', async () => {
  preparar();
  await avisarIndisponibilidade(['5511111111', '5522222222']);
  assert.equal(captura.enviados.length, 2);
});

test('o mesmo telefone repetido na lista recebe um aviso só', async () => {
  preparar();
  await avisarIndisponibilidade([TEL, TEL, TEL]);
  assert.equal(captura.enviados.length, 1);
});

test('o aviso não depende do banco', async () => {
  preparar();
  dbClient.prisma = {
    $transaction: () => {
      throw new Error('banco fora');
    },
  };

  await avisarIndisponibilidade([TEL]);
  assert.equal(captura.enviados.length, 1, 'mesmo sem banco, o aviso sai');
});

test('telefone em formato inválido não gera aviso', async () => {
  preparar();
  await avisarIndisponibilidade([]);
  await avisarIndisponibilidade(['nao-e-telefone']);
  assert.equal(captura.enviados.length, 0);
});

// --- Retry-After ---------------------------------------------------------

test('429 com Retry-After espera o que a Meta pediu, não o backoff próprio', async () => {
  preparar();
  captura.programar([{ status: 429, retryAfter: '1' }]);

  const antes = Date.now();
  const r = await postarComRetry(corpoTexto(TEL, 'oi'));
  const decorrido = Date.now() - antes;

  assert.equal(r.ok, true);
  assert.equal(captura.enviados.length, 2);
  // O backoff próprio da 1a retentativa é ~300ms; a Meta pediu 1s.
  assert.ok(decorrido >= 950, `esperou ${decorrido}ms, devia ter esperado ~1000ms`);
});

test('Retry-After longo demais não segura a execução', async () => {
  preparar();
  // 5 minutos: acima do teto de 60s que vale a pena esperar aqui.
  captura.programar([{ status: 429, retryAfter: '300' }]);

  const antes = Date.now();
  const r = await postarComRetry(corpoTexto(TEL, 'oi'));
  const decorrido = Date.now() - antes;

  assert.equal(r.ok, false);
  assert.equal(r.permanente, false, 'segue pendente para o varredor tentar depois');
  assert.equal(captura.enviados.length, 1, 'não insistiu');
  assert.ok(decorrido < 1_000, `voltou em ${decorrido}ms, sem esperar os 5min`);
});

test('Retry-After em data HTTP também é entendido', async () => {
  preparar();
  // Data HTTP tem precisão de segundo: `toUTCString()` joga fora os
  // milissegundos, então +2s vira uma espera real entre ~1s e 2s. O limite de
  // baixo do assert respeita isso - e o que importa é ser MUITO maior que os
  // ~300ms do backoff próprio.
  const daquiDoisSegundos = new Date(Date.now() + 2_000).toUTCString();
  captura.programar([{ status: 429, retryAfter: daquiDoisSegundos }]);

  const antes = Date.now();
  const r = await postarComRetry(corpoTexto(TEL, 'oi'));
  const decorrido = Date.now() - antes;

  assert.equal(r.ok, true);
  assert.ok(decorrido >= 900, `esperou ${decorrido}ms; a data devia virar espera`);
});

test('sem Retry-After o backoff próprio continua valendo', async () => {
  preparar();
  captura.programar([{ status: 429 }]);

  const antes = Date.now();
  const r = await postarComRetry(corpoTexto(TEL, 'oi'));
  const decorrido = Date.now() - antes;

  assert.equal(r.ok, true);
  assert.ok(decorrido < 950, `esperou ${decorrido}ms; sem header devia usar o backoff curto`);
});

// --- o menu cresce sem perder opção --------------------------------------
//
// Existia aqui uma bateria sobre a ESCOLHA DE FORMATO: até 3 opções viravam
// botões, de 4 a 10 viravam lista, e cada formato tinha o seu teto. Tudo isso
// desapareceu com os formatos interativos.
//
// O que a bateria protegia continua valendo, e é o que ficou: acrescentar um
// campo não pode fazer uma opção sumir da conversa sem aviso.

const opcoes = (n: number) =>
  Array.from({ length: n }, (_, i) => ({ id: `op_${i}`, texto: `Opção ${i}` }));

test('menu de edição mantém uma opção por campo mesmo se CAMPOS crescer', () => {
  const corpo: any = corpoEscolha(TEL, 'Qual informação deseja corrigir?', [
    { id: 'editar_nome', texto: 'Nome' },
    { id: 'editar_resumo', texto: 'Resumo' },
    { id: 'editar_descricao', texto: 'Descrição' },
    { id: 'editar_setor', texto: 'Setor' },
  ]);

  assert.ok(corpo.text.includes('4. Setor'), 'o quarto campo não pode sumir do menu');
});

test('vinte opções continuam todas na mensagem', () => {
  // Com a lista da Meta, a décima primeira era descartada. Aqui não há teto.
  const corpo: any = corpoEscolha(TEL, 'texto', opcoes(20));

  assert.ok(corpo.text.includes('20. Opção 19'));
  assert.equal(corpo.text.split('\n').filter((l: string) => /^\d+\. /.test(l)).length, 20);
});

test('a instrução final orienta a responder com o número', () => {
  const corpo: any = corpoEscolha(TEL, 'texto', opcoes(2));
  assert.match(corpo.text, /responda com o número/i);
});

// --- alerta de mensagem descartada --------------------------------------

// `alertar` é disparado sem await de propósito (a rede do alerta não pode
// atrasar o varredor), então o teste precisa ceder o laço de eventos.
const cederLaco = () => new Promise((r) => setTimeout(r, 0));

test('desistir de uma mensagem dispara alerta', async () => {
  const e = preparar();
  _resetAlertas();

  const m = await e.prisma.mensagem.create({
    data: { telefone: TEL, remetente: 'sistema', texto: 'oi', payload: corpoTexto(TEL, 'oi') },
  });

  // 400: falha permanente, o caminho em que a outbox desiste na hora.
  captura.programar([{ status: 400 }]);
  await despachar(m.id, corpoTexto(TEL, 'oi'));
  await cederLaco();

  assert.equal(captura.alertas.length, 1, 'o usuário ficou sem resposta e ninguém era avisado');
  assert.equal(captura.alertas[0].detalhes.mensagemId, m.id);
});

test('o alerta não carrega telefone nem texto da mensagem', async () => {
  const e = preparar();
  _resetAlertas();

  const m = await e.prisma.mensagem.create({
    data: {
      telefone: TEL,
      remetente: 'sistema',
      texto: 'Confirma a abertura do chamado?',
      payload: corpoTexto(TEL, 'Confirma a abertura do chamado?'),
    },
  });

  captura.programar([{ status: 400 }]);
  await despachar(m.id, corpoTexto(TEL, 'Confirma a abertura do chamado?'));
  await cederLaco();

  // O destino é um canal de equipe, fora da retenção deste sistema: o id basta
  // para achar a linha no banco.
  const corpo = JSON.stringify(captura.alertas[0]);
  assert.ok(!corpo.includes(TEL), 'telefone não pode ir para o canal');
  assert.ok(!corpo.includes('Confirma a abertura'), 'texto não pode ir para o canal');
});

test('rajada de desistências vira um alerta só, com a contagem do resto', async () => {
  const e = preparar();
  _resetAlertas();

  for (let i = 0; i < 4; i++) {
    const m = await e.prisma.mensagem.create({
      data: { telefone: TEL, remetente: 'sistema', texto: 'oi', payload: corpoTexto(TEL, 'oi') },
    });
    captura.programar([{ status: 400 }]);
    await despachar(m.id, corpoTexto(TEL, 'oi'));
  }
  await cederLaco();

  // Sem a janela de coalescência, uma queda longa da Graph API enche o canal de
  // avisos idênticos - e um canal com centenas de alertas é um canal que
  // ninguém lê.
  assert.equal(captura.alertas.length, 1);
  assert.ok(!captura.alertas[0].text.includes('semelhante'), 'o primeiro não suprimiu ninguém');

  // O próximo a passar da janela leva o que ficou pelo caminho.
  _resetAlertas();
  const m = await e.prisma.mensagem.create({
    data: { telefone: TEL, remetente: 'sistema', texto: 'oi', payload: corpoTexto(TEL, 'oi') },
  });
  captura.programar([{ status: 400 }]);
  await despachar(m.id, corpoTexto(TEL, 'oi'));
  await cederLaco();
  assert.equal(captura.alertas.length, 2);
});

test('alerta que falha não derruba o envio', async () => {
  const e = preparar();
  _resetAlertas();
  const original = globalThis.fetch;
  globalThis.fetch = (async (url: any, opts: any) => {
    if (String(url).includes('alerta.invalido')) throw new Error('canal fora');
    return original(url, opts);
  }) as any;

  try {
    const m = await e.prisma.mensagem.create({
      data: { telefone: TEL, remetente: 'sistema', texto: 'oi', payload: corpoTexto(TEL, 'oi') },
    });
    captura.programar([{ status: 400 }]);
    // O alerta existe para avisar sobre a falha, não para virar uma segunda.
    assert.equal(await despachar(m.id, corpoTexto(TEL, 'oi')), false);
    await cederLaco();
  } finally {
    globalThis.fetch = original;
  }
});
