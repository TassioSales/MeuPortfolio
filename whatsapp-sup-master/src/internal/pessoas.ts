import { FastifyInstance } from 'fastify';
import { prisma } from '../db/client';
import { exigirToken } from './auth';

/**
 * CRUD do cadastro de pessoas do painel.
 *
 * Existe porque a lista precisa ser COMPARTILHADA. Antes ela vivia no
 * `localStorage` de cada navegador, então cada atendente mantinha o seu próprio
 * cadastro e nenhum via o do outro — o oposto do que uma bolha de perfil serve
 * para fazer.
 *
 * NÃO é a lista de quem pode entrar no painel: isso é o Entra ID que decide, na
 * atribuição do App Registration. Aqui é cadastro de EXIBIÇÃO — quem aparece no
 * seletor de "Responsável" e nas bolhas do quadro.
 *
 * Guarda `oid` e `email` desde que o login passou a criar o perfil de quem
 * entra: sem o `oid` não há como reconhecer que o login de hoje é a mesma
 * pessoa do login de ontem, e cada sessão criaria uma linha nova. Nenhum dos
 * dois serve para autenticar nada — a decisão de acesso continua inteira no
 * Entra ID, e a listagem nem devolve o e-mail (ver `CAMPOS`).
 */

const PARAMS = {
  type: 'object',
  properties: { id: { type: 'integer', minimum: 1 } },
  required: ['id'],
} as const;

// `minLength: 0` de propósito: o painel cria a pessoa e só então deixa digitar o
// nome, e a bolha já desenha "?" enquanto ele está vazio. Exigir nome aqui
// obrigaria a tela a inventar um "Nova pessoa" que o atendente teria de apagar.
const NOME = { type: 'string', minLength: 0, maxLength: 120 } as const;

// #RRGGBB — o único formato que o `<input type="color">` emite. Validar aqui é o
// que impede uma chamada fora do painel gravar algo que a tela não sabe pintar.
const COR = { type: 'string', pattern: '^#[0-9a-fA-F]{6}$' } as const;

const PESSOA = {
  type: 'object',
  properties: {
    id: { type: 'integer' },
    nome: { type: 'string' },
    cor: { type: 'string' },
  },
  required: ['id', 'nome', 'cor'],
} as const;

const RESPOSTA_LISTA = {
  type: 'object',
  properties: { pessoas: { type: 'array', items: PESSOA } },
  required: ['pessoas'],
} as const;

const RESPOSTA_APAGADA = {
  type: 'object',
  properties: { id: { type: 'integer' }, apagada: { type: 'boolean' } },
  required: ['id', 'apagada'],
} as const;

const CORPO_CRIAR = {
  type: 'object',
  properties: { nome: NOME, cor: COR },
  required: ['nome', 'cor'],
  additionalProperties: false,
} as const;

// `minProperties: 1` para um PATCH vazio ser 400 em vez de uma escrita que não
// escreve nada e mesmo assim responde 200.
const CORPO_ALTERAR = {
  type: 'object',
  properties: { nome: NOME, cor: COR },
  additionalProperties: false,
  minProperties: 1,
} as const;

type CorpoCriar = { nome: string; cor: string };
type CorpoAlterar = { nome?: string; cor?: string };

// `criadoEm`/`atualizadoEm` existem na tabela e ficam de fora da resposta: a
// tela não os usa, e campo que ninguém lê só cria contrato para manter.
const CAMPOS = { id: true, nome: true, cor: true } as const;

const CORPO_IDENTIDADE = {
  type: 'object',
  properties: {
    oid: { type: 'string', minLength: 1, maxLength: 120 },
    nome: { type: 'string', minLength: 0, maxLength: 120 },
    email: { type: 'string', minLength: 0, maxLength: 200 },
  },
  required: ['oid'],
  additionalProperties: false,
} as const;

type CorpoIdentidade = { oid: string; nome?: string; email?: string };

/**
 * Cor estável a partir do `oid`.
 *
 * Derivada, e não sorteada: o perfil criado pelo login não passa pela tela de
 * cadastro, então ninguém escolheu cor para ele. Tirá-la do `oid` faz a bolha
 * da pessoa ser a MESMA em qualquer instalação e depois de qualquer
 * reinstalação — e continua editável na tela depois, porque a coluna guarda o
 * valor em vez de recalculá-lo a cada leitura.
 */
// A MESMA paleta que o painel usa nas bolhas (`CORES_SOLICITANTE` e
// `PERSON_COLORS` em activity-dashboard/app.js) — o comentário de lá explica
// por que são oito e não dez, e por que elas não mudam com o tema claro/escuro.
// Trocar aqui sem trocar lá pintaria a mesma equipe com duas paletas.
const CORES = [
  '#96421C',
  '#4C3BA8',
  '#8A5000',
  '#3B3F8F',
  '#3D6B33',
  '#5E4B8B',
  '#7A3E12',
  '#0F6068',
];

function corDoOid(oid: string): string {
  let soma = 0;
  for (let i = 0; i < oid.length; i++) soma = (soma + oid.charCodeAt(i)) % 9973;
  return CORES[soma % CORES.length];
}

export function registrarRotasDePessoas(app: FastifyInstance): void {
  /**
   * O perfil de quem acabou de entrar pelo Entra ID.
   *
   * Quem chama é o `servidor-painel.mjs`, no fim do login — do SERVIDOR, nunca
   * do navegador. A diferença importa: a identidade vem do `id_token` que o
   * painel acabou de validar contra as chaves do tenant, e não de um corpo que
   * a página poderia inventar. Uma rota que aceitasse "sou o oid X" vinda do
   * cliente deixaria qualquer um com o token da API criar perfil como qualquer
   * pessoa.
   *
   * Três caminhos, nesta ordem:
   *
   *   1. já existe perfil com esse `oid` -> atualiza nome e e-mail. É o que
   *      mantém o cadastro em dia quando alguém muda de nome no diretório;
   *   2. existe UM perfil com o mesmo nome e sem `oid` -> adota. Cobre o caso
   *      real de quem já tinha sido cadastrado à mão antes do primeiro login,
   *      e é o que evita duas "Ana Souza" na lista. Só com um candidato exato:
   *      com dois, adotar seria escolher no escuro;
   *   3. nada encontrado -> cria.
   *
   * Idempotente de propósito: o login acontece a cada sessão, e isto roda em
   * todos eles.
   */
  app.put<{ Body: CorpoIdentidade }>(
    '/internal/pessoas/identidade',
    {
      onRequest: exigirToken('Acesso negado ao registro de identidade'),
      schema: { body: CORPO_IDENTIDADE, response: { 200: PESSOA } },
    },
    async (req) => {
      const { oid } = req.body;
      const nome = (req.body.nome ?? '').trim();
      const email = (req.body.email ?? '').trim();

      const existente = await prisma.pessoa.findUnique({ where: { oid }, select: { id: true } });
      if (existente) {
        const atualizada = await prisma.pessoa.update({
          where: { id: existente.id },
          // Nome vazio não sobrescreve: um `id_token` sem `name` não pode
          // apagar o nome que alguém ajustou na tela.
          data: { ...(nome !== '' ? { nome } : {}), ...(email !== '' ? { email } : {}) },
          select: CAMPOS,
        });
        return atualizada;
      }

      if (nome !== '') {
        const homonimos = await prisma.pessoa.findMany({
          where: { nome, oid: null },
          select: { id: true },
          take: 2,
        });
        if (homonimos.length === 1) {
          const adotada = await prisma.pessoa.update({
            where: { id: homonimos[0].id },
            data: { oid, ...(email !== '' ? { email } : {}) },
            select: CAMPOS,
          });
          req.log.info({ pessoaId: adotada.id }, 'Perfil existente vinculado ao login');
          return adotada;
        }
      }

      const criada = await prisma.pessoa.create({
        data: { nome, cor: corDoOid(oid), oid, ...(email !== '' ? { email } : {}) },
        select: CAMPOS,
      });
      req.log.info({ pessoaId: criada.id }, 'Perfil criado no primeiro login');
      return criada;
    }
  );

  // Ordem alfabética, com o `id` como desempate: sem o segundo critério, duas
  // pessoas de mesmo nome trocariam de lugar entre uma carga e outra e a fila de
  // bolhas dançaria na tela sem nada ter mudado.
  app.get(
    '/internal/pessoas',
    {
      onRequest: exigirToken('Acesso negado à listagem de pessoas'),
      schema: { response: { 200: RESPOSTA_LISTA } },
    },
    async () => {
      const pessoas = await prisma.pessoa.findMany({
        orderBy: [{ nome: 'asc' }, { id: 'asc' }],
        select: CAMPOS,
      });

      return { pessoas };
    }
  );

  app.post<{ Body: CorpoCriar }>(
    '/internal/pessoas',
    {
      onRequest: exigirToken('Acesso negado à criação de pessoa'),
      schema: { body: CORPO_CRIAR, response: { 201: PESSOA } },
    },
    async (req, reply) => {
      const criada = await prisma.pessoa.create({
        data: { nome: req.body.nome.trim(), cor: req.body.cor },
        select: CAMPOS,
      });

      req.log.info({ pessoaId: criada.id }, 'Pessoa criada');
      return reply.status(201).send(criada);
    }
  );

  app.patch<{ Params: { id: number }; Body: CorpoAlterar }>(
    '/internal/pessoas/:id',
    {
      onRequest: exigirToken('Acesso negado à alteração de pessoa'),
      schema: { params: PARAMS, body: CORPO_ALTERAR, response: { 200: PESSOA } },
    },
    async (req, reply) => {
      const { id } = req.params;

      // Confere antes de escrever para a resposta ser 404, e não o P2025 genérico
      // do Prisma virando 500 — quem chama precisa distinguir "não existe" de
      // "falhou".
      const existe = await prisma.pessoa.findUnique({ where: { id }, select: { id: true } });
      if (!existe) return reply.status(404).send({ erro: 'pessoa não encontrada' });

      const dados: CorpoAlterar = {};
      if (req.body.nome !== undefined) dados.nome = req.body.nome.trim();
      if (req.body.cor !== undefined) dados.cor = req.body.cor;

      return prisma.pessoa.update({ where: { id }, data: dados, select: CAMPOS });
    }
  );

  // Apagar de verdade, e não desativar: diferente de `Categoria`, nada aponta
  // para `Pessoa` — não há histórico para perder nem menu para deslocar.
  app.delete<{ Params: { id: number } }>(
    '/internal/pessoas/:id',
    {
      onRequest: exigirToken('Acesso negado à exclusão de pessoa'),
      schema: { params: PARAMS, response: { 200: RESPOSTA_APAGADA } },
    },
    async (req, reply) => {
      const { id } = req.params;

      const existe = await prisma.pessoa.findUnique({ where: { id }, select: { id: true } });
      if (!existe) return reply.status(404).send({ erro: 'pessoa não encontrada' });

      await prisma.pessoa.delete({ where: { id } });
      req.log.info({ pessoaId: id }, 'Pessoa removida');
      return reply.send({ id, apagada: true });
    }
  );
}
