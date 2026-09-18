import './env';
import assert from 'node:assert/strict';
import test, { after, beforeEach } from 'node:test';
import { Categoria, Estado, Pessoa, Setor, capturarEnvios, criarFakePrisma } from './fake-prisma';

const dbClient = require('../src/db/client');
const { criarApp } = require('../src/app');
const { _resetThrottle } = require('../src/whatsapp/throttle');

const TOKEN = 'token_interno_de_teste';
const TEL = '5511998877665';

/**
 * Os campos de separação e classificação de chamado: setores, tipo (interno x
 * franquia), prioridade, prazo, canal, avaliação pós-fechamento, etiquetas
 * livres, comentários, anexos e dependência entre chamados.
 *
 * Arquivo próprio, e não mais um bloco em `rotas.test.ts`, pela mesma razão que
 * `internal/setores.ts` e `internal/detalhes.ts` são módulos próprios: são rotas
 * novas com regras próprias, e enfiá-las num arquivo de 700 linhas faria o
 * conjunto perder a divisão que o servidor tem.
 */

const captura = capturarEnvios();
const app = criarApp();

after(() => app.close());
beforeEach(() => _resetThrottle());

const ASSUNTOS: Partial<Categoria>[] = [
  { id: 1, codigo: 'sistema_vetor', nome: 'SISTEMA VETOR', rotulo: 'SUPORTE AO SISTEMA VETOR' },
];

const SETORES: Partial<Setor>[] = [
  { id: 1, codigo: 'ti', nome: 'TI', ordem: 1 },
  { id: 2, codigo: 'financeiro', nome: 'Financeiro', ordem: 2 },
  { id: 3, codigo: 'rh', nome: 'RH', ordem: 3, ativo: false },
];

const PESSOAS: Partial<Pessoa>[] = [
  { id: 1, nome: 'Natan Ferreira', cor: '#0052CC' },
  { id: 2, nome: 'Ana Souza', cor: '#00875A' },
];

function preparar(setores: Partial<Setor>[] = SETORES): Estado {
  const estado = criarFakePrisma(undefined, ASSUNTOS, setores, PESSOAS);
  dbClient.prisma = estado.prisma;
  captura.reset();
  return estado;
}

function pedir(metodo: string, url: string, payload?: unknown, token: string | null = TOKEN) {
  return app.inject({
    method: metodo as any,
    url,
    payload: payload as any,
    headers: token === null ? {} : { authorization: `Bearer ${token}` },
  });
}

/**
 * Um chamado com TODAS as colunas NOT NULL preenchidas.
 *
 * O preenchimento completo não é zelo: o schema de resposta declara `prioridade`,
 * `canal` e os três booleanos como obrigatórios, e o serializador do Fastify
 * recebe o que estiver na linha. Uma fixture pela metade faria o teste falhar na
 * serialização - longe da regra que ele deveria estar verificando.
 */
function chamadoBase(over: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 1,
    nome: 'Maria',
    telefone: TEL,
    resumo: 'PDV não abre',
    descricao: 'Desde as 8h o caixa 3 não abre.',
    situacao: 'aberto',
    origem: 'whatsapp',
    categoriaId: null,
    dataAbertura: new Date('2026-08-30T09:00:00Z'),
    atualizadoEm: new Date('2026-08-30T09:00:00Z'),
    primeiroAtendimentoEm: null,
    resolvidoEm: null,
    tipo: null,
    setorId: null,
    setorOrigemId: null,
    responsavelId: null,
    prioridade: 'media',
    canal: 'whatsapp',
    contato: null,
    prazoEm: null,
    tipoSolicitacao: null,
    impacto: null,
    sistemaAfetado: null,
    tempoEstimadoMin: null,
    tempoGastoMin: null,
    franquiaCodigo: null,
    franquiaNome: null,
    franqueadoNome: null,
    franqueadoContato: null,
    localizacao: null,
    tipoFranquia: null,
    afetaAtendimento: false,
    envolveCusto: false,
    valorEstimadoCentavos: null,
    precisaAprovacao: false,
    urgenciaComercial: null,
    avaliacaoNota: null,
    avaliacaoComentario: null,
    avaliadoEm: null,
    tagIds: [] as number[],
    ...over,
  };
}

function comChamado(over: Record<string, unknown> = {}): Estado {
  const e = preparar();
  e.chamados.push(chamadoBase(over));
  return e;
}

// ===================== Setores =========================================

test('listagem de setores exige token', async () => {
  preparar();
  const r = await pedir('GET', '/internal/setores', undefined, null);
  assert.equal(r.statusCode, 401);
});

test('listagem devolve todos os setores, inclusive os inativos', async () => {
  preparar();

  const r = await pedir('GET', '/internal/setores');
  assert.equal(r.statusCode, 200);

  const { setores } = r.json();
  // O inativo TEM de vir: se a rota filtrasse por `ativo`, o setor desativado
  // sumiria da tela e não haveria como reativá-lo.
  assert.equal(setores.length, 3);
  assert.deepEqual(
    setores.map((x: any) => x.codigo),
    ['ti', 'financeiro', 'rh']
  );
  assert.equal(setores[2].ativo, false);
});

test('a listagem separa quem ATENDE de quem ABRIU o chamado', async () => {
  const e = preparar();
  // TI atende dois; Financeiro abriu os dois e não atende nenhum.
  e.chamados.push(
    chamadoBase({ id: 1, setorId: 1, setorOrigemId: 2 }),
    chamadoBase({ id: 2, setorId: 1, setorOrigemId: 2 })
  );

  const { setores } = (await pedir('GET', '/internal/setores')).json();
  const ti = setores.find((x: any) => x.codigo === 'ti');
  const financeiro = setores.find((x: any) => x.codigo === 'financeiro');

  // Os dois números são perguntas diferentes - "quem mais atende" e "quem mais
  // nos demanda". Com uma contagem só, os dois relatórios viram o mesmo.
  assert.equal(ti.chamados, 2);
  assert.equal(ti.origens, 0);
  assert.equal(financeiro.chamados, 0);
  assert.equal(financeiro.origens, 2);
});

test('criar setor normaliza o código para minúsculas e sem espaço', async () => {
  preparar([]);

  const r = await pedir('POST', '/internal/setores', { codigo: '  Pos_Venda ', nome: 'Pós-venda' });
  assert.equal(r.statusCode, 201);
  // "TI " e "ti" apontando para dois setores é o tipo de duplicata que só
  // aparece no relatório, meses depois.
  assert.equal(r.json().codigo, 'pos_venda');
  assert.equal(r.json().chamados, 0);
});

test('setor sem ordem entra no fim da lista', async () => {
  preparar();

  const r = await pedir('POST', '/internal/setores', { codigo: 'novo', nome: 'Novo' });
  assert.equal(r.statusCode, 201);
  // O maior `ordem` era 3; entra em 4 para "adicionar" ser um clique só.
  assert.equal(r.json().ordem, 4);
});

test('código de setor repetido é 409, não 500', async () => {
  preparar();

  const r = await pedir('POST', '/internal/setores', { codigo: 'ti', nome: 'Outro TI' });
  assert.equal(r.statusCode, 409);
  assert.match(r.json().erro, /ti/);
});

test('o código do setor não pode ser renomeado', async () => {
  preparar();

  // `codigo` fora do schema de alteração: é a chave estável de quem integra de
  // fora, e renomeá-la quebraria o casamento em silêncio.
  const r = await pedir('PATCH', '/internal/setores/1', { codigo: 'outro' });
  assert.equal(r.statusCode, 400);
});

test('PATCH de setor vazio é 400 em vez de escrita que não escreve', async () => {
  preparar();
  const r = await pedir('PATCH', '/internal/setores/1', {});
  assert.equal(r.statusCode, 400);
});

test('desativar setor é alteração comum', async () => {
  const e = preparar();

  const r = await pedir('PATCH', '/internal/setores/1', { ativo: false, nome: '  TI  ' });
  assert.equal(r.statusCode, 200);
  assert.equal(r.json().ativo, false);
  // O trim acontece antes de gravar: `maxLength` conta caracteres crus.
  assert.equal(e.setores.find((x) => x.id === 1)!.nome, 'TI');
});

test('setor inexistente é 404 nas duas rotas que o alteram', async () => {
  preparar();
  assert.equal((await pedir('PATCH', '/internal/setores/99', { nome: 'x' })).statusCode, 404);
  assert.equal((await pedir('DELETE', '/internal/setores/99')).statusCode, 404);
});

test('excluir setor em uso é recusado, contando as DUAS pontas', async () => {
  const e = preparar();
  // Ninguém ATENDE pelo Financeiro; ele só ABRIU um chamado. Ainda assim tem
  // histórico a perder.
  e.chamados.push(chamadoBase({ id: 1, setorId: null, setorOrigemId: 2 }));

  const r = await pedir('DELETE', '/internal/setores/2');
  assert.equal(r.statusCode, 409);
  assert.match(r.json().erro, /Desative/);
  // Contar só `setorId` deixaria este DELETE passar e o `SetNull` apagaria a
  // origem do chamado sem ninguém pedir.
  assert.equal(e.setores.length, 3);
});

test('setor sem uso é excluído de verdade', async () => {
  const e = preparar();

  const r = await pedir('DELETE', '/internal/setores/2');
  assert.equal(r.statusCode, 200);
  assert.deepEqual(r.json(), { id: 2, apagado: true });
  assert.equal(e.setores.length, 2);
});

// ===================== Campos de classificação ==========================

test('alteração de classificação exige token', async () => {
  comChamado();
  const r = await pedir('PATCH', '/internal/chamados/1', { prioridade: 'alta' }, null);
  assert.equal(r.statusCode, 401);
});

test('classificar chamado inexistente é 404', async () => {
  preparar();
  const r = await pedir('PATCH', '/internal/chamados/99', { prioridade: 'alta' });
  assert.equal(r.statusCode, 404);
});

test('PATCH de classificação vazio é 400', async () => {
  comChamado();
  const r = await pedir('PATCH', '/internal/chamados/1', {});
  assert.equal(r.statusCode, 400);
});

test('grava tipo, setor e prioridade e devolve o chamado inteiro', async () => {
  comChamado();

  const r = await pedir('PATCH', '/internal/chamados/1', {
    tipo: 'interno',
    setorId: 1,
    setorOrigemId: 2,
    prioridade: 'urgente',
    canal: 'telefone',
    impacto: 'bloqueia_operacao',
    tipoSolicitacao: 'bug',
    sistemaAfetado: 'Vetor',
    tempoEstimadoMin: 90,
  });

  assert.equal(r.statusCode, 200);
  const c = r.json();
  assert.equal(c.tipo, 'interno');
  assert.equal(c.setorId, 1);
  assert.equal(c.setorOrigemId, 2);
  assert.equal(c.prioridade, 'urgente');
  assert.equal(c.canal, 'telefone');
  assert.equal(c.impacto, 'bloqueia_operacao');
  assert.equal(c.tempoEstimadoMin, 90);
  // A resposta é o chamado COMPLETO, e não um delta: é o que deixa o painel
  // repintar cartão e detalhe sem uma segunda ida ao servidor.
  assert.equal(c.resumo, 'PDV não abre');
  assert.deepEqual(c.tags, []);
});

test('campo ausente não é mexido; null limpa', async () => {
  const e = comChamado({ setorId: 1, prioridade: 'alta', sistemaAfetado: 'Vetor' });

  // Só `sistemaAfetado` no corpo: os outros dois não podem se mover.
  await pedir('PATCH', '/internal/chamados/1', { sistemaAfetado: null });

  const c = e.chamados[0];
  assert.equal(c.sistemaAfetado, null);
  assert.equal(c.setorId, 1, 'campo ausente do corpo é "não mexa"');
  assert.equal(c.prioridade, 'alta');
});

test('texto só de espaços vira null, e não string vazia', async () => {
  const e = comChamado();

  await pedir('PATCH', '/internal/chamados/1', { contato: '   ', franquiaNome: '  Loja 4  ' });

  // "não informado" tem UMA representação no banco. Sem isto, a tela mostraria
  // o campo como preenchido e ninguém conseguiria usar o conteúdo.
  assert.equal(e.chamados[0].contato, null);
  assert.equal(e.chamados[0].franquiaNome, 'Loja 4');
});

test('FK inexistente é 400 com o nome do campo, não 500', async () => {
  comChamado();

  const r = await pedir('PATCH', '/internal/chamados/1', { setorId: 99 });
  assert.equal(r.statusCode, 400);
  // Sem a checagem, o Prisma estouraria P2003 e viraria 500 - e quem chama não
  // saberia qual dos três campos de chave estava errado.
  assert.match(r.json().erro, /setorId/);
});

test('atribuir responsável liga o chamado ao cadastro de pessoas', async () => {
  const e = comChamado();

  const r = await pedir('PATCH', '/internal/chamados/1', { responsavelId: 2 });
  assert.equal(r.statusCode, 200);
  assert.equal(r.json().responsavelId, 2);
  assert.equal(e.chamados[0].responsavelId, 2);

  // `null` devolve o chamado para "sem responsável" - o estado em que ele nasce,
  // e o único jeito de desatribuir.
  const limpo = await pedir('PATCH', '/internal/chamados/1', { responsavelId: null });
  assert.equal(limpo.json().responsavelId, null);
});

test('excluir a pessoa não apaga o chamado dela', async () => {
  const e = comChamado({ responsavelId: 2 });

  const r = await pedir('DELETE', '/internal/pessoas/2');
  assert.equal(r.statusCode, 200);

  // `onDelete: SetNull` no schema: tirar alguém do cadastro devolve os chamados
  // para "sem responsável", e não os leva embora. O dublê não simula a FK, então
  // o que este teste prova é que a ROTA não recusa nem apaga chamado - a outra
  // metade (a coluna zerar) é do banco, e sai em `npm run dev:verificar-banco`.
  assert.equal(e.chamados.length, 1);
  assert.equal(e.pessoas.length, 1);
});

test('responsável inexistente também é 400', async () => {
  comChamado();
  const r = await pedir('PATCH', '/internal/chamados/1', { responsavelId: 42 });
  assert.equal(r.statusCode, 400);
  assert.match(r.json().erro, /responsavelId/);
});

test('prazo inválido é recusado em vez de sumir em silêncio', async () => {
  comChamado();

  const r = await pedir('PATCH', '/internal/chamados/1', { prazoEm: 'semana que vem' });
  assert.equal(r.statusCode, 400);
  // `new Date('semana que vem')` é Invalid Date, e o Prisma o gravaria como
  // null: o prazo desapareceria e a tela diria "sem prazo combinado".
  assert.match(r.json().erro, /prazoEm/);
});

test('prazo em ISO é gravado; null o remove', async () => {
  const e = comChamado();

  const r = await pedir('PATCH', '/internal/chamados/1', { prazoEm: '2026-09-02T18:00:00Z' });
  assert.equal(r.statusCode, 200);
  assert.equal(r.json().prazoEm, '2026-09-02T18:00:00.000Z');

  await pedir('PATCH', '/internal/chamados/1', { prazoEm: null });
  assert.equal(e.chamados[0].prazoEm, null);
});

test('valor de custo fora da faixa é recusado pelo schema', async () => {
  comChamado();
  assert.equal(
    (await pedir('PATCH', '/internal/chamados/1', { valorEstimadoCentavos: -1 })).statusCode,
    400
  );
  assert.equal(
    (await pedir('PATCH', '/internal/chamados/1', { tempoGastoMin: -5 })).statusCode,
    400
  );
});

test('campo desconhecido no corpo é recusado', async () => {
  comChamado();
  // `additionalProperties: false`: um campo com erro de digitação seria aceito e
  // descartado em silêncio, e quem chamou acharia que gravou.
  const r = await pedir('PATCH', '/internal/chamados/1', { prioridadeee: 'alta' });
  assert.equal(r.statusCode, 400);
});

// ===================== Situações novas e SLA =============================

test('fechar chamado preenche a data de conclusão', async () => {
  const e = comChamado();

  const r = await pedir('PATCH', '/internal/chamados/1/situacao', { situacao: 'fechado' });
  assert.equal(r.statusCode, 200);
  assert.ok(r.json().resolvidoEm, 'fechado é conclusão, como resolvido');
  assert.ok(e.chamados[0].primeiroAtendimentoEm, 'saiu de aberto: o marco de atendimento move');
});

test('resolvido -> fechado NÃO remarca a data de conclusão', async () => {
  const e = comChamado({
    situacao: 'resolvido',
    primeiroAtendimentoEm: new Date('2026-08-30T10:00:00Z'),
    resolvidoEm: new Date('2026-08-30T11:00:00Z'),
  });

  await pedir('PATCH', '/internal/chamados/1/situacao', { situacao: 'fechado' });

  // Só a ENTRADA no conjunto de concluídas conta. Remarcar aqui apagaria a data
  // real de conclusão do chamado que estava sendo dado por concluído.
  assert.equal((e.chamados[0].resolvidoEm as Date).toISOString(), '2026-08-30T11:00:00.000Z');
});

test('sair de fechado para aberto zera a data de conclusão', async () => {
  const e = comChamado({
    situacao: 'fechado',
    primeiroAtendimentoEm: new Date('2026-08-30T10:00:00Z'),
    resolvidoEm: new Date('2026-08-30T11:00:00Z'),
  });

  await pedir('PATCH', '/internal/chamados/1/situacao', { situacao: 'aberto' });

  // Chamado reaberto não está concluído. Sem o zerar, a média de tempo de
  // resolução contaria uma resolução desfeita.
  assert.equal(e.chamados[0].resolvidoEm, null);
  // O primeiro atendimento NÃO volta: ele mede a espera original, e ela
  // aconteceu.
  assert.ok(e.chamados[0].primeiroAtendimentoEm);
});

test('aguardando_resposta avisa o usuário pedindo que ele responda', async () => {
  comChamado();

  const r = await pedir('PATCH', '/internal/chamados/1/situacao', {
    situacao: 'aguardando_resposta',
    notificarUsuario: true,
  });

  assert.equal(r.statusCode, 200);
  assert.equal(r.json().notificado, true);
  // A única das mensagens que PEDE algo: é o estado que só sai do lugar quando o
  // solicitante responde, e um aviso que não diz isso deixa os dois esperando.
  assert.match(captura.ultimoTexto(), /aguardando sua resposta/i);
});

// ===================== Avaliação pós-fechamento ==========================

test('avaliar chamado aberto é recusado', async () => {
  comChamado();

  const r = await pedir('PUT', '/internal/chamados/1/avaliacao', { nota: 5 });
  // "Avaliação pós-fechamento" avalia um atendimento que terminou. Aceitar aqui
  // deixaria a nota ser dada antes do trabalho, sem ninguém saber disso olhando
  // o número.
  assert.equal(r.statusCode, 409);
  assert.match(r.json().erro, /aberto/);
});

test('avaliar chamado resolvido grava nota, comentário e o instante', async () => {
  const e = comChamado({ situacao: 'resolvido', resolvidoEm: new Date('2026-08-30T11:00:00Z') });

  const r = await pedir('PUT', '/internal/chamados/1/avaliacao', {
    nota: 4,
    comentario: '  resolveram rápido  ',
  });

  assert.equal(r.statusCode, 200);
  assert.equal(r.json().avaliacaoNota, 4);
  assert.equal(r.json().avaliacaoComentario, 'resolveram rápido');
  // `avaliadoEm` é gravado pelo servidor e não vem do corpo: quem chama não pode
  // datar a avaliação para trás.
  assert.ok(r.json().avaliadoEm);
  assert.ok(e.chamados[0].avaliadoEm);
});

test('chamado fechado também aceita avaliação', async () => {
  comChamado({ situacao: 'fechado', resolvidoEm: new Date('2026-08-30T11:00:00Z') });
  const r = await pedir('PUT', '/internal/chamados/1/avaliacao', { nota: 1 });
  assert.equal(r.statusCode, 200);
});

test('nota vazia distingue-se de nota zero', async () => {
  comChamado({ situacao: 'resolvido' });

  // A faixa é 1..5. Zero não é "sem nota", é fora da escala.
  assert.equal((await pedir('PUT', '/internal/chamados/1/avaliacao', { nota: 0 })).statusCode, 400);
  assert.equal((await pedir('PUT', '/internal/chamados/1/avaliacao', { nota: 6 })).statusCode, 400);
});

// ===================== Etiquetas ========================================

test('criar chamado no painel liga as etiquetas por nome', async () => {
  const e = preparar();

  const r = await pedir('POST', '/internal/tarefas', {
    nome: 'Ana',
    resumo: 'Trocar cabo do PDV 3',
    descricao: 'O cabo de rede do caixa 3 está rompido.',
    tipo: 'franquia',
    setorId: 1,
    franquiaCodigo: 'BM-042',
    afetaAtendimento: true,
    tags: ['PDV', 'pdv', '  Black Friday  ', ''],
  });

  assert.equal(r.statusCode, 201);
  assert.equal(r.json().origem, 'painel');

  // Normalizado no SERVIDOR: "PDV" e "pdv" são a mesma etiqueta, e a repetida e
  // a vazia saem. Sem isso, o relatório contaria o mesmo assunto duas vezes.
  assert.deepEqual(e.tags.map((t) => t.nome).sort(), ['black friday', 'pdv']);
  assert.equal(e.chamados[0].tagIds.length, 2);
  assert.equal(e.chamados[0].afetaAtendimento, true);
  assert.equal(e.chamados[0].franquiaCodigo, 'BM-042');
});

test('chamado criado no painel nasce com canal presencial, não whatsapp', async () => {
  const e = preparar();

  await pedir('POST', '/internal/tarefas', {
    nome: 'Ana',
    resumo: 'Trocar cabo',
    descricao: 'O cabo de rede do caixa 3 está rompido.',
  });

  // O default do BANCO é `whatsapp`, e whatsapp é exatamente o que esta tarefa
  // não é: ela foi digitada por alguém. Herdar o default marcaria como vinda do
  // bot todo chamado registrado à mão.
  assert.equal(e.chamados[0].canal, 'presencial');
  assert.equal(e.chamados[0].telefone, undefined, 'tarefa do painel não tem titular');
});

test('canal informado no corpo vence o padrão da rota', async () => {
  const e = preparar();

  await pedir('POST', '/internal/tarefas', {
    nome: 'Ana',
    resumo: 'Pedido por telefone',
    descricao: 'A franqueada ligou pedindo segunda via.',
    canal: 'telefone',
  });

  assert.equal(e.chamados[0].canal, 'telefone');
});

test('PUT de etiquetas substitui o conjunto inteiro', async () => {
  const e = comChamado();

  await pedir('PUT', '/internal/chamados/1/tags', { tags: ['pdv', 'urgente'] });
  const r = await pedir('PUT', '/internal/chamados/1/tags', { tags: ['fiscal'] });

  assert.equal(r.statusCode, 200);
  assert.deepEqual(r.json().tags, ['fiscal']);
  // A `Tag` continua existindo: `set` desconecta sem apagar a linha, porque
  // outros chamados podem usá-la.
  assert.ok(e.tags.some((t) => t.nome === 'pdv'));
  assert.equal(e.chamados[0].tagIds.length, 1);
});

test('etiquetas aparecem na listagem do quadro', async () => {
  comChamado();
  await pedir('PUT', '/internal/chamados/1/tags', { tags: ['pdv'] });

  const { chamados } = (await pedir('GET', '/internal/chamados')).json();
  // Tag vem na LISTAGEM (ao contrário de comentário e anexo) porque aparece no
  // cartão. Sem isso o quadro precisaria de uma requisição por cartão.
  assert.deepEqual(chamados[0].tags, ['pdv']);
});

// ===================== Comentários ======================================

test('comentário exige chamado que existe', async () => {
  preparar();
  const r = await pedir('POST', '/internal/chamados/99/comentarios', { texto: 'oi' });
  assert.equal(r.statusCode, 404);
});

test('comentário só de espaços é recusado', async () => {
  comChamado();
  const r = await pedir('POST', '/internal/chamados/1/comentarios', { texto: '   ' });
  assert.equal(r.statusCode, 400);
});

test('comentário é gravado com autor e data', async () => {
  const e = comChamado();

  const r = await pedir('POST', '/internal/chamados/1/comentarios', {
    texto: '  cliente já reclamou disso antes  ',
    autor: 'Natan',
  });

  assert.equal(r.statusCode, 201);
  assert.equal(r.json().texto, 'cliente já reclamou disso antes');
  assert.equal(r.json().autor, 'Natan');
  assert.ok(r.json().criadoEm);
  assert.equal(e.comentarios.length, 1);
});

test('comentário NÃO vira mensagem de WhatsApp', async () => {
  const e = comChamado();

  await pedir('POST', '/internal/chamados/1/comentarios', {
    texto: 'nota interna: cliente é encrenqueiro',
  });

  // A regressão que este teste existe para impedir. Se o comentário caísse na
  // tabela `Mensagem`, a varredura da outbox despacharia a nota interna para o
  // cliente na primeira passada.
  assert.equal(e.mensagens.length, 0, 'nota interna não pode entrar na fila de envio');
  assert.equal(captura.enviados.length, 0);
});

// ===================== Anexos ===========================================

const PNG_BASE64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==';

test('anexo em base64 é gravado com nome, tipo e tamanho', async () => {
  const e = comChamado();

  const r = await pedir('POST', '/internal/chamados/1/anexos', {
    nome: 'C:\\Users\\natan\\Desktop\\print.png',
    mime: 'image/png',
    conteudoBase64: PNG_BASE64,
    enviadoPor: 'Natan',
  });

  assert.equal(r.statusCode, 201);
  // O caminho da máquina de quem enviou não vira nome de arquivo na tela.
  assert.equal(r.json().nome, 'print.png');
  assert.equal(r.json().mime, 'image/png');
  assert.ok(r.json().bytes > 0);
  assert.equal(e.anexos.length, 1);
  // `bytes` é gravado em coluna própria: sem ela, cada listagem teria de ler os
  // BLOBs inteiros só para dizer "2,4 MB".
  assert.equal(e.anexos[0].bytes, e.anexos[0].conteudo.length);
});

test('base64 inválido é recusado em vez de gravar lixo', async () => {
  comChamado();

  const r = await pedir('POST', '/internal/chamados/1/anexos', {
    nome: 'x.png',
    mime: 'image/png',
    conteudoBase64: 'isto não é base64!!',
  });

  // `Buffer.from(x, 'base64')` nunca estoura: ignora o inválido e devolve o que
  // sobrou. Sem a conferência, gravaria um anexo de lixo que só falharia quando
  // alguém tentasse abrir o arquivo, semanas depois.
  assert.equal(r.statusCode, 400);
  assert.match(r.json().erro, /base64/);
});

test('tipo de arquivo fora da lista é recusado', async () => {
  comChamado();

  const r = await pedir('POST', '/internal/chamados/1/anexos', {
    nome: 'pagina.html',
    mime: 'text/html',
    conteudoBase64: PNG_BASE64,
  });

  // HTML guardado aqui voltaria pelo GET com `Content-Type: text/html`, servido
  // pela mesma origem do painel - com acesso ao que aquela origem tem.
  assert.equal(r.statusCode, 400);
  assert.match(r.json().erro, /não é aceito/);
});

test('anexo acima do limite é 413 com o tamanho em MB', async () => {
  comChamado();

  // ANEXO_MAX_BYTES nos testes é pequeno de propósito (ver test/env.ts): sem
  // isso, este caso exigiria montar um corpo de vários megabytes.
  const grande = Buffer.alloc(4096, 7).toString('base64');
  const r = await pedir('POST', '/internal/chamados/1/anexos', {
    nome: 'grande.pdf',
    mime: 'application/pdf',
    conteudoBase64: grande,
  });

  assert.equal(r.statusCode, 413);
  assert.match(r.json().erro, /MB/);
});

test('download devolve os bytes e força attachment', async () => {
  comChamado();
  const criado = await pedir('POST', '/internal/chamados/1/anexos', {
    nome: 'print.png',
    mime: 'image/png',
    conteudoBase64: PNG_BASE64,
  });

  const r = await pedir('GET', '/internal/anexos/' + criado.json().id);
  assert.equal(r.statusCode, 200);
  assert.equal(r.headers['content-type'], 'image/png');
  // `attachment` sempre, mesmo em imagem: é o que impede um arquivo enviado por
  // terceiro de ser RENDERIZADO na origem do painel.
  assert.match(String(r.headers['content-disposition']), /^attachment/);
  assert.equal(r.headers['x-content-type-options'], 'nosniff');
  assert.equal(r.rawPayload.toString('base64'), PNG_BASE64);
});

test('download de anexo exige token e existe de verdade', async () => {
  comChamado();
  assert.equal((await pedir('GET', '/internal/anexos/1', undefined, null)).statusCode, 401);
  assert.equal((await pedir('GET', '/internal/anexos/1')).statusCode, 404);
});

test('anexo pode ser excluído — diferente de comentário', async () => {
  const e = comChamado();
  const criado = await pedir('POST', '/internal/chamados/1/anexos', {
    nome: 'print.png',
    mime: 'image/png',
    conteudoBase64: PNG_BASE64,
  });

  // Anexo é ARQUIVO, não rastro: quem sobe o print com o dado de outra pessoa
  // precisa poder tirá-lo. Comentário, ao contrário, não tem rota de exclusão.
  const r = await pedir('DELETE', '/internal/anexos/' + criado.json().id);
  assert.equal(r.statusCode, 200);
  assert.equal(e.anexos.length, 0);
});

// ===================== Dependências =====================================

function comDoisChamados(): Estado {
  const e = preparar();
  e.chamados.push(
    chamadoBase({ id: 1, resumo: 'PDV não abre' }),
    chamadoBase({ id: 2, resumo: 'Trocar switch da loja' })
  );
  return e;
}

test('marcar dependência liga os dois chamados na direção certa', async () => {
  const e = comDoisChamados();

  const r = await pedir('POST', '/internal/chamados/1/dependencias', { bloqueadorId: 2 });
  assert.equal(r.statusCode, 201);
  // A direção está no nome da rota: o `:id` é sempre o TRAVADO.
  assert.deepEqual(r.json(), {
    chamadoId: 2,
    resumo: 'Trocar switch da loja',
    situacao: 'aberto',
  });
  assert.equal(e.dependencias[0].bloqueadoId, 1);
  assert.equal(e.dependencias[0].bloqueadorId, 2);
});

test('chamado não pode bloquear a si mesmo', async () => {
  comDoisChamados();
  const r = await pedir('POST', '/internal/chamados/1/dependencias', { bloqueadorId: 1 });
  assert.equal(r.statusCode, 400);
});

test('o ciclo de dois é recusado', async () => {
  comDoisChamados();
  await pedir('POST', '/internal/chamados/1/dependencias', { bloqueadorId: 2 });

  // A trava e a inversa juntas: nenhum dos dois poderia jamais sair da fila. É o
  // erro que se comete sem perceber, e por isso é o que a rota olha.
  const r = await pedir('POST', '/internal/chamados/2/dependencias', { bloqueadorId: 1 });
  assert.equal(r.statusCode, 409);
  assert.match(r.json().erro, /ciclo/);
});

test('a mesma dependência duas vezes é 409, não uma linha repetida', async () => {
  const e = comDoisChamados();
  await pedir('POST', '/internal/chamados/1/dependencias', { bloqueadorId: 2 });

  const r = await pedir('POST', '/internal/chamados/1/dependencias', { bloqueadorId: 2 });
  assert.equal(r.statusCode, 409);
  assert.equal(e.dependencias.length, 1);
});

test('bloqueador inexistente é 400', async () => {
  comDoisChamados();
  const r = await pedir('POST', '/internal/chamados/1/dependencias', { bloqueadorId: 99 });
  assert.equal(r.statusCode, 400);
});

test('dependência pode ser removida', async () => {
  const e = comDoisChamados();
  await pedir('POST', '/internal/chamados/1/dependencias', { bloqueadorId: 2 });

  const r = await pedir('DELETE', '/internal/chamados/1/dependencias/2');
  assert.equal(r.statusCode, 200);
  assert.equal(e.dependencias.length, 0);

  // De novo: já não existe.
  assert.equal((await pedir('DELETE', '/internal/chamados/1/dependencias/2')).statusCode, 404);
});

// ===================== Detalhe ==========================================

test('o detalhe traz as quatro listas numa requisição só', async () => {
  comDoisChamados();
  await pedir('POST', '/internal/chamados/1/comentarios', { texto: 'olhando', autor: 'Natan' });
  await pedir('POST', '/internal/chamados/1/anexos', {
    nome: 'print.png',
    mime: 'image/png',
    conteudoBase64: PNG_BASE64,
  });
  await pedir('POST', '/internal/chamados/1/dependencias', { bloqueadorId: 2 });

  const r = await pedir('GET', '/internal/chamados/1/detalhe');
  assert.equal(r.statusCode, 200);

  const d = r.json();
  assert.equal(d.chamadoId, 1);
  assert.equal(d.comentarios.length, 1);
  assert.equal(d.comentarios[0].autor, 'Natan');
  assert.equal(d.anexos.length, 1);
  // O BLOB fica fora: abrir um chamado com cinco prints não pode baixar os cinco
  // arquivos para desenhar cinco nomes.
  assert.equal(d.anexos[0].conteudo, undefined);
  assert.equal(d.bloqueadoPor.length, 1);
  assert.equal(d.bloqueadoPor[0].chamadoId, 2);
  assert.equal(d.bloqueia.length, 0);

  // E a ponta oposta vê a mesma ligação pelo outro lado.
  const outro = (await pedir('GET', '/internal/chamados/2/detalhe')).json();
  assert.equal(outro.bloqueia.length, 1);
  assert.equal(outro.bloqueia[0].chamadoId, 1);
  assert.equal(outro.bloqueadoPor.length, 0);
});

// ===================== Conversa do WhatsApp =============================

/**
 * Empilha uma troca de mensagens no chamado 1, como o fluxo da conversa a deixa:
 * a pergunta do bot e a resposta da pessoa, alternadas, com a saída carregando
 * `payload` (o corpo da Graph API) e `enviadaEm`.
 */
function comConversa(): Estado {
  const e = comChamado();
  const base = new Date('2026-08-30T09:00:00Z').getTime();
  const MIN = 60 * 1000;

  const msg = (i: number, remetente: string, texto: string, extra: any = {}) => ({
    id: i,
    chamadoId: 1,
    telefone: TEL,
    remetente,
    texto,
    timestamp: new Date(base + i * MIN),
    whatsappMessageId: remetente === 'usuario' ? `wamid.${i}` : null,
    // O corpo exato postado na Graph API. CONTÉM o telefone — é o que a rota não
    // pode devolver.
    payload: remetente === 'sistema' ? { to: TEL, text: { body: texto } } : null,
    enviadaEm: remetente === 'sistema' ? new Date(base + i * MIN) : null,
    tentativas: 0,
    ...extra,
  });

  e.mensagens.push(
    msg(1, 'sistema', 'Para abrir seu chamado, qual é o seu nome?'),
    msg(2, 'usuario', 'Maria'),
    msg(3, 'sistema', 'Obrigado! Agora resuma seu problema em uma frase curta.'),
    msg(4, 'usuario', 'PDV não abre'),
    // Saída ainda na fila: `enviadaEm` nulo. É a distinção que o painel precisa
    // fazer entre "a equipe não respondeu" e "a resposta não saiu daqui".
    msg(5, 'sistema', 'Seu chamado #1 está sendo analisado.', { enviadaEm: null })
  );

  return e;
}

test('o detalhe devolve a conversa do WhatsApp na ordem em que aconteceu', async () => {
  comConversa();

  const r = await pedir('GET', '/internal/chamados/1/detalhe');
  assert.equal(r.statusCode, 200);

  const { mensagens } = r.json();
  assert.equal(mensagens.length, 5);
  // Do mais ANTIGO para o mais novo: é uma conversa, e conversa se lê na ordem em
  // que aconteceu — ao contrário do histórico de situação, que é do mais novo.
  assert.deepEqual(
    mensagens.map((m: any) => m.texto),
    [
      'Para abrir seu chamado, qual é o seu nome?',
      'Maria',
      'Obrigado! Agora resuma seu problema em uma frase curta.',
      'PDV não abre',
      'Seu chamado #1 está sendo analisado.',
    ]
  );
  assert.deepEqual(
    mensagens.map((m: any) => m.remetente),
    ['sistema', 'usuario', 'sistema', 'usuario', 'sistema']
  );
});

test('a conversa NÃO devolve telefone, payload nem wamid', async () => {
  comConversa();

  const { mensagens } = (await pedir('GET', '/internal/chamados/1/detalhe')).json();

  for (const m of mensagens) {
    // A regressão que este teste existe para impedir. `payload` é o corpo exato
    // postado na Graph API e CARREGA o telefone: devolvê-lo entregaria pela porta
    // de trás o dado que todas as outras rotas escondem.
    assert.equal(m.telefone, undefined, 'telefone não pode sair na conversa');
    assert.equal(m.payload, undefined, 'payload carrega o telefone');
    assert.equal(m.whatsappMessageId, undefined, 'wamid é protocolo interno');
    assert.equal(m.tentativas, undefined, 'contador do varredor é ruído operacional');
    // E o que SOBRA tem de estar completo, senão o teste passaria com a rota
    // devolvendo lista de objetos vazios.
    assert.ok(m.id > 0);
    assert.ok(typeof m.texto === 'string' && m.texto.length > 0);
    assert.match(m.timestamp, /^\d{4}-\d{2}-\d{2}T/);
  }
});

test('mensagem de saída ainda na fila chega com enviadaEm nulo', async () => {
  comConversa();

  const { mensagens } = (await pedir('GET', '/internal/chamados/1/detalhe')).json();
  const pendente = mensagens.find((m: any) => m.texto.includes('sendo analisado'));

  // "A equipe não respondeu" e "a resposta existe e não saiu daqui" são coisas
  // diferentes, e este é o único campo de entrega que a rota expõe para
  // distingui-las.
  assert.equal(pendente.enviadaEm, null);
  assert.ok(mensagens[0].enviadaEm, 'as já entregues trazem o instante');
});

test('chamado criado no painel tem conversa vazia, e isso não é erro', async () => {
  preparar();
  const criado = await pedir('POST', '/internal/tarefas', {
    nome: 'Ana',
    resumo: 'Trocar cabo do PDV 3',
    descricao: 'O cabo de rede do caixa 3 está rompido.',
  });

  const r = await pedir('GET', '/internal/chamados/' + criado.json().id + '/detalhe');
  assert.equal(r.statusCode, 200);
  // Tarefa do painel não tem telefone, então não tem sessão nem log de conversa —
  // lista vazia é o estado correto, não uma falha de carregamento.
  assert.deepEqual(r.json().mensagens, []);
});

test('a conversa não mistura mensagens de outro chamado', async () => {
  const e = comConversa();
  e.chamados.push(chamadoBase({ id: 2, resumo: 'Outro chamado' }));
  e.mensagens.push({
    id: 99,
    chamadoId: 2,
    telefone: TEL,
    remetente: 'usuario',
    texto: 'isto é de outro chamado',
    timestamp: new Date('2026-08-30T08:00:00Z'),
    payload: null,
    enviadaEm: null,
    tentativas: 0,
  });

  const { mensagens } = (await pedir('GET', '/internal/chamados/1/detalhe')).json();
  assert.equal(mensagens.length, 5);
  assert.ok(!mensagens.some((m: any) => m.texto.includes('outro chamado')));
});

test('detalhe de chamado inexistente é 404', async () => {
  preparar();
  const r = await pedir('GET', '/internal/chamados/99/detalhe');
  assert.equal(r.statusCode, 404);
});

test('detalhe exige token', async () => {
  comChamado();
  const r = await pedir('GET', '/internal/chamados/1/detalhe', undefined, null);
  assert.equal(r.statusCode, 401);
});

// ===================== Métricas pelos eixos novos ========================

test('as métricas agrupam por setor e por tipo, além de por assunto', async () => {
  const e = preparar();
  const base = new Date('2026-08-25T09:00:00Z').getTime();
  const HORA = 60 * 60 * 1000;

  e.chamados.push(
    chamadoBase({
      id: 1,
      tipo: 'interno',
      setorId: 1,
      categoriaId: 1,
      situacao: 'resolvido',
      dataAbertura: new Date(base),
      primeiroAtendimentoEm: new Date(base + HORA),
      resolvidoEm: new Date(base + 3 * HORA),
    }),
    chamadoBase({
      id: 2,
      tipo: 'interno',
      setorId: 1,
      categoriaId: 1,
      situacao: 'aguardando_resposta',
      dataAbertura: new Date(base),
      primeiroAtendimentoEm: new Date(base + HORA),
    }),
    chamadoBase({
      id: 3,
      tipo: 'franquia',
      setorId: 2,
      categoriaId: null,
      situacao: 'fechado',
      dataAbertura: new Date(base),
      primeiroAtendimentoEm: new Date(base + HORA),
      resolvidoEm: new Date(base + 5 * HORA),
    }),
    // Sem tipo e sem setor: o chamado que ninguém classificou ainda.
    chamadoBase({ id: 4, situacao: 'aberto', dataAbertura: new Date(base) })
  );

  const r = await pedir('GET', '/internal/metricas');
  assert.equal(r.statusCode, 200);
  const m = r.json();

  // Os contadores das situações novas existem. Sem eles, os dois estados
  // sumiriam do relatório e o total deixaria de bater com a soma das colunas.
  assert.equal(m.geral.total, 4);
  assert.equal(m.geral.aguardando_resposta, 1);
  assert.equal(m.geral.fechado, 1);
  assert.equal(m.geral.resolvido, 1);
  assert.equal(m.geral.aberto, 1);

  const somaSituacoes =
    m.geral.aberto +
    m.geral.em_andamento +
    m.geral.aguardando_resposta +
    m.geral.resolvido +
    m.geral.fechado +
    m.geral.cancelado;
  assert.equal(somaSituacoes, m.geral.total, 'a soma das situações fecha com o total');

  // `fechado` conta como conclusão na amostra de resolução, como `resolvido`.
  assert.equal(m.geral.resolvidos, 2);

  const ti = m.porSetor.find((x: any) => x.codigo === 'ti');
  assert.equal(ti.total, 2);
  assert.equal(ti.id, 1);

  const semSetor = m.porSetor.find((x: any) => x.codigo === 'sem_setor');
  assert.equal(semSetor.total, 1, 'chamado sem setor continua sendo atendimento');
  assert.equal(semSetor.id, null);

  const interno = m.porTipo.find((x: any) => x.codigo === 'interno');
  assert.equal(interno.total, 2);
  // Grupo por enum não tem id de tabela: `id` nulo é a resposta certa, não zero.
  assert.equal(interno.id, null);

  const semTipo = m.porTipo.find((x: any) => x.codigo === 'sem_tipo');
  assert.equal(semTipo.total, 1);

  // Cada corte tem de fechar com o geral: é a prova de que nenhum agrupamento
  // descarta linha.
  for (const eixo of ['porCategoria', 'porSetor', 'porTipo']) {
    const soma = m[eixo].reduce((t: number, c: any) => t + c.total, 0);
    assert.equal(soma, m.geral.total, `${eixo} tem de fechar com o geral`);
  }
});
