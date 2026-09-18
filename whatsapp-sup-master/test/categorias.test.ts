import './env';
import assert from 'node:assert/strict';
import test, { after, beforeEach } from 'node:test';
import { Categoria, Estado, Sessao, capturarEnvios, criarFakePrisma } from './fake-prisma';

const dbClient = require('../src/db/client');
const { criarApp } = require('../src/app');
const { processarMensagem } = require('../src/conversation/handler');
const { _resetThrottle } = require('../src/whatsapp/throttle');

const TEL = '5511998877665';
const TOKEN = 'token_interno_de_teste';

const captura = capturarEnvios();
const app = criarApp();

after(() => app.close());
beforeEach(() => _resetThrottle());

function preparar(
  categorias: Partial<Categoria>[] = [],
  sessaoInicial?: Partial<Sessao> & { telefone: string }
): Estado {
  const estado = criarFakePrisma(sessaoInicial, categorias);
  dbClient.prisma = estado.prisma;
  captura.reset();
  return estado;
}

const texto = (valor: string) => ({ tipo: 'texto' as const, valor });
const botao = (id: string) => ({ tipo: 'botao' as const, id });

/**
 * Os seis grupos de atendimento da empresa, como o seed da migração os cria.
 * `nome` e `rotulo` divergem de propósito em dois deles: é assim na tela de
 * origem, e é o que prova que o menu mostra o rótulo de EXIBIÇÃO.
 */
const ASSUNTOS: Partial<Categoria>[] = [
  {
    id: 1,
    codigo: 'cadastro_ifood',
    nome: 'CADASTRO NO IFOOD',
    rotulo: 'CADASTRO NO IFOOD',
    ordem: 1,
  },
  {
    id: 2,
    codigo: 'demanda_interna_franqueadora',
    nome: 'DEMANDA INTERNA FRANQUEADORA',
    rotulo: 'SUPORTE A FRANQUEADORA',
    ordem: 2,
  },
  { id: 3, codigo: 'mudanca_cnpj', nome: 'MUDANÇA DE CNPJ', rotulo: 'MUDANÇA DE CNPJ', ordem: 3 },
  {
    id: 4,
    codigo: 'sistema_vetor',
    nome: 'PROBLEMAS RELACIONADOS AO SISTEMA VETOR',
    rotulo: 'SUPORTE AO SISTEMA VETOR',
    ordem: 4,
  },
  {
    id: 5,
    codigo: 'suporte_franqueado',
    nome: 'SUPORTE TÉCNICO AO FRANQUEADO',
    rotulo: 'SUPORTE AO FRANQUEADO',
    ordem: 5,
  },
  {
    id: 6,
    codigo: 'suporte_loja_propria',
    nome: 'SUPORTE TÉCNICO LOJA PRÓPRIA',
    rotulo: 'SUPORTE LOJA PRÓPRIA',
    ordem: 6,
  },
];

/** Uma árvore de dois níveis, para exercitar a descida e o "voltar". */
const COM_SUBASSUNTOS: Partial<Categoria>[] = [
  { id: 1, codigo: 'sistema_vetor', rotulo: 'SUPORTE AO SISTEMA VETOR', ordem: 1 },
  { id: 2, codigo: 'cadastro_ifood', rotulo: 'CADASTRO NO IFOOD', ordem: 2 },
  { id: 10, codigo: 'vetor_pdv', rotulo: 'PDV', ordem: 1, paiId: 1 },
  { id: 11, codigo: 'vetor_fiscal', rotulo: 'FISCAL', ordem: 2, paiId: 1 },
];

// =========================================================================
// O menu na conversa
// =========================================================================

test('o primeiro contato recebe o menu numerado de assuntos, não a pergunta do nome', async () => {
  const e = preparar(ASSUNTOS);

  await processarMensagem(TEL, texto('oi'), 'w1');

  const corpo = captura.ultimoTexto();
  assert.match(corpo, /escolha o assunto/i);
  assert.match(corpo, /1\. CADASTRO NO IFOOD/);
  assert.match(corpo, /4\. SUPORTE AO SISTEMA VETOR/);
  assert.match(corpo, /6\. SUPORTE LOJA PRÓPRIA/);
  assert.match(corpo, /Responda com o número/i);

  // O rótulo de EXIBIÇÃO, e não o nome interno: quem está no WhatsApp lê
  // "SUPORTE AO SISTEMA VETOR", não "PROBLEMAS RELACIONADOS AO SISTEMA VETOR".
  assert.ok(
    !corpo.includes('PROBLEMAS RELACIONADOS'),
    'o menu mostra o rótulo, não o nome interno'
  );

  assert.equal(e.sessoes.get(TEL)!.etapa, 'categoria');
  assert.equal(e.sessoes.get(TEL)!.categoriaId, null, 'a saudação não escolhe assunto nenhum');
});

test('escolher pelo número grava o assunto e avança para o nome', async () => {
  const e = preparar(ASSUNTOS);
  await processarMensagem(TEL, texto('oi'), 'w1');

  await processarMensagem(TEL, texto('4'), 'w2');

  const sessao = e.sessoes.get(TEL)!;
  assert.equal(sessao.categoriaId, 4, 'o 4 é a quarta opção do menu, não o id cru digitado');
  assert.equal(sessao.etapa, 'nome');

  // O rótulo volta junto com a pergunta seguinte: a escolha foi um número, e é
  // vendo o nome por extenso que a pessoa percebe na hora se errou a tecla.
  assert.match(captura.ultimoTexto(), /SUPORTE AO SISTEMA VETOR/);
  assert.match(captura.ultimoTexto(), /qual é o seu nome/i);
});

test('o id interno ainda escolhe, vindo de um menu antigo', async () => {
  const e = preparar(ASSUNTOS);
  await processarMensagem(TEL, texto('oi'), 'w1');

  // O menu agora é texto numerado: a posição é o que a pessoa digita, e não há
  // mais id trafegando na mensagem.
  const opcoes = captura.ultimasOpcoes();
  assert.equal(opcoes.length, 6);
  assert.equal(opcoes[0].id, '1', 'a posição é o que se responde');

  // O id `cat_<id>` continua sendo aceito: uma conversa que estava no meio da
  // migração pode ter um menu interativo antigo na tela.
  await processarMensagem(TEL, botao('cat_3'), 'w2');

  assert.equal(e.sessoes.get(TEL)!.categoriaId, 3);
  assert.equal(e.sessoes.get(TEL)!.etapa, 'nome');
});

test('digitar o rótulo por extenso também escolhe, com ou sem acento', async () => {
  const e = preparar(ASSUNTOS);
  await processarMensagem(TEL, texto('oi'), 'w1');

  await processarMensagem(TEL, texto('mudanca de cnpj'), 'w2');

  assert.equal(e.sessoes.get(TEL)!.categoriaId, 3);
  assert.equal(e.sessoes.get(TEL)!.etapa, 'nome');
});

test('opção fora do menu repete o menu e não avança', async () => {
  const e = preparar(ASSUNTOS);
  await processarMensagem(TEL, texto('oi'), 'w1');

  await processarMensagem(TEL, texto('99'), 'w2');

  assert.equal(e.sessoes.get(TEL)!.etapa, 'categoria', 'não pode avançar sem assunto');
  assert.equal(e.sessoes.get(TEL)!.categoriaId, null);

  const corpo = captura.ultimoTexto();
  assert.match(corpo, /não reconheci/i);
  assert.match(corpo, /1\. CADASTRO NO IFOOD/, 'o menu vem junto com a recusa');
});

test('texto livre na etapa de assunto não vira o nome da pessoa', async () => {
  const e = preparar(ASSUNTOS);
  await processarMensagem(TEL, texto('oi'), 'w1');

  // O bug que a etapa nova podia reintroduzir: a resposta que não é escolha
  // sendo gravada no primeiro campo de texto que aparecesse pela frente.
  await processarMensagem(TEL, texto('Natan'), 'w2');

  assert.equal(e.sessoes.get(TEL)!.nome, null);
  assert.equal(e.sessoes.get(TEL)!.categoriaId, null);
  assert.equal(e.sessoes.get(TEL)!.etapa, 'categoria');
});

test('assunto inativo não aparece e a numeração não ganha buraco', async () => {
  const comInativa = ASSUNTOS.map((c) => (c.id === 2 ? { ...c, ativa: false } : c));
  preparar(comInativa);

  await processarMensagem(TEL, texto('oi'), 'w1');

  const corpo = captura.ultimoTexto();
  assert.ok(!corpo.includes('SUPORTE A FRANQUEADORA'), 'inativa some do menu');

  // A numeração é a posição entre as ATIVAS: com a segunda desativada, o antigo
  // "3" vira "2". É por isso que o número não pode ser guardado em lugar nenhum.
  assert.match(corpo, /1\. CADASTRO NO IFOOD/);
  assert.match(corpo, /2\. MUDANÇA DE CNPJ/);
  assert.ok(!/3\. MUDANÇA DE CNPJ/.test(corpo), 'a numeração não pode pular');
});

test('a numeração acompanha a lista ativa, e o id gravado é o da categoria', async () => {
  const comInativa = ASSUNTOS.map((c) => (c.id === 2 ? { ...c, ativa: false } : c));
  const e = preparar(comInativa);
  await processarMensagem(TEL, texto('oi'), 'w1');

  await processarMensagem(TEL, texto('2'), 'w2');

  assert.equal(e.sessoes.get(TEL)!.categoriaId, 3, 'a 2ª ativa é MUDANÇA DE CNPJ, id 3');
});

// =========================================================================
// Assunto de uso interno (`visivelNoWhatsapp: false`)
//
// O eixo é SEPARADO de `ativa`, e é isso que estes testes protegem: o assunto
// interno está VIVO - classifica chamado e soma no relatório -, só não é
// oferecido na conversa. Confundir os dois campos devolveria o problema que a
// coluna resolve: hoje, esconder um assunto do cliente exigiria desativá-lo, e
// aí ele sumiria também do seletor do painel, que é onde ele precisa estar.
// =========================================================================

test('assunto de uso interno não aparece no menu, e a numeração não ganha buraco', async () => {
  const comInterna = ASSUNTOS.map((c) => (c.id === 2 ? { ...c, visivelNoWhatsapp: false } : c));
  preparar(comInterna);

  await processarMensagem(TEL, texto('oi'), 'w1');

  const corpo = captura.ultimoTexto();
  assert.ok(!corpo.includes('SUPORTE A FRANQUEADORA'), 'o interno some do menu');

  // Mesma regra do inativo: o número é a posição entre as OFERECIDAS.
  assert.match(corpo, /1\. CADASTRO NO IFOOD/);
  assert.match(corpo, /2\. MUDANÇA DE CNPJ/);
  assert.ok(!/3\. MUDANÇA DE CNPJ/.test(corpo), 'a numeração não pode pular');
});

test('o número que o assunto interno "teria" escolhe o seguinte, não ele', async () => {
  const comInterna = ASSUNTOS.map((c) => (c.id === 2 ? { ...c, visivelNoWhatsapp: false } : c));
  const e = preparar(comInterna);
  await processarMensagem(TEL, texto('oi'), 'w1');

  await processarMensagem(TEL, texto('2'), 'w2');

  assert.equal(e.sessoes.get(TEL)!.categoriaId, 3, 'a 2ª oferecida é MUDANÇA DE CNPJ, id 3');
});

test('digitar o rótulo do assunto interno por extenso não o escolhe', async () => {
  const comInterna = ASSUNTOS.map((c) => (c.id === 2 ? { ...c, visivelNoWhatsapp: false } : c));
  const e = preparar(comInterna);
  await processarMensagem(TEL, texto('oi'), 'w1');

  // O rótulo digitado é uma das três formas aceitas, e passa pela MESMA
  // whitelist do número. Se ela fosse montada de outra lista que não a do menu,
  // quem soubesse o nome do assunto interno o alcançaria pelo texto.
  await processarMensagem(TEL, texto('SUPORTE A FRANQUEADORA'), 'w2');

  assert.equal(e.sessoes.get(TEL)!.categoriaId, null, 'não escolheu nada');
  assert.equal(e.sessoes.get(TEL)!.etapa, 'categoria');
  assert.match(captura.ultimoTexto(), /não reconheci/i);
});

test('o botão antigo de um assunto que virou interno deixa de ser aceito', async () => {
  const comInterna = ASSUNTOS.map((c) => (c.id === 2 ? { ...c, visivelNoWhatsapp: false } : c));
  const e = preparar(comInterna);
  await processarMensagem(TEL, texto('oi'), 'w1');

  // O WhatsApp mantém clicável o menu antigo no histórico. Marcar um assunto como
  // interno tem de valer também para o toque numa mensagem anterior - senão
  // "esconder do cliente" duraria só até alguém rolar a conversa para cima.
  await processarMensagem(TEL, botao('cat_2'), 'w2');

  assert.equal(e.sessoes.get(TEL)!.categoriaId, null);
  assert.match(captura.ultimoTexto(), /não reconheci/i);
});

test('sub-assunto interno some do menu, e o irmão visível continua', async () => {
  const e = preparar(
    COM_SUBASSUNTOS.map((c) => (c.id === 11 ? { ...c, visivelNoWhatsapp: false } : c))
  );
  await processarMensagem(TEL, texto('oi'), 'w1');

  await processarMensagem(TEL, texto('1'), 'w2');

  const corpo = captura.ultimoTexto();
  assert.match(corpo, /1\. PDV/);
  assert.ok(!corpo.includes('FISCAL'), 'o sub-assunto interno não é oferecido');
  assert.equal(e.sessoes.get(TEL)!.etapa, 'categoria', 'ainda há o que escolher');
});

test('assunto guarda-chuva interno esconde a subárvore inteira', async () => {
  const e = preparar(
    COM_SUBASSUNTOS.map((c) => (c.id === 1 ? { ...c, visivelNoWhatsapp: false } : c))
  );

  await processarMensagem(TEL, texto('oi'), 'w1');

  // As filhas continuam com `visivelNoWhatsapp: true` no banco - o servidor não
  // reescreve as filhas de propósito, para religar o pai devolver o ramo inteiro.
  // Quem as torna inalcançáveis é a navegação: o menu desce um nível por vez, e
  // um pai que nunca é oferecido nunca vira o nó cujas filhas são consultadas.
  const corpo = captura.ultimoTexto();
  assert.ok(!corpo.includes('SUPORTE AO SISTEMA VETOR'), 'o pai interno some');
  assert.ok(!corpo.includes('PDV'), 'e as filhas dele não sobem para a raiz');
  assert.ok(!corpo.includes('FISCAL'));
  assert.match(corpo, /1\. CADASTRO NO IFOOD/, 'a outra raiz continua, renumerada');

  await processarMensagem(TEL, texto('1'), 'w2');
  assert.equal(e.sessoes.get(TEL)!.categoriaId, 2, 'o 1 é CADASTRO NO IFOOD');
});

test('guarda-chuva visível com todas as filhas internas para no pai', async () => {
  const e = preparar(
    COM_SUBASSUNTOS.map((c) => (c.paiId === 1 ? { ...c, visivelNoWhatsapp: false } : c))
  );
  await processarMensagem(TEL, texto('oi'), 'w1');

  await processarMensagem(TEL, texto('1'), 'w2');

  // Sem filha oferecível, o nó vira folha: é o mesmo caminho de quando todas as
  // filhas são desativadas. Melhor do que um menu vazio - e o pai é justamente o
  // nível que o cliente sabe nomear; o refino fica para quem atende.
  assert.equal(e.sessoes.get(TEL)!.categoriaId, 1, 'a escolha parou no pai');
  assert.equal(e.sessoes.get(TEL)!.etapa, 'nome');
  assert.match(captura.ultimoTexto(), /qual é o seu nome/i);
});

test('com todos os assuntos internos a etapa é pulada, e a conversa não trava', async () => {
  const todosInternos = ASSUNTOS.map((c) => ({ ...c, visivelNoWhatsapp: false }));
  const e = preparar(todosInternos);

  await processarMensagem(TEL, texto('oi'), 'w1');

  assert.equal(e.sessoes.get(TEL)!.etapa, 'nome');
  assert.match(captura.ultimoTexto(), /qual é o seu nome/i);

  await processarMensagem(TEL, texto('Natan'), 'w2');
  assert.equal(e.sessoes.get(TEL)!.nome, 'Natan');
});

test('sem assunto oferecível, "Corrigir: Assunto" não entra no menu de confirmação', async () => {
  const todosInternos = ASSUNTOS.map((c) => ({ ...c, visivelNoWhatsapp: false }));
  preparar(todosInternos);

  await processarMensagem(TEL, texto('oi'), 'w1');
  await processarMensagem(TEL, texto('Natan'), 'w2');
  await processarMensagem(TEL, texto('Sistema fora do ar'), 'w3');
  await processarMensagem(TEL, texto('Desde as 9h não consigo acessar.'), 'w4');

  // Oferecer "corrigir o assunto" levaria a um menu que não tem nenhuma opção -
  // e o usuário ficaria repetindo a escolha sem saber o que responder.
  const corpo = captura.ultimoTexto();
  assert.ok(!/Corrigir: Assunto/i.test(corpo), 'não há assunto para corrigir');
  assert.match(corpo, /Confirmar e abrir o chamado/);
});

test('marcar como interno alcança a conversa que JÁ ESTAVA dentro do ramo', async () => {
  const e = preparar(COM_SUBASSUNTOS);
  await processarMensagem(TEL, texto('oi'), 'w1');
  await processarMensagem(TEL, texto('1'), 'w2'); // desceu para as filhas de 1
  assert.equal(e.sessoes.get(TEL)!.categoriaId, 1, 'está dentro do guarda-chuva');

  // Agora o painel marca o guarda-chuva como de uso interno, com a conversa
  // aberta. O filtro do menu olha as FILHAS, e elas continuam com a coluna
  // intacta - sem o reset do nó, esta pessoa continuaria recebendo PDV e FISCAL
  // por horas, até a sessão expirar.
  e.categorias.find((c) => c.id === 1)!.visivelNoWhatsapp = false;

  await processarMensagem(TEL, texto('1'), 'w3');

  const corpo = captura.ultimoTexto();
  assert.ok(!corpo.includes('PDV'), 'as filhas do ramo interno param de ser oferecidas');
  assert.ok(!corpo.includes('FISCAL'));
  assert.match(corpo, /deixou de estar disponível/i, 'e a pessoa é avisada do porquê');
  assert.match(corpo, /1\. CADASTRO NO IFOOD/, 'voltou para o menu raiz');
  assert.equal(e.sessoes.get(TEL)!.categoriaId, null, 'o nó foi resetado');
  assert.equal(e.sessoes.get(TEL)!.etapa, 'categoria', 'e a escolha recomeça');
});

test('o reset do nó vale antes de INTERPRETAR, e não só de exibir', async () => {
  const e = preparar(COM_SUBASSUNTOS);
  await processarMensagem(TEL, texto('oi'), 'w1');
  await processarMensagem(TEL, texto('1'), 'w2');

  e.categorias.find((c) => c.id === 1)!.visivelNoWhatsapp = false;

  // "1" era PDV no menu que a pessoa tem na tela. Duas coisas não podem
  // acontecer, e a segunda é a menos óbvia:
  //   - gravar PDV, que é o assunto do ramo que acabou de ser escondido;
  //   - gravar o "1" do menu NOVO, que é outro assunto inteiro. A resposta foi
  //     escrita lendo uma lista que não vale mais, então ela é descartada e o
  //     menu volta com o aviso.
  await processarMensagem(TEL, texto('1'), 'w3');

  const sessao = e.sessoes.get(TEL)!;
  assert.equal(sessao.categoriaId, null, 'nem PDV, nem o 1 do menu novo');
  assert.equal(sessao.etapa, 'categoria', 'a etapa não avançou com uma escolha que ninguém fez');
  assert.match(captura.ultimoTexto(), /deixou de estar disponível/i);
});

test('desativar o guarda-chuva no meio da conversa tem o mesmo efeito', async () => {
  const e = preparar(COM_SUBASSUNTOS);
  await processarMensagem(TEL, texto('oi'), 'w1');
  await processarMensagem(TEL, texto('1'), 'w2');

  // O furo era o mesmo para `ativa`, e a correção é uma só: quem valida o nó
  // atual cobre os dois eixos.
  e.categorias.find((c) => c.id === 1)!.ativa = false;

  await processarMensagem(TEL, texto('1'), 'w3');

  assert.equal(e.sessoes.get(TEL)!.categoriaId, null, 'voltou para a raiz');
  assert.match(captura.ultimoTexto(), /deixou de estar disponível/i);
  assert.match(captura.ultimoTexto(), /1\. CADASTRO NO IFOOD/);

  // E o menu novo funciona normalmente na mensagem seguinte.
  await processarMensagem(TEL, texto('1'), 'w4');
  assert.equal(e.sessoes.get(TEL)!.categoriaId, 2, 'o 1 do menu raiz é CADASTRO NO IFOOD');
  assert.equal(e.sessoes.get(TEL)!.etapa, 'nome');
});

test('o nó válido não é mexido: quem está num ramo normal continua onde estava', async () => {
  const e = preparar(COM_SUBASSUNTOS);
  await processarMensagem(TEL, texto('oi'), 'w1');
  await processarMensagem(TEL, texto('1'), 'w2');

  // Nada mudou no painel. O reset não pode disparar por conta própria, senão
  // toda conversa com sub-assunto voltaria ao início a cada mensagem.
  await processarMensagem(TEL, texto('nao entendi'), 'w3');

  assert.equal(e.sessoes.get(TEL)!.categoriaId, 1, 'continua dentro do guarda-chuva');
  assert.match(captura.ultimoTexto(), /1\. PDV/);
});

test('assunto com sub-assuntos desce um nível em vez de fechar a escolha', async () => {
  const e = preparar(COM_SUBASSUNTOS);
  await processarMensagem(TEL, texto('oi'), 'w1');

  await processarMensagem(TEL, texto('1'), 'w2');

  assert.equal(e.sessoes.get(TEL)!.etapa, 'categoria', 'ainda escolhendo');
  assert.equal(e.sessoes.get(TEL)!.categoriaId, 1, 'aqui a coluna é ONDE ESTOU, não a escolha');

  const corpo = captura.ultimoTexto();
  assert.match(corpo, /1\. PDV/);
  assert.match(corpo, /2\. FISCAL/);
  assert.match(corpo, /0 para voltar/i);

  await processarMensagem(TEL, texto('2'), 'w3');

  assert.equal(e.sessoes.get(TEL)!.categoriaId, 11, 'a folha FISCAL');
  assert.equal(e.sessoes.get(TEL)!.etapa, 'nome');
  assert.match(captura.ultimoTexto(), /SUPORTE AO SISTEMA VETOR \/ FISCAL/);
});

test('"0" volta um nível na árvore', async () => {
  const e = preparar(COM_SUBASSUNTOS);
  await processarMensagem(TEL, texto('oi'), 'w1');
  await processarMensagem(TEL, texto('1'), 'w2');

  await processarMensagem(TEL, texto('0'), 'w3');

  assert.equal(e.sessoes.get(TEL)!.categoriaId, null, 'voltou para a raiz');
  assert.equal(e.sessoes.get(TEL)!.etapa, 'categoria');
  assert.match(captura.ultimoTexto(), /1\. SUPORTE AO SISTEMA VETOR/);
});

test('"0" na raiz não é opção e cai na recusa', async () => {
  const e = preparar(ASSUNTOS);
  await processarMensagem(TEL, texto('oi'), 'w1');

  await processarMensagem(TEL, texto('0'), 'w2');

  assert.equal(e.sessoes.get(TEL)!.etapa, 'categoria');
  assert.match(captura.ultimoTexto(), /não reconheci/i);
  assert.ok(!captura.ultimoTexto().includes('0 para voltar'), 'não há para onde voltar na raiz');
});

test('botão de um menu antigo, de outro ramo, não é aceito', async () => {
  const e = preparar(COM_SUBASSUNTOS);
  await processarMensagem(TEL, texto('oi'), 'w1');
  await processarMensagem(TEL, texto('1'), 'w2'); // desceu para as filhas de 1

  // O WhatsApp deixa os botões antigos clicáveis no histórico. `cat_2` é uma
  // RAIZ, e não está sendo oferecida neste nível: aceitar seria pular para outro
  // ramo da árvore por um toque numa mensagem de três atrás.
  await processarMensagem(TEL, botao('cat_2'), 'w3');

  assert.equal(e.sessoes.get(TEL)!.categoriaId, 1, 'continua onde estava');
  assert.equal(e.sessoes.get(TEL)!.etapa, 'categoria');
  assert.match(captura.ultimoTexto(), /não reconheci/i);
});

test('sem nenhum assunto ativo a etapa é pulada, e a conversa não trava', async () => {
  const todasInativas = ASSUNTOS.map((c) => ({ ...c, ativa: false }));
  const e = preparar(todasInativas);

  await processarMensagem(TEL, texto('oi'), 'w1');

  assert.equal(e.sessoes.get(TEL)!.etapa, 'nome');
  assert.match(captura.ultimoTexto(), /qual é o seu nome/i);

  await processarMensagem(TEL, texto('Natan'), 'w2');
  assert.equal(e.sessoes.get(TEL)!.nome, 'Natan');
});

test('o chamado nasce com o assunto escolhido, e a confirmação o mostra', async () => {
  const e = preparar(ASSUNTOS);

  await processarMensagem(TEL, texto('oi'), 'w1');
  await processarMensagem(TEL, texto('5'), 'w2');
  await processarMensagem(TEL, texto('Natan'), 'w3');
  await processarMensagem(TEL, texto('Sistema fora do ar'), 'w4');
  await processarMensagem(TEL, texto('Desde as 9h não consigo acessar.'), 'w5');

  const confirmacao = captura.ultimoTexto();
  assert.match(confirmacao, /Confirma a abertura/);
  assert.match(confirmacao, /\*Assunto:\* SUPORTE AO FRANQUEADO/);

  await processarMensagem(TEL, botao('confirmar'), 'w6');

  assert.equal(e.chamados.length, 1);
  assert.equal(e.chamados[0].categoriaId, 5);
});

test('o menu de correção passa a oferecer o assunto', async () => {
  preparar(ASSUNTOS, {
    telefone: TEL,
    etapa: 'confirmacao',
    categoriaId: 5,
    nome: 'Natan',
    resumo: 'r',
    descricao: 'd',
  });

  await processarMensagem(TEL, botao('editar'), 'w1');

  // O menu foi ACHATADO: confirmar, as correções e cancelar num nível só. O id
  // não trafega mais, então o que se observa é a ordem dos rótulos.
  const rotulos = captura.ultimasOpcoes().map((o) => o.texto);
  assert.match(rotulos[0], /confirmar/i, 'confirmar é sempre a primeira');
  assert.match(rotulos[rotulos.length - 1], /cancelar/i, 'cancelar é sempre a última');
  assert.ok(
    rotulos.some((r) => /assunto/i.test(r)),
    'com categoria ativa, o assunto entra no menu'
  );
  for (const campo of ['nome', 'resumo', 'descrição']) {
    assert.ok(
      rotulos.some((r) => new RegExp(campo, 'i').test(r)),
      `o campo ${campo} deveria estar no menu`
    );
  }
});

test('sem categoria ativa, o assunto não entra no menu de correção', async () => {
  preparar([], {
    telefone: TEL,
    etapa: 'confirmacao',
    nome: 'Natan',
    resumo: 'r',
    descricao: 'd',
  });

  await processarMensagem(TEL, botao('editar'), 'w1');

  const rotulos = captura.ultimasOpcoes().map((o) => o.texto);
  assert.equal(
    rotulos.some((r) => /assunto/i.test(r)),
    false,
    'oferecer o assunto levaria a um menu vazio'
  );
});

test('corrigir o assunto reinicia o menu do topo e volta para a confirmação', async () => {
  const e = preparar(COM_SUBASSUNTOS, {
    telefone: TEL,
    etapa: 'confirmacao',
    categoriaId: 11, // a folha FISCAL, escolhida antes
    nome: 'Natan',
    resumo: 'r',
    descricao: 'd',
  });

  await processarMensagem(TEL, botao('editar_categoria'), 'w1');

  // O menu tem de voltar para a RAIZ. Se `categoriaId` continuasse apontando
  // para a folha, o menu ofereceria as filhas dela - que não existem - e a
  // correção terminaria sem nunca ter mostrado opção nenhuma.
  assert.equal(e.sessoes.get(TEL)!.etapa, 'categoria');
  assert.equal(e.sessoes.get(TEL)!.categoriaId, null);
  assert.match(captura.ultimoTexto(), /1\. SUPORTE AO SISTEMA VETOR/);
  assert.match(captura.ultimoTexto(), /2\. CADASTRO NO IFOOD/);

  await processarMensagem(TEL, texto('2'), 'w2');

  assert.equal(e.sessoes.get(TEL)!.categoriaId, 2);
  assert.equal(e.sessoes.get(TEL)!.etapa, 'confirmacao', 'edição volta para a confirmação');
  assert.equal(e.sessoes.get(TEL)!.editando, false);
  assert.match(captura.ultimoTexto(), /\*Assunto:\* CADASTRO NO IFOOD/);
});

test('cancelar continua valendo na etapa de assunto', async () => {
  const e = preparar(ASSUNTOS);
  await processarMensagem(TEL, texto('oi'), 'w1');

  await processarMensagem(TEL, texto('cancelar'), 'w2');

  assert.equal(e.sessoes.has(TEL), false);
  assert.match(captura.ultimoTexto(), /cancelei/i);
});

test('áudio na etapa de assunto explica a limitação e repete o menu', async () => {
  const e = preparar(ASSUNTOS);
  await processarMensagem(TEL, texto('oi'), 'w1');

  await processarMensagem(TEL, { tipo: 'midia', formato: 'áudio' }, 'w2');

  assert.equal(e.sessoes.get(TEL)!.etapa, 'categoria');
  const corpo = captura.ultimoTexto();
  assert.match(corpo, /só consigo ler mensagens de texto/i);
  assert.match(corpo, /1\. CADASTRO NO IFOOD/, 'o menu volta junto com o aviso');
});

// =========================================================================
// API de assuntos (o painel)
// =========================================================================

function pedir(metodo: string, url: string, payload?: unknown, token: string | null = TOKEN) {
  return app.inject({
    method: metodo as any,
    url,
    payload: payload as any,
    headers: token === null ? {} : { authorization: `Bearer ${token}` },
  });
}

test('listagem de categorias exige token', async () => {
  preparar(ASSUNTOS);
  const r = await pedir('GET', '/internal/categorias', undefined, null);
  assert.equal(r.statusCode, 401);
});

test('listagem devolve a árvore inteira, inclusive as inativas', async () => {
  const comInativa = ASSUNTOS.map((c) => (c.id === 2 ? { ...c, ativa: false } : c));
  preparar(comInativa);

  const r = await pedir('GET', '/internal/categorias');
  assert.equal(r.statusCode, 200);

  const { categorias } = r.json();
  assert.equal(categorias.length, 6, 'a inativa continua na lista do painel');
  const inativa = categorias.find((c: any) => c.id === 2);
  assert.equal(inativa.ativa, false, 'sem isto não haveria como reativá-la');
  assert.equal(inativa.chamados, 0);
});

test('listagem devolve as de uso interno junto, com a marcação', async () => {
  const comInterna = ASSUNTOS.map((c) => (c.id === 2 ? { ...c, visivelNoWhatsapp: false } : c));
  preparar(comInterna);

  const { categorias } = (await pedir('GET', '/internal/categorias')).json();

  // O painel é o ÚNICO lugar onde o assunto interno aparece - é o que faz dele
  // um assunto e não um registro morto. Filtrá-lo aqui esvaziaria o recurso.
  assert.equal(categorias.length, 6);
  const interna = categorias.find((c: any) => c.id === 2);
  assert.equal(interna.visivelNoWhatsapp, false);
  assert.equal(interna.ativa, true, 'interno não é o mesmo que desativado');

  const comum = categorias.find((c: any) => c.id === 1);
  assert.equal(comum.visivelNoWhatsapp, true, 'o campo vem em todas, não só nas internas');
});

test('criar sem dizer nada nasce visível no WhatsApp', async () => {
  preparar(ASSUNTOS);

  const r = await pedir('POST', '/internal/categorias', {
    codigo: 'trocas_devolucoes',
    nome: 'TROCAS E DEVOLUÇÕES',
    rotulo: 'TROCAS E DEVOLUÇÕES',
  });

  assert.equal(r.statusCode, 201);
  assert.equal(r.json().visivelNoWhatsapp, true, 'assunto de atendimento é o padrão');
});

test('criar já como de uso interno é aceito', async () => {
  const e = preparar(ASSUNTOS);

  const r = await pedir('POST', '/internal/categorias', {
    codigo: 'infra_interna',
    nome: 'INFRAESTRUTURA INTERNA',
    rotulo: 'INFRAESTRUTURA INTERNA',
    visivelNoWhatsapp: false,
  });

  assert.equal(r.statusCode, 201);
  assert.equal(r.json().visivelNoWhatsapp, false);
  assert.equal(r.json().ativa, true, 'nasce vivo, só não é oferecido');

  const criada = e.categorias.find((c) => c.codigo === 'infra_interna')!;
  assert.equal(criada.visivelNoWhatsapp, false, 'foi para o banco, não só para a resposta');
});

test('marcar um assunto existente como de uso interno não mexe em mais nada', async () => {
  const e = preparar(ASSUNTOS);

  const r = await pedir('PATCH', '/internal/categorias/4', { visivelNoWhatsapp: false });

  assert.equal(r.statusCode, 200);
  assert.equal(r.json().visivelNoWhatsapp, false);

  // A separação inteira depende disto: quem esconde um assunto do cliente NÃO
  // está tirando ele de circulação, e um `ativa` derrubado junto quebraria o
  // seletor do painel - que é justamente onde o assunto tem de continuar.
  assert.equal(r.json().ativa, true);
  assert.equal(e.categorias.find((c) => c.id === 4)!.ativa, true);
});

test('voltar o assunto para o menu é o mesmo PATCH ao contrário', async () => {
  const e = preparar(ASSUNTOS.map((c) => (c.id === 4 ? { ...c, visivelNoWhatsapp: false } : c)));

  const r = await pedir('PATCH', '/internal/categorias/4', { visivelNoWhatsapp: true });

  assert.equal(r.statusCode, 200);
  assert.equal(e.categorias.find((c) => c.id === 4)!.visivelNoWhatsapp, true);
});

test('marcar o pai como interno não reescreve as filhas', async () => {
  const e = preparar(COM_SUBASSUNTOS);

  await pedir('PATCH', '/internal/categorias/1', { visivelNoWhatsapp: false });

  // Elas já ficam inalcançáveis na conversa (a navegação desce um nível por vez),
  // e é por isso que a coluna delas pode ficar quieta. O ganho é reversível:
  // religar o pai devolve o ramo exatamente como estava, sem ninguém ter de
  // lembrar quais filhas eram internas por conta própria.
  assert.equal(e.categorias.find((c) => c.id === 10)!.visivelNoWhatsapp, true);
  assert.equal(e.categorias.find((c) => c.id === 11)!.visivelNoWhatsapp, true);
});

test('a contagem de chamados vem junto, para o painel saber se dá para excluir', async () => {
  const e = preparar(ASSUNTOS);
  e.chamados.push({ id: 1, categoriaId: 4 }, { id: 2, categoriaId: 4 }, { id: 3, categoriaId: 1 });

  const { categorias } = (await pedir('GET', '/internal/categorias')).json();

  assert.equal(categorias.find((c: any) => c.id === 4).chamados, 2);
  assert.equal(categorias.find((c: any) => c.id === 1).chamados, 1);
  assert.equal(categorias.find((c: any) => c.id === 6).chamados, 0);
});

test('criar categoria sem ordem a coloca no fim das irmãs', async () => {
  const e = preparar(ASSUNTOS);

  const r = await pedir('POST', '/internal/categorias', {
    codigo: 'trocas_devolucoes',
    nome: 'TROCAS E DEVOLUÇÕES',
    rotulo: 'TROCAS E DEVOLUÇÕES',
  });

  assert.equal(r.statusCode, 201);
  assert.equal(r.json().ordem, 7, 'entra depois da última, sem precisar dizer a posição');
  assert.equal(r.json().chamados, 0);
  assert.equal(e.categorias.length, 7);
});

test('código repetido é recusado com 409, e não com erro interno', async () => {
  preparar(ASSUNTOS);

  const r = await pedir('POST', '/internal/categorias', {
    codigo: 'mudanca_cnpj',
    nome: 'OUTRA COISA',
    rotulo: 'OUTRA COISA',
  });

  assert.equal(r.statusCode, 409);
  assert.match(r.json().erro, /já existe/i);
});

test('código com espaço ou acento é recusado na validação', async () => {
  preparar(ASSUNTOS);

  const r = await pedir('POST', '/internal/categorias', {
    codigo: 'Mudança de CNPJ',
    nome: 'X',
    rotulo: 'X',
  });

  assert.equal(r.statusCode, 400, 'o código é chave estável, não um segundo rótulo');
});

test('renomear muda o rótulo sem tocar no código', async () => {
  const e = preparar(ASSUNTOS);

  const r = await pedir('PATCH', '/internal/categorias/4', { rotulo: 'SUPORTE VETOR' });

  assert.equal(r.statusCode, 200);
  assert.equal(r.json().rotulo, 'SUPORTE VETOR');
  assert.equal(e.categorias.find((c) => c.id === 4)!.codigo, 'sistema_vetor');
});

test('desativar não apaga: o chamado continua apontando para ela', async () => {
  const e = preparar(ASSUNTOS);
  e.chamados.push({ id: 1, categoriaId: 4 });

  const r = await pedir('PATCH', '/internal/categorias/4', { ativa: false });

  assert.equal(r.statusCode, 200);
  assert.equal(r.json().ativa, false);
  assert.equal(e.chamados[0].categoriaId, 4, 'o histórico do dashboard não pode se perder');
});

test('mover uma categoria para debaixo da própria filha é recusado', async () => {
  preparar(COM_SUBASSUNTOS);

  // 10 (PDV) é filha de 1. Pendurar 1 embaixo de 10 fecharia um ciclo - e um
  // ciclo aqui faria o menu descer para sempre dentro da transação do usuário.
  const r = await pedir('PATCH', '/internal/categorias/1', { paiId: 10 });

  assert.equal(r.statusCode, 400);
  assert.match(r.json().erro, /ciclo/i);
});

test('uma categoria não pode ser pai dela mesma', async () => {
  preparar(ASSUNTOS);
  const r = await pedir('PATCH', '/internal/categorias/4', { paiId: 4 });
  assert.equal(r.statusCode, 400);
});

test('paiId inexistente é recusado', async () => {
  preparar(ASSUNTOS);
  const r = await pedir('PATCH', '/internal/categorias/4', { paiId: 999 });
  assert.equal(r.statusCode, 400);
  assert.match(r.json().erro, /paiId/);
});

test('paiId nulo promove a categoria a raiz', async () => {
  const e = preparar(COM_SUBASSUNTOS);

  const r = await pedir('PATCH', '/internal/categorias/10', { paiId: null });

  assert.equal(r.statusCode, 200);
  assert.equal(e.categorias.find((c) => c.id === 10)!.paiId, null);
});

test('excluir categoria em uso é recusado com 409 e manda desativar', async () => {
  const e = preparar(ASSUNTOS);
  e.chamados.push({ id: 1, categoriaId: 4 });

  const r = await pedir('DELETE', '/internal/categorias/4');

  assert.equal(r.statusCode, 409);
  assert.match(r.json().erro, /desative/i);
  assert.equal(e.categorias.length, 6, 'nada foi apagado');
});

test('excluir categoria com sub-assuntos é recusado', async () => {
  const e = preparar(COM_SUBASSUNTOS);

  const r = await pedir('DELETE', '/internal/categorias/1');

  assert.equal(r.statusCode, 409);
  assert.match(r.json().erro, /sub-assunto/i);
  assert.equal(e.categorias.length, 4);
});

test('excluir categoria sem uso e sem filhas funciona', async () => {
  const e = preparar(ASSUNTOS);

  const r = await pedir('DELETE', '/internal/categorias/6');

  assert.equal(r.statusCode, 200);
  assert.deepEqual(r.json(), { id: 6, apagada: true });
  assert.equal(e.categorias.length, 5);
});

// =========================================================================
// Assunto do chamado, pelo quadro
// =========================================================================

function comChamado(categoriaId: number | null = null): Estado {
  const e = preparar(ASSUNTOS);
  e.chamados.push({
    id: 100,
    nome: 'Natan',
    telefone: TEL,
    resumo: 'Sistema fora',
    descricao: 'Desde as 9h',
    situacao: 'aberto',
    origem: 'whatsapp',
    categoriaId,
    dataAbertura: new Date('2026-08-27T12:00:00Z'),
    atualizadoEm: new Date('2026-08-27T12:00:00Z'),
    primeiroAtendimentoEm: null,
    resolvidoEm: null,
  });
  return e;
}

test('o quadro consegue classificar um chamado que veio sem assunto', async () => {
  const e = comChamado(null);

  const r = await pedir('PATCH', '/internal/chamados/100/categoria', { categoriaId: 3 });

  assert.equal(r.statusCode, 200);
  assert.deepEqual(r.json(), { id: 100, categoriaId: 3 });
  assert.equal(e.chamados[0].categoriaId, 3);
});

test('trocar o assunto não notifica ninguém nem entra na auditoria de situação', async () => {
  const e = comChamado(4);

  await pedir('PATCH', '/internal/chamados/100/categoria', { categoriaId: 3 });

  assert.equal(captura.enviados.length, 0, 'correção de classificação não é evento de atendimento');
  assert.equal(e.mudancas.length, 0, 'MudancaSituacao é auditoria de SITUAÇÃO');
});

test('classificar com categoria inativa é permitido', async () => {
  const e = comChamado(null);
  e.categorias.find((c) => c.id === 4)!.ativa = false;

  const r = await pedir('PATCH', '/internal/chamados/100/categoria', { categoriaId: 4 });

  // Ela sumiu do menu do WhatsApp, mas continua sendo classificação válida para
  // quem atende - recusar impediria corrigir o chamado para o assunto certo.
  assert.equal(r.statusCode, 200);
});

test('classificar com assunto de uso interno é o caso de uso, não a exceção', async () => {
  const e = comChamado(null);
  e.categorias.find((c) => c.id === 4)!.visivelNoWhatsapp = false;

  const r = await pedir('PATCH', '/internal/chamados/100/categoria', { categoriaId: 4 });

  // O assunto interno existe PARA isto: classificar do lado de cá o que o
  // cliente nunca escolheu na conversa. Recusar aqui seria recusar o recurso.
  assert.equal(r.statusCode, 200);
  assert.equal(e.chamados.find((c) => c.id === 100)!.categoriaId, 4);
});

test('categoria inexistente é recusada', async () => {
  comChamado(null);
  const r = await pedir('PATCH', '/internal/chamados/100/categoria', { categoriaId: 999 });
  assert.equal(r.statusCode, 400);
});

test('tirar o assunto do chamado é uma operação válida', async () => {
  const e = comChamado(4);
  const r = await pedir('PATCH', '/internal/chamados/100/categoria', { categoriaId: null });

  assert.equal(r.statusCode, 200);
  assert.equal(e.chamados[0].categoriaId, null);
});

test('tarefa criada no painel pode nascer com assunto', async () => {
  const e = preparar(ASSUNTOS);

  const r = await pedir('POST', '/internal/tarefas', {
    nome: 'Equipe',
    resumo: 'Trocar cabo do PDV 3',
    descricao: 'Cabo de rede rompido',
    categoriaId: 4,
  });

  assert.equal(r.statusCode, 201);
  assert.equal(e.chamados[0].categoriaId, 4);
  assert.equal(e.chamados[0].origem, 'painel');
});

test('tarefa com categoria inexistente é recusada', async () => {
  preparar(ASSUNTOS);
  const r = await pedir('POST', '/internal/tarefas', {
    nome: 'Equipe',
    resumo: 'Trocar cabo',
    descricao: 'Cabo rompido',
    categoriaId: 999,
  });
  assert.equal(r.statusCode, 400);
});

test('a listagem entrega o assunto e os marcos de SLA', async () => {
  const e = comChamado(4);
  e.chamados[0].primeiroAtendimentoEm = new Date('2026-08-27T12:30:00Z');

  const { chamados } = (await pedir('GET', '/internal/chamados')).json();

  assert.equal(chamados[0].categoriaId, 4);
  assert.equal(chamados[0].primeiroAtendimentoEm, '2026-08-27T12:30:00.000Z');
  assert.equal(chamados[0].resolvidoEm, null, 'marco que não aconteceu é null, não some');
});

// =========================================================================
// Marcos de SLA
// =========================================================================

function mover(situacao: string) {
  return pedir('PATCH', '/internal/chamados/100/situacao', { situacao });
}

test('sair de aberto grava o primeiro atendimento', async () => {
  const e = comChamado();

  await mover('em_andamento');

  assert.ok(e.chamados[0].primeiroAtendimentoEm instanceof Date);
  assert.equal(e.chamados[0].resolvidoEm, null);
});

test('o primeiro atendimento não se repete quando o chamado é reaberto', async () => {
  const e = comChamado();

  await mover('em_andamento');
  const primeiro = e.chamados[0].primeiroAtendimentoEm;

  await mover('aberto');
  await mover('em_andamento');

  // "Tempo até alguém pegar" mede a espera ORIGINAL do solicitante. Regravar aqui
  // faria um chamado reaberto e pego de novo aparecer como atendido na hora.
  assert.equal(e.chamados[0].primeiroAtendimentoEm, primeiro);
});

test('resolver grava o marco, e reabrir o zera', async () => {
  const e = comChamado();

  await mover('resolvido');
  assert.ok(e.chamados[0].resolvidoEm instanceof Date);

  await mover('aberto');
  // Chamado reaberto NÃO está resolvido. Sem zerar, a média de tempo de
  // resolução contaria uma resolução desfeita.
  assert.equal(e.chamados[0].resolvidoEm, null);
});

test('ir direto de aberto para resolvido grava os dois marcos', async () => {
  const e = comChamado();

  await mover('resolvido');

  assert.ok(e.chamados[0].primeiroAtendimentoEm instanceof Date, 'também foi uma saída de aberto');
  assert.ok(e.chamados[0].resolvidoEm instanceof Date);
});

test('repetir a situação atual não move marco nenhum', async () => {
  const e = comChamado();

  await mover('aberto');

  assert.equal(e.chamados[0].primeiroAtendimentoEm, null);
  assert.equal(e.mudancas.length, 0, 'nem histórico, pela mesma regra');
});

test('cancelar conta como saída de aberto, mas não como resolução', async () => {
  const e = comChamado();

  await mover('cancelado');

  assert.ok(e.chamados[0].primeiroAtendimentoEm instanceof Date);
  assert.equal(e.chamados[0].resolvidoEm, null);
});

// =========================================================================
// Métricas
// =========================================================================

const HORA = 60 * 60 * 1000;

function comHistorico(): Estado {
  const e = preparar(ASSUNTOS);
  const base = new Date('2026-08-20T09:00:00Z').getTime();

  const chamado = (
    id: number,
    categoriaId: number | null,
    situacao: string,
    dias: number,
    atendimentoH: number | null,
    resolucaoH: number | null
  ) => ({
    id,
    nome: 'n',
    resumo: 'r',
    descricao: 'd',
    origem: 'whatsapp',
    situacao,
    categoriaId,
    dataAbertura: new Date(base + dias * 24 * HORA),
    atualizadoEm: new Date(base + dias * 24 * HORA),
    primeiroAtendimentoEm:
      atendimentoH === null ? null : new Date(base + dias * 24 * HORA + atendimentoH * HORA),
    resolvidoEm: resolucaoH === null ? null : new Date(base + dias * 24 * HORA + resolucaoH * HORA),
  });

  e.chamados.push(
    chamado(1, 4, 'resolvido', 0, 1, 3), // vetor: 60 min para pegar, 180 para resolver
    chamado(2, 4, 'resolvido', 1, 3, 5), // vetor: 180 min / 300 min
    chamado(3, 4, 'aberto', 2, null, null), // vetor: ainda esperando
    chamado(4, 1, 'em_andamento', 3, 2, null), // ifood: 120 min, sem resolução
    chamado(5, null, 'aberto', 4, null, null) // sem assunto
  );
  return e;
}

test('métricas exigem token', async () => {
  comHistorico();
  const r = await pedir('GET', '/internal/metricas', undefined, null);
  assert.equal(r.statusCode, 401);
});

test('métricas separam os números por assunto', async () => {
  comHistorico();

  const r = await pedir('GET', '/internal/metricas');
  assert.equal(r.statusCode, 200);
  const { geral, porCategoria } = r.json();

  assert.equal(geral.total, 5);
  assert.equal(geral.aberto, 2);
  assert.equal(geral.em_andamento, 1);
  assert.equal(geral.resolvido, 2);

  // Maior volume primeiro: é a ordem em que a lista responde "onde está o
  // atendimento".
  assert.equal(porCategoria[0].codigo, 'sistema_vetor');
  assert.equal(porCategoria[0].total, 3);

  const soma = porCategoria.reduce((t: number, c: any) => t + c.total, 0);
  assert.equal(soma, geral.total, 'o total por assunto tem de fechar com o geral');
});

test('chamado sem assunto entra como "sem assunto" em vez de sumir', async () => {
  comHistorico();

  const { porCategoria } = (await pedir('GET', '/internal/metricas')).json();
  const sem = porCategoria.find((c: any) => c.codigo === 'sem_categoria');

  // Chamado sem assunto continua sendo atendimento: descartar a linha faria o
  // relatório mostrar menos trabalho do que houve.
  assert.equal(sem.total, 1);
  // `id` e nao `categoriaId`: a mesma linha de metrica descreve grupo de
  // assunto, de setor e de tipo desde que os tres cortes existem, e um campo
  // chamado `categoriaId` dentro do agrupamento por setor seria mentira.
  assert.equal(sem.id, null);
});

test('as médias de SLA saem em minutos, só com quem atingiu o marco', async () => {
  comHistorico();

  const { porCategoria } = (await pedir('GET', '/internal/metricas')).json();
  const vetor = porCategoria.find((c: any) => c.codigo === 'sistema_vetor');

  // Dois dos três chamados foram atendidos (60 e 180 min): média 120. O terceiro
  // ainda espera e NÃO entra na conta - incluí-lo como zero faria a fila parecer
  // mais rápida justamente quando está mais lenta.
  assert.equal(vetor.atendidos, 2);
  assert.equal(vetor.atendimentoMedioMin, 120);

  // Resolução: 180 e 300 min sobre a abertura.
  assert.equal(vetor.resolvidos, 2);
  assert.equal(vetor.resolucaoMediaMin, 240);
});

test('média nula, e não zero, quando ninguém atingiu o marco', async () => {
  comHistorico();

  const { porCategoria } = (await pedir('GET', '/internal/metricas')).json();
  const sem = porCategoria.find((c: any) => c.codigo === 'sem_categoria');

  // Zero minutos e "nunca aconteceu" viram a mesma barra no gráfico se as duas
  // saírem como 0.
  assert.equal(sem.atendimentoMedioMin, null);
  assert.equal(sem.resolucaoMediaMin, null);
  assert.equal(sem.atendidos, 0);
});

test('a janela corta pelas duas pontas', async () => {
  comHistorico();

  // Aberturas em 20, 21, 22, 23 e 24 de agosto. A janela pega 21 e 22.
  const r = await pedir(
    'GET',
    '/internal/metricas?desde=2026-08-21T00:00:00Z&ate=2026-08-22T23:59:59Z'
  );

  assert.equal(r.statusCode, 200);
  assert.equal(r.json().geral.total, 2);
  assert.equal(r.json().janela.desde, '2026-08-21T00:00:00.000Z');
});

test('janela com data inválida é recusada em vez de ignorada', async () => {
  comHistorico();

  // Ignorar em silêncio devolveria número certo do período errado - o pior
  // resultado possível para um relatório.
  const r = await pedir('GET', '/internal/metricas?desde=ontem');

  assert.equal(r.statusCode, 400);
  assert.match(r.json().erro, /desde/);
});

test('categoria desativada continua no relatório', async () => {
  const e = comHistorico();
  e.categorias.find((c) => c.id === 4)!.ativa = false;

  const { porCategoria } = (await pedir('GET', '/internal/metricas')).json();

  // Sumir daqui faria o total por assunto não fechar com o total geral.
  assert.ok(porCategoria.some((c: any) => c.codigo === 'sistema_vetor'));
});
