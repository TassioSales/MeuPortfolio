import './env';
import assert from 'node:assert/strict';
import test, { after } from 'node:test';
import { Estado, Pessoa, criarFakePrisma } from './fake-prisma';

const dbClient = require('../src/db/client');
const { criarApp } = require('../src/app');

const TOKEN = 'token_interno_de_teste';

const app = criarApp();
after(() => app.close());

function preparar(pessoas: Partial<Pessoa>[] = []): Estado {
  const estado = criarFakePrisma(undefined, [], [], pessoas);
  dbClient.prisma = estado.prisma;
  return estado;
}

/**
 * `oid` de verdade é o GUID que o Entra ID emite. Uso dois formatos reais e
 * distintos porque a cor do perfil é DERIVADA dele: com strings curtas
 * inventadas eu não veria se a derivação é estável de fato.
 */
const OID = '9f8b2c1e-4d3a-4f7b-8e2d-1a5c6b7d8e9f';
const OUTRO_OID = '11223344-5566-7788-99aa-bbccddeeff00';

function registrarIdentidade(corpo: unknown, token: string | null = TOKEN) {
  return app.inject({
    method: 'PUT',
    url: '/internal/pessoas/identidade',
    payload: corpo,
    headers: token === null ? {} : { authorization: `Bearer ${token}` },
  });
}

const listar = () =>
  app.inject({
    method: 'GET',
    url: '/internal/pessoas',
    headers: { authorization: `Bearer ${TOKEN}` },
  });

// --- o primeiro login ----------------------------------------------------

test('primeiro login cria o perfil de quem entrou', async () => {
  const e = preparar();

  const r = await registrarIdentidade({ oid: OID, nome: 'Ana Souza', email: 'ana@empresa.com' });
  assert.equal(r.statusCode, 200);

  const corpo = r.json();
  assert.equal(corpo.nome, 'Ana Souza');
  assert.match(corpo.cor, /^#[0-9A-Fa-f]{6}$/);

  // O banco, e não só a resposta: era exatamente esta asserção que pegou o
  // 409-que-apagava nas dependências.
  assert.equal(e.pessoas.length, 1);
  assert.equal(e.pessoas[0].oid, OID);
  assert.equal(e.pessoas[0].email, 'ana@empresa.com');
});

test('o perfil criado pelo login aparece na listagem do painel', async () => {
  preparar();

  await registrarIdentidade({ oid: OID, nome: 'Ana Souza', email: 'ana@empresa.com' });

  // Este é o teste do problema relatado: dois logins e o modal de Pessoas
  // vazio. Se a listagem não mostrar quem entrou, a correção não corrigiu.
  const { pessoas } = (await listar()).json();
  assert.equal(pessoas.length, 1);
  assert.equal(pessoas[0].nome, 'Ana Souza');
});

test('dois logins de pessoas diferentes viram dois perfis', async () => {
  const e = preparar();

  await registrarIdentidade({ oid: OID, nome: 'Ana Souza', email: 'ana@empresa.com' });
  await registrarIdentidade({ oid: OUTRO_OID, nome: 'Bruno Lima', email: 'bruno@empresa.com' });

  assert.equal(e.pessoas.length, 2);
  const { pessoas } = (await listar()).json();
  assert.deepEqual(
    pessoas.map((p: any) => p.nome),
    ['Ana Souza', 'Bruno Lima']
  );
});

// --- os logins seguintes -------------------------------------------------

test('login repetido NÃO duplica o perfil', async () => {
  const e = preparar();

  const primeiro = await registrarIdentidade({ oid: OID, nome: 'Ana Souza' });
  const segundo = await registrarIdentidade({ oid: OID, nome: 'Ana Souza' });

  // Idempotência não é luxo aqui: isto roda em TODO login, e o painel é usado
  // todos os dias. Sem ela, a lista de pessoas cresceria uma linha por sessão.
  assert.equal(e.pessoas.length, 1);
  assert.equal(primeiro.json().id, segundo.json().id);
});

test('mudança de nome no diretório atualiza o perfil em vez de criar outro', async () => {
  const e = preparar();

  await registrarIdentidade({ oid: OID, nome: 'Ana Souza' });
  const r = await registrarIdentidade({ oid: OID, nome: 'Ana Souza Ribeiro' });

  assert.equal(r.statusCode, 200);
  assert.equal(e.pessoas.length, 1);
  assert.equal(e.pessoas[0].nome, 'Ana Souza Ribeiro');
});

test('a cor escolhida na tela sobrevive ao próximo login', async () => {
  const e = preparar();

  const criada = await registrarIdentidade({ oid: OID, nome: 'Ana Souza' });
  const id = criada.json().id;

  // Alguém troca a cor no modal de Pessoas...
  await app.inject({
    method: 'PATCH',
    url: `/internal/pessoas/${id}`,
    payload: { cor: '#FF8B00' },
    headers: { authorization: `Bearer ${TOKEN}` },
  });

  // ...e entra de novo amanhã. A cor derivada do oid não pode voltar por cima
  // da escolha: por isso ela é gravada na criação, e não recalculada a cada
  // leitura.
  await registrarIdentidade({ oid: OID, nome: 'Ana Souza' });
  assert.equal(e.pessoas[0].cor, '#FF8B00');
});

test('id_token sem nome não apaga o nome ajustado na tela', async () => {
  const e = preparar();

  await registrarIdentidade({ oid: OID, nome: 'Ana Souza' });
  const r = await registrarIdentidade({ oid: OID });

  assert.equal(r.statusCode, 200);
  assert.equal(e.pessoas[0].nome, 'Ana Souza');
});

// --- a adoção do cadastro feito à mão ------------------------------------

test('perfil cadastrado à mão antes do primeiro login é adotado, não duplicado', async () => {
  const e = preparar([{ id: 7, nome: 'Ana Souza', cor: '#5243AA' }]);

  const r = await registrarIdentidade({ oid: OID, nome: 'Ana Souza', email: 'ana@empresa.com' });
  assert.equal(r.statusCode, 200);

  // O caso real: a equipe cadastra as pessoas no painel antes de todos terem
  // entrado. Criar um segundo registro aqui deixaria duas "Ana Souza" na lista
  // e o histórico de chamados preso na primeira.
  assert.equal(e.pessoas.length, 1);
  assert.equal(r.json().id, 7);
  assert.equal(e.pessoas[0].oid, OID);
  assert.equal(e.pessoas[0].email, 'ana@empresa.com');
  // A cor que já estava lá manda: ela pode ter sido escolhida a dedo.
  assert.equal(e.pessoas[0].cor, '#5243AA');
});

test('com DOIS homônimos sem oid não adota nenhum: cria', async () => {
  const e = preparar([
    { id: 1, nome: 'Ana Souza', cor: '#5243AA' },
    { id: 2, nome: 'Ana Souza', cor: '#00875A' },
  ]);

  const r = await registrarIdentidade({ oid: OID, nome: 'Ana Souza' });
  assert.equal(r.statusCode, 200);

  // Adotar um dos dois seria escolher no escuro, e a escolha errada amarraria a
  // identidade de alguém ao perfil de outra pessoa. Três "Ana Souza" na lista é
  // um problema visível, que a equipe resolve apagando; vínculo errado é
  // invisível.
  assert.equal(e.pessoas.length, 3);
  assert.equal(e.pessoas[2].oid, OID);
});

test('homônimo que JÁ tem oid de outra pessoa não é adotado', async () => {
  const e = preparar([{ id: 1, nome: 'Ana Souza', cor: '#5243AA', oid: OUTRO_OID }]);

  await registrarIdentidade({ oid: OID, nome: 'Ana Souza' });

  // Duas pessoas de mesmo nome no diretório existem. Roubar o perfil da
  // primeira daria a uma o histórico da outra.
  assert.equal(e.pessoas.length, 2);
  assert.equal(e.pessoas[0].oid, OUTRO_OID);
  assert.equal(e.pessoas[1].oid, OID);
});

test('nome vazio não adota ninguém pelo nome', async () => {
  const e = preparar([{ id: 1, nome: '', cor: '#5243AA' }]);

  await registrarIdentidade({ oid: OID });

  // Casar por nome vazio adotaria a primeira pessoa que alguém criou no painel
  // e ainda não nomeou - um vínculo tirado do nada.
  assert.equal(e.pessoas.length, 2);
  assert.equal(e.pessoas[0].oid, null);
});

// --- minimização de dado pessoal -----------------------------------------

test('a listagem não leva e-mail nem oid ao navegador', async () => {
  preparar();
  await registrarIdentidade({ oid: OID, nome: 'Ana Souza', email: 'ana@empresa.com' });

  // As duas colunas nasceram para o servidor reconhecer quem entrou, não para
  // a tela mostrar. O painel roda no navegador, e o que ele recebe é o que
  // qualquer aba aberta pode ler.
  const { pessoas } = (await listar()).json();
  assert.equal(pessoas[0].email, undefined, 'e-mail não pode chegar ao painel');
  assert.equal(pessoas[0].oid, undefined, 'oid não pode chegar ao painel');
  assert.deepEqual(Object.keys(pessoas[0]).sort(), ['cor', 'id', 'nome']);
});

test('a rota de identidade também não devolve e-mail nem oid', async () => {
  preparar();
  const r = await registrarIdentidade({ oid: OID, nome: 'Ana Souza', email: 'ana@empresa.com' });
  assert.deepEqual(Object.keys(r.json()).sort(), ['cor', 'id', 'nome']);
});

// --- a cor derivada ------------------------------------------------------

test('a cor derivada do oid é a mesma em qualquer instalação', async () => {
  const primeira = preparar();
  await registrarIdentidade({ oid: OID, nome: 'Ana Souza' });
  const cor = primeira.pessoas[0].cor;

  // Banco novo, mesmo oid: reinstalar não pode trocar a bolha de cor de todo
  // mundo.
  const segunda = preparar();
  await registrarIdentidade({ oid: OID, nome: 'Ana Souza' });
  assert.equal(segunda.pessoas[0].cor, cor);
});

// --- a porta -------------------------------------------------------------

test('sem token a rota de identidade não escreve nada', async () => {
  const e = preparar();

  const r = await registrarIdentidade({ oid: OID, nome: 'Ana Souza' }, null);
  assert.equal(r.statusCode, 401);
  assert.equal(e.pessoas.length, 0);
});

test('sem oid o corpo é recusado', async () => {
  const e = preparar();

  const r = await registrarIdentidade({ nome: 'Ana Souza' });
  assert.equal(r.statusCode, 400);
  assert.equal(e.pessoas.length, 0);
});

test('oid vazio é recusado', async () => {
  const e = preparar();

  // `minLength: 1` no schema: string vazia como chave única casaria com a
  // próxima string vazia e juntaria duas pessoas num só perfil.
  const r = await registrarIdentidade({ oid: '', nome: 'Ana Souza' });
  assert.equal(r.statusCode, 400);
  assert.equal(e.pessoas.length, 0);
});
