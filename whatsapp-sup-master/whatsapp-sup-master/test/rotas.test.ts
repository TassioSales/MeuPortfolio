import './env';
import assert from 'node:assert/strict';
import test, { after, beforeEach } from 'node:test';
import { Estado, capturarEnvios, criarFakePrisma } from './fake-prisma';

const dbClient = require('../src/db/client');
const { criarApp } = require('../src/app');
const { _resetThrottle } = require('../src/whatsapp/throttle');
const { _resetAvisos } = require('../src/whatsapp/indisponibilidade');

const TEL = '5511998877665';
const OUTRO = '5511900000001';
const SEGREDO = 'segredo_de_teste';
const TOKEN_INTERNO = 'token_interno_de_teste';

const captura = capturarEnvios();
const app = criarApp();

after(() => app.close());

function preparar(sessaoInicial?: any): Estado {
  const estado = criarFakePrisma(sessaoInicial);
  dbClient.prisma = estado.prisma;
  captura.reset();
  return estado;
}

beforeEach(() => {
  _resetThrottle();
  _resetAvisos();
});

/**
 * O segredo vai no CAMINHO, não num cabeçalho.
 *
 * `segredo` undefined usa o certo; passar outro valor exercita a recusa.
 */
function postWebhook(payload: unknown, segredo: string = SEGREDO) {
  return app.inject({
    method: 'POST',
    url: `/webhook/${segredo}`,
    payload: JSON.stringify(payload),
    headers: { 'content-type': 'application/json' },
  });
}

const mensagem = (de: string, id: string, texto = 'oi') => ({
  key: { remoteJid: `${de}@s.whatsapp.net`, fromMe: false, id },
  message: { conversation: texto },
  messageType: 'conversation',
});

const lote = (...mensagens: unknown[]) => ({
  event: 'messages.upsert',
  instance: 'teste',
  data: mensagens,
});

// --- health / ready ------------------------------------------------------

test('/health responde sem tocar o banco', async () => {
  const e = preparar();
  e.bancoFora = true; // não importa: liveness não pergunta pelo banco

  const r = await app.inject({ method: 'GET', url: '/health' });
  assert.equal(r.statusCode, 200);
  assert.deepEqual(r.json(), { status: 'ok' });
});

test('/ready responde 200 com o banco de pé', async () => {
  preparar();
  const r = await app.inject({ method: 'GET', url: '/ready' });
  assert.equal(r.statusCode, 200);
});

test('/ready responde 503 com o banco fora', async () => {
  const e = preparar();
  e.bancoFora = true;

  const r = await app.inject({ method: 'GET', url: '/ready' });
  assert.equal(r.statusCode, 503, 'para o balanceador tirar a instância de rotação');
});

// --- o handshake deixou de existir ---------------------------------------
//
// `GET /webhook` era exigência da Meta ao cadastrar o webhook. A Evolution não
// faz nada equivalente, e a rota foi removida. O teste fixa a REMOÇÃO: se
// alguém a reintroduzir, é sinal de que voltou um caminho de autenticação
// paralelo ao segredo do caminho.

test('GET /webhook não existe mais', async () => {
  preparar();
  const r = await app.inject({ method: 'GET', url: `/webhook/${SEGREDO}` });
  assert.equal(r.statusCode, 404);
});

// --- POST /webhook: o segredo no caminho ---------------------------------

test('webhook sem segredo é recusado antes de tocar a conversa', async () => {
  const e = preparar();
  const r = await postWebhook(lote(mensagem(TEL, 'w1')), '');

  // 404 e não 401: para quem não tem o segredo, a rota não deve nem parecer
  // existir. Com o segredo vazio o caminho vira `/webhook/`, que não casa.
  assert.equal(r.statusCode, 404);
  assert.equal(e.mensagens.length, 0, 'nada chegou na lógica de conversa');
});

test('webhook com outro segredo é recusado', async () => {
  const e = preparar();
  const r = await postWebhook(lote(mensagem(TEL, 'w1')), 'segredo_errado');

  assert.equal(r.statusCode, 404);
  assert.equal(e.mensagens.length, 0);
});

test('webhook com o segredo certo processa e responde 200', async () => {
  const e = preparar();
  const r = await postWebhook(lote(mensagem(TEL, 'w1', 'Natan')));

  assert.equal(r.statusCode, 200);
  assert.ok(e.sessoes.has(TEL), 'a mensagem foi processada');
  assert.equal(e.mensagens.filter((m: any) => m.remetente === 'usuario').length, 1);
});

test('corpo que não é JSON válido recebe 400', async () => {
  preparar();
  const r = await app.inject({
    method: 'POST',
    url: `/webhook/${SEGREDO}`,
    payload: '{isso nao e json',
    headers: { 'content-type': 'application/json' },
  });

  assert.equal(r.statusCode, 400);
});

// --- POST /webhook: uma falha não derruba o lote ------------------------

test('mensagem que estoura não descarta as outras do mesmo lote', async () => {
  const e = preparar();
  e.falharPara.add(OUTRO);

  const r = await postWebhook(
    lote(
      mensagem(TEL, 'w1', 'Natan'),
      mensagem(OUTRO, 'w2'),
      mensagem('5511900000002', 'w3', 'Ana')
    )
  );

  assert.equal(r.statusCode, 200);
  // A Meta não reentrega depois de um 200, então as mensagens seguintes à que
  // falhou precisavam ser processadas nesta mesma passada.
  assert.ok(e.sessoes.has(TEL));
  assert.ok(e.sessoes.has('5511900000002'), 'a mensagem DEPOIS da que falhou foi processada');
  assert.equal(e.sessoes.has(OUTRO), false, 'a que falhou não criou sessão');
});

test('só o telefone que falhou recebe aviso de indisponibilidade', async () => {
  const e = preparar();
  e.falharPara.add(OUTRO);

  await postWebhook(lote(mensagem(TEL, 'w1', 'Natan'), mensagem(OUTRO, 'w2')));

  const avisos = captura.enviados.filter((m: any) => (m.text ?? '').includes('problema técnico'));
  assert.equal(avisos.length, 1);
  assert.equal(avisos[0].number, OUTRO, 'quem foi atendido não pode receber aviso de falha');
});

// --- endpoint interno ---------------------------------------------------

function patch(id: string | number, corpo: unknown, token?: string | null) {
  return app.inject({
    method: 'PATCH',
    url: `/internal/chamados/${id}/situacao`,
    payload: corpo,
    headers: token === null ? {} : { authorization: `Bearer ${token ?? TOKEN_INTERNO}` },
  });
}

function comChamado(): Estado {
  const e = preparar();
  e.chamados.push({
    id: 100,
    nome: 'Natan',
    telefone: TEL,
    resumo: 'Sistema fora',
    descricao: 'Desde as 9h',
    situacao: 'aberto',
    origem: 'whatsapp',
  });
  return e;
}

test('endpoint interno sem token é recusado', async () => {
  comChamado();
  const r = await patch(100, { situacao: 'resolvido' }, null);
  assert.equal(r.statusCode, 401);
});

test('endpoint interno com token errado é recusado', async () => {
  const e = comChamado();
  const r = await patch(100, { situacao: 'resolvido' }, 'token_errado');

  assert.equal(r.statusCode, 401);
  assert.equal(e.chamados[0].situacao, 'aberto', 'nada foi alterado');
});

test('situação fora da lista é recusada', async () => {
  const e = comChamado();
  const r = await patch(100, { situacao: 'inventada' });

  assert.equal(r.statusCode, 400);
  assert.equal(e.chamados[0].situacao, 'aberto');
});

test('id inválido é recusado', async () => {
  comChamado();
  for (const id of ['abc', '0', '-3', '1.5']) {
    const r = await patch(id, { situacao: 'resolvido' });
    assert.equal(r.statusCode, 400, `id ${id} deveria ser recusado`);
  }
});

test('chamado inexistente devolve 404', async () => {
  comChamado();
  const r = await patch(999, { situacao: 'resolvido' });
  assert.equal(r.statusCode, 404);
});

test('mudança de situação sem notificar não manda mensagem', async () => {
  const e = comChamado();
  const r = await patch(100, { situacao: 'em_andamento' });

  assert.equal(r.statusCode, 200);
  const corpo = r.json();
  assert.equal(corpo.id, 100);
  assert.equal(corpo.situacao, 'em_andamento');
  assert.equal(corpo.anterior, 'aberto');
  assert.equal(corpo.notificado, false);

  // Sair de `aberto` é o marco de primeiro atendimento, e ele vai na resposta
  // para o painel atualizar o cartão sem uma segunda ida ao servidor.
  assert.equal(typeof corpo.primeiroAtendimentoEm, 'string');
  assert.equal(corpo.resolvidoEm, null, 'em_andamento não é resolução');

  assert.equal(e.chamados[0].situacao, 'em_andamento');
  assert.equal(captura.enviados.length, 0, 'notificar é opcional e desligado por padrão');
});

test('notificarUsuario grava na outbox e envia', async () => {
  const e = comChamado();
  const r = await patch(100, { situacao: 'resolvido', notificarUsuario: true });

  assert.equal(r.statusCode, 200);
  assert.equal(r.json().notificado, true);

  const saida = e.mensagens.find((m) => m.remetente === 'sistema');
  assert.ok(saida, 'a notificação passa pela outbox, para ser reenviável');
  assert.equal(saida.chamadoId, 100);
  assert.ok(saida.enviadaEm instanceof Date);
  assert.match(captura.ultimoTexto(), /#100 foi marcado como resolvido/);
});

test('notificar situação igual à atual não manda nada', async () => {
  const e = comChamado();
  const r = await patch(100, { situacao: 'aberto', notificarUsuario: true });

  assert.equal(r.statusCode, 200);
  assert.equal(r.json().notificado, false);
  assert.equal(captura.enviados.length, 0);
  assert.equal(e.mensagens.length, 0);
});

test('envio da notificação que falha não desfaz a mudança de situação', async () => {
  const e = comChamado();
  captura.programar(['erro-de-rede', 'erro-de-rede', 'erro-de-rede']);

  const r = await patch(100, { situacao: 'cancelado', notificarUsuario: true });

  assert.equal(r.statusCode, 200);
  assert.equal(r.json().notificado, false);
  assert.equal(e.chamados[0].situacao, 'cancelado', 'a situação persiste');

  const saida = e.mensagens.find((m) => m.remetente === 'sistema');
  assert.equal(saida.enviadaEm, null, 'fica pendente para o varredor');
});

// --- schemas, 404 e cabeçalhos de segurança ------------------------------

test('rota inexistente devolve 404 no formato da casa', async () => {
  preparar();
  const r = await app.inject({ method: 'GET', url: '/wp-login.php' });

  assert.equal(r.statusCode, 404);
  assert.deepEqual(r.json(), { erro: 'rota não encontrada' });
});

test('situação inválida diz qual campo e quais valores são aceitos', async () => {
  comChamado();
  const r = await patch(100, { situacao: 'inventada' });

  assert.equal(r.statusCode, 400);
  const corpo = r.json();
  assert.equal(corpo.erro, 'requisição inválida');
  assert.equal(corpo.detalhes[0].campo, 'situacao');
  // A validação escrita à mão devolvia a lista de aceitas; o schema não pode
  // regredir nisso.
  assert.deepEqual(corpo.detalhes[0].aceitos, [
    'aberto',
    'em_andamento',
    'aguardando_resposta',
    'resolvido',
    'fechado',
    'cancelado',
  ]);
});

test('corpo sem situação é recusado pelo schema', async () => {
  comChamado();
  const r = await patch(100, {});

  assert.equal(r.statusCode, 400);
  assert.equal(r.json().detalhes[0].campo, 'situacao');
});

test('campo desconhecido no corpo é descartado, nunca interpretado', async () => {
  const e = comChamado();
  const r = await patch(100, { situacao: 'resolvido', notificarUsuario: true, inventado: 'x' });

  // `additionalProperties: false` + o `removeAdditional` que o Fastify liga por
  // padrão: o campo estranho é REMOVIDO antes do handler, não recusado. O que
  // este teste fixa é que ele não chega ao handler - o resto do corpo vale.
  assert.equal(r.statusCode, 200);
  assert.equal(e.chamados[0].situacao, 'resolvido');
  assert.equal(r.json().inventado, undefined, 'não volta na resposta serializada');
});

test('sem token, o 401 vem ANTES da validação do corpo', async () => {
  comChamado();
  // Corpo inválido E sem token: se a autenticação rodasse depois da validação,
  // quem não tem token receberia 400 com a lista de situações aceitas de
  // presente.
  const r = await patch('abc', { situacao: 'inventada' }, null);

  assert.equal(r.statusCode, 401);
  assert.deepEqual(r.json(), { erro: 'não autorizado' });
});

test('resposta traz os cabeçalhos de segurança do helmet', async () => {
  preparar();
  const r = await app.inject({ method: 'GET', url: '/health' });

  assert.equal(r.headers['x-content-type-options'], 'nosniff');
  assert.equal(r.headers['content-security-policy'], "default-src 'none';frame-ancestors 'none'");
  assert.equal(r.headers['x-frame-options'], 'SAMEORIGIN');
});

// --- listagem de chamados para o painel ----------------------------------

function listar(query = '', token?: string | null) {
  return app.inject({
    method: 'GET',
    url: `/internal/chamados${query}`,
    headers: token === null ? {} : { authorization: `Bearer ${token ?? TOKEN_INTERNO}` },
  });
}

function comVariosChamados(): Estado {
  const e = preparar();
  // `origem` como o banco: NOT NULL com default. Estes três têm telefone, logo
  // vieram da conversa. Sem o campo, a linha do dublê é uma que o Postgres não
  // conseguiria produzir — e o serializador da resposta reclama, com razão.
  const base = { nome: 'Natan', resumo: 'r', descricao: 'd', origem: 'whatsapp' };
  e.chamados.push(
    {
      id: 1,
      telefone: TEL,
      dataAbertura: new Date('2026-08-01'),
      atualizadoEm: new Date('2026-08-01'),
      situacao: 'aberto',
      ...base,
    },
    {
      id: 2,
      telefone: OUTRO,
      dataAbertura: new Date('2026-08-03'),
      atualizadoEm: new Date('2026-08-03'),
      situacao: 'resolvido',
      ...base,
    },
    {
      id: 3,
      telefone: TEL,
      dataAbertura: new Date('2026-08-02'),
      atualizadoEm: new Date('2026-08-02'),
      situacao: 'aberto',
      ...base,
    }
  );
  return e;
}

test('listagem sem token é recusada', async () => {
  comVariosChamados();
  const r = await listar('', null);
  assert.equal(r.statusCode, 401);
});

test('listagem devolve os chamados sem telefone', async () => {
  comVariosChamados();
  const r = await listar();

  assert.equal(r.statusCode, 200);
  const { chamados } = r.json();
  assert.equal(chamados.length, 3);

  // Minimização de dado pessoal: o painel roda no navegador e não recebe
  // telefone nenhum. Se este teste falhar, vazou dado do titular.
  for (const c of chamados) {
    assert.equal(c.telefone, undefined, 'telefone não pode chegar ao painel');
    assert.equal(typeof c.dataAbertura, 'string', 'data vai como ISO');
  }
});

test('listagem filtra por situação', async () => {
  comVariosChamados();
  const r = await listar('?situacao=aberto');

  assert.equal(r.statusCode, 200);
  const { chamados } = r.json();
  assert.equal(chamados.length, 2);
  assert.ok(chamados.every((c: any) => c.situacao === 'aberto'));
});

test('situação inexistente na listagem é recusada pelo schema', async () => {
  comVariosChamados();
  const r = await listar('?situacao=inventada');
  assert.equal(r.statusCode, 400);
});

test('limite fora da faixa é recusado', async () => {
  comVariosChamados();
  assert.equal((await listar('?limite=0')).statusCode, 400);
  assert.equal((await listar('?limite=501')).statusCode, 400);
  assert.equal((await listar('?limite=10')).statusCode, 200);
});

// --- histórico de mudanças de situação ----------------------------------
//
// Antes, "quem mudou o quê" existia só na linha de log da aplicação: não dava
// para responder a pergunta por chamado, e o registro sumia com o contêiner.

function historico(id: string | number, token?: string | null) {
  return app.inject({
    method: 'GET',
    url: `/internal/chamados/${id}/historico`,
    headers: token === null ? {} : { authorization: `Bearer ${token ?? TOKEN_INTERNO}` },
  });
}

test('mudança de situação registra de/para no histórico', async () => {
  const e = comChamado();

  await patch(100, { situacao: 'em_andamento' });

  assert.equal(e.mudancas.length, 1);
  assert.equal(e.mudancas[0].chamadoId, 100);
  assert.equal(e.mudancas[0].de, 'aberto');
  assert.equal(e.mudancas[0].para, 'em_andamento');
});

test('o autor informado é gravado; sem autor, fica nulo', async () => {
  const e = comChamado();

  await patch(100, { situacao: 'em_andamento', autor: 'Natan' });
  assert.equal(e.mudancas[0].autor, 'Natan');

  await patch(100, { situacao: 'resolvido' });
  assert.equal(e.mudancas[1].autor, null, 'quem não manda autor continua funcionando');
});

test('PATCH que repete a situação atual não vira linha de histórico', async () => {
  const e = comChamado();

  const r = await patch(100, { situacao: 'aberto' });

  assert.equal(r.statusCode, 200);
  assert.equal(e.mudancas.length, 0, 'não houve evento de atendimento');
});

test('autor vazio ou gigante é recusado pelo schema', async () => {
  const e = comChamado();

  assert.equal((await patch(100, { situacao: 'resolvido', autor: '' })).statusCode, 400);
  assert.equal(
    (await patch(100, { situacao: 'resolvido', autor: 'x'.repeat(121) })).statusCode,
    400
  );
  assert.equal(e.mudancas.length, 0, 'nada foi gravado');
});

test('histórico vem do mais novo para o mais velho', async () => {
  const e = comChamado();

  await patch(100, { situacao: 'em_andamento', autor: 'Ana' });
  await patch(100, { situacao: 'resolvido', autor: 'Bruno' });
  // O dublê carimba `criadoEm` com o relógio real; sem separar, as duas linhas
  // podem cair no mesmo milissegundo e a ordenação não provaria nada.
  e.mudancas[0].criadoEm = new Date('2026-01-01T10:00:00Z');
  e.mudancas[1].criadoEm = new Date('2026-01-01T11:00:00Z');

  const r = await historico(100);

  assert.equal(r.statusCode, 200);
  const { chamadoId, mudancas } = r.json();
  assert.equal(chamadoId, 100);
  assert.deepEqual(
    mudancas.map((m: any) => [m.de, m.para, m.autor]),
    [
      ['em_andamento', 'resolvido', 'Bruno'],
      ['aberto', 'em_andamento', 'Ana'],
    ]
  );
});

test('histórico exige token', async () => {
  comChamado();
  assert.equal((await historico(100, null)).statusCode, 401);
  assert.equal((await historico(100, 'token_errado')).statusCode, 401);
});

test('histórico de chamado inexistente é 404, e não lista vazia', async () => {
  comChamado();

  const r = await historico(999);

  // Devolver `mudancas: []` aqui deixaria "não existe" indistinguível de
  // "existe e nunca mudou de situação".
  assert.equal(r.statusCode, 404);
});

test('chamado que existe e nunca mudou devolve histórico vazio', async () => {
  comChamado();

  const r = await historico(100);

  assert.equal(r.statusCode, 200);
  assert.deepEqual(r.json().mudancas, []);
});

test('histórico não devolve telefone', async () => {
  comChamado();
  await patch(100, { situacao: 'resolvido', autor: 'Ana' });

  const r = await historico(100);

  assert.ok(!r.body.includes(TEL), 'minimização: o painel não precisa do telefone');
});

/* ---------- Tarefas criadas no painel ---------------------------------- */

function criarTarefa(corpo: unknown, token?: string | null) {
  return app.inject({
    method: 'POST',
    url: '/internal/tarefas',
    payload: corpo,
    headers: token === null ? {} : { authorization: `Bearer ${token ?? TOKEN_INTERNO}` },
  });
}

const TAREFA = {
  nome: 'Marcos Loja 12',
  resumo: 'Trocar cabo do PDV 3',
  descricao: 'Intermitente',
};

test('criar tarefa sem token é recusado', async () => {
  preparar();
  const r = await criarTarefa(TAREFA, null);
  assert.equal(r.statusCode, 401);
});

test('tarefa nasce no painel, aberta, sem telefone', async () => {
  const e = preparar();
  const r = await criarTarefa(TAREFA);
  assert.equal(r.statusCode, 201, r.body);

  const corpo = r.json();
  assert.equal(corpo.situacao, 'aberto');
  assert.equal(corpo.origem, 'painel');

  assert.equal(e.chamados.length, 1);
  const gravado = e.chamados[0];
  assert.equal(gravado.resumo, TAREFA.resumo);
  assert.equal(gravado.nome, TAREFA.nome);
  assert.equal(gravado.origem, 'painel');
  // Nem string vazia, nem sentinela: a coluna é nula, e é isso que a distingue
  // de um chamado de conversa para a retenção e para `esquecerTitular`.
  assert.equal(gravado.telefone, undefined);
});

test('regressão: criar tarefa NÃO gera log de conversa', async () => {
  // É o requisito central da feature. Tarefa não tem telefone, então não existe
  // de quem receber nem a quem enviar - nada em `Mensagem`, nada em sessão.
  const e = preparar();
  assert.equal((await criarTarefa(TAREFA)).statusCode, 201);
  assert.equal(e.mensagens.length, 0, 'tarefa não pode criar linha em Mensagem');
  assert.equal(e.sessoes.size, 0, 'tarefa não pode abrir sessão de conversa');
  assert.equal(captura.enviados.length, 0, 'e nada pode ir para a Graph API');
});

test('a origem não pode ser forjada pelo corpo', async () => {
  // `origem` é fixada na rota, nunca lida do corpo. Se um dia vier de fora, uma
  // tarefa poderia se apresentar como vinda de conversa - e passaria a contar
  // como dado de titular para a retenção e para `esquecerTitular`.
  //
  // O ajv do Fastify vem com `removeAdditional`, então `additionalProperties:
  // false` REMOVE o campo extra em vez de responder 400. O efeito prático é o
  // mesmo e é o que este teste fixa: o campo forjado não chega ao handler e não
  // encosta no banco. Vale saber qual dos dois é, porque um dia alguém vai
  // escrever um cliente contando com o 400 que não vem.
  const e = preparar();
  const r = await criarTarefa({ ...TAREFA, origem: 'whatsapp', telefone: '5511999999999' });
  assert.equal(r.statusCode, 201, r.body);
  assert.equal(r.json().origem, 'painel', 'a origem do corpo foi ignorada');
  assert.equal(e.chamados[0].origem, 'painel');
  assert.equal(e.chamados[0].telefone, undefined, 'e o telefone forjado não foi gravado');
});

test('tarefa recusa campo curto, campo só de espaços e campo longo', async () => {
  const e = preparar();
  assert.equal((await criarTarefa({ ...TAREFA, resumo: 'x' })).statusCode, 400, 'curto');
  // `minLength` conta caracteres crus, então isto passa pelo schema e tem de
  // morrer no trim do handler.
  assert.equal((await criarTarefa({ ...TAREFA, resumo: '     ' })).statusCode, 400, 'só espaços');
  assert.equal(
    (await criarTarefa({ ...TAREFA, resumo: 'x'.repeat(201) })).statusCode,
    400,
    'acima do LIMITES.resumo do fluxo de conversa'
  );
  assert.equal(
    (await criarTarefa({ nome: 'a b', resumo: 'r r' })).statusCode,
    400,
    'sem descricao'
  );
  assert.equal(e.chamados.length, 0, 'nenhuma recusa pode ter gravado');
});

test('a tarefa aparece na listagem, com origem e sem telefone', async () => {
  const e = preparar();
  await criarTarefa(TAREFA);
  // A listagem serializa datas; o dublê não aplica default de coluna de data.
  e.chamados[0].dataAbertura = new Date('2026-08-27');
  e.chamados[0].atualizadoEm = new Date('2026-08-27');

  const r = await listar();
  assert.equal(r.statusCode, 200, r.body);
  const [cartao] = r.json().chamados;
  assert.equal(cartao.origem, 'painel');
  assert.equal(cartao.resumo, TAREFA.resumo);
  assert.equal(cartao.telefone, undefined, 'telefone nunca entra na resposta');
});

test('regressão: mover tarefa com notificarUsuario NÃO gera log de conversa', async () => {
  // O outro caminho que grava em `Mensagem`: a linha de saída do aviso. Um
  // atendente com "avisar" ligado move a tarefa e o aviso não pode ser tentado -
  // mas a situação tem de mudar, senão ele não consegue mover tarefa nenhuma.
  const e = preparar();
  const id = (await criarTarefa(TAREFA)).json().id;

  const r = await patch(id, { situacao: 'resolvido', notificarUsuario: true, autor: 'Ana' });
  assert.equal(r.statusCode, 200, r.body);
  assert.equal(r.json().notificado, false, 'não havia a quem notificar');
  assert.equal(r.json().situacao, 'resolvido', 'e a situação mudou de qualquer forma');

  assert.equal(e.mensagens.length, 0, 'nenhuma linha de saída pode ter sido criada');
  assert.equal(captura.enviados.length, 0);
  assert.equal(e.chamados[0].situacao, 'resolvido');
});

test('a auditoria de tarefa funciona igual à de chamado', async () => {
  // `MudancaSituacao` não depende de telefone: o histórico vale para tarefa.
  const e = preparar();
  const id = (await criarTarefa(TAREFA)).json().id;
  await patch(id, { situacao: 'em_andamento', autor: 'Ana' });

  assert.equal(e.mudancas.length, 1);
  assert.equal(e.mudancas[0].de, 'aberto');
  assert.equal(e.mudancas[0].para, 'em_andamento');
  assert.equal(e.mudancas[0].autor, 'Ana');
});
