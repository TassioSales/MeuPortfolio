import './env';
import assert from 'node:assert/strict';

import test, { beforeEach } from 'node:test';

const { segredoValido, comparacaoSegura } = require('../src/whatsapp/signature');
const { permitirMensagem, devolverMensagem, _resetThrottle } = require('../src/whatsapp/throttle');
const { mascararTelefones, erroSeguro } = require('../src/log');

const SEGREDO = 'segredo_de_teste';

// --- segredo do webhook --------------------------------------------------
//
// Substituiu a validação de assinatura HMAC quando o projeto saiu da Meta para a
// Evolution, que não assina o corpo. O que estes testes cobrem é MENOS do que os
// antigos cobriam, e isso é uma consequência do mecanismo, não um descuido: não
// há como provar integridade do corpo sem assinatura. Ver
// src/whatsapp/signature.ts.

test('o segredo correto é aceito', () => {
  assert.equal(segredoValido(SEGREDO, SEGREDO), true);
});

test('outro segredo é recusado', () => {
  assert.equal(segredoValido('outro_segredo_qualquer', SEGREDO), false);
});

test('segredo ausente, vazio ou de outro tipo é recusado', () => {
  for (const valor of [undefined, '', null, 42, {}, []]) {
    assert.equal(segredoValido(valor, SEGREDO), false, `valor: ${String(valor)}`);
  }
});

test('segredo esperado vazio recusa qualquer coisa', () => {
  // Defesa contra configuração pela metade: se `WEBHOOK_SEGREDO` chegasse vazio,
  // comparar "" com "" liberaria o webhook inteiro. O config.ts já impede subir
  // sem a variável, mas a função é segura por si.
  assert.equal(segredoValido('', ''), false);
  assert.equal(segredoValido('qualquer', ''), false);
});

test('um prefixo do segredo não passa', () => {
  assert.equal(segredoValido(SEGREDO.slice(0, -1), SEGREDO), false);
  assert.equal(segredoValido(SEGREDO + 'a', SEGREDO), false);
});

test('comparacaoSegura não vaza por tamanho diferente', () => {
  assert.equal(comparacaoSegura('abc', 'abc'), true);
  assert.equal(comparacaoSegura('abc', 'abcd'), false);
  assert.equal(comparacaoSegura('', ''), true);
});

// --- limite por telefone -------------------------------------------------

beforeEach(() => _resetThrottle());

// `permitirMensagem` passou a ser assíncrona quando o estado saiu do módulo para
// `src/estado/janelas.ts` (memória por padrão, Redis com REDIS_URL). O `agora`
// explícito continua existindo justamente para estes testes: sem ele, exercitar a
// virada de janela exigiria esperar um minuto de verdade.
test('limite por telefone corta o excesso dentro da janela', async () => {
  const t0 = 5_000_000;
  const limite = Number(process.env.MSGS_POR_MINUTO_POR_TELEFONE ?? 20);

  const permitidas: boolean[] = [];
  for (let i = 0; i < limite + 3; i++) permitidas.push(await permitirMensagem('5511111', t0));
  assert.equal(permitidas.filter(Boolean).length, limite);
  assert.equal(await permitirMensagem('5511111', t0 + 59_000), false, 'ainda na mesma janela');
  assert.equal(await permitirMensagem('5511111', t0 + 60_001), true, 'janela nova libera');
});

test('limite de um telefone não afeta os outros', async () => {
  const t0 = 6_000_000;
  for (let i = 0; i < 50; i++) await permitirMensagem('5511222', t0);
  assert.equal(await permitirMensagem('5511333', t0), true);
});

test('a cota devolvida volta a ficar disponível na mesma janela', async () => {
  // É o caminho da reentrega da Meta: a mensagem descartada como duplicata
  // devolve a cota que consumiu antes de tocar o banco. Sem isso, uma rajada de
  // reentregas comia o limite de quem não mandou nada de novo.
  //
  // A ordem aqui espelha o webhook: `devolverMensagem` só é chamada para uma
  // mensagem que PASSOU pelo limite e depois se revelou duplicata. Mensagem
  // recusada não devolve nada — e, de propósito, continua contando, para quem
  // está em flood não ganhar cota nova no meio da janela.
  const t0 = 7_000_000;
  const limite = Number(process.env.MSGS_POR_MINUTO_POR_TELEFONE ?? 20);

  for (let i = 0; i < limite; i++) {
    assert.equal(await permitirMensagem('5511444', t0), true, `a ${i + 1}ª deveria passar`);
  }

  await devolverMensagem('5511444', t0);
  assert.equal(await permitirMensagem('5511444', t0), true, 'a cota devolvida liberou uma');
  assert.equal(await permitirMensagem('5511444', t0), false, 'e só uma');

  // Devolver depois de a janela virar não pode dar crédito à janela nova.
  await devolverMensagem('5511444', t0 + 60_001);
  const novaJanela: boolean[] = [];
  for (let i = 0; i < limite + 1; i++) {
    novaJanela.push(await permitirMensagem('5511444', t0 + 60_001));
  }
  assert.equal(
    novaJanela.filter(Boolean).length,
    limite,
    'janela nova vale o limite cheio, não mais'
  );
});

// --- logs ----------------------------------------------------------------

test('telefones são mascarados no log', () => {
  assert.equal(mascararTelefones('erro para 5511998877665 agora'), 'erro para ***7665 agora');
  assert.equal(mascararTelefones('sem numero aqui'), 'sem numero aqui');
});

test('erroSeguro reduz o erro e mascara telefone', () => {
  const err = Object.assign(new Error('falhou em 5511998877665'), { code: 'P2002' });
  const saida = erroSeguro(err);

  assert.equal(saida.codigo, 'P2002');
  assert.equal(saida.mensagem.includes('5511998877665'), false);
  assert.match(saida.mensagem, /\*\*\*7665/);
});

test('erroSeguro trunca mensagem gigante', () => {
  const saida = erroSeguro(new Error('x'.repeat(5000)));
  assert.ok(saida.mensagem.length <= 300);
});
