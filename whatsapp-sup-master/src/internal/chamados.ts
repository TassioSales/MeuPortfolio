import { FastifyInstance } from 'fastify';
import { Prisma, Situacao, TipoChamado } from '../generated/prisma/client';
import { LIMITES, MIN_CARACTERES } from '../conversation/flows';
import { prisma } from '../db/client';
import { erroSeguro } from '../log';
import { CorpoWhatsApp, corpoTexto } from '../whatsapp/client';
import { despachar } from '../whatsapp/outbox';
import { exigirToken } from './auth';
import {
  CAMPOS_PAINEL,
  CHAMADO_NO_PAINEL,
  Corpo as CorpoCampos,
  LIMITES_CAMPOS,
  PROPRIEDADES,
  montarDados,
  paraOPainel,
} from './camposDeChamado';

// O bot nunca muda a situação sozinho - isso é decisão de um atendente humano.
// Este endpoint é a metade que faltava: sem ele o chamado nasce `aberto` e nada
// no sistema consegue movê-lo.

// A lista tem de acompanhar o enum `Situacao` do schema, e a ordem e a do ciclo
// de vida - e a mesma das colunas do quadro (`columns` em data.js).
//
// `aguardando_resposta` e `fechado` entraram com a classificacao: a primeira e o
// chamado parado esperando QUEM PEDIU (e nao a equipe), a segunda e o
// encerramento administrativo depois de resolvido. Ver o comentario do enum.
const SITUACOES: readonly Situacao[] = [
  'aberto',
  'em_andamento',
  'aguardando_resposta',
  'resolvido',
  'fechado',
  'cancelado',
];

// As situacoes que contam como CONCLUSAO - as que preenchem `resolvidoEm`.
//
// Sao duas desde que `fechado` existe, e e por isso que virou constante em vez de
// um `=== 'resolvido'` espalhado: a regra "chamado concluido" e lida em tres
// lugares (`marcosDeSla`, a avaliacao pos-fechamento e o relatorio), e a terceira
// copia e a que esquece de incluir `fechado`.
const CONCLUIDAS: readonly Situacao[] = ['resolvido', 'fechado'];

// Validação declarada em JSON Schema em vez de escrita à mão no handler. O
// Fastify roda isto antes do handler e ainda compila um serializador para a
// resposta. A regra do `id` (inteiro >= 1) e a lista de situações aceitas
// ficam em UM lugar só, em vez de espalhadas por dois `if` que podiam divergir
// da lista acima.
const PARAMS = {
  type: 'object',
  properties: { id: { type: 'integer', minimum: 1 } },
  required: ['id'],
} as const;

const CORPO = {
  type: 'object',
  properties: {
    situacao: { type: 'string', enum: [...SITUACOES] },
    // Avisar o usuário manda mensagem para uma pessoa real: continua sendo
    // opção explícita de quem chama, e o padrão continua sendo não avisar.
    notificarUsuario: { type: 'boolean', default: false },
    // Quem está mudando, para o histórico. Opcional: quem integra sem ter esse
    // dado continua funcionando, e a linha do histórico ainda registra o
    // de/para. O teto de tamanho existe porque isto vai para o banco.
    autor: { type: 'string', minLength: 1, maxLength: 120 },
  },
  required: ['situacao'],
  additionalProperties: false,
} as const;

// `null` é a operação "tirar o assunto deste chamado", e por isso é um valor
// aceito e não a ausência do campo.
const CORPO_CATEGORIA = {
  type: 'object',
  properties: { categoriaId: { type: 'integer', minimum: 1, nullable: true } },
  required: ['categoriaId'],
  additionalProperties: false,
} as const;

// Os limites são os MESMOS do fluxo de conversa (conversation/flows.ts), e são
// importados em vez de repetidos: tarefa e chamado terminam na mesma coluna, e
// dois números que precisam bater e vivem em arquivos diferentes acabam
// divergindo. `MIN_CARACTERES` barra o campo de uma letra; o `trim` no handler
// barra o campo só de espaços, que `minLength` deixa passar.
const CORPO_TAREFA = {
  type: 'object',
  properties: {
    nome: { type: 'string', minLength: MIN_CARACTERES, maxLength: LIMITES.nome },
    resumo: { type: 'string', minLength: MIN_CARACTERES, maxLength: LIMITES.resumo },
    descricao: { type: 'string', minLength: MIN_CARACTERES, maxLength: LIMITES.descricao },
    // Opcional: tarefa interna nem sempre tem assunto na lista de atendimento, e
    // exigir um faria quem cria escolher qualquer coisa só para o formulário
    // passar - que é pior que a coluna nula para o dashboard.
    categoriaId: { type: 'integer', minimum: 1, nullable: true },
    // Os campos de classificação, espalhados a partir da declaração única em
    // `camposDeChamado.ts`. Todos opcionais: o formulário do painel pede o que
    // faz sentido para o tipo escolhido, e obrigar a preencher os 24 aqui faria
    // "criar tarefa" deixar de ser um caminho rápido.
    ...PROPRIEDADES,
    // As etiquetas livres, por NOME e não por id: quem cria digita "black
    // friday", não escolhe de uma lista. Quem resolve nome -> linha da tabela
    // `Tag` é o servidor, com `connectOrCreate`.
    //
    // `minLength: 0` de propósito: uma caixa de texto separada por vírgula produz
    // item vazio com facilidade ("pdv, , fiscal"), e recusar o pedido INTEIRO por
    // causa de uma vírgula sobrando seria hostil. `normalizarTags` descarta o
    // vazio - a validação que importa (repetida, caixa alta) mora lá de qualquer
    // forma, porque tem de valer para quem chama a API sem passar pela tela.
    tags: { type: 'array', items: { type: 'string', minLength: 0, maxLength: 40 }, maxItems: 20 },
  },
  required: ['nome', 'resumo', 'descricao'],
  additionalProperties: false,
} as const;

// Devolve o mínimo: o painel recarrega a lista depois de criar, em vez de montar
// o cartão a partir daqui. Assim existe UMA forma de um cartão chegar à tela (a
// listagem), e não duas que podem divergir.
const RESPOSTA_TAREFA = {
  type: 'object',
  properties: {
    id: { type: 'integer' },
    situacao: { type: 'string' },
    origem: { type: 'string' },
  },
  required: ['id', 'situacao', 'origem'],
} as const;

const QUERY_LISTA = {
  type: 'object',
  properties: {
    situacao: { type: 'string', enum: [...SITUACOES] },
    limite: { type: 'integer', minimum: 1, maximum: 500, default: 200 },
  },
} as const;

// `CHAMADO_NO_PAINEL` e `CAMPOS_PAINEL` moram em `camposDeChamado.ts`, junto da
// declaração dos campos que eles expõem: a rota de criação, a de alteração e esta
// listagem precisam da MESMA lista de colunas, e mantê-la em três arquivos é como
// um campo novo aparece no banco e nunca chega à tela.

const RESPOSTA_LISTA = {
  type: 'object',
  properties: {
    chamados: { type: 'array', items: CHAMADO_NO_PAINEL },
  },
  required: ['chamados'],
} as const;

const RESPOSTA = {
  type: 'object',
  properties: {
    id: { type: 'integer' },
    situacao: { type: 'string' },
    anterior: { type: 'string' },
    notificado: { type: 'boolean' },
    // Os marcos como ficaram DEPOIS da mudança, para o painel atualizar o cartão
    // sem uma segunda ida ao servidor.
    primeiroAtendimentoEm: { type: 'string', nullable: true },
    resolvidoEm: { type: 'string', nullable: true },
  },
  required: ['id', 'situacao', 'anterior', 'notificado'],
} as const;

const RESPOSTA_CATEGORIA = {
  type: 'object',
  properties: {
    id: { type: 'integer' },
    categoriaId: { type: 'integer', nullable: true },
  },
  required: ['id'],
} as const;

// Todos os campos de classificação, todos opcionais.
//
// `minProperties: 1` barra o PATCH literalmente vazio, mas NÃO basta, e é bom
// saber por quê: o Fastify roda o AJV com `removeAdditional`, e o AJV avalia
// `minProperties` ANTES de remover o que `additionalProperties: false` recusa.
// Então `{ "prioridadeee": "alta" }` passa pelas duas regras - tem uma
// propriedade na hora da contagem, e chega ao handler sem nenhuma. Quem fecha
// essa brecha é a conferência de `dados` vazio no handler.
const CORPO_CAMPOS = {
  type: 'object',
  properties: { ...PROPRIEDADES },
  additionalProperties: false,
  minProperties: 1,
} as const;

// Nota de 1 a 5. A faixa é conferida aqui, e não por CHECK no banco: o SQLite
// tem CHECK, mas o Prisma não o declara no schema, então uma restrição criada à
// mão sumiria na próxima migração que reconstruísse a tabela - e reconstruir a
// tabela é como o SQLite adiciona coluna.
const CORPO_AVALIACAO = {
  type: 'object',
  properties: {
    nota: { type: 'integer', minimum: 1, maximum: 5 },
    // O teto vem de `LIMITES_CAMPOS` e não repetido aqui: é o mesmo texto que
    // termina na mesma coluna, e dois números que precisam bater e vivem em
    // arquivos diferentes acabam divergindo.
    comentario: {
      type: 'string',
      maxLength: LIMITES_CAMPOS.avaliacaoComentario,
      nullable: true,
    },
  },
  required: ['nota'],
  additionalProperties: false,
} as const;

const RESPOSTA_AVALIACAO = {
  type: 'object',
  properties: {
    id: { type: 'integer' },
    avaliacaoNota: { type: 'integer', nullable: true },
    avaliacaoComentario: { type: 'string', nullable: true },
    avaliadoEm: { type: 'string', nullable: true },
  },
  required: ['id'],
} as const;

const RESPOSTA_HISTORICO = {
  type: 'object',
  properties: {
    chamadoId: { type: 'integer' },
    mudancas: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          de: { type: 'string' },
          para: { type: 'string' },
          // `nullable` e não a ausência do campo: quem consome não precisa
          // distinguir "não informado" de "campo que às vezes some".
          autor: { type: 'string', nullable: true },
          criadoEm: { type: 'string' },
        },
        required: ['de', 'para', 'criadoEm'],
      },
    },
  },
  required: ['chamadoId', 'mudancas'],
} as const;

const QUERY_METRICAS = {
  type: 'object',
  properties: {
    // ISO-8601. Validado com `Date.parse` no handler em vez de `format:
    // date-time` no schema: o `format` depende de o AJV estar com os formatos
    // carregados, e uma janela silenciosamente ignorada devolveria número certo
    // do período errado.
    desde: { type: 'string', minLength: 4, maxLength: 40 },
    ate: { type: 'string', minLength: 4, maxLength: 40 },
  },
} as const;

const LINHA_METRICA = {
  type: 'object',
  properties: {
    // `id` e nao `categoriaId`: a mesma linha agora descreve grupo de assunto, de
    // setor e de tipo, e um campo chamado `categoriaId` dentro de um agrupamento
    // por setor seria mentira. Nulo no grupo "sem classificacao" e no geral.
    id: { type: 'integer', nullable: true },
    codigo: { type: 'string' },
    rotulo: { type: 'string' },
    total: { type: 'integer' },
    // Um contador por situacao. Precisa acompanhar o enum `Situacao`: uma
    // situacao sem contador aqui some do relatorio sem aparecer em lugar nenhum,
    // e o total deixa de bater com a soma das colunas.
    aberto: { type: 'integer' },
    em_andamento: { type: 'integer' },
    aguardando_resposta: { type: 'integer' },
    resolvido: { type: 'integer' },
    fechado: { type: 'integer' },
    cancelado: { type: 'integer' },
    // Médias em MINUTOS, nulas enquanto nenhum chamado do grupo atingiu o marco.
    // Zero e "nunca aconteceu" são coisas diferentes e não podem virar o mesmo
    // número no gráfico.
    atendimentoMedioMin: { type: 'number', nullable: true },
    resolucaoMediaMin: { type: 'number', nullable: true },
    // O tamanho da amostra de cada média. Sem ele, "12 min" calculado sobre um
    // chamado só é indistinguível de "12 min" sobre duzentos.
    atendidos: { type: 'integer' },
    resolvidos: { type: 'integer' },
  },
  required: ['id', 'codigo', 'rotulo', 'total', 'atendidos', 'resolvidos'],
} as const;

const RESPOSTA_METRICAS = {
  type: 'object',
  properties: {
    janela: {
      type: 'object',
      properties: {
        desde: { type: 'string', nullable: true },
        ate: { type: 'string', nullable: true },
      },
    },
    geral: LINHA_METRICA,
    // Tres cortes do mesmo periodo, e nao um so: assunto responde "sobre o que
    // nos procuram", setor responde "quem esta atendendo" e tipo separa a
    // demanda interna da rede de franquias. Sao a razao de os campos existirem, e
    // agrupar tres vezes custa uma passada a mais sobre linhas ja carregadas.
    porCategoria: { type: 'array', items: LINHA_METRICA },
    porSetor: { type: 'array', items: LINHA_METRICA },
    porTipo: { type: 'array', items: LINHA_METRICA },
  },
  required: ['janela', 'geral', 'porCategoria', 'porSetor', 'porTipo'],
} as const;

const AVISOS: Partial<Record<Situacao, (id: number) => string>> = {
  em_andamento: (id) => `Seu chamado #${id} está sendo analisado pela nossa equipe.`,
  // A única das mensagens que PEDE algo: é o estado que só sai do lugar quando o
  // solicitante responde, e um aviso que não diz isso deixa os dois lados
  // esperando o outro.
  aguardando_resposta: (id) =>
    `Seu chamado #${id} está aguardando sua resposta. ` +
    `Assim que você responder por aqui, seguimos com o atendimento.`,
  resolvido: (id) =>
    `Seu chamado #${id} foi marcado como resolvido. ` +
    `Se o problema continuar, é só mandar uma mensagem que abrimos outro.`,
  fechado: (id) =>
    `Seu chamado #${id} foi encerrado. Obrigado pelo contato — ` +
    `se precisar de algo, é só mandar uma mensagem que abrimos um novo.`,
  cancelado: (id) => `Seu chamado #${id} foi cancelado.`,
};

type Alterada = {
  anterior: Situacao;
  situacao: Situacao;
  primeiroAtendimentoEm: Date | null;
  resolvidoEm: Date | null;
  /** Linha da outbox a despachar depois do commit, se for para notificar. */
  saida: { id: number; corpo: CorpoWhatsApp } | null;
  /** Pediram aviso, a situação mudou, e não havia telefone: é tarefa do painel. */
  avisoImpossivel?: boolean;
};

/**
 * Os dois marcos de SLA, decididos em um lugar só.
 *
 * Esta é a REGRA que justifica `primeiroAtendimentoEm` e `resolvidoEm` serem
 * colunas em vez de um `SELECT` sobre `MudancaSituacao`. Derivar exigiria varrer
 * o histórico a cada consulta do painel e reimplementar estas três linhas em cada
 * consumidor - e a segunda cópia é a que erra.
 *
 *   - `primeiroAtendimentoEm`: a PRIMEIRA saída de `aberto`. Não se repete, e é o
 *     `=== null` que garante isso: um chamado reaberto e pego de novo continua
 *     medindo a espera original, que é o que "tempo até alguém pegar" significa.
 *   - `resolvidoEm`: preenchido ao entrar em situação CONCLUÍDA (`resolvido` ou
 *     `fechado`), ZERADO ao sair de todas elas. Sem o zerar, a média de tempo de
 *     resolução contaria uma resolução desfeita - e um chamado que voltou para
 *     `aberto` apareceria como resolvido no relatório.
 *
 *     As duas situações contam porque `fechado` é o encerramento administrativo
 *     de um chamado que ACABOU: se só `resolvido` marcasse o instante, mover de
 *     `resolvido` para `fechado` apagaria a data de conclusão do próprio chamado
 *     que estava sendo dado por concluído. E `resolvido -> fechado` não move o
 *     marco de novo, porque as duas já são concluídas - só a ENTRADA no conjunto
 *     conta.
 */
function marcosDeSla(
  anterior: Situacao,
  situacao: Situacao,
  primeiroAtendimentoEm: Date | null,
  agora: Date
): { primeiroAtendimentoEm?: Date; resolvidoEm?: Date | null } {
  const marcos: { primeiroAtendimentoEm?: Date; resolvidoEm?: Date | null } = {};

  if (primeiroAtendimentoEm === null && situacao !== 'aberto') {
    marcos.primeiroAtendimentoEm = agora;
  }

  const eraConcluida = CONCLUIDAS.includes(anterior);
  const ehConcluida = CONCLUIDAS.includes(situacao);
  if (ehConcluida && !eraConcluida) marcos.resolvidoEm = agora;
  else if (eraConcluida && !ehConcluida) marcos.resolvidoEm = null;

  return marcos;
}

/**
 * Aplica a mudança de situação lendo e gravando na MESMA transação.
 *
 * A transação é o que serializa duas mudanças concorrentes no mesmo chamado:
 * antes, ler a situação atual e gravar a nova eram duas consultas soltas, então
 * dois PATCH simultâneos liam a mesma situação anterior, os dois consideravam
 * que houve mudança e os dois notificavam o usuário.
 *
 * No Postgres quem garantia isso era o `SELECT ... FOR UPDATE`, que travava só
 * a linha disputada. No SQLite não existe lock de linha - e não é preciso: o
 * adaptador segura um mutex do `BEGIN` até o commit, então duas transações deste
 * processo nunca se sobrepõem (ver src/db/client.ts). Por isso a leitura aqui
 * voltou a ser um `findUnique` comum: o que a torna segura é estar DENTRO do
 * `$transaction`, e tirá-la de lá reintroduz a corrida.
 *
 * Vale para os marcos de SLA também: `primeiroAtendimentoEm` é lido e gravado
 * aqui dentro, então dois PATCH simultâneos não conseguem os dois achar que a
 * coluna estava nula.
 *
 * A notificação é apenas ENFILEIRADA aqui; o envio acontece depois do commit,
 * para não segurar o lock de escrita do banco durante uma chamada HTTP - o que
 * no SQLite é mais grave que no Postgres, porque o lock é do ARQUIVO INTEIRO.
 */
async function alterarSituacao(
  id: number,
  situacao: Situacao,
  notificar: boolean,
  autor?: string
): Promise<Alterada | null> {
  return prisma.$transaction(async (tx) => {
    const atual = await tx.chamado.findUnique({
      where: { id },
      select: {
        situacao: true,
        telefone: true,
        primeiroAtendimentoEm: true,
        resolvidoEm: true,
      },
    });
    if (atual === null) return null;

    const { situacao: anterior, telefone } = atual;

    // Um PATCH que repete a situação atual não é evento de atendimento: não move
    // marco, não grava histórico e não notifica. As três regras leem a MESMA
    // comparação, de propósito.
    const mudou = situacao !== anterior;
    const marcos = mudou
      ? marcosDeSla(anterior, situacao, atual.primeiroAtendimentoEm, new Date())
      : {};

    const depois = await tx.chamado.update({
      where: { id },
      data: { situacao, ...marcos },
      select: { primeiroAtendimentoEm: true, resolvidoEm: true },
    });

    // Histórico dentro da MESMA transação que leu a situação anterior: ou a
    // situação muda e fica registrada, ou nada acontece. Gravar depois do
    // commit deixaria a janela em que o chamado mudou e a auditoria não sabe.
    if (mudou) {
      await tx.mudancaSituacao.create({
        data: { chamadoId: id, de: anterior, para: situacao, autor: autor ?? null },
      });
    }

    const comum = {
      anterior,
      situacao,
      primeiroAtendimentoEm: depois.primeiroAtendimentoEm,
      resolvidoEm: depois.resolvidoEm,
    };

    // Avisar o usuário é opcional e desligado por padrão: manda mensagem para
    // uma pessoa real, então quem chama decide.
    //
    // Tarefa criada no painel não tem telefone, e a consequência é maior do que
    // "não dá para avisar": ela é o que garante que tarefa NÃO gera log de
    // conversa. A única linha de `Mensagem` que este arquivo cria é a de saída,
    // logo abaixo — sem telefone o fluxo para aqui e nada é gravado.
    //
    // A situação muda de qualquer forma: recusar o PATCH inteiro faria um
    // atendente com "avisar" ligado não conseguir mover tarefa nenhuma. Em vez
    // de silêncio, devolvemos `avisoImpossivel` para a rota registrar.
    // `!telefone` e não `=== null`: a coluna nula é o caso de hoje, mas string
    // vazia também não é destino de mensagem, e o guarda não deve depender de
    // qual das duas formas o driver devolve.
    const querAviso = notificar && mudou;
    if (querAviso && !telefone) {
      return { ...comum, saida: null, avisoImpossivel: true };
    }
    const texto = querAviso ? AVISOS[situacao]?.(id) : undefined;
    if (!texto || !telefone) return { ...comum, saida: null };

    const corpo = corpoTexto(telefone, texto);
    const linha = await tx.mensagem.create({
      data: {
        telefone,
        chamadoId: id,
        remetente: 'sistema',
        texto,
        payload: corpo as Prisma.InputJsonValue,
        enviadaEm: null,
      },
    });

    return { ...comum, saida: { id: linha.id, corpo } };
  });
}

// --- Métricas -------------------------------------------------------------

type LinhaCrua = {
  categoriaId: number | null;
  setorId: number | null;
  tipo: TipoChamado | null;
  situacao: Situacao;
  dataAbertura: Date;
  primeiroAtendimentoEm: Date | null;
  resolvidoEm: Date | null;
};

type Acumulador = {
  // Nulo quando o grupo não tem id numérico: o grupo "sem classificação", o
  // total geral, e os grupos por `tipo` (cuja chave é o próprio valor do enum,
  // não uma linha de tabela).
  id: number | null;
  codigo: string;
  rotulo: string;
  total: number;
  aberto: number;
  em_andamento: number;
  aguardando_resposta: number;
  resolvido: number;
  fechado: number;
  cancelado: number;
  somaAtendimento: number;
  atendidos: number;
  somaResolucao: number;
  resolvidos: number;
};

/** Como um grupo se apresenta: chave estável para integração, texto para gente. */
type Rotulo = { codigo: string; rotulo: string };

const MS_POR_MINUTO = 60_000;

function novoAcumulador(id: number | null, codigo: string, rotulo: string): Acumulador {
  return {
    id,
    codigo,
    rotulo,
    total: 0,
    aberto: 0,
    em_andamento: 0,
    aguardando_resposta: 0,
    resolvido: 0,
    fechado: 0,
    cancelado: 0,
    somaAtendimento: 0,
    atendidos: 0,
    somaResolucao: 0,
    resolvidos: 0,
  };
}

/**
 * Duração em minutos entre dois instantes, ou `null` se o marco não aconteceu.
 *
 * O `Math.max(0, ...)` cobre um caso que existe de verdade: o marco gravado
 * ANTES da abertura, o que só acontece com relógio fora de sincronia ou linha
 * editada à mão. Um negativo entrando na soma puxa a média para baixo e é
 * invisível no resultado; zero é errado do mesmo jeito, mas não mente sobre a
 * direção.
 */
function duracaoMin(de: Date, ate: Date | null): number | null {
  if (ate === null) return null;
  return Math.max(0, (ate.getTime() - de.getTime()) / MS_POR_MINUTO);
}

function somar(acc: Acumulador, linha: LinhaCrua): void {
  acc.total += 1;
  acc[linha.situacao] += 1;

  const atendimento = duracaoMin(linha.dataAbertura, linha.primeiroAtendimentoEm);
  if (atendimento !== null) {
    acc.somaAtendimento += atendimento;
    acc.atendidos += 1;
  }

  const resolucao = duracaoMin(linha.dataAbertura, linha.resolvidoEm);
  if (resolucao !== null) {
    acc.somaResolucao += resolucao;
    acc.resolvidos += 1;
  }
}

/** Arredonda para uma casa: minuto com seis decimais não informa nada a mais. */
function media(soma: number, n: number): number | null {
  return n === 0 ? null : Math.round((soma / n) * 10) / 10;
}

function publicar(acc: Acumulador) {
  const { somaAtendimento, somaResolucao, ...resto } = acc;
  return {
    ...resto,
    atendimentoMedioMin: media(somaAtendimento, acc.atendidos),
    resolucaoMediaMin: media(somaResolucao, acc.resolvidos),
  };
}

/**
 * Agrupa as MESMAS linhas por um eixo qualquer.
 *
 * Escrita uma vez e usada três (assunto, setor, tipo) porque as três respondem
 * perguntas diferentes sobre o mesmo período - "sobre o que nos procuram", "quem
 * está atendendo", "quanto é interno e quanto é da rede" - e o que muda entre
 * elas é só de onde sai a chave e de onde sai o rótulo. Triplicar o laço seria
 * triplicar a chance de um dos três esquecer uma situação nova.
 *
 * `semClassificacao` é o grupo de quem não tem o campo preenchido, e ele ENTRA no
 * resultado em vez de a linha ser descartada: chamado sem setor continua sendo
 * atendimento, e sumir com ele faria a soma dos grupos não bater com o total.
 *
 * Maior volume primeiro: é a ordem em que a lista é lida quando a pergunta é
 * "onde está o atendimento".
 */
function agrupar(
  linhas: readonly LinhaCrua[],
  chave: (l: LinhaCrua) => number | string | null,
  rotulos: Map<number | string, Rotulo>,
  semClassificacao: Rotulo
) {
  const grupos = new Map<number | string | null, Acumulador>();

  for (const linha of linhas) {
    const k = chave(linha);
    let grupo = grupos.get(k);

    if (grupo === undefined) {
      const r = k === null ? undefined : rotulos.get(k);
      // `r` ausente com `k` presente é a linha órfã: o setor ou a categoria foi
      // apagada por SQL crua e a coluna ficou apontando para um id que não
      // existe mais. Entra como "sem classificação" em vez de derrubar a
      // resposta - o mesmo tratamento que a coluna nula recebe.
      grupo = novoAcumulador(
        r && typeof k === 'number' ? k : null,
        r ? r.codigo : semClassificacao.codigo,
        r ? r.rotulo : semClassificacao.rotulo
      );
      grupos.set(k, grupo);
    }

    somar(grupo, linha);
  }

  return [...grupos.values()].sort((a, b) => b.total - a.total).map(publicar);
}

// Os dois valores de `TipoChamado`, com texto de tela. É um mapa literal e não
// uma consulta porque `tipo` é enum: a lista só muda com migração, e é aí que
// este mapa tem de ser lembrado.
const ROTULOS_TIPO = new Map<number | string, Rotulo>([
  ['interno', { codigo: 'interno', rotulo: 'Interno' }],
  ['franquia', { codigo: 'franquia', rotulo: 'Franquia' }],
]);

export function registrarRotasInternas(app: FastifyInstance): void {
  // Leitura para o painel de chamados.
  //
  // `telefone` NÃO entra na resposta, e isso não é esquecimento: é a mesma
  // minimização que a view `chamados_para_cards` aplica. O painel roda no
  // navegador de quem atende e não precisa do telefone para nada - `nome`,
  // `resumo` e `descricao` já são dado pessoal suficiente para exigir token.
  //
  // A consulta é pelo Prisma, e não pela view, de propósito: a view é aplicada
  // à mão (ver sql/view_chamados_para_cards.sql) e pode não existir num banco
  // recém-migrado. Ela continua servindo o caso para o qual foi feita - um
  // usuário de banco separado, com SELECT só nela.
  app.get<{ Querystring: { situacao?: Situacao; limite?: number } }>(
    '/internal/chamados',
    {
      onRequest: exigirToken('Acesso negado à listagem de chamados'),
      schema: {
        querystring: QUERY_LISTA,
        response: { 200: RESPOSTA_LISTA },
      },
    },
    async (req) => {
      const { situacao, limite = 200 } = req.query;

      const chamados = await prisma.chamado.findMany({
        where: situacao ? { situacao } : undefined,
        // A lista de colunas mora em `camposDeChamado.ts`, junto do schema que as
        // declara: campo novo entra em um lugar e chega à tela por este select.
        //
        // `tags` sai junto, e é a única relação carregada aqui. As outras três
        // (comentários, anexos, dependências) ficam para `GET
        // /internal/chamados/:id/detalhe`: elas são listas que só o chamado
        // ABERTO na tela precisa, e trazê-las para 500 cartões carregaria centenas
        // de linhas que ninguém vai olhar. Tag é diferente porque aparece NO
        // cartão.
        select: { ...CAMPOS_PAINEL, tags: { select: { nome: true }, orderBy: { nome: 'asc' } } },
        orderBy: { dataAbertura: 'desc' },
        take: limite,
      });

      return { chamados: chamados.map(paraOPainel) };
    }
  );

  /**
   * Números por assunto e tempo de atendimento, para o dashboard.
   *
   * A agregação acontece em JS, e não em `groupBy`/SQL crua, por dois motivos que
   * puxam para o mesmo lado: as duas médias precisam de uma REGRA (só entra na
   * conta quem atingiu o marco, e a amostra viaja junto com a média) que em SQL
   * viraria um `CASE` por coluna; e SQL crua neste projeto já quebrou duas vezes
   * na comparação de data com o SQLite (ver o comentário no model `Mensagem`).
   *
   * O custo é ler as linhas da janela. Com o volume deste bot é uma varredura de
   * índice sobre alguns milhares de linhas de cinco colunas - se um dia deixar de
   * ser, o caminho é materializar por dia, não voltar para SQL crua.
   */
  app.get<{ Querystring: { desde?: string; ate?: string } }>(
    '/internal/metricas',
    {
      onRequest: exigirToken('Acesso negado às métricas'),
      schema: { querystring: QUERY_METRICAS, response: { 200: RESPOSTA_METRICAS } },
    },
    async (req, reply) => {
      const analisar = (valor: string | undefined, campo: string): Date | null | undefined => {
        if (valor === undefined) return null;
        const instante = new Date(valor);
        if (Number.isNaN(instante.getTime())) {
          void reply.status(400).send({ erro: `${campo} não é uma data ISO-8601 válida` });
          return undefined;
        }
        return instante;
      };

      const desde = analisar(req.query.desde, 'desde');
      if (desde === undefined) return reply;
      const ate = analisar(req.query.ate, 'ate');
      if (ate === undefined) return reply;

      const janela: Prisma.DateTimeFilter = {};
      if (desde !== null) janela.gte = desde;
      if (ate !== null) janela.lte = ate;

      const linhas = (await prisma.chamado.findMany({
        where: desde !== null || ate !== null ? { dataAbertura: janela } : undefined,
        select: {
          categoriaId: true,
          setorId: true,
          tipo: true,
          situacao: true,
          dataAbertura: true,
          primeiroAtendimentoEm: true,
          resolvidoEm: true,
        },
      })) as LinhaCrua[];

      // Os rótulos vêm da tabela, e as INATIVAS entram: um assunto desativado
      // ontem continua tendo histórico, e sumir do relatório faria o total por
      // categoria não bater com o total geral.
      const categorias = await prisma.categoria.findMany({
        select: { id: true, codigo: true, rotulo: true },
      });
      const setores = await prisma.setor.findMany({
        select: { id: true, codigo: true, nome: true },
      });

      const rotulosCategoria = new Map<number | string, Rotulo>(
        categorias.map((c) => [c.id, { codigo: c.codigo, rotulo: c.rotulo }])
      );
      // O setor tem `nome` e não `rotulo`: ele nunca aparece na conversa, então
      // não existe a divisão entre nome interno e nome de exibição que a
      // `Categoria` carrega.
      const rotulosSetor = new Map<number | string, Rotulo>(
        setores.map((x) => [x.id, { codigo: x.codigo, rotulo: x.nome }])
      );

      const geral = novoAcumulador(null, 'geral', 'Todos os chamados');
      for (const linha of linhas) somar(geral, linha);

      return reply.send({
        janela: {
          desde: desde?.toISOString() ?? null,
          ate: ate?.toISOString() ?? null,
        },
        geral: publicar(geral),
        porCategoria: agrupar(linhas, (l) => l.categoriaId, rotulosCategoria, {
          codigo: 'sem_categoria',
          rotulo: 'Sem assunto',
        }),
        porSetor: agrupar(linhas, (l) => l.setorId, rotulosSetor, {
          codigo: 'sem_setor',
          rotulo: 'Sem setor',
        }),
        porTipo: agrupar(linhas, (l) => l.tipo, ROTULOS_TIPO, {
          codigo: 'sem_tipo',
          rotulo: 'Sem tipo',
        }),
      });
    }
  );

  // Histórico de atendimento do chamado. Sem `telefone` aqui também, pela mesma
  // minimização da listagem: o painel mostra quem mexeu e quando, não o dado do
  // titular.
  app.get<{ Params: { id: number } }>(
    '/internal/chamados/:id/historico',
    {
      onRequest: exigirToken('Acesso negado ao histórico de chamado'),
      schema: { params: PARAMS, response: { 200: RESPOSTA_HISTORICO } },
    },
    async (req, reply) => {
      const { id } = req.params;

      // Checa o chamado antes: sem isso, um id inexistente devolveria
      // `mudancas: []` - indistinguível de um chamado que existe e nunca mudou
      // de situação.
      const existe = await prisma.chamado.findUnique({ where: { id }, select: { id: true } });
      if (!existe) return reply.status(404).send({ erro: 'chamado não encontrado' });

      const mudancas = await prisma.mudancaSituacao.findMany({
        where: { chamadoId: id },
        select: { de: true, para: true, autor: true, criadoEm: true },
        orderBy: { criadoEm: 'desc' },
      });

      return reply.send({
        chamadoId: id,
        // ISO pelo mesmo motivo da listagem: o painel precisa do instante em UTC
        // para mostrar no fuso de quem está olhando.
        mudancas: mudancas.map((m) => ({ ...m, criadoEm: m.criadoEm.toISOString() })),
      });
    }
  );

  app.patch<{
    Params: { id: number };
    Body: { situacao: Situacao; notificarUsuario?: boolean; autor?: string };
  }>(
    '/internal/chamados/:id/situacao',
    {
      onRequest: exigirToken('Acesso negado ao endpoint interno'),
      schema: {
        params: PARAMS,
        body: CORPO,
        response: { 200: RESPOSTA },
      },
    },
    async (req, reply) => {
      const { id } = req.params;
      const { situacao, notificarUsuario, autor } = req.body;

      const r = await alterarSituacao(id, situacao, notificarUsuario === true, autor);
      if (!r) return reply.status(404).send({ erro: 'chamado não encontrado' });

      req.log.info(
        { chamadoId: id, de: r.anterior, para: situacao, autor },
        'Situação do chamado alterada'
      );

      // Pediram aviso numa tarefa do painel. Não é erro — a situação mudou e a
      // resposta diz `notificado: false` —, mas não pode ser silencioso: quem
      // integra sem ler `origem` acharia que avisou alguém.
      if (r.avisoImpossivel) {
        req.log.warn(
          { chamadoId: id },
          'Aviso pedido para tarefa do painel: não há telefone, nada foi enviado'
        );
      }

      // Fora da transação: nenhuma chamada de rede segurando lock de linha.
      let notificado = false;
      if (r.saida) {
        try {
          notificado = await despachar(r.saida.id, r.saida.corpo);
        } catch (err) {
          // A mudança de situação já foi persistida; a notificação não pode
          // desfazê-la. Fica pendente na outbox e o varredor tenta de novo.
          req.log.error(erroSeguro(err), 'Falha ao notificar usuário');
        }
      }

      return reply.send({
        id,
        situacao: r.situacao,
        anterior: r.anterior,
        notificado,
        primeiroAtendimentoEm: r.primeiroAtendimentoEm?.toISOString() ?? null,
        resolvidoEm: r.resolvidoEm?.toISOString() ?? null,
      });
    }
  );

  /**
   * Troca o assunto do chamado.
   *
   * Rota separada da de situação porque as duas mudanças não têm nada em comum
   * além do alvo: mudar situação é evento de atendimento (vai para o histórico,
   * pode notificar o usuário, move marco de SLA); mudar assunto é correção de
   * classificação. Juntar as duas num PATCH genérico faria uma correção de
   * digitação disparar mensagem de WhatsApp.
   *
   * Não notifica ninguém e não grava em `MudancaSituacao` - que é auditoria de
   * SITUAÇÃO, e enfiar outro tipo de evento ali quebraria todo consumidor que lê
   * `de`/`para` como situação.
   */
  app.patch<{ Params: { id: number }; Body: { categoriaId: number | null } }>(
    '/internal/chamados/:id/categoria',
    {
      onRequest: exigirToken('Acesso negado à alteração de categoria do chamado'),
      schema: { params: PARAMS, body: CORPO_CATEGORIA, response: { 200: RESPOSTA_CATEGORIA } },
    },
    async (req, reply) => {
      const { id } = req.params;
      const { categoriaId } = req.body;

      const existe = await prisma.chamado.findUnique({ where: { id }, select: { id: true } });
      if (!existe) return reply.status(404).send({ erro: 'chamado não encontrado' });

      // Só checa que a categoria EXISTE. Nem `ativa` nem `visivelNoWhatsapp`
      // entram na conta, e as duas omissões são deliberadas:
      //   - a INATIVA some do menu, mas continua sendo classificação válida para
      //     quem atende; recusar impediria corrigir um chamado para o assunto
      //     certo só porque ele saiu de circulação;
      //   - a de USO INTERNO existe exatamente para ser usada aqui. É o assunto
      //     que o cliente nunca escolhe e que a TI aplica a mão - recusar neste
      //     ponto seria recusar o recurso inteiro.
      if (categoriaId !== null) {
        const categoria = await prisma.categoria.findUnique({
          where: { id: categoriaId },
          select: { id: true },
        });
        if (!categoria) return reply.status(400).send({ erro: 'categoria não encontrada' });
      }

      await prisma.chamado.update({ where: { id }, data: { categoriaId } });
      req.log.info({ chamadoId: id, categoriaId }, 'Assunto do chamado alterado');

      return reply.send({ id, categoriaId });
    }
  );

  // Criação de tarefa: um chamado que nasce no painel, sem conversa por trás.
  //
  // Rota própria, e não um POST em `/internal/chamados`, por uma razão de
  // segurança e não de estética: `origem: 'painel'` é fixado AQUI DENTRO e não
  // vem do corpo. Não existe como criar, por esta porta, um chamado que se
  // apresente como vindo de conversa — o que importa porque `origem` é o que
  // distingue dado de titular (sujeito a `esquecerTitular`) de trabalho interno.
  //
  // E nada é gravado em `Mensagem`: tarefa não tem log de conversa. Não é uma
  // regra escrita em algum lugar, é consequência de não haver telefone — sem ele
  // não há de quem receber nem a quem enviar. Ver o teste de regressão em
  // test/rotas.test.ts.
  app.post<{
    Body: CorpoCampos & {
      nome: string;
      resumo: string;
      descricao: string;
      categoriaId?: number | null;
      tags?: string[];
    };
  }>(
    '/internal/tarefas',
    {
      onRequest: exigirToken('Acesso negado à criação de tarefa'),
      schema: {
        body: CORPO_TAREFA,
        response: { 201: RESPOSTA_TAREFA },
      },
    },
    async (req, reply) => {
      // `minLength` do schema conta caracteres crus, então "  " passa por ele.
      // O trim acontece antes de gravar, e o que sobra é revalidado: campo só de
      // espaço não vira tarefa com título vazio no quadro.
      const nome = req.body.nome.trim();
      const resumo = req.body.resumo.trim();
      const descricao = req.body.descricao.trim();
      const categoriaId = req.body.categoriaId ?? null;

      if (
        nome.length < MIN_CARACTERES ||
        resumo.length < MIN_CARACTERES ||
        descricao.length < MIN_CARACTERES
      ) {
        return reply
          .status(400)
          .send({ erro: `nome, resumo e descricao precisam de ${MIN_CARACTERES} caracteres` });
      }

      if (categoriaId !== null) {
        const categoria = await prisma.categoria.findUnique({
          where: { id: categoriaId },
          select: { id: true },
        });
        if (!categoria) return reply.status(400).send({ erro: 'categoria não encontrada' });
      }

      // Os campos de classificação passam pela MESMA montagem do PATCH: mesmo
      // trim, mesma checagem de FK, mesma leitura de data ISO. É o motivo de
      // `camposDeChamado.ts` existir - antes disto, criar e corrigir teriam duas
      // validações livres para divergir.
      const montagem = await montarDados(req.body);
      if (!montagem.ok) return reply.status(400).send({ erro: montagem.erro });

      // `canal` não pode herdar o default do banco aqui. Ele é `whatsapp`, e
      // whatsapp é justamente o que esta tarefa NÃO é: ela foi digitada por
      // alguém. `presencial` é o menos errado dos quatro quando não se disse
      // nada, e o formulário do painel oferece os outros três.
      const canal = req.body.canal ?? 'presencial';

      // Etiquetas: `connectOrCreate` por nome normalizado. É o servidor que
      // normaliza (minúsculas, sem espaço nas pontas) porque a garantia tem de
      // valer para quem chama a API sem passar pela tela - sem isso, "PDV" e
      // "pdv" viram duas linhas e o relatório conta o mesmo assunto duas vezes.
      const tags = normalizarTags(req.body.tags);

      const tarefa = await prisma.chamado.create({
        data: {
          ...(montagem.dados as Prisma.ChamadoUncheckedCreateInput),
          nome,
          resumo,
          descricao,
          categoriaId,
          canal,
          // Fixados AQUI DENTRO e não vindos do corpo: não existe como criar, por
          // esta porta, um chamado que se apresente como vindo de conversa.
          origem: 'painel',
          situacao: 'aberto',
          tags: tags.length
            ? { connectOrCreate: tags.map((nome) => ({ where: { nome }, create: { nome } })) }
            : undefined,
        },
        select: { id: true, situacao: true, origem: true },
      });

      req.log.info(
        { chamadoId: tarefa.id, categoriaId, tipo: req.body.tipo, setorId: req.body.setorId },
        'Tarefa criada no painel'
      );
      return reply.status(201).send(tarefa);
    }
  );

  /**
   * Corrige a CLASSIFICAÇÃO do chamado: setor, tipo, prioridade, prazo,
   * responsável, canal e os dois blocos específicos (interno e franquia).
   *
   * Rota separada das outras duas de PATCH, e a separação é a mesma linha que já
   * separava situação de assunto: o que decide não é a forma do dado, é a
   * CONSEQUÊNCIA da escrita.
   *
   *   - situação é evento de atendimento: vai para `MudancaSituacao`, move marco
   *     de SLA e pode disparar mensagem de WhatsApp para o solicitante.
   *   - classificação é organização interna: não notifica ninguém, não entra na
   *     auditoria de situação e não move marco.
   *
   * Se os campos daqui viajassem no mesmo PATCH da situação, corrigir o setor de
   * um chamado mandaria "seu chamado está sendo analisado" para o cliente.
   *
   * A rota NÃO exige que o campo faça sentido para o `tipo`. Preencher
   * `franquiaCodigo` num chamado `interno` é aceito de propósito: o tipo costuma
   * ser descoberto DEPOIS dos dados, e recusar obrigaria a classificar na ordem
   * certa ou perder o que já foi digitado. Quem esconde o campo que não se aplica
   * é o formulário.
   */
  app.patch<{ Params: { id: number }; Body: CorpoCampos }>(
    '/internal/chamados/:id',
    {
      onRequest: exigirToken('Acesso negado à alteração de chamado'),
      schema: {
        params: PARAMS,
        body: CORPO_CAMPOS,
        response: { 200: CHAMADO_NO_PAINEL },
      },
    },
    async (req, reply) => {
      const { id } = req.params;

      const existe = await prisma.chamado.findUnique({ where: { id }, select: { id: true } });
      if (!existe) return reply.status(404).send({ erro: 'chamado não encontrado' });

      const montagem = await montarDados(req.body);
      if (!montagem.ok) return reply.status(400).send({ erro: montagem.erro });

      // Corpo que chegou aqui sem campo nenhum reconhecido: ou vinha vazio, ou
      // todo o conteúdo era campo desconhecido que o Fastify removeu (ver o
      // comentário em `CORPO_CAMPOS`). Nos dois casos, responder 200 com o
      // chamado inteiro faria quem chamou acreditar que gravou - que é o pior
      // resultado possível para um PATCH com nome de campo digitado errado.
      if (Object.keys(montagem.dados).length === 0) {
        return reply
          .status(400)
          .send({ erro: 'nenhum campo conhecido no corpo: nada seria alterado' });
      }

      const atualizado = await prisma.chamado.update({
        where: { id },
        data: montagem.dados,
        select: { ...CAMPOS_PAINEL, tags: { select: { nome: true }, orderBy: { nome: 'asc' } } },
      });

      req.log.info(
        { chamadoId: id, campos: Object.keys(montagem.dados) },
        'Classificação do chamado alterada'
      );

      // Devolve o chamado INTEIRO, e não só o que mudou: o painel repinta o
      // cartão e o detalhe com esta resposta, e um delta obrigaria a tela a
      // remontar o objeto por conta própria - a segunda cópia da tradução que
      // `paraOPainel` existe para evitar.
      return reply.send(paraOPainel(atualizado));
    }
  );

  /**
   * Avaliação pós-fechamento: nota de 1 a 5 e um comentário.
   *
   * `PUT` e não `PATCH` porque a operação é substituir a avaliação inteira -
   * mandar só o comentário e deixar a nota anterior de pé produziria uma
   * avaliação que ninguém deu.
   *
   * Só aceita em chamado CONCLUÍDO (`resolvido` ou `fechado`), e a recusa é o
   * ponto da rota: "avaliação pós-fechamento" avalia um atendimento que
   * terminou. Aceitar num chamado `aberto` deixaria a nota ser dada antes do
   * trabalho e ninguém saberia disso olhando o número.
   *
   * `avaliadoEm` é gravado aqui e não vem do corpo: é o instante em que a
   * avaliação chegou, e quem chama não deve poder datá-la para trás.
   */
  app.put<{ Params: { id: number }; Body: { nota: number; comentario?: string | null } }>(
    '/internal/chamados/:id/avaliacao',
    {
      onRequest: exigirToken('Acesso negado à avaliação de chamado'),
      schema: { params: PARAMS, body: CORPO_AVALIACAO, response: { 200: RESPOSTA_AVALIACAO } },
    },
    async (req, reply) => {
      const { id } = req.params;
      const { nota } = req.body;

      const atual = await prisma.chamado.findUnique({
        where: { id },
        select: { id: true, situacao: true },
      });
      if (!atual) return reply.status(404).send({ erro: 'chamado não encontrado' });

      if (!CONCLUIDAS.includes(atual.situacao)) {
        return reply.status(409).send({
          erro:
            `chamado está em "${atual.situacao}": a avaliação é pós-fechamento e só ` +
            `vale em ${CONCLUIDAS.join(' ou ')}.`,
        });
      }

      const bruto = req.body.comentario;
      const comentario = bruto == null || bruto.trim() === '' ? null : bruto.trim();

      const salvo = await prisma.chamado.update({
        where: { id },
        data: {
          avaliacaoNota: nota,
          avaliacaoComentario: comentario,
          avaliadoEm: new Date(),
        },
        select: { id: true, avaliacaoNota: true, avaliacaoComentario: true, avaliadoEm: true },
      });

      req.log.info({ chamadoId: id, nota }, 'Chamado avaliado');
      return reply.send({ ...salvo, avaliadoEm: salvo.avaliadoEm?.toISOString() ?? null });
    }
  );
}

/**
 * Etiquetas em forma canônica: minúsculas, sem espaço nas pontas, sem vazias e
 * sem repetidas.
 *
 * Roda no SERVIDOR e não só na tela porque `Tag.nome` é único: sem normalizar,
 * "PDV" e "pdv" viram duas linhas, o relatório conta o mesmo assunto duas vezes,
 * e o `connectOrCreate` do mesmo POST estouraria ao tentar criar as duas na
 * mesma transação se elas diferissem só na caixa.
 */
export function normalizarTags(tags: string[] | undefined): string[] {
  if (!tags) return [];
  const vistas = new Set<string>();
  for (const t of tags) {
    const limpo = t.trim().toLowerCase();
    if (limpo !== '') vistas.add(limpo);
  }
  return [...vistas];
}
