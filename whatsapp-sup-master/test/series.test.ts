import './env';
import assert from 'node:assert/strict';
import test, { after } from 'node:test';
import { Estado, criarFakePrisma } from './fake-prisma';

const dbClient = require('../src/db/client');
const { criarApp } = require('../src/app');

const TOKEN = 'token_interno_de_teste';

const app = criarApp();
after(() => app.close());

/**
 * Série temporal do dashboard.
 *
 * O que estes testes vigiam não é "a rota responde 200": é que os números
 * DERIVADOS estejam certos. A curva da fila e os baldes por fuso são
 * reconstruções, e reconstrução errada não quebra nada — devolve um gráfico
 * plausível com o número errado, que é o pior desfecho possível para um painel
 * de gestão.
 */

// UTC-3, o fuso do escritório, no formato que o navegador produz
// (`getTimezoneOffset()` devolve 180 em UTC-3).
const TZ = 180;

function preparar(setores: Array<{ id: number; codigo: string; nome: string }> = []): Estado {
  const estado = criarFakePrisma(undefined, [], setores);
  dbClient.prisma = estado.prisma;
  return estado;
}

const BASE = {
  nome: 'Natan',
  resumo: 'r',
  descricao: 'd',
  origem: 'whatsapp',
  telefone: '5511999999999',
  categoriaId: null,
  setorId: null,
  responsavelId: null,
  tipo: null,
  primeiroAtendimentoEm: null,
  resolvidoEm: null,
  prazoEm: null,
  avaliacaoNota: null,
};

let proximoId = 1;

function chamado(e: Estado, dados: Record<string, unknown>): number {
  const id = proximoId++;
  const abertura = dados.dataAbertura as Date;
  e.chamados.push({
    id,
    ...BASE,
    situacao: 'aberto',
    atualizadoEm: abertura,
    ...dados,
  });
  return id;
}

function mudanca(e: Estado, chamadoId: number, de: string, para: string, em: Date) {
  e.mudancas.push({ id: e.mudancas.length + 1, chamadoId, de, para, autor: null, criadoEm: em });
  const c = e.chamados.find((x) => x.id === chamadoId);
  // O banco real move `atualizadoEm` a cada escrita; o dublê não tem
  // `@updatedAt`, então quem semeia a mudança acerta as duas pontas. Sem isso a
  // transição sintética da rota entraria em cena por engano.
  if (c && em > c.atualizadoEm) c.atualizadoEm = em;
}

function mensagem(e: Estado, dados: Record<string, unknown>) {
  e.mensagens.push({
    id: e.mensagens.length + 1,
    telefone: '5511999999999',
    chamadoId: null,
    texto: 't',
    whatsappMessageId: null,
    payload: null,
    enviadaEm: null,
    tentativas: 0,
    ultimaTentativaEm: null,
    ...dados,
  });
}

function buscar(query: string, token: string | null = TOKEN) {
  return app.inject({
    method: 'GET',
    url: '/internal/series' + query,
    headers: token === null ? {} : { authorization: `Bearer ${token}` },
  });
}

/** A janela de uma semana de agosto de 2026, em UTC-3, baldeada por dia. */
const SEMANA = `?desde=2026-08-03T03:00:00.000Z&ate=2026-08-10T03:00:00.000Z&balde=dia&tz=${TZ}`;

// --- baldes e fuso -------------------------------------------------------

test('os baldes de dia começam à meia-noite LOCAL, não à meia-noite UTC', async () => {
  preparar();

  const r = await buscar(SEMANA);
  assert.equal(r.statusCode, 200);
  const { baldes, janela } = r.json();

  assert.equal(janela.balde, 'dia');
  assert.equal(baldes.length, 7);
  // 03:00Z é meia-noite em UTC-3. Se o corte fosse em UTC, o primeiro balde
  // começaria em 00:00Z e o gráfico inteiro ficaria três horas deslocado.
  for (const b of baldes) {
    assert.ok(b.inicio.endsWith('T03:00:00.000Z'), `balde fora da meia-noite local: ${b.inicio}`);
  }
});

test('chamado aberto às 21h locais cai no dia LOCAL, não no seguinte', async () => {
  const e = preparar();
  // 2026-08-04T00:30:00Z = 2026-08-03 21:30 em UTC-3. É dia 3, não dia 4.
  chamado(e, { dataAbertura: new Date('2026-08-04T00:30:00.000Z') });

  const { baldes } = (await buscar(SEMANA)).json();
  assert.equal(baldes[0].inicio, '2026-08-03T03:00:00.000Z');
  assert.equal(baldes[0].aberturas, 1, 'a abertura das 21h30 foi para o dia errado');
  assert.equal(baldes[1].aberturas, 0);
});

test('sem balde pedido, a janela escolhe a resolução', async () => {
  preparar();

  const doisDias = await buscar(
    `?desde=2026-08-08T03:00:00.000Z&ate=2026-08-10T03:00:00.000Z&tz=${TZ}`
  );
  assert.equal(doisDias.json().janela.balde, 'hora');

  const umMes = await buscar(
    `?desde=2026-07-11T03:00:00.000Z&ate=2026-08-10T03:00:00.000Z&tz=${TZ}`
  );
  assert.equal(umMes.json().janela.balde, 'dia');

  const umAno = await buscar(
    `?desde=2025-08-10T03:00:00.000Z&ate=2026-08-10T03:00:00.000Z&tz=${TZ}`
  );
  assert.equal(umAno.json().janela.balde, 'semana');
});

// --- a curva da fila -----------------------------------------------------

test('a fila de cada dia conta quem ainda estava aberto no FIM do dia', async () => {
  const e = preparar();
  // Abre na terça (dia 4), resolve na quinta (dia 6).
  const id = chamado(e, { dataAbertura: new Date('2026-08-04T12:00:00.000Z') });
  mudanca(e, id, 'aberto', 'resolvido', new Date('2026-08-06T12:00:00.000Z'));
  const c = e.chamados.find((x) => x.id === id)!;
  c.situacao = 'resolvido';
  c.resolvidoEm = new Date('2026-08-06T12:00:00.000Z');

  const { baldes } = (await buscar(SEMANA)).json();
  const fila = baldes.map((b: any) => b.filaFim);

  // seg  ter  qua  qui  sex  sab  dom
  assert.deepEqual(fila, [0, 1, 1, 0, 0, 0, 0]);
  assert.equal(baldes[1].aberturas, 1);
  assert.equal(baldes[3].resolucoes, 1);
  assert.equal(baldes[3].saidas, 1);
});

test('aberto e resolvido no mesmo dia não sobra na fila daquele dia', async () => {
  const e = preparar();
  const id = chamado(e, { dataAbertura: new Date('2026-08-04T12:00:00.000Z') });
  mudanca(e, id, 'aberto', 'resolvido', new Date('2026-08-04T16:00:00.000Z'));
  const c = e.chamados.find((x) => x.id === id)!;
  c.situacao = 'resolvido';
  c.resolvidoEm = new Date('2026-08-04T16:00:00.000Z');

  const { baldes } = (await buscar(SEMANA)).json();
  // A curva responde "quanto sobrou de trabalho no fim do dia". Este chamado
  // não sobrou — mas a abertura e a resolução dele contam, cada uma no seu
  // lugar. Somar ele na fila faria o dia parecer pior do que foi.
  assert.equal(baldes[1].filaFim, 0);
  assert.equal(baldes[1].aberturas, 1);
  assert.equal(baldes[1].resolucoes, 1);
});

test('a fila se decompõe por situação e as partes somam o total', async () => {
  const e = preparar();
  const a = chamado(e, { dataAbertura: new Date('2026-08-04T10:00:00.000Z') });
  const b = chamado(e, { dataAbertura: new Date('2026-08-04T10:00:00.000Z') });
  chamado(e, { dataAbertura: new Date('2026-08-04T10:00:00.000Z') });

  mudanca(e, a, 'aberto', 'em_andamento', new Date('2026-08-04T11:00:00.000Z'));
  e.chamados.find((x) => x.id === a)!.situacao = 'em_andamento';
  mudanca(e, b, 'aberto', 'aguardando_resposta', new Date('2026-08-04T11:00:00.000Z'));
  e.chamados.find((x) => x.id === b)!.situacao = 'aguardando_resposta';

  const { baldes } = (await buscar(SEMANA)).json();
  const t = baldes[1];
  assert.equal(t.filaAberto, 1);
  assert.equal(t.filaEmAndamento, 1);
  assert.equal(t.filaAguardando, 1);
  assert.equal(t.filaFim, 3, 'o total da fila tem de bater com a soma das partes');
});

test('reabertura volta para a fila e é contada', async () => {
  const e = preparar();
  const id = chamado(e, { dataAbertura: new Date('2026-08-04T10:00:00.000Z') });
  mudanca(e, id, 'aberto', 'resolvido', new Date('2026-08-05T10:00:00.000Z'));
  mudanca(e, id, 'resolvido', 'em_andamento', new Date('2026-08-07T10:00:00.000Z'));
  e.chamados.find((x) => x.id === id)!.situacao = 'em_andamento';

  const { baldes } = (await buscar(SEMANA)).json();

  // ter: na fila. qua: saiu. qui: ainda fora. sex: voltou.
  assert.deepEqual(
    baldes.map((b: any) => b.filaFim),
    [0, 1, 0, 0, 1, 1, 1]
  );
  assert.equal(baldes[4].reaberturas, 1);
  // A reabertura NÃO é uma abertura: o chamado não é novo, e somar os dois
  // inflaria a taxa de entrada de quem só reabriu chamado antigo.
  assert.equal(baldes[4].aberturas, 0);
});

test('cancelamento sai da fila mas não conta como resolução', async () => {
  const e = preparar();
  const id = chamado(e, { dataAbertura: new Date('2026-08-04T10:00:00.000Z') });
  mudanca(e, id, 'aberto', 'cancelado', new Date('2026-08-05T10:00:00.000Z'));
  e.chamados.find((x) => x.id === id)!.situacao = 'cancelado';

  const { baldes } = (await buscar(SEMANA)).json();
  assert.equal(baldes[2].saidas, 1, 'cancelar tira da fila');
  assert.equal(baldes[2].cancelamentos, 1);
  assert.equal(baldes[2].resolucoes, 0, 'cancelar não resolve nada');
  assert.equal(baldes[2].filaFim, 0);
});

test('chamado encerrado SEM histórico de mudança não fica preso na fila', async () => {
  const e = preparar();
  // O caso real: linha alterada por SQL, ou anterior à tabela de auditoria.
  // Sem tratamento, a linha do tempo diria "aberto para sempre" e a fila
  // cresceria sozinha na tela.
  chamado(e, {
    dataAbertura: new Date('2026-08-04T10:00:00.000Z'),
    situacao: 'fechado',
    atualizadoEm: new Date('2026-08-05T10:00:00.000Z'),
  });

  const { baldes, agora } = (await buscar(SEMANA)).json();
  assert.deepEqual(
    baldes.map((b: any) => b.filaFim),
    [0, 1, 0, 0, 0, 0, 0]
  );
  // A transição sintética conta como saída, no `atualizadoEm` — a melhor data
  // disponível para "quando isso mudou".
  assert.equal(baldes[2].saidas, 1);
  assert.equal(agora.fila, 0);
});

test('chamado aberto ANTES da janela já entra na fila do primeiro dia', async () => {
  const e = preparar();
  chamado(e, { dataAbertura: new Date('2026-07-20T10:00:00.000Z') });

  const { baldes } = (await buscar(SEMANA)).json();
  // A curva é de ESTOQUE, não de eventos da janela: quem já estava na fila
  // continua nela. Contar só as aberturas do período faria a fila começar em
  // zero em toda troca de período.
  assert.equal(baldes[0].filaFim, 1);
  assert.equal(baldes[0].aberturas, 0, 'a abertura ficou fora da janela');
});

// --- tempos --------------------------------------------------------------

test('as durações caem no balde do MARCO, não no da abertura', async () => {
  const e = preparar();
  // Abre na segunda, é atendido na quarta: os 2 dias de espera pertencem à
  // quarta, que é quando o atendimento aconteceu.
  chamado(e, {
    dataAbertura: new Date('2026-08-03T12:00:00.000Z'),
    primeiroAtendimentoEm: new Date('2026-08-05T12:00:00.000Z'),
  });

  const { baldes } = (await buscar(SEMANA)).json();
  assert.equal(baldes[0].atendimentoN, 0);
  assert.equal(baldes[2].atendimentoN, 1);
  assert.equal(baldes[2].atendimentoP50, 2 * 24 * 60);
});

test('p50 e p90 saem por posto, sem inventar valor intermediário', async () => {
  const e = preparar();
  const dia = new Date('2026-08-04T09:00:00.000Z');
  // Dez atendimentos, de 10 a 100 minutos.
  for (let i = 1; i <= 10; i++) {
    chamado(e, {
      dataAbertura: dia,
      primeiroAtendimentoEm: new Date(+dia + i * 10 * 60_000),
    });
  }

  const { baldes, desempenho } = (await buscar(SEMANA)).json();
  const b = baldes[1];
  assert.equal(b.atendimentoN, 10);
  // Todo valor devolvido é a duração de um chamado que existe: 50 e 90 estão
  // na amostra, 55 (a interpolação) não estaria.
  assert.equal(b.atendimentoP50, 50);
  assert.equal(b.atendimentoP90, 90);
  assert.equal(desempenho.atendimento.media, 55);
});

test('balde sem amostra devolve nulo, e não zero', async () => {
  preparar();
  const { baldes } = (await buscar(SEMANA)).json();
  // Zero minutos e "não houve atendimento" são coisas diferentes, e um gráfico
  // que desenhe 0 para o segundo caso mostra uma queda que não aconteceu.
  assert.equal(baldes[0].atendimentoP50, null);
  assert.equal(baldes[0].atendimentoN, 0);
});

// --- prazo e avaliação ---------------------------------------------------

test('cumprimento de prazo separa dentro, fora e sem prazo', async () => {
  const e = preparar();
  const abertura = new Date('2026-08-04T09:00:00.000Z');

  chamado(e, {
    dataAbertura: abertura,
    resolvidoEm: new Date('2026-08-04T10:00:00.000Z'),
    prazoEm: new Date('2026-08-04T12:00:00.000Z'),
    situacao: 'resolvido',
  });
  chamado(e, {
    dataAbertura: abertura,
    resolvidoEm: new Date('2026-08-04T18:00:00.000Z'),
    prazoEm: new Date('2026-08-04T12:00:00.000Z'),
    situacao: 'resolvido',
  });
  chamado(e, {
    dataAbertura: abertura,
    resolvidoEm: new Date('2026-08-04T18:00:00.000Z'),
    situacao: 'resolvido',
  });

  const { desempenho } = (await buscar(SEMANA)).json();
  assert.deepEqual(desempenho.prazo, { dentro: 1, fora: 1, semPrazo: 1 });
});

test('chamado com prazo e ainda NÃO resolvido não conta como fora do prazo', async () => {
  const e = preparar();
  chamado(e, {
    dataAbertura: new Date('2026-08-04T09:00:00.000Z'),
    prazoEm: new Date('2026-08-04T12:00:00.000Z'),
  });

  const { desempenho } = (await buscar(SEMANA)).json();
  // Ele está vencido - e aparece em `agora.vencidos`. Mas cumprimento de prazo
  // é uma conta sobre trabalho TERMINADO: incluí-lo aqui misturaria "não
  // entregamos a tempo" com "ainda não entregamos".
  assert.deepEqual(desempenho.prazo, { dentro: 0, fora: 0, semPrazo: 0 });
});

test('a avaliação traz média, amostra e distribuição', async () => {
  const e = preparar();
  const abertura = new Date('2026-08-04T09:00:00.000Z');
  for (const nota of [5, 5, 4, 3, 1]) {
    chamado(e, { dataAbertura: abertura, avaliacaoNota: nota, situacao: 'fechado' });
  }

  const { desempenho } = (await buscar(SEMANA)).json();
  assert.equal(desempenho.avaliacao.n, 5);
  assert.equal(desempenho.avaliacao.media, 3.6);
  // A distribuição existe porque a média esconde a forma: 3,6 pode ser "todos
  // deram 4" ou "metade deu 5 e um deu 1", e as duas pedem reação diferente.
  assert.deepEqual(desempenho.avaliacao.distribuicao, [1, 0, 1, 1, 2]);
});

// --- o instante presente -------------------------------------------------

test('agora separa fila, sem responsável, sem primeiro atendimento e vencidos', async () => {
  const e = preparar();
  const passado = new Date(Date.now() - 5 * 24 * 3600_000);

  // Na fila, sem responsável, sem atendimento, com prazo estourado.
  chamado(e, { dataAbertura: passado, prazoEm: new Date(Date.now() - 3600_000) });
  // Na fila, com responsável e já atendido, prazo folgado.
  chamado(e, {
    dataAbertura: passado,
    responsavelId: 7,
    primeiroAtendimentoEm: passado,
    prazoEm: new Date(Date.now() + 10 * 24 * 3600_000),
    situacao: 'em_andamento',
  });
  // Vence dentro de 24h.
  chamado(e, { dataAbertura: passado, prazoEm: new Date(Date.now() + 3600_000) });
  // Fora da fila: não pode entrar em nenhuma das contagens de agora.
  chamado(e, { dataAbertura: passado, situacao: 'fechado', atualizadoEm: passado });

  const janela = `?desde=${new Date(Date.now() - 7 * 24 * 3600_000).toISOString()}&balde=dia&tz=${TZ}`;
  const { agora } = (await buscar(janela)).json();

  assert.equal(agora.fila, 3);
  assert.equal(agora.aguardandoPrimeiro, 2);
  assert.equal(agora.semResponsavel, 2);
  assert.equal(agora.vencidos, 1);
  assert.equal(agora.venceEm24h, 1);
  assert.equal(agora.porSituacao.aberto, 2);
  assert.equal(agora.porSituacao.em_andamento, 1);
  assert.equal(agora.porSituacao.fechado, 1);
});

// --- mensagens e fila de envio -------------------------------------------

test('mensagens recebidas e enviadas contam por balde, cada uma pela sua data', async () => {
  const e = preparar();
  mensagem(e, { remetente: 'usuario', timestamp: new Date('2026-08-04T10:00:00.000Z') });
  mensagem(e, { remetente: 'usuario', timestamp: new Date('2026-08-04T11:00:00.000Z') });
  // Nasceu na terça e só saiu na quarta: a saída pertence à quarta, porque a
  // pergunta é "quantas o bot ENTREGOU nesse dia".
  mensagem(e, {
    remetente: 'sistema',
    timestamp: new Date('2026-08-04T23:00:00.000Z'),
    enviadaEm: new Date('2026-08-05T10:00:00.000Z'),
  });

  const { baldes } = (await buscar(SEMANA)).json();
  assert.equal(baldes[1].recebidas, 2);
  assert.equal(baldes[1].enviadas, 0);
  assert.equal(baldes[2].enviadas, 1);
});

test('a fila de envio é reconstruída: pendente enquanto não saiu', async () => {
  const e = preparar();
  // Nasceu antes da janela e saiu na quarta: fica pendente na segunda e na
  // terça, e some depois. Um `where` que só olhasse a janela perderia esta
  // linha e a curva começaria em zero.
  mensagem(e, {
    remetente: 'sistema',
    timestamp: new Date('2026-08-01T10:00:00.000Z'),
    enviadaEm: new Date('2026-08-05T10:00:00.000Z'),
  });
  // Nunca saiu: pendente até o fim.
  mensagem(e, {
    remetente: 'sistema',
    timestamp: new Date('2026-08-06T10:00:00.000Z'),
    enviadaEm: null,
    tentativas: 4,
  });

  const { baldes, agora } = (await buscar(SEMANA)).json();
  assert.deepEqual(
    baldes.map((b: any) => b.envioPendenteFim),
    [1, 1, 0, 1, 1, 1, 1]
  );
  assert.equal(agora.envioPendente, 1);
  // Uma tentativa é o normal - a primeira. Da segunda em diante houve falha, e
  // é só isso que este número precisa acusar.
  assert.equal(agora.envioComFalha, 1);
});

test('mensagem com uma única tentativa não conta como falha de envio', async () => {
  const e = preparar();
  mensagem(e, {
    remetente: 'sistema',
    timestamp: new Date('2026-08-06T10:00:00.000Z'),
    enviadaEm: null,
    tentativas: 1,
  });

  const { agora } = (await buscar(SEMANA)).json();
  assert.equal(agora.envioPendente, 1);
  assert.equal(agora.envioComFalha, 0);
});

// --- por setor -----------------------------------------------------------

test('a tabela por setor ordena pela fila e nomeia o que não tem setor', async () => {
  const e = preparar([
    { id: 1, codigo: 'ti', nome: 'TI' },
    { id: 2, codigo: 'fin', nome: 'Financeiro' },
  ]);
  const abertura = new Date('2026-08-04T09:00:00.000Z');

  chamado(e, { dataAbertura: abertura, setorId: 1 });
  chamado(e, { dataAbertura: abertura, setorId: 1 });
  chamado(e, { dataAbertura: abertura, setorId: 2 });
  chamado(e, { dataAbertura: abertura, setorId: null });

  const { porSetor } = (await buscar(SEMANA)).json();
  assert.deepEqual(
    porSetor.map((s: any) => [s.rotulo, s.fila]),
    [
      ['TI', 2],
      ['Financeiro', 1],
      ['Sem setor', 1],
    ]
  );
  // "Sem setor" é uma linha e não um descarte: chamado sem classificação
  // continua sendo atendimento, e some-lo faria a tabela não bater com o total.
  assert.equal(porSetor[2].codigo, 'sem_setor');
  assert.equal(porSetor[2].id, null);
});

// --- o portão e os limites ----------------------------------------------

test('sem token a série não é servida', async () => {
  preparar();
  const r = await buscar(SEMANA, null);
  assert.equal(r.statusCode, 401);
});

test('data inválida é recusada com 400', async () => {
  preparar();
  const r = await buscar('?desde=ontem&balde=dia');
  assert.equal(r.statusCode, 400);
  assert.match(r.json().erro, /desde/);
});

test('janela invertida é recusada com 400', async () => {
  preparar();
  const r = await buscar('?desde=2026-08-10T00:00:00.000Z&ate=2026-08-03T00:00:00.000Z');
  assert.equal(r.statusCode, 400);
});

test('balde fora da lista é recusado pelo schema', async () => {
  preparar();
  const r = await buscar('?balde=decada');
  assert.equal(r.statusCode, 400);
});

test('banco vazio devolve baldes zerados, e não erro', async () => {
  preparar();
  const r = await buscar(SEMANA);
  assert.equal(r.statusCode, 200);

  const { baldes, agora, desempenho, porSetor } = r.json();
  // Painel novo, sem chamado nenhum, é o primeiro estado que qualquer
  // instalação atravessa: ele tem de desenhar o eixo vazio em vez de falhar.
  assert.equal(baldes.length, 7);
  assert.ok(baldes.every((b: any) => b.aberturas === 0 && b.filaFim === 0));
  assert.equal(agora.fila, 0);
  assert.equal(desempenho.atendimento.p50, null);
  assert.deepEqual(porSetor, []);
});

test('regressão: o último balde de uma janela até agora não zera a fila', async () => {
  const e = preparar();
  chamado(e, { dataAbertura: new Date(Date.now() - 3 * 24 * 3600_000) });
  chamado(e, { dataAbertura: new Date(Date.now() - 2 * 24 * 3600_000) });

  const { baldes, agora } = (
    await buscar(
      `?desde=${new Date(Date.now() - 7 * 24 * 3600_000).toISOString()}&balde=dia&tz=${TZ}`
    )
  ).json();

  // O trecho ainda aberto do chamado tem de ficar SEM fim, e não terminar em
  // `agora`: o fim do último balde vale exatamente `agora` numa janela até
  // agora, e o intervalo é meio-aberto - por meio instante a curva despencava
  // para zero no último ponto enquanto `agora.fila` dizia o contrário. Foi
  // visto na tela antes de ser visto aqui.
  const ultimo = baldes[baldes.length - 1];
  assert.equal(ultimo.filaFim, 2);
  assert.equal(
    ultimo.filaFim,
    agora.fila,
    'o último ponto da curva tem de bater com a fila do instante presente'
  );
});
