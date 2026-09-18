import { FastifyInstance } from 'fastify';
import { Prisma } from '../generated/prisma/client';
import { prisma } from '../db/client';
import { exigirToken } from './auth';

/**
 * CRUD da árvore de assuntos.
 *
 * Esta rota existe porque `Categoria` é TABELA e não `enum`: a lista veio dos
 * grupos de atendimento da empresa e muda por decisão de negócio. Sem uma porta
 * de escrita, mudar um rótulo exigiria migração e deploy - e aí, na prática,
 * ninguém muda e o menu envelhece.
 *
 * O que ela protege, e é o motivo de metade do código aqui ser guarda:
 *   - a numeração do menu não pode ganhar buraco (por isso `ordem` é sequência,
 *     e o número do menu é calculado na hora - ver conversation/categorias.ts);
 *   - a árvore não pode ganhar ciclo, senão a conversa entra em laço;
 *   - categoria com chamado apontando para ela não pode ser apagada, senão o
 *     dashboard perde o histórico. Para isso existe `ativa`.
 *
 * `visivelNoWhatsapp` é o interruptor do ASSUNTO DE USO INTERNO, e por desenho
 * não tem guarda nenhuma aqui: marcar um assunto como interno nunca invalida
 * nada. O que ele governa mora todo do outro lado - `filhasNoMenu`, em
 * conversation/categorias.ts, é a única consulta que o lê. Um assunto interno
 * continua editável, continua no seletor do painel e continua somando no
 * relatório; ele só deixa de ser oferecido na conversa.
 */

// Mesmo teto de `conversation/categorias.ts`. Uma árvore mais funda que isto não
// é menu de atendimento, é labirinto - e o `caminhoDaCategoria` para de subir aí.
const MAX_PROFUNDIDADE = 10;

const PARAMS = {
  type: 'object',
  properties: { id: { type: 'integer', minimum: 1 } },
  required: ['id'],
} as const;

// `codigo` é o identificador estável: o que uma integração externa usa para casar
// categoria por chave, e não por texto. O padrão restrito existe para ele
// continuar sendo isso - um código com espaço ou acento vira, na prática, um
// segundo rótulo que ninguém consegue digitar igual duas vezes.
const CODIGO = { type: 'string', minLength: 2, maxLength: 60, pattern: '^[a-z0-9_]+$' } as const;
const NOME = { type: 'string', minLength: 2, maxLength: 120 } as const;
const ORDEM = { type: 'integer', minimum: 0, maximum: 9999 } as const;

// `visivelNoWhatsapp` tem o mesmo `default: true` de `ativa` e pelo mesmo motivo:
// quem cria um assunto pelo formulário sem tocar no interruptor está criando um
// assunto de atendimento normal. Interno é a exceção e precisa ser dita.
const CORPO_CRIAR = {
  type: 'object',
  properties: {
    codigo: CODIGO,
    nome: NOME,
    rotulo: NOME,
    ordem: ORDEM,
    ativa: { type: 'boolean', default: true },
    visivelNoWhatsapp: { type: 'boolean', default: true },
    paiId: { type: 'integer', minimum: 1, nullable: true },
  },
  required: ['codigo', 'nome', 'rotulo'],
  additionalProperties: false,
} as const;

// Tudo opcional: o painel manda só o que mudou. `codigo` NÃO está aqui de
// propósito - ele é a chave estável para quem integra de fora, e renomear chave
// estável é o mesmo que apagar e criar outra.
const CORPO_ALTERAR = {
  type: 'object',
  properties: {
    nome: NOME,
    rotulo: NOME,
    ordem: ORDEM,
    ativa: { type: 'boolean' },
    visivelNoWhatsapp: { type: 'boolean' },
    paiId: { type: 'integer', minimum: 1, nullable: true },
  },
  additionalProperties: false,
} as const;

const CATEGORIA = {
  type: 'object',
  properties: {
    id: { type: 'integer' },
    codigo: { type: 'string' },
    nome: { type: 'string' },
    rotulo: { type: 'string' },
    ordem: { type: 'integer' },
    ativa: { type: 'boolean' },
    // `false` = assunto de uso interno: fora do menu do WhatsApp, dentro do
    // seletor do painel. É o que o painel lê para desenhar o interruptor da
    // linha e para marcar as filhas que herdam a invisibilidade de um pai
    // interno - a herança é só visual, a coluna da filha não muda.
    visivelNoWhatsapp: { type: 'boolean' },
    paiId: { type: 'integer', nullable: true },
    // Quantos chamados apontam para ela. É o que o painel usa para saber, ANTES
    // de tentar, que o botão de excluir vai levar 409 - e para oferecer
    // "desativar" no lugar.
    chamados: { type: 'integer' },
  },
  required: ['id', 'codigo', 'nome', 'rotulo', 'ordem', 'ativa', 'visivelNoWhatsapp', 'chamados'],
} as const;

const RESPOSTA_LISTA = {
  type: 'object',
  properties: { categorias: { type: 'array', items: CATEGORIA } },
  required: ['categorias'],
} as const;

const RESPOSTA_APAGADA = {
  type: 'object',
  properties: { id: { type: 'integer' }, apagada: { type: 'boolean' } },
  required: ['id', 'apagada'],
} as const;

type CorpoCriar = {
  codigo: string;
  nome: string;
  rotulo: string;
  ordem?: number;
  ativa?: boolean;
  visivelNoWhatsapp?: boolean;
  paiId?: number | null;
};

type CorpoAlterar = Partial<Omit<CorpoCriar, 'codigo'>>;

/**
 * Mover um nó para debaixo de um descendente seu fecharia um ciclo - e um ciclo
 * aqui não é um erro abstrato: `filhasNoMenu` desceria para sempre e a conversa
 * do usuário travaria dentro da transação que atende a mensagem dele.
 *
 * Estourar a profundidade também recusa. Ou a árvore já está funda demais para o
 * `caminhoDaCategoria` conseguir subir inteira, ou já existe um ciclo gravado por
 * fora da API - nos dois casos, deixar passar piora.
 */
async function criariaCiclo(id: number, novoPaiId: number): Promise<boolean> {
  let atual: number | null = novoPaiId;

  for (let i = 0; i < MAX_PROFUNDIDADE; i++) {
    if (atual === null) return false;
    if (atual === id) return true;

    const no: { paiId: number | null } | null = await prisma.categoria.findUnique({
      where: { id: atual },
      select: { paiId: true },
    });
    if (no === null) return false; // pai inexistente: quem recusa é o outro guarda
    atual = no.paiId;
  }

  return true;
}

/** P2002 = violação de unicidade. Aqui só existe uma: o `codigo`. */
function ehCodigoRepetido(err: unknown): boolean {
  return err instanceof Prisma.PrismaClientKnownRequestError && err.code === 'P2002';
}

export function registrarRotasDeCategorias(app: FastifyInstance): void {
  // Lista TODA a árvore: as inativas e as de uso interno junto.
  //
  // O menu do WhatsApp filtra as duas coisas; o painel não pode filtrar nenhuma,
  // e por motivos diferentes. A desativada some da tela e não haveria como
  // reativá-la; a interna é justamente o assunto que só existe aqui - escondê-la
  // do painel esvaziaria o recurso inteiro. Quem monta a hierarquia é o painel,
  // a partir de `paiId` - devolver aninhado obrigaria a inventar um formato
  // recursivo no schema de resposta para nenhum ganho.
  app.get(
    '/internal/categorias',
    {
      onRequest: exigirToken('Acesso negado à listagem de categorias'),
      schema: { response: { 200: RESPOSTA_LISTA } },
    },
    async () => {
      const categorias = await prisma.categoria.findMany({
        orderBy: [{ ordem: 'asc' }, { id: 'asc' }],
        select: {
          id: true,
          codigo: true,
          nome: true,
          rotulo: true,
          ordem: true,
          ativa: true,
          visivelNoWhatsapp: true,
          paiId: true,
          _count: { select: { chamados: true } },
        },
      });

      return {
        categorias: categorias.map(({ _count, ...c }) => ({ ...c, chamados: _count.chamados })),
      };
    }
  );

  app.post<{ Body: CorpoCriar }>(
    '/internal/categorias',
    {
      onRequest: exigirToken('Acesso negado à criação de categoria'),
      schema: { body: CORPO_CRIAR, response: { 201: CATEGORIA } },
    },
    async (req, reply) => {
      const { codigo, nome, rotulo, ativa = true, visivelNoWhatsapp = true } = req.body;
      const paiId = req.body.paiId ?? null;

      if (paiId !== null) {
        const pai = await prisma.categoria.findUnique({
          where: { id: paiId },
          select: { id: true },
        });
        if (!pai) return reply.status(400).send({ erro: 'paiId não existe' });
      }

      // Sem `ordem` no corpo, entra no fim das irmãs. É o que faz "adicionar" ser
      // um clique só no painel: a posição só precisa ser dita quando importa.
      let ordem = req.body.ordem;
      if (ordem === undefined) {
        const ultima = await prisma.categoria.findFirst({
          where: { paiId },
          orderBy: { ordem: 'desc' },
          select: { ordem: true },
        });
        ordem = (ultima?.ordem ?? 0) + 1;
      }

      try {
        const criada = await prisma.categoria.create({
          data: {
            codigo,
            nome: nome.trim(),
            rotulo: rotulo.trim(),
            ordem,
            ativa,
            visivelNoWhatsapp,
            paiId,
          },
          select: {
            id: true,
            codigo: true,
            nome: true,
            rotulo: true,
            ordem: true,
            ativa: true,
            visivelNoWhatsapp: true,
            paiId: true,
          },
        });

        req.log.info({ categoriaId: criada.id, codigo }, 'Categoria criada');
        // `chamados: 0` sem consultar: acabou de nascer.
        return reply.status(201).send({ ...criada, chamados: 0 });
      } catch (err) {
        if (ehCodigoRepetido(err)) {
          return reply.status(409).send({ erro: `já existe categoria com o código "${codigo}"` });
        }
        throw err;
      }
    }
  );

  app.patch<{ Params: { id: number }; Body: CorpoAlterar }>(
    '/internal/categorias/:id',
    {
      onRequest: exigirToken('Acesso negado à alteração de categoria'),
      schema: { params: PARAMS, body: CORPO_ALTERAR, response: { 200: CATEGORIA } },
    },
    async (req, reply) => {
      const { id } = req.params;
      const corpo = req.body;

      const atual = await prisma.categoria.findUnique({ where: { id }, select: { id: true } });
      if (!atual) return reply.status(404).send({ erro: 'categoria não encontrada' });

      if (corpo.paiId !== undefined && corpo.paiId !== null) {
        if (corpo.paiId === id) {
          return reply.status(400).send({ erro: 'uma categoria não pode ser pai dela mesma' });
        }
        const pai = await prisma.categoria.findUnique({
          where: { id: corpo.paiId },
          select: { id: true },
        });
        if (!pai) return reply.status(400).send({ erro: 'paiId não existe' });

        if (await criariaCiclo(id, corpo.paiId)) {
          return reply
            .status(400)
            .send({ erro: 'esse pai está abaixo da própria categoria: criaria um ciclo' });
        }
      }

      // Só o que veio no corpo. `undefined` é "não mexa"; `null` em `paiId` é
      // "promova para raiz", e os dois precisam continuar distinguíveis.
      const dados: Prisma.CategoriaUpdateInput = {};
      if (corpo.nome !== undefined) dados.nome = corpo.nome.trim();
      if (corpo.rotulo !== undefined) dados.rotulo = corpo.rotulo.trim();
      if (corpo.ordem !== undefined) dados.ordem = corpo.ordem;
      if (corpo.ativa !== undefined) dados.ativa = corpo.ativa;
      if (corpo.visivelNoWhatsapp !== undefined) {
        dados.visivelNoWhatsapp = corpo.visivelNoWhatsapp;
      }
      if (corpo.paiId !== undefined) {
        dados.pai = corpo.paiId === null ? { disconnect: true } : { connect: { id: corpo.paiId } };
      }

      const alterada = await prisma.categoria.update({
        where: { id },
        data: dados,
        select: {
          id: true,
          codigo: true,
          nome: true,
          rotulo: true,
          ordem: true,
          ativa: true,
          visivelNoWhatsapp: true,
          paiId: true,
          _count: { select: { chamados: true } },
        },
      });

      req.log.info({ categoriaId: id, campos: Object.keys(dados) }, 'Categoria alterada');

      const { _count, ...resto } = alterada;
      return reply.send({ ...resto, chamados: _count.chamados });
    }
  );

  // Apagar de verdade, e só quando não sobra rastro.
  //
  // Duas recusas, as duas com o mesmo motivo de fundo - apagar aqui destruiria
  // informação em outro lugar:
  //   - com chamado apontando para ela, `SetNull` zeraria a categoria daqueles
  //     chamados e o dashboard perderia o histórico;
  //   - com filhas, `SetNull` promoveria as filhas a raízes, e o menu do
  //     WhatsApp mudaria de forma sem ninguém ter pedido.
  //
  // Em vez de fazer qualquer uma das duas em silêncio, a resposta manda desativar
  // - que é exatamente o que a coluna `ativa` existe para resolver.
  app.delete<{ Params: { id: number } }>(
    '/internal/categorias/:id',
    {
      onRequest: exigirToken('Acesso negado à exclusão de categoria'),
      schema: { params: PARAMS, response: { 200: RESPOSTA_APAGADA } },
    },
    async (req, reply) => {
      const { id } = req.params;

      const alvo = await prisma.categoria.findUnique({
        where: { id },
        select: { id: true, _count: { select: { chamados: true, filhas: true } } },
      });
      if (!alvo) return reply.status(404).send({ erro: 'categoria não encontrada' });

      if (alvo._count.chamados > 0) {
        return reply.status(409).send({
          erro:
            `${alvo._count.chamados} chamado(s) usam esta categoria. ` +
            'Desative-a em vez de excluir, para o histórico continuar somando.',
        });
      }

      if (alvo._count.filhas > 0) {
        return reply.status(409).send({
          erro:
            `esta categoria tem ${alvo._count.filhas} sub-assunto(s). ` +
            'Mova ou exclua os sub-assuntos antes.',
        });
      }

      await prisma.categoria.delete({ where: { id } });
      req.log.info({ categoriaId: id }, 'Categoria excluída');
      return reply.send({ id, apagada: true });
    }
  );
}
