import './env';
import assert from 'node:assert/strict';
import test, { beforeEach } from 'node:test';
import { Estado, criarFakePrisma } from './fake-prisma';

const dbClient = require('../src/db/client');
const configMod = require('../src/config');
const {
  TAMANHO_LOTE,
  aplicar,
  contar,
  esquecerTitular,
  interpretarArgs,
  main,
} = require('../src/scripts/retencao');

/**
 * Retenção (LGPD) — o código mais destrutivo do repositório.
 *
 * Duas obrigações distintas se encontram aqui, e cada uma erra para um lado:
 *   - apagar o que passou do prazo. Errar para menos deixa dado pessoal no
 *     banco além do combinado;
 *   - apagar TUDO de um titular que pediu eliminação, e SÓ dele. Errar para
 *     mais apaga o chamado de outra pessoa.
 *
 * A trava contra o segundo tipo de erro é a simulação, que roda por padrão. Por
 * isso o primeiro teste deste arquivo é o de que a simulação não apaga nada: se
 * só uma coisa aqui continuar verdadeira, que seja essa.
 */

const TEL = '5511998877665';
const OUTRO = '5511900000001';

const diasAtras = (dias: number) => new Date(Date.now() - dias * 24 * 60 * 60 * 1000);

let e: Estado;

// Política que veio do ambiente de teste, para devolver depois de cada caso.
const politicaOriginal = {
  mensagens: configMod.config.retencaoMensagensDias,
  chamados: configMod.config.retencaoChamadosDias,
};

function politica(mensagensDias: number, chamadosDias: number): void {
  configMod.config.retencaoMensagensDias = mensagensDias;
  configMod.config.retencaoChamadosDias = chamadosDias;
}

beforeEach(() => {
  e = criarFakePrisma();
  dbClient.prisma = e.prisma;
  politica(politicaOriginal.mensagens, politicaOriginal.chamados);
});

/** Um chamado com mensagens penduradas nele. */
function chamadoCom(id: number, telefone: string, idade: number, mensagens: number): void {
  e.chamados.push({
    id,
    nome: 'Fulano',
    telefone,
    dataAbertura: diasAtras(idade),
    resumo: 'r',
    descricao: 'd',
    situacao: 'aberto',
  });
  for (let i = 0; i < mensagens; i++) {
    e.mensagens.push({
      id: e.mensagens.length + 1,
      chamadoId: id,
      telefone,
      remetente: 'usuario',
      texto: 'oi',
      timestamp: diasAtras(idade),
    });
  }
}

function mensagemSolta(telefone: string, idade: number): any {
  const m = {
    id: e.mensagens.length + 1,
    chamadoId: null,
    telefone,
    remetente: 'usuario',
    texto: 'oi',
    timestamp: diasAtras(idade),
  };
  e.mensagens.push(m);
  return m;
}

// --- a trava de segurança ------------------------------------------------

test('simulação não apaga absolutamente nada', async () => {
  politica(30, 30);
  chamadoCom(1, TEL, 400, 3);
  mensagemSolta(TEL, 400);
  e.sessoes.set(TEL, { telefone: TEL, atualizadoEm: diasAtras(30) } as any);

  const n = await contar();

  assert.ok(n.mensagens > 0 && n.chamados > 0 && n.sessoes > 0, 'havia o que apagar');
  assert.equal(e.mensagens.length, 4, 'nenhuma mensagem foi tocada');
  assert.equal(e.chamados.length, 1, 'nenhum chamado foi tocado');
  assert.equal(e.sessoes.size, 1, 'nenhuma sessão foi tocada');
});

test('sem política configurada, mensagens e chamados não são apagados', async () => {
  politica(0, 0);
  chamadoCom(1, TEL, 3650, 2); // dez anos: só o prazo é que segura
  mensagemSolta(TEL, 3650);
  e.sessoes.set(TEL, { telefone: TEL, atualizadoEm: diasAtras(30) } as any);

  const n = await contar();
  assert.equal(n.mensagens, 0);
  assert.equal(n.chamados, 0);

  const r = await aplicar();

  assert.equal(e.mensagens.length, 3, 'prazo é decisão do negócio; sem ele nada sai');
  assert.equal(e.chamados.length, 1);
  // Sessão abandonada é a exceção: o prazo dela é o SESSAO_TTL_HORAS.
  assert.equal(r.sessoes, 1);
  assert.equal(e.sessoes.size, 0);
});

// --- prazo de mensagens e de chamados ------------------------------------

test('apaga só o que passou do prazo', async () => {
  politica(30, 0);
  mensagemSolta(TEL, 60); // fora do prazo
  const recente = mensagemSolta(TEL, 10); // dentro

  const r = await aplicar();

  assert.equal(r.mensagens, 1);
  assert.equal(e.mensagens.length, 1);
  assert.equal(e.mensagens[0].id, recente.id, 'a que sobrou é a que estava no prazo');
});

test('apagar um chamado leva as mensagens dele junto', async () => {
  politica(0, 30);
  chamadoCom(1, TEL, 60, 5); // vai embora, com as 5
  chamadoCom(2, TEL, 10, 2); // fica

  const r = await aplicar();

  assert.equal(r.chamados, 1);
  assert.equal(r.mensagens, 5);
  assert.equal(e.chamados.length, 1);
  assert.equal(e.chamados[0].id, 2);
  assert.equal(e.mensagens.length, 2, 'as mensagens do chamado que ficou continuam lá');
});

test('a simulação conta as mensagens que somem junto com o chamado', async () => {
  // O caso que a simulação escondia: o chamado está fora do prazo (30 dias),
  // mas as mensagens dele são recentes para o prazo de mensagens (90 dias).
  // Contar só pelo `timestamp` dizia "0 mensagens" e o --confirmar apagava as 4.
  politica(90, 30);
  chamadoCom(1, TEL, 60, 4);

  const previsto = await contar();
  const real = await aplicar();

  assert.equal(previsto.mensagens, 4, 'a simulação precisa avisar destas 4');
  assert.equal(real.mensagens, previsto.mensagens, 'simulação e realidade batem');
  assert.equal(previsto.chamados, real.chamados);
});

test('a mensagem que se encaixa nos dois prazos é contada uma vez só', async () => {
  politica(30, 30);
  chamadoCom(1, TEL, 60, 3); // velha pelos dois critérios

  const previsto = await contar();
  const real = await aplicar();

  assert.equal(previsto.mensagens, 3, 'sem contar em dobro');
  assert.equal(real.mensagens, 3);
});

// --- lotes ---------------------------------------------------------------

test('apaga mensagens em lotes até o fim, sem parar no primeiro', async () => {
  politica(30, 0);
  const total = TAMANHO_LOTE * 2 + 137;
  for (let i = 0; i < total; i++) mensagemSolta(TEL, 60);

  const r = await aplicar();

  assert.equal(r.mensagens, total, 'o laço tem que seguir além do primeiro lote');
  assert.equal(e.mensagens.length, 0);
});

test('apaga chamados em lotes até o fim', async () => {
  politica(0, 30);
  const total = TAMANHO_LOTE + 5;
  for (let i = 1; i <= total; i++) chamadoCom(i, TEL, 60, 1);

  const r = await aplicar();

  assert.equal(r.chamados, total);
  assert.equal(r.mensagens, total);
  assert.equal(e.chamados.length, 0);
  assert.equal(e.mensagens.length, 0);
});

// --- direito à eliminação ------------------------------------------------

test('esquecer titular em simulação conta e não apaga', async () => {
  chamadoCom(1, TEL, 5, 2);
  mensagemSolta(TEL, 5);
  e.sessoes.set(TEL, { telefone: TEL, atualizadoEm: new Date() } as any);

  const n = await esquecerTitular(TEL, false);

  assert.equal(n.chamados, 1);
  assert.equal(n.mensagens, 3);
  assert.equal(n.sessoes, 1);
  assert.equal(e.mensagens.length, 3, 'nada apagado sem --confirmar');
  assert.equal(e.chamados.length, 1);
  assert.equal(e.sessoes.size, 1);
});

test('esquecer titular apaga tudo dele e NADA dos outros', async () => {
  chamadoCom(1, TEL, 5, 3);
  mensagemSolta(TEL, 5);
  e.sessoes.set(TEL, { telefone: TEL, atualizadoEm: new Date() } as any);

  chamadoCom(2, OUTRO, 5, 2);
  mensagemSolta(OUTRO, 5);
  e.sessoes.set(OUTRO, { telefone: OUTRO, atualizadoEm: new Date() } as any);

  const r = await esquecerTitular(TEL, true);

  assert.equal(r.chamados, 1);
  assert.equal(r.mensagens, 4);
  assert.equal(r.sessoes, 1);

  assert.equal(e.chamados.length, 1, 'o chamado do outro titular continua');
  assert.equal(e.chamados[0].telefone, OUTRO);
  assert.equal(e.mensagens.length, 3, 'as mensagens do outro continuam');
  assert.ok(
    e.mensagens.every((m) => m.telefone === OUTRO),
    'não pode sobrar nem uma mensagem do titular que pediu eliminação'
  );
  assert.deepEqual([...e.sessoes.keys()], [OUTRO]);
});

test('esquecer titular ignora o prazo de retenção', async () => {
  // Pedido do titular não espera prazo nenhum: mesmo com a política desligada,
  // e com dado recém-criado, tudo dele sai.
  politica(0, 0);
  chamadoCom(1, TEL, 0, 2);

  const r = await esquecerTitular(TEL, true);

  assert.equal(r.chamados, 1);
  assert.equal(r.mensagens, 2);
  assert.equal(e.mensagens.length, 0);
});

// --- linha de comando ----------------------------------------------------

test('--confirmar só vale quando escrito', () => {
  assert.equal(interpretarArgs([]).confirmar, false);
  assert.equal(interpretarArgs(['--esquecer', TEL]).confirmar, false);
  assert.equal(interpretarArgs(['--confirmar']).confirmar, true);
});

test('interpretarArgs lê o telefone do --esquecer', () => {
  assert.deepEqual(interpretarArgs(['--esquecer', TEL, '--confirmar']), {
    confirmar: true,
    esquecer: true,
    telefone: TEL,
  });
  assert.equal(interpretarArgs(['--esquecer']).telefone, undefined);
});

test('--esquecer com telefone inválido não apaga nada', async () => {
  chamadoCom(1, TEL, 5, 2);
  const exitCodeOriginal = process.exitCode;
  const errOriginal = console.error;
  console.error = () => {};

  try {
    // Sem a validação de telefone, um `--esquecer` sem argumento viraria
    // `telefone === undefined` e um deleteMany com filtro vazio.
    await main(['--esquecer', 'nao-e-telefone', '--confirmar']);
    await main(['--esquecer', '--confirmar']);

    assert.equal(e.chamados.length, 1);
    assert.equal(e.mensagens.length, 2);
    assert.equal(process.exitCode, 1, 'sai com erro para o cron perceber');
  } finally {
    console.error = errOriginal;
    process.exitCode = exitCodeOriginal;
  }
});
