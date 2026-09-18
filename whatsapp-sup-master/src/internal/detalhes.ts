import { FastifyInstance, FastifyReply } from 'fastify';
import { Prisma } from '../generated/prisma/client';
import { config } from '../config';
import { prisma } from '../db/client';
import { exigirToken } from './auth';
import { normalizarTags } from './chamados';

/**
 * O que pende de UM chamado: comentários da equipe, anexos, etiquetas e
 * dependências entre chamados.
 *
 * Mora em arquivo separado de `chamados.ts` porque a diferença não é de assunto,
 * é de CARDINALIDADE. Tudo em `chamados.ts` é coluna da linha do chamado - uma
 * leitura devolve o chamado inteiro. Aqui são listas que crescem sem teto, e
 * carregá-las na listagem do quadro traria centenas de linhas que ninguém abriu:
 * 500 cartões x N comentários x M anexos, para mostrar 4 campos por cartão.
 *
 * Por isso a divisão de leitura é esta:
 *   - `GET /internal/chamados` devolve as colunas + as tags (que aparecem NO
 *     cartão);
 *   - `GET /internal/chamados/:id/detalhe` devolve estas listas, e só quando um
 *     chamado é aberto na tela.
 *
 * A CONVERSA do WhatsApp entrou aqui pelo mesmo critério, e é a única das listas
 * que este servidor não criava: ela mora em `Mensagem`, que já existia como log
 * de entrega, e até agora nenhuma rota a expunha. Quem atendia via o resumo e a
 * descrição, mas não o que a pessoa escreveu para chegar até eles.
 */

const PARAMS = {
  type: 'object',
  properties: { id: { type: 'integer', minimum: 1 } },
  required: ['id'],
} as const;

const PARAMS_DEPENDENCIA = {
  type: 'object',
  properties: {
    id: { type: 'integer', minimum: 1 },
    bloqueadorId: { type: 'integer', minimum: 1 },
  },
  required: ['id', 'bloqueadorId'],
} as const;

const AUTOR = { type: 'string', minLength: 1, maxLength: 120 } as const;

const CORPO_COMENTARIO = {
  type: 'object',
  properties: {
    texto: { type: 'string', minLength: 1, maxLength: 4000 },
    autor: AUTOR,
  },
  required: ['texto'],
  additionalProperties: false,
} as const;

const COMENTARIO = {
  type: 'object',
  properties: {
    id: { type: 'integer' },
    autor: { type: 'string', nullable: true },
    texto: { type: 'string' },
    criadoEm: { type: 'string' },
  },
  required: ['id', 'texto', 'criadoEm'],
} as const;

// `conteudo` NÃO está aqui, e é a razão de a listagem existir separada do
// download: com o BLOB dentro, abrir um chamado com cinco prints baixaria os
// cinco arquivos para desenhar cinco nomes na tela.
const ANEXO = {
  type: 'object',
  properties: {
    id: { type: 'integer' },
    nome: { type: 'string' },
    mime: { type: 'string' },
    bytes: { type: 'integer' },
    enviadoPor: { type: 'string', nullable: true },
    criadoEm: { type: 'string' },
  },
  required: ['id', 'nome', 'mime', 'bytes', 'criadoEm'],
} as const;

/**
 * Uma mensagem da conversa do WhatsApp.
 *
 * O que NÃO está aqui é a parte que importa:
 *
 *   - `telefone`, pela mesma minimização da listagem e da view de cards;
 *   - `payload`, que é o corpo exato postado na Evolution — e ele **contém o
 *     telefone**. Expor `payload` teria devolvido pela porta de trás justamente o
 *     dado que todas as outras rotas escondem;
 *   - `whatsappMessageId`, que é protocolo interno (o `key.id` da Evolution) e só serve
 *     para descartar reentrega;
 *   - `tentativas` e `ultimaTentativaEm`, que são ruído operacional do varredor.
 *
 * `enviadaEm` SIM está, e é o único campo de entrega que sobrou: numa mensagem de
 * saída, nulo significa "ainda na fila da outbox". É a diferença entre "a equipe
 * não respondeu" e "a resposta existe e não saiu daqui" — e sem ele quem atende
 * não tem como saber qual dos dois está olhando.
 */
const MENSAGEM = {
  type: 'object',
  properties: {
    id: { type: 'integer' },
    // 'usuario' ou 'sistema'. É o que decide de que lado da conversa a bolha é
    // desenhada; o NOME de quem falou não vem daqui porque não existe em
    // `Mensagem` — o do solicitante está no chamado, e do outro lado é o bot.
    remetente: { type: 'string' },
    texto: { type: 'string' },
    timestamp: { type: 'string' },
    enviadaEm: { type: 'string', nullable: true },
  },
  required: ['id', 'remetente', 'texto', 'timestamp'],
} as const;

// A ponta oposta da dependência, com o mínimo para a tela desenhar um link: o
// número, o título e a situação (que é o que diz se o bloqueio ainda vale).
const LIGACAO = {
  type: 'object',
  properties: {
    chamadoId: { type: 'integer' },
    resumo: { type: 'string' },
    situacao: { type: 'string' },
  },
  required: ['chamadoId', 'resumo', 'situacao'],
} as const;

const RESPOSTA_DETALHE = {
  type: 'object',
  properties: {
    chamadoId: { type: 'integer' },
    // A conversa com o SOLICITANTE (WhatsApp) e as notas INTERNAS da equipe, em
    // listas separadas. Não é organização: são coisas com destinatários
    // diferentes, e juntá-las numa timeline única faria a tela ter de decidir a
    // cada linha se aquilo pode ser lido pelo cliente.
    mensagens: { type: 'array', items: MENSAGEM },
    comentarios: { type: 'array', items: COMENTARIO },
    anexos: { type: 'array', items: ANEXO },
    // Duas listas e não uma: "quem me trava" e "quem eu travo" são leituras
    // opostas, e juntá-las numa lista com um campo `direcao` obrigaria a tela a
    // separar de novo para poder escrever as duas frases.
    bloqueadoPor: { type: 'array', items: LIGACAO },
    bloqueia: { type: 'array', items: LIGACAO },
  },
  required: ['chamadoId', 'mensagens', 'comentarios', 'anexos', 'bloqueadoPor', 'bloqueia'],
} as const;

// `minLength: 0` como no POST de tarefa: a caixa de texto separada por vírgula
// produz item vazio com facilidade, e `normalizarTags` o descarta. Recusar o
// pedido inteiro por uma vírgula sobrando seria hostil.
//
// Lista VAZIA é um valor legítimo e não um erro: é a operação "tire todas as
// etiquetas deste chamado", e sem ela não haveria como desfazer uma etiquetagem.
const CORPO_TAGS = {
  type: 'object',
  properties: {
    tags: { type: 'array', items: { type: 'string', minLength: 0, maxLength: 40 }, maxItems: 20 },
  },
  required: ['tags'],
  additionalProperties: false,
} as const;

const RESPOSTA_TAGS = {
  type: 'object',
  properties: {
    chamadoId: { type: 'integer' },
    tags: { type: 'array', items: { type: 'string' } },
  },
  required: ['chamadoId', 'tags'],
} as const;

/**
 * O binário chega em base64 dentro do JSON, e não como `multipart/form-data`.
 *
 * É a escolha que evita uma dependência nova (`@fastify/multipart`) para uma
 * rota só, e mantém este servidor com o mesmo formato de corpo em todas as
 * rotas - o que significa que o token, a validação por JSON Schema e o
 * tratamento de erro já existentes valem aqui sem exceção.
 *
 * O preço é conhecido e está medido no `bodyLimit` da rota: base64 infla o
 * conteúdo em 4/3. Um anexo de 5 MB viaja como ~6,7 MB de texto.
 */
const CORPO_ANEXO = {
  type: 'object',
  properties: {
    nome: { type: 'string', minLength: 1, maxLength: 255 },
    mime: { type: 'string', minLength: 1, maxLength: 120 },
    conteudoBase64: { type: 'string', minLength: 1 },
    enviadoPor: AUTOR,
  },
  required: ['nome', 'mime', 'conteudoBase64'],
  additionalProperties: false,
} as const;

// Teto de anexos por chamado. O binário mora DENTRO do SQLite (model `Anexo`),
// então cada anexo engorda o arquivo do banco: 10 x ANEXO_MAX_BYTES por chamado.
// Sem este teto, quem tem o token do painel podia subir milhares de anexos e
// encher o disco - e disco cheio derruba a escrita do webhook, ou seja, o
// serviço inteiro. Dez cobre "as fotos de um caso" com folga.
const MAX_ANEXOS_POR_CHAMADO = 10;

const RESPOSTA_APAGADO = {
  type: 'object',
  properties: { id: { type: 'integer' }, apagado: { type: 'boolean' } },
  required: ['id', 'apagado'],
} as const;

/**
 * O que se aceita anexar.
 *
 * Lista fechada, e não "qualquer coisa": o conteúdo volta pelo `GET` com o
 * `Content-Type` que foi declarado no upload, e um `text/html` guardado aqui
 * seria uma página servida pela mesma origem do painel - com acesso ao que a
 * origem do painel tem. Imagem, PDF, texto e os formatos de escritório cobrem
 * "foto, documento, print" sem abrir essa porta.
 *
 * O `Content-Disposition: attachment` da rota de download é a segunda tranca; a
 * lista é a primeira, porque depender de um cabeçalho só é depender de o
 * navegador respeitá-lo.
 */
const MIMES_ACEITOS = new Set([
  'image/png',
  'image/jpeg',
  'image/gif',
  'image/webp',
  'image/heic',
  'application/pdf',
  'text/plain',
  'text/csv',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
]);

/**
 * Base64 para bytes, recusando o que não é base64.
 *
 * `Buffer.from(x, 'base64')` NUNCA estoura: ele ignora todo caractere inválido e
 * devolve o que sobrou. Sem esta conferência, mandar "isto não é base64" gravaria
 * um anexo de poucos bytes de lixo, e o erro só apareceria quando alguém tentasse
 * abrir o arquivo semanas depois.
 *
 * A ida e volta é a prova: se re-codificar os bytes não reproduz a entrada
 * (normalizada, sem espaço em branco), então a entrada não era base64 daqueles
 * bytes.
 */
function decodificarBase64(valor: string): Uint8Array<ArrayBuffer> | null {
  const limpo = valor.replace(/\s+/g, '');
  if (limpo === '' || !/^[A-Za-z0-9+/]+={0,2}$/.test(limpo)) return null;

  const bytes = Buffer.from(limpo, 'base64');
  if (bytes.length === 0) return null;
  if (bytes.toString('base64').replace(/=+$/, '') !== limpo.replace(/=+$/, '')) return null;

  // Copia para um `Uint8Array` próprio em vez de devolver o `Buffer`.
  //
  // O Prisma declara `Bytes` como `Uint8Array<ArrayBuffer>` - um array que É
  // dono do seu buffer. O `Buffer` do Node vive num pool compartilhado, e o
  // TypeScript o tipa como `ArrayBufferLike`, que pode ser um
  // `SharedArrayBuffer`: passar um direto não compila, e forçar com `as` seria
  // esconder o fato em vez de resolvê-lo.
  //
  // `new Uint8Array(tamanho)` + `set` aloca um buffer exclusivo. O custo é uma
  // cópia por upload, não uma por laço.
  const copia = new Uint8Array(bytes.byteLength);
  copia.set(bytes);
  return copia;
}

/** 404 numa resposta só, para as rotas que só precisam saber se o chamado existe. */
async function chamadoExiste(id: number): Promise<boolean> {
  const c = await prisma.chamado.findUnique({ where: { id }, select: { id: true } });
  return c !== null;
}

/**
 * Chamado encerrado não aceita mais mexida em dependência.
 *
 * O caminho combinado com a equipe é o inverso: quem precisa alterar um chamado
 * já resolvido volta a situação para "em andamento" primeiro. Isso mantém a
 * mudança dentro do histórico de situação (`MudancaSituacao`) em vez de ela
 * acontecer por baixo de um chamado que, para todos os efeitos, já terminou.
 *
 * A regra vive AQUI, e não só na tela, porque a tela é uma das formas de chamar
 * esta rota - e a que não vale como garantia.
 */
const ENCERRADAS = ['resolvido', 'fechado', 'cancelado'] as const;

type Encerrada = (typeof ENCERRADAS)[number];

function ehEncerrada(s: string): s is Encerrada {
  return (ENCERRADAS as readonly string[]).includes(s);
}

/**
 * A situação encerrada do chamado, ou `null` se ele aceita mudança.
 *
 * Devolve DADO, e não a resposta pronta. A primeira versão desta função era
 * `recusarSeEncerrado(id, reply)`, que fazia `return reply.status(409).send(...)`
 * para o chamador repassar com `if (recusa) return recusa`. Parecia mais seguro
 * e era o contrário: `Reply` do Fastify é *thenable* (tem `.then()`, para
 * permitir `await reply`), então uma função `async` que o retorna faz a Promise
 * ADOTAR esse thenable e resolver para `undefined`. O `if` nunca era verdadeiro,
 * a execução seguia, e a rota respondia 409 *e apagava a dependência* - o pior
 * dos dois mundos, porque o cliente via a recusa e o banco via a mudança.
 *
 * Por isso a regra aqui: helper de validação devolve dado; quem monta a resposta
 * é a rota.
 */
async function situacaoEncerrada(id: number): Promise<Encerrada | null> {
  const c = await prisma.chamado.findUnique({ where: { id }, select: { situacao: true } });
  if (c === null) return null;
  return ehEncerrada(c.situacao) ? c.situacao : null;
}

function recusaDeEncerrado(reply: FastifyReply, situacao: Encerrada) {
  return reply
    .status(409)
    .send({ erro: `não é possível finalizar essa operação em um chamado ${situacao}` });
}

export function registrarRotasDeDetalhes(app: FastifyInstance): void {
  /* ---------- Leitura ------------------------------------------------- */

  app.get<{ Params: { id: number } }>(
    '/internal/chamados/:id/detalhe',
    {
      onRequest: exigirToken('Acesso negado ao detalhe do chamado'),
      schema: { params: PARAMS, response: { 200: RESPOSTA_DETALHE } },
    },
    async (req, reply) => {
      const { id } = req.params;

      // Uma consulta só, com as quatro listas aninhadas. Cinco idas ao banco
      // para desenhar um modal seriam cinco travessias do lock de escrita do
      // SQLite atrás de uma requisição que o atendente está esperando.
      const chamado = await prisma.chamado.findUnique({
        where: { id },
        select: {
          id: true,
          // Do mais ANTIGO para o mais novo: é uma conversa, e conversa se lê na
          // ordem em que aconteceu. `id` desempata porque duas mensagens do mesmo
          // lote podem cair no mesmo milissegundo, e sem o segundo critério a
          // ordem delas mudaria entre duas leituras.
          mensagens: {
            select: {
              id: true,
              remetente: true,
              texto: true,
              timestamp: true,
              enviadaEm: true,
            },
            orderBy: [{ timestamp: 'asc' }, { id: 'asc' }],
          },
          comentarios: {
            select: { id: true, autor: true, texto: true, criadoEm: true },
            // Do mais ANTIGO para o mais novo, ao contrário do histórico de
            // situação: isto é uma conversa, e conversa se lê na ordem em que
            // aconteceu.
            orderBy: { criadoEm: 'asc' },
          },
          anexos: {
            select: {
              id: true,
              nome: true,
              mime: true,
              bytes: true,
              enviadoPor: true,
              criadoEm: true,
            },
            orderBy: { criadoEm: 'asc' },
          },
          bloqueadoPor: {
            select: {
              bloqueador: { select: { id: true, resumo: true, situacao: true } },
            },
            orderBy: { criadoEm: 'asc' },
          },
          bloqueia: {
            select: {
              bloqueado: { select: { id: true, resumo: true, situacao: true } },
            },
            orderBy: { criadoEm: 'asc' },
          },
        },
      });

      if (!chamado) return reply.status(404).send({ erro: 'chamado não encontrado' });

      return reply.send({
        chamadoId: chamado.id,
        mensagens: chamado.mensagens.map((m) => ({
          ...m,
          timestamp: m.timestamp.toISOString(),
          // ISO nas duas datas, como no resto do painel: quem está olhando
          // precisa do instante em UTC para ver no próprio fuso.
          enviadaEm: m.enviadaEm?.toISOString() ?? null,
        })),
        comentarios: chamado.comentarios.map((c) => ({
          ...c,
          criadoEm: c.criadoEm.toISOString(),
        })),
        anexos: chamado.anexos.map((a) => ({ ...a, criadoEm: a.criadoEm.toISOString() })),
        bloqueadoPor: chamado.bloqueadoPor.map((d) => ({
          chamadoId: d.bloqueador.id,
          resumo: d.bloqueador.resumo,
          situacao: d.bloqueador.situacao,
        })),
        bloqueia: chamado.bloqueia.map((d) => ({
          chamadoId: d.bloqueado.id,
          resumo: d.bloqueado.resumo,
          situacao: d.bloqueado.situacao,
        })),
      });
    }
  );

  /* ---------- Comentários --------------------------------------------- */

  /**
   * Acrescenta um comentário. NÃO existe rota para editar nem para apagar, e a
   * ausência é a decisão: o pedido disse "pra time trocar info sem perder o
   * rastro", e rastro que se reescreve não é rastro. É o mesmo desenho de
   * `MudancaSituacao`.
   *
   * O comentário fica só neste banco. Ele NUNCA vira mensagem de WhatsApp - a
   * única coisa que escreve na tabela `Mensagem` é o fluxo de conversa e a
   * notificação de situação, e nenhuma delas passa por aqui. Sem essa separação,
   * uma nota interna ("cliente já reclamou disso três vezes") sairia para o
   * cliente na varredura seguinte da outbox.
   */
  app.post<{ Params: { id: number }; Body: { texto: string; autor?: string } }>(
    '/internal/chamados/:id/comentarios',
    {
      onRequest: exigirToken('Acesso negado ao comentário de chamado'),
      schema: { params: PARAMS, body: CORPO_COMENTARIO, response: { 201: COMENTARIO } },
    },
    async (req, reply) => {
      const { id } = req.params;

      if (!(await chamadoExiste(id))) {
        return reply.status(404).send({ erro: 'chamado não encontrado' });
      }

      // `minLength: 1` do schema conta caracteres crus: "   " passa por ele. O
      // trim é o que impede um comentário em branco entrar na conversa.
      const texto = req.body.texto.trim();
      if (texto === '') return reply.status(400).send({ erro: 'texto não pode ser vazio' });

      const criado = await prisma.comentario.create({
        data: { chamadoId: id, texto, autor: req.body.autor?.trim() || null },
        select: { id: true, autor: true, texto: true, criadoEm: true },
      });

      req.log.info({ chamadoId: id, comentarioId: criado.id }, 'Comentário registrado');
      return reply.status(201).send({ ...criado, criadoEm: criado.criadoEm.toISOString() });
    }
  );

  /* ---------- Etiquetas ----------------------------------------------- */

  /**
   * Substitui o conjunto INTEIRO de etiquetas do chamado.
   *
   * `PUT` com a lista completa, e não `POST`/`DELETE` por etiqueta, porque é
   * assim que a tela funciona: o campo é uma caixa de texto com as tags
   * separadas, e o que ela sabe dizer é "no fim, são estas". Duas rotas de
   * delta obrigariam o painel a calcular o que entrou e o que saiu - a conta
   * que o `set` abaixo faz de graça.
   *
   * `set` desconecta o que não está na lista sem apagar a linha da `Tag`: a
   * etiqueta continua existindo para os outros chamados que a usam.
   */
  app.put<{ Params: { id: number }; Body: { tags: string[] } }>(
    '/internal/chamados/:id/tags',
    {
      onRequest: exigirToken('Acesso negado às etiquetas do chamado'),
      schema: { params: PARAMS, body: CORPO_TAGS, response: { 200: RESPOSTA_TAGS } },
    },
    async (req, reply) => {
      const { id } = req.params;

      if (!(await chamadoExiste(id))) {
        return reply.status(404).send({ erro: 'chamado não encontrado' });
      }

      // A mesma normalização da criação de tarefa, importada e não recopiada:
      // duas normalizações diferentes fariam a mesma etiqueta virar duas linhas
      // dependendo da rota por onde entrou.
      const tags = normalizarTags(req.body.tags);

      const salvo = await prisma.chamado.update({
        where: { id },
        data: {
          tags: {
            set: [],
            connectOrCreate: tags.map((nome) => ({ where: { nome }, create: { nome } })),
          },
        },
        select: { id: true, tags: { select: { nome: true }, orderBy: { nome: 'asc' } } },
      });

      req.log.info({ chamadoId: id, tags }, 'Etiquetas do chamado atualizadas');
      return reply.send({ chamadoId: salvo.id, tags: salvo.tags.map((t) => t.nome) });
    }
  );

  /* ---------- Anexos --------------------------------------------------- */

  app.post<{
    Params: { id: number };
    Body: { nome: string; mime: string; conteudoBase64: string; enviadoPor?: string };
  }>(
    '/internal/chamados/:id/anexos',
    {
      onRequest: exigirToken('Acesso negado ao anexo de chamado'),
      // Limite PRÓPRIO, acima do global de 256 KB: é a única rota deste servidor
      // que recebe arquivo. `4/3` é a inflação do base64; os 4 KB são o resto do
      // JSON (nome, mime, quem enviou).
      bodyLimit: Math.ceil((config.anexoMaxBytes * 4) / 3) + 4096,
      schema: { params: PARAMS, body: CORPO_ANEXO, response: { 201: ANEXO } },
    },
    async (req, reply) => {
      const { id } = req.params;

      if (!(await chamadoExiste(id))) {
        return reply.status(404).send({ erro: 'chamado não encontrado' });
      }

      // Teto por chamado: barra o abuso de armazenamento antes de decodificar o
      // corpo. Conta e cria não estão numa transação, então dois uploads
      // simultâneos poderiam passar de 10 por um - o que importa é o limite
      // grosso contra enchimento de disco, não a exatidão do décimo anexo.
      const jaTem = await prisma.anexo.count({ where: { chamadoId: id } });
      if (jaTem >= MAX_ANEXOS_POR_CHAMADO) {
        return reply.status(409).send({
          erro: `limite de ${MAX_ANEXOS_POR_CHAMADO} anexos por chamado atingido`,
        });
      }

      const mime = req.body.mime.trim().toLowerCase();
      if (!MIMES_ACEITOS.has(mime)) {
        return reply.status(400).send({
          erro:
            `tipo "${mime}" não é aceito. São aceitos imagem (png, jpeg, gif, webp, heic), ` +
            'pdf, texto (txt, csv) e documentos do Office.',
        });
      }

      const bytes = decodificarBase64(req.body.conteudoBase64);
      if (bytes === null) {
        return reply.status(400).send({ erro: 'conteudoBase64 não é base64 válido' });
      }

      // O `bodyLimit` acima barra o corpo grande antes de alocar; esta segunda
      // conferência é sobre o ARQUIVO já decodificado, que é o número que o
      // usuário conhece ("meu print tem 6 MB"). Sem ela, a mensagem de erro
      // falaria de um limite de corpo que ninguém sabe converter.
      if (bytes.length > config.anexoMaxBytes) {
        const mb = (config.anexoMaxBytes / (1024 * 1024)).toFixed(1);
        return reply.status(413).send({ erro: `anexo passa do limite de ${mb} MB` });
      }

      const criado = await prisma.anexo.create({
        data: {
          chamadoId: id,
          // O nome é só rótulo de tela e sugestão de download - nunca caminho de
          // arquivo, porque não existe arquivo. O `basename` à mão tira diretório
          // de um nome vindo de Windows ou de Unix, para a tela não mostrar
          // "C:\\Users\\...\\print.png" inteiro.
          nome: req.body.nome.trim().split(/[\\/]/).pop() || 'anexo',
          mime,
          bytes: bytes.length,
          conteudo: bytes,
          enviadoPor: req.body.enviadoPor?.trim() || null,
        },
        select: { id: true, nome: true, mime: true, bytes: true, enviadoPor: true, criadoEm: true },
      });

      req.log.info(
        { chamadoId: id, anexoId: criado.id, bytes: criado.bytes },
        'Anexo gravado no chamado'
      );
      return reply.status(201).send({ ...criado, criadoEm: criado.criadoEm.toISOString() });
    }
  );

  /**
   * Baixa o conteúdo de um anexo.
   *
   * Endereçada por `/internal/anexos/:id` e não por `/internal/chamados/:id/...`
   * porque o id do anexo já é único: exigir o chamado na URL faria a tela montar
   * um caminho com dois ids que precisam concordar, e um que não concordasse
   * daria 404 por um motivo que não é "não existe".
   *
   * `Content-Disposition: attachment` sempre, mesmo em imagem: o painel mostra a
   * miniatura por outra via, e forçar download é o que impede um arquivo enviado
   * por terceiro de ser RENDERIZADO na origem do painel. A lista `MIMES_ACEITOS`
   * do upload é a outra metade dessa proteção.
   *
   * `X-Content-Type-Options: nosniff` para o navegador não adivinhar um tipo
   * diferente do declarado - o helmet já o põe nas respostas, e aqui ele é
   * explícito porque esta é a única rota que devolve conteúdo de terceiro.
   */
  app.get<{ Params: { id: number } }>(
    '/internal/anexos/:id',
    {
      onRequest: exigirToken('Acesso negado ao download de anexo'),
      // Sem `response` no schema: o corpo é binário, e um serializador de JSON
      // compilado em cima dele transformaria os bytes em outra coisa.
      schema: { params: PARAMS },
    },
    async (req, reply) => {
      const { id } = req.params;

      const anexo = await prisma.anexo.findUnique({
        where: { id },
        select: { nome: true, mime: true, bytes: true, conteudo: true },
      });
      if (!anexo) return reply.status(404).send({ erro: 'anexo não encontrado' });

      return (
        reply
          .header('content-type', anexo.mime)
          .header('content-length', String(anexo.bytes))
          .header('x-content-type-options', 'nosniff')
          // O nome vai como `filename*` em UTF-8 porque anexo brasileiro tem acento
          // e `filename=` puro só carrega ASCII.
          .header(
            'content-disposition',
            `attachment; filename*=UTF-8''${encodeURIComponent(anexo.nome)}`
          )
          .send(Buffer.from(anexo.conteudo))
      );
    }
  );

  // Apagar anexo existe (diferente de comentário) porque anexo é ARQUIVO, não
  // rastro: quem sobe o print errado - ou o print com o dado de outra pessoa -
  // precisa poder tirá-lo. E, no SQLite, o espaço só volta quando a linha sai.
  app.delete<{ Params: { id: number } }>(
    '/internal/anexos/:id',
    {
      onRequest: exigirToken('Acesso negado à exclusão de anexo'),
      schema: { params: PARAMS, response: { 200: RESPOSTA_APAGADO } },
    },
    async (req, reply) => {
      const { id } = req.params;

      const existe = await prisma.anexo.findUnique({ where: { id }, select: { id: true } });
      if (!existe) return reply.status(404).send({ erro: 'anexo não encontrado' });

      await prisma.anexo.delete({ where: { id } });
      req.log.info({ anexoId: id }, 'Anexo excluído');
      return reply.send({ id, apagado: true });
    }
  );

  /* ---------- Dependências -------------------------------------------- */

  /**
   * Registra que ESTE chamado (`:id`) está bloqueado por outro (`bloqueadorId`).
   *
   * A direção está no nome, e é o que evita a ambiguidade de "vincular chamados":
   * o `:id` é sempre o travado. Para dizer o contrário, chama-se a rota com os
   * dois trocados.
   *
   * Duas recusas, as duas por motivos concretos:
   *   - um chamado bloqueado por si mesmo é um deadlock desenhado à mão;
   *   - A bloquear B com B já bloqueando A é o ciclo de dois, e nenhum dos dois
   *     poderia jamais sair da fila. Ciclos mais longos (A->B->C->A) NÃO são
   *     recusados: detectá-los exige percorrer o grafo a cada inserção, e o
   *     estrago de um ciclo longo é uma leitura confusa, não um travamento -
   *     diferente do caso de dois, que é o erro que se comete sem perceber.
   */
  app.post<{ Params: { id: number }; Body: { bloqueadorId: number } }>(
    '/internal/chamados/:id/dependencias',
    {
      onRequest: exigirToken('Acesso negado às dependências do chamado'),
      schema: {
        params: PARAMS,
        body: {
          type: 'object',
          properties: { bloqueadorId: { type: 'integer', minimum: 1 } },
          required: ['bloqueadorId'],
          additionalProperties: false,
        },
        response: { 201: LIGACAO },
      },
    },
    async (req, reply) => {
      const { id } = req.params;
      const { bloqueadorId } = req.body;

      if (id === bloqueadorId) {
        return reply.status(400).send({ erro: 'um chamado não pode bloquear a si mesmo' });
      }

      if (!(await chamadoExiste(id))) {
        return reply.status(404).send({ erro: 'chamado não encontrado' });
      }

      // O `:id` é o chamado que RECEBE a dependência - é ele que muda, e é ele
      // que precisa estar aberto para mudar.
      const encerrada = await situacaoEncerrada(id);
      if (encerrada !== null) return recusaDeEncerrado(reply, encerrada);

      const bloqueador = await prisma.chamado.findUnique({
        where: { id: bloqueadorId },
        select: { id: true, resumo: true, situacao: true },
      });
      if (!bloqueador) {
        return reply.status(400).send({ erro: `chamado ${bloqueadorId} não existe` });
      }

      const inversa = await prisma.dependencia.findUnique({
        where: { bloqueadoId_bloqueadorId: { bloqueadoId: bloqueadorId, bloqueadorId: id } },
        select: { id: true },
      });
      if (inversa) {
        return reply.status(409).send({
          erro: `chamado ${bloqueadorId} já está bloqueado por este: criaria um ciclo`,
        });
      }

      try {
        await prisma.dependencia.create({ data: { bloqueadoId: id, bloqueadorId } });
      } catch (err) {
        // P2002 = a mesma dependência já registrada. Não é erro do ponto de vista
        // de quem clicou duas vezes: o estado desejado já vale.
        if (err instanceof Prisma.PrismaClientKnownRequestError && err.code === 'P2002') {
          return reply.status(409).send({ erro: 'essa dependência já está registrada' });
        }
        throw err;
      }

      req.log.info({ chamadoId: id, bloqueadorId }, 'Dependência registrada');
      return reply.status(201).send({
        chamadoId: bloqueador.id,
        resumo: bloqueador.resumo,
        situacao: bloqueador.situacao,
      });
    }
  );

  app.delete<{ Params: { id: number; bloqueadorId: number } }>(
    '/internal/chamados/:id/dependencias/:bloqueadorId',
    {
      onRequest: exigirToken('Acesso negado às dependências do chamado'),
      schema: { params: PARAMS_DEPENDENCIA, response: { 200: RESPOSTA_APAGADO } },
    },
    async (req, reply) => {
      const { id, bloqueadorId } = req.params;

      // Mesma regra da criação: destravar também é mexer no chamado. Sem isto,
      // um chamado resolvido aceitaria perder dependência mas não ganhar - meia
      // regra, que é pior que nenhuma porque ninguém consegue prever.
      const encerrada = await situacaoEncerrada(id);
      if (encerrada !== null) return recusaDeEncerrado(reply, encerrada);

      const alvo = await prisma.dependencia.findUnique({
        where: { bloqueadoId_bloqueadorId: { bloqueadoId: id, bloqueadorId } },
        select: { id: true },
      });
      if (!alvo) return reply.status(404).send({ erro: 'dependência não encontrada' });

      await prisma.dependencia.delete({ where: { id: alvo.id } });
      req.log.info({ chamadoId: id, bloqueadorId }, 'Dependência removida');
      return reply.send({ id: alvo.id, apagado: true });
    }
  );
}
