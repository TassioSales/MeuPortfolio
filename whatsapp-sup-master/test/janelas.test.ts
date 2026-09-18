import './env';

import assert from 'node:assert/strict';
import test from 'node:test';

const { janelasEmMemoria, janelasNoRedis } = require('../src/estado/janelas');
const { criarFakeRedis } = require('./fake-redis');

// Estado compartilhado entre instâncias (src/estado/janelas.ts).
//
// O que estes testes cobrem, e o que NÃO cobrem, está dito de forma explícita em
// test/fake-redis.ts: sem um Redis de pé, o que se prova aqui é a semântica das
// operações e o comportamento do fallback — não a atomicidade real do Lua nem a
// expiração pelo relógio do servidor. Esses dois precisam de Redis de verdade.

const JANELA = 60_000;
const T0 = 5_000_000;

// --- memória: o comportamento que o projeto já tinha --------------------------

test('memória: a janela conta a partir da primeira chamada e vira sozinha', async () => {
  const j = janelasEmMemoria();
  assert.equal(await j.incrementar('a', JANELA, T0), 1);
  assert.equal(await j.incrementar('a', JANELA, T0 + 1), 2);
  assert.equal(await j.incrementar('a', JANELA, T0 + 59_999), 3, 'ainda a mesma janela');
  assert.equal(await j.incrementar('a', JANELA, T0 + 60_000), 1, 'janela nova recomeça em 1');
});

test('memória: chaves diferentes não se misturam', async () => {
  const j = janelasEmMemoria();
  for (let i = 0; i < 30; i++) await j.incrementar('a', JANELA, T0);
  assert.equal(await j.incrementar('b', JANELA, T0), 1);
});

test('memória: devolver não estica a janela nem dá crédito à janela seguinte', async () => {
  const j = janelasEmMemoria();
  await j.incrementar('a', JANELA, T0);
  await j.incrementar('a', JANELA, T0);
  await j.devolver('a', JANELA, T0);
  assert.equal(await j.incrementar('a', JANELA, T0), 2, 'a devolução liberou uma');

  // Devolver com a janela já virada é no-op: não pode roubar cota da nova.
  await j.devolver('a', JANELA, T0 + 60_001);
  assert.equal(await j.incrementar('a', JANELA, T0 + 60_001), 1, 'janela nova começa cheia');
});

test('memória: devolver nunca deixa o contador negativo', async () => {
  const j = janelasEmMemoria();
  await j.incrementar('a', JANELA, T0);
  for (let i = 0; i < 5; i++) await j.devolver('a', JANELA, T0);
  assert.equal(await j.incrementar('a', JANELA, T0), 1, 'o contador parou em zero, não em -4');
});

test('memória: reservar é do primeiro, e volta a ser livre quando a janela vira', async () => {
  const j = janelasEmMemoria();
  assert.equal(await j.reservar('a', JANELA, T0), true, 'o primeiro leva');
  assert.equal(await j.reservar('a', JANELA, T0 + 1), false);
  assert.equal(await j.reservar('a', JANELA, T0 + 59_999), false, 'ainda reservada');
  assert.equal(await j.reservar('a', JANELA, T0 + 60_000), true, 'janela nova libera');
});

// --- Redis (contra o dublê) ---------------------------------------------------

test('redis: a chave leva o prefixo configurado', async () => {
  // O prefixo existe porque um Redis gerenciado costuma ser compartilhado: sem
  // ele, dois sistemas que usem o telefone como chave se atropelam.
  const fake = criarFakeRedis();
  const j = janelasNoRedis('', 'wa', fake);
  await j.incrementar('throttle:5511999', JANELA);
  await j.reservar('aviso:5511999', JANELA);
  assert.deepEqual(fake.chaves(), ['wa:aviso:5511999', 'wa:throttle:5511999']);
});

test('redis: incrementar conta e a chave expira pelo prazo da janela', async () => {
  const fake = criarFakeRedis();
  const j = janelasNoRedis('', 'wa', fake);
  assert.equal(await j.incrementar('a', JANELA), 1);
  assert.equal(await j.incrementar('a', JANELA), 2);
  assert.equal(fake.valor('wa:a'), 2);

  fake.agora += JANELA; // o prazo passou
  assert.equal(await j.incrementar('a', JANELA), 1, 'a chave expirou e a contagem recomeçou');
});

test('redis: devolver decrementa sem renovar o prazo', async () => {
  // É a razão de o script usar DECR e não SET: SET renovaria o TTL e a janela
  // nunca fecharia para quem manda mensagem sem parar.
  const fake = criarFakeRedis();
  const j = janelasNoRedis('', 'wa', fake);
  await j.incrementar('a', JANELA);
  await j.incrementar('a', JANELA);
  fake.agora += 30_000; // metade da janela
  await j.devolver('a', JANELA);
  assert.equal(fake.valor('wa:a'), 1);

  fake.agora += 30_000; // completa a janela original
  assert.equal(fake.valor('wa:a'), undefined, 'a devolução não empurrou o prazo para frente');
});

test('redis: devolver em chave ausente não cria nada', async () => {
  const fake = criarFakeRedis();
  const j = janelasNoRedis('', 'wa', fake);
  await j.devolver('a', JANELA);
  assert.deepEqual(fake.chaves(), [], 'nada foi criado por um DECR especulativo');
});

test('redis: reservar é do primeiro (SET NX) e expira pelo prazo', async () => {
  const fake = criarFakeRedis();
  const j = janelasNoRedis('', 'wa', fake);
  assert.equal(await j.reservar('a', 600_000), true);
  assert.equal(await j.reservar('a', 600_000), false, 'NX barrou o segundo');
  fake.agora += 600_000;
  assert.equal(await j.reservar('a', 600_000), true, 'janela nova libera');
});

// --- o que acontece quando o Redis cai ---------------------------------------

test('redis fora do ar: o limite NÃO desliga, cai para memória', async () => {
  // A escolha registrada em src/estado/janelas.ts: fechar descartaria mensagem
  // de gente real em silêncio, abrir removeria o único controle de abuso que
  // existe depois da validação de assinatura. Degradar para "o limite de antes,
  // por instância" é a única opção que não troca um problema por outro pior.
  const fake = criarFakeRedis();
  const j = janelasNoRedis('', 'wa', fake);
  fake.falhar = true;

  assert.equal(await j.incrementar('a', JANELA, T0), 1);
  assert.equal(await j.incrementar('a', JANELA, T0), 2, 'a contagem continua, em memória');
  await j.devolver('a', JANELA, T0);
  assert.equal(await j.incrementar('a', JANELA, T0), 2, 'devolver também funciona no fallback');
  assert.deepEqual(fake.chaves(), [], 'nada chegou ao Redis');
});

test('redis fora do ar: reservar continua limitando (por instância)', async () => {
  const fake = criarFakeRedis();
  const j = janelasNoRedis('', 'wa', fake);
  fake.falhar = true;
  assert.equal(await j.reservar('a', 600_000, T0), true);
  assert.equal(
    await j.reservar('a', 600_000, T0),
    false,
    'o aviso não vira spam por causa da queda'
  );
});

test('redis volta: o comando seguinte já usa o Redis de novo', async () => {
  const fake = criarFakeRedis();
  const j = janelasNoRedis('', 'wa', fake);
  fake.falhar = true;
  await j.incrementar('a', JANELA, T0);
  fake.falhar = false;
  assert.equal(await j.incrementar('a', JANELA, T0), 1, 'o Redis estava vazio: começa em 1');
  assert.equal(fake.valor('wa:a'), 1);
});

// --- as duas implementações precisam concordar --------------------------------

test('memória e Redis dão o mesmo resultado para o mesmo roteiro', async () => {
  // Sem isto, trocar de implementação mudaria o limite efetivo sem ninguém
  // notar — que é exatamente a classe de problema que este módulo existe para
  // resolver. O roteiro usa só o relógio do dublê para os dois lados.
  const roteiro = async (j: any, avancar: (ms: number) => void): Promise<unknown[]> => {
    const saida: unknown[] = [];
    saida.push(await j.incrementar('x', JANELA));
    saida.push(await j.incrementar('x', JANELA));
    saida.push(await j.reservar('y', JANELA));
    saida.push(await j.reservar('y', JANELA));
    await j.devolver('x', JANELA);
    saida.push(await j.incrementar('x', JANELA));
    avancar(JANELA);
    saida.push(await j.incrementar('x', JANELA));
    saida.push(await j.reservar('y', JANELA));
    return saida;
  };

  const fake = criarFakeRedis();
  const noRedis = await roteiro(janelasNoRedis('', 'wa', fake), (ms) => {
    fake.agora += ms;
  });

  // A implementação em memória recebe o tempo por parâmetro, então o "avançar"
  // dela é fechar sobre um relógio próprio.
  let agora = T0;
  const memoria = janelasEmMemoria();
  const envolver = {
    incrementar: (c: string, j: number) => memoria.incrementar(c, j, agora),
    devolver: (c: string, j: number) => memoria.devolver(c, j, agora),
    reservar: (c: string, j: number) => memoria.reservar(c, j, agora),
  };
  const emMemoria = await roteiro(envolver, (ms) => {
    agora += ms;
  });

  assert.deepEqual(emMemoria, noRedis);
});
