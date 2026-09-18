import { FastifyInstance } from 'fastify';
import { Prisma } from '../generated/prisma/client';
import { prisma } from '../db/client';
import { exigirToken } from './auth';

/**
 * CRUD dos setores da empresa: TI, Financeiro, Operações, Marketing, Manutenção,
 * RH e o que mais a rede tiver.
 *
 * É a lista que responde "de quem é esse chamado". Mora no banco e é editável
 * aqui, e não num `enum` do Prisma, pela mesma razão de `Categoria`: organograma
 * muda por decisão de negócio, e enum só muda com migração e deploy.
 *
 * NÃO se confunde com as categorias (`internal/categorias.ts`). As duas
 * classificam o mesmo chamado por eixos diferentes, e as rotas são separadas
 * porque as telas que as consomem são separadas:
 *
 *   - categoria é o ASSUNTO que o cliente escolhe no menu numerado do WhatsApp;
 *     mexer nela muda o que o cliente lê na conversa seguinte.
 *   - setor é a ÁREA INTERNA que atende; ela nunca aparece na conversa.
 *
 * Um chamado aponta para setor DUAS vezes - `setorId` (quem resolve) e
 * `setorOrigemId` (quem pediu) -, e é por isso que a contagem de uso somada nas
 * respostas abaixo olha as duas pontas.
 */

const PARAMS = {
  type: 'object',
  properties: { id: { type: 'integer', minimum: 1 } },
  required: ['id'],
} as const;

// `codigo` é o identificador estável: o que um relatório externo usa para casar
// setor por chave e não por texto. Só entra na criação — a rota de alteração não
// o aceita, pelo mesmo desenho de `Categoria`.
const CODIGO = { type: 'string', minLength: 1, maxLength: 60 } as const;
const NOME = { type: 'string', minLength: 1, maxLength: 120 } as const;

const SETOR = {
  type: 'object',
  properties: {
    id: { type: 'integer' },
    codigo: { type: 'string' },
    nome: { type: 'string' },
    ordem: { type: 'integer' },
    ativo: { type: 'boolean' },
    // Quantos chamados este setor ATENDE e quantos ele ABRIU. Os dois números
    // viajam separados porque o painel usa cada um para uma coisa: o primeiro
    // decide se dá para excluir, e os dois juntos são a leitura de carga de
    // trabalho contra volume de demanda.
    chamados: { type: 'integer' },
    origens: { type: 'integer' },
  },
  required: ['id', 'codigo', 'nome', 'ordem', 'ativo', 'chamados', 'origens'],
} as const;

const RESPOSTA_LISTA = {
  type: 'object',
  properties: { setores: { type: 'array', items: SETOR } },
  required: ['setores'],
} as const;

const RESPOSTA_APAGADO = {
  type: 'object',
  properties: { id: { type: 'integer' }, apagado: { type: 'boolean' } },
  required: ['id', 'apagado'],
} as const;

const CORPO_CRIAR = {
  type: 'object',
  properties: {
    codigo: CODIGO,
    nome: NOME,
    // Sem `ordem`, entra no fim da lista. É o que faz "adicionar" ser um clique
    // só no painel: a posição só precisa ser dita quando importa.
    ordem: { type: 'integer', minimum: 0 },
    ativo: { type: 'boolean', default: true },
  },
  required: ['codigo', 'nome'],
  additionalProperties: false,
} as const;

// Tudo opcional: o painel manda só o que mudou. `codigo` NÃO está aqui de
// propósito - ele é a chave estável de quem integra de fora, e renomeá-lo depois
// quebraria o casamento silenciosamente.
//
// `minProperties: 1` barra o PATCH literalmente vazio, mas não basta: o Fastify
// roda o AJV com `removeAdditional`, e o AJV conta as propriedades ANTES de
// remover as que `additionalProperties: false` recusa. Então um corpo que só tem
// `codigo` passa pelas duas regras e chega vazio ao handler - quem fecha essa
// brecha é a conferência de `dados` vazio, logo abaixo.
const CORPO_ALTERAR = {
  type: 'object',
  properties: {
    nome: NOME,
    ordem: { type: 'integer', minimum: 0 },
    ativo: { type: 'boolean' },
  },
  additionalProperties: false,
  minProperties: 1,
} as const;

type CorpoCriar = { codigo: string; nome: string; ordem?: number; ativo?: boolean };
type CorpoAlterar = { nome?: string; ordem?: number; ativo?: boolean };

const CAMPOS = {
  id: true,
  codigo: true,
  nome: true,
  ordem: true,
  ativo: true,
  _count: { select: { chamados: true, origens: true } },
} as const;

type LinhaComContagem = {
  id: number;
  codigo: string;
  nome: string;
  ordem: number;
  ativo: boolean;
  _count: { chamados: number; origens: number };
};

/** Achata o `_count` do Prisma na forma que o schema de resposta declara. */
function publicar(s: LinhaComContagem) {
  const { _count, ...resto } = s;
  return { ...resto, chamados: _count.chamados, origens: _count.origens };
}

/** P2002 = violação de unicidade. Aqui só existe uma: o `codigo`. */
function ehCodigoRepetido(err: unknown): boolean {
  return err instanceof Prisma.PrismaClientKnownRequestError && err.code === 'P2002';
}

export function registrarRotasDeSetores(app: FastifyInstance): void {
  // Lista TODOS, inclusive os inativos.
  //
  // Os seletores do painel filtram por `ativo` na tela; a rota não pode, senão o
  // setor desativado sumiria da lista e não haveria como reativá-lo. É a mesma
  // decisão da listagem de categorias.
  //
  // `nome` como desempate de `ordem`: empate é permitido (criar dois setores na
  // mesma posição não é erro), e sem o segundo critério a lista trocaria de
  // ordem entre duas cargas sem nada ter mudado.
  app.get(
    '/internal/setores',
    {
      onRequest: exigirToken('Acesso negado à listagem de setores'),
      schema: { response: { 200: RESPOSTA_LISTA } },
    },
    async () => {
      const setores = (await prisma.setor.findMany({
        orderBy: [{ ordem: 'asc' }, { nome: 'asc' }, { id: 'asc' }],
        select: CAMPOS,
      })) as LinhaComContagem[];

      return { setores: setores.map(publicar) };
    }
  );

  app.post<{ Body: CorpoCriar }>(
    '/internal/setores',
    {
      onRequest: exigirToken('Acesso negado à criação de setor'),
      schema: { body: CORPO_CRIAR, response: { 201: SETOR } },
    },
    async (req, reply) => {
      const { nome, ativo = true } = req.body;
      // Minúsculas e sem espaço nas pontas: o `codigo` é chave, e "TI " e "ti"
      // apontando para dois setores diferentes é o tipo de duplicata que o
      // relatório só mostra meses depois.
      const codigo = req.body.codigo.trim().toLowerCase();
      if (codigo === '') return reply.status(400).send({ erro: 'codigo não pode ser vazio' });

      let ordem = req.body.ordem;
      if (ordem === undefined) {
        const ultimo = await prisma.setor.findFirst({
          orderBy: { ordem: 'desc' },
          select: { ordem: true },
        });
        ordem = (ultimo?.ordem ?? 0) + 1;
      }

      try {
        const criado = await prisma.setor.create({
          data: { codigo, nome: nome.trim(), ordem, ativo },
          select: { id: true, codigo: true, nome: true, ordem: true, ativo: true },
        });

        req.log.info({ setorId: criado.id, codigo }, 'Setor criado');
        // Zerados sem consultar: acabou de nascer, ninguém aponta para ele.
        return reply.status(201).send({ ...criado, chamados: 0, origens: 0 });
      } catch (err) {
        if (ehCodigoRepetido(err)) {
          return reply.status(409).send({ erro: `já existe setor com o código "${codigo}"` });
        }
        throw err;
      }
    }
  );

  app.patch<{ Params: { id: number }; Body: CorpoAlterar }>(
    '/internal/setores/:id',
    {
      onRequest: exigirToken('Acesso negado à alteração de setor'),
      schema: { params: PARAMS, body: CORPO_ALTERAR, response: { 200: SETOR } },
    },
    async (req, reply) => {
      const { id } = req.params;
      const corpo = req.body;

      // Confere antes de escrever para a resposta ser 404, e não o P2025 genérico
      // do Prisma virando 500.
      const existe = await prisma.setor.findUnique({ where: { id }, select: { id: true } });
      if (!existe) return reply.status(404).send({ erro: 'setor não encontrado' });

      const dados: CorpoAlterar = {};
      if (corpo.nome !== undefined) dados.nome = corpo.nome.trim();
      if (corpo.ordem !== undefined) dados.ordem = corpo.ordem;
      if (corpo.ativo !== undefined) dados.ativo = corpo.ativo;

      // Nada reconhecido no corpo. O caso concreto é uma tentativa de renomear o
      // `codigo`: ele é removido pelo AJV e o PATCH viraria um 200 que não
      // alterou nada, fazendo quem chamou acreditar que o código mudou.
      if (Object.keys(dados).length === 0) {
        return reply
          .status(400)
          .send({ erro: 'nenhum campo alterável no corpo (o codigo não pode ser alterado)' });
      }

      const alterado = (await prisma.setor.update({
        where: { id },
        data: dados,
        select: CAMPOS,
      })) as LinhaComContagem;

      req.log.info({ setorId: id, campos: Object.keys(dados) }, 'Setor alterado');
      return reply.send(publicar(alterado));
    }
  );

  // Apagar de verdade, e só quando não sobra rastro.
  //
  // A recusa é a mesma de `Categoria` e pelo mesmo motivo: com chamado
  // apontando para o setor, o `SetNull` zeraria a coluna daqueles chamados e o
  // relatório por setor perderia o histórico - em silêncio, que é o pior jeito.
  // Em vez disso a resposta manda desativar, que é o que a coluna `ativo`
  // existe para resolver.
  //
  // As DUAS pontas contam: um setor que nunca atendeu nada mas abriu 40 chamados
  // ainda tem histórico a perder.
  app.delete<{ Params: { id: number } }>(
    '/internal/setores/:id',
    {
      onRequest: exigirToken('Acesso negado à exclusão de setor'),
      schema: { params: PARAMS, response: { 200: RESPOSTA_APAGADO } },
    },
    async (req, reply) => {
      const { id } = req.params;

      const alvo = await prisma.setor.findUnique({
        where: { id },
        select: { id: true, _count: { select: { chamados: true, origens: true } } },
      });
      if (!alvo) return reply.status(404).send({ erro: 'setor não encontrado' });

      const usos = alvo._count.chamados + alvo._count.origens;
      if (usos > 0) {
        return reply.status(409).send({
          erro:
            `${usos} chamado(s) apontam para este setor ` +
            `(${alvo._count.chamados} como responsável, ${alvo._count.origens} como origem). ` +
            'Desative-o em vez de excluir, para o histórico continuar somando.',
        });
      }

      await prisma.setor.delete({ where: { id } });
      req.log.info({ setorId: id }, 'Setor excluído');
      return reply.send({ id, apagado: true });
    }
  );
}
