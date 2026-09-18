import { FastifyInstance } from 'fastify';
import { Situacao } from '../generated/prisma/client';
import { prisma } from '../db/client';
import { exigirToken } from './auth';

/**
 * Série temporal do atendimento, para o dashboard.
 *
 * Por que uma rota nova e não mais campos em `/internal/metricas`: aquela
 * responde "quanto deu no período", agrupado por assunto/setor/tipo. Esta
 * responde "como variou ao longo do período", que é uma pergunta de forma
 * diferente — o resultado é uma lista de baldes no tempo, não um agregado. Somar
 * as duas na mesma resposta faria um objeto em que metade das chaves ignora o
 * `balde` e a outra metade depende dele.
 *
 * ---------------------------------------------------------------------------
 * O QUE ESTE BANCO PERMITE, E O QUE NÃO
 *
 * O painel que serviu de referência é de fila de mensagens, e lá toda métrica é
 * uma TAXA AMOSTRADA: um agente lê "mensagens por segundo" a cada 15s e grava o
 * ponto. Aqui não existe amostragem — existem EVENTOS com data. Isso muda o que
 * é possível:
 *
 *   - Taxa (aberturas por dia, resoluções por dia, mensagens por hora) sai
 *     direto: é contar eventos por balde.
 *   - Quantidade acumulada (o tamanho da fila às 18h de terça) NÃO está gravada
 *     em lugar nenhum. Ela é RECONSTRUÍDA: para cada chamado se monta a linha do
 *     tempo das situações e se pergunta em que estado ele estava no fim de cada
 *     balde. É exato, não é estimativa - mas é derivado, e é por isso que este
 *     arquivo tem tanto comentário sobre a reconstrução.
 *   - Nada que dependa de amostrar recurso da máquina (memória, disco, sockets)
 *     tem equivalente: este projeto não coleta isso, e inventar um número para
 *     preencher o lugar de um gráfico seria pior que deixar o lugar vazio.
 *
 * A fonte da linha do tempo é `MudancaSituacao`, e não `Chamado.atualizadoEm`.
 * O comentário do próprio model explica por quê: `atualizadoEm` diz QUANDO mudou
 * pela última vez, não DE onde para onde - um chamado resolvido e reaberto é
 * indistinguível de um que nunca saiu de aberto. Usar `atualizadoEm` para
 * desenhar a curva da fila repetiria exatamente o erro que aquela tabela existe
 * para corrigir.
 */

// As situações em que o chamado está NA FILA - ou seja, é trabalho da equipe.
// `aguardando_resposta` entra: o chamado continua aberto e continua ocupando
// lugar, mesmo que o relógio de SLA não deva correr contra a equipe.
const NA_FILA: readonly Situacao[] = ['aberto', 'em_andamento', 'aguardando_resposta'];

// Encerradas. `cancelado` conta como saída da fila mas NÃO como resolução: o
// chamado deixou de ser trabalho sem o problema ter sido resolvido, e somar os
// dois faria a taxa de resolução subir ao cancelar em massa.
const ENCERRADAS: readonly Situacao[] = ['resolvido', 'fechado', 'cancelado'];

const naFila = (s: Situacao) => NA_FILA.includes(s);

type Balde = 'hora' | 'dia' | 'semana';

const MINUTO = 60_000;
const HORA = 60 * MINUTO;
const DIA = 24 * HORA;

const QUERY = {
  type: 'object',
  properties: {
    // ISO-8601, validado com `Date` no handler e não com `format: date-time` no
    // schema - mesma decisão de `/internal/metricas`, e pelo mesmo motivo: o
    // `format` depende de o AJV ter os formatos carregados, e uma janela
    // silenciosamente ignorada devolveria número certo do período errado.
    desde: { type: 'string', minLength: 4, maxLength: 40 },
    ate: { type: 'string', minLength: 4, maxLength: 40 },
    balde: { type: 'string', enum: ['hora', 'dia', 'semana'] },
    /**
     * Deslocamento do fuso de QUEM OLHA, em minutos, no formato que o navegador
     * já produz: `new Date().getTimezoneOffset()` devolve 180 em UTC-3.
     *
     * Vem do cliente e não é constante do servidor porque as datas são gravadas
     * em UTC e "dia" é um conceito local: um chamado aberto às 21h de terça em
     * UTC-3 é 00h de quarta em UTC. Baldeando em UTC, o pico do fim da tarde
     * apareceria no dia seguinte, e o gráfico mentiria justamente na hora de
     * maior movimento.
     *
     * Limite conhecido: é um deslocamento fixo, não um fuso com regras. Numa
     * janela que atravesse mudança de horário de verão, o balde da virada fica
     * uma hora deslocado. O Brasil não tem mais horário de verão desde 2019, o
     * que torna isso teórico aqui - mas está escrito para quem levar o projeto
     * para outro lugar.
     */
    tz: { type: 'integer', minimum: -900, maximum: 900 },
  },
} as const;

const NUM_OU_NULO = { type: ['number', 'null'] } as const;

const BALDE = {
  type: 'object',
  properties: {
    inicio: { type: 'string' },
    aberturas: { type: 'integer' },
    saidas: { type: 'integer' },
    resolucoes: { type: 'integer' },
    cancelamentos: { type: 'integer' },
    reaberturas: { type: 'integer' },
    filaFim: { type: 'integer' },
    filaAberto: { type: 'integer' },
    filaEmAndamento: { type: 'integer' },
    filaAguardando: { type: 'integer' },
    recebidas: { type: 'integer' },
    enviadas: { type: 'integer' },
    envioPendenteFim: { type: 'integer' },
    atendimentoP50: NUM_OU_NULO,
    atendimentoP90: NUM_OU_NULO,
    atendimentoN: { type: 'integer' },
    resolucaoP50: NUM_OU_NULO,
    resolucaoP90: NUM_OU_NULO,
    resolucaoN: { type: 'integer' },
  },
  required: ['inicio'],
} as const;

const RESPOSTA = {
  type: 'object',
  properties: {
    janela: {
      type: 'object',
      properties: {
        desde: { type: 'string' },
        ate: { type: 'string' },
        balde: { type: 'string' },
        tz: { type: 'integer' },
      },
      required: ['desde', 'ate', 'balde', 'tz'],
    },
    baldes: { type: 'array', items: BALDE },
    agora: {
      type: 'object',
      properties: {
        fila: { type: 'integer' },
        aguardandoPrimeiro: { type: 'integer' },
        semResponsavel: { type: 'integer' },
        semClassificacao: { type: 'integer' },
        vencidos: { type: 'integer' },
        venceEm24h: { type: 'integer' },
        envioPendente: { type: 'integer' },
        envioComFalha: { type: 'integer' },
        conversasEmAndamento: { type: 'integer' },
        porSituacao: {
          type: 'object',
          properties: {
            aberto: { type: 'integer' },
            em_andamento: { type: 'integer' },
            aguardando_resposta: { type: 'integer' },
            resolvido: { type: 'integer' },
            fechado: { type: 'integer' },
            cancelado: { type: 'integer' },
          },
        },
      },
    },
    desempenho: {
      type: 'object',
      properties: {
        atendimento: {
          type: 'object',
          properties: {
            p50: NUM_OU_NULO,
            p90: NUM_OU_NULO,
            media: NUM_OU_NULO,
            n: { type: 'integer' },
          },
        },
        resolucao: {
          type: 'object',
          properties: {
            p50: NUM_OU_NULO,
            p90: NUM_OU_NULO,
            media: NUM_OU_NULO,
            n: { type: 'integer' },
          },
        },
        prazo: {
          type: 'object',
          properties: {
            dentro: { type: 'integer' },
            fora: { type: 'integer' },
            semPrazo: { type: 'integer' },
          },
        },
        avaliacao: {
          type: 'object',
          properties: {
            media: NUM_OU_NULO,
            n: { type: 'integer' },
            distribuicao: { type: 'array', items: { type: 'integer' } },
          },
        },
      },
    },
    porSetor: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: ['integer', 'null'] },
          codigo: { type: 'string' },
          rotulo: { type: 'string' },
          fila: { type: 'integer' },
          resolucoes: { type: 'integer' },
          atendimentoP50: NUM_OU_NULO,
          dentro: { type: 'integer' },
          fora: { type: 'integer' },
          nota: NUM_OU_NULO,
          notaN: { type: 'integer' },
        },
        required: ['codigo', 'rotulo'],
      },
    },
  },
  required: ['janela', 'baldes', 'agora', 'desempenho', 'porSetor'],
} as const;

/* ------------------------------------------------------------------ *
 *  Baldes
 * ------------------------------------------------------------------ */

/**
 * Início do balde que contém `t`, no fuso de quem olha.
 *
 * A conta é sempre a mesma: joga o instante para "hora local expressa em ms",
 * corta na unidade, e devolve para UTC. Cortar direto em UTC daria o balde
 * errado em qualquer fuso que não o de Greenwich.
 */
function inicioDoBalde(t: number, balde: Balde, tzMin: number): number {
  const local = t - tzMin * MINUTO;

  if (balde === 'hora') return Math.floor(local / HORA) * HORA + tzMin * MINUTO;

  const dia = Math.floor(local / DIA) * DIA;
  if (balde === 'dia') return dia + tzMin * MINUTO;

  // Semana começando na SEGUNDA. A época (1970-01-01) foi uma quinta, então
  // `dia / DIA` tem resto 3 na segunda - daí o deslocamento de 4 antes do
  // módulo. Segunda e não domingo porque a semana de trabalho é o que o
  // dashboard compara.
  const diasDesdeEpoca = dia / DIA;
  const desdeSegunda = (((diasDesdeEpoca + 4) % 7) + 7) % 7;
  return dia - desdeSegunda * DIA + tzMin * MINUTO;
}

function proximoBalde(inicio: number, balde: Balde, tzMin: number): number {
  if (balde === 'hora') return inicio + HORA;
  // Somar 24h e recortar: em fuso fixo dá no mesmo, mas recortar deixa o
  // resultado correto também se um dia entrar fuso com regra de verão.
  return inicioDoBalde(inicio + (balde === 'dia' ? DIA : 7 * DIA) + HORA, balde, tzMin);
}

/**
 * O balde escolhido quando o cliente não pede um.
 *
 * A regra é "não passar de ~90 pontos no gráfico": mais que isso e cada ponto
 * fica com menos de um pixel de largura útil, o que transforma a linha em ruído.
 */
function baldePadrao(duracaoMs: number): Balde {
  if (duracaoMs <= 3 * DIA) return 'hora';
  if (duracaoMs <= 120 * DIA) return 'dia';
  return 'semana';
}

/* ------------------------------------------------------------------ *
 *  Estatística
 * ------------------------------------------------------------------ */

/**
 * Percentil por posto mais próximo, sobre uma lista JÁ ORDENADA.
 *
 * Sem interpolação de propósito: os valores são durações reais de chamados
 * reais, e devolver um número que não é a duração de nenhum chamado só
 * atrapalha quem vai conferir a conta na tela.
 */
function percentil(ordenada: number[], p: number): number | null {
  if (ordenada.length === 0) return null;
  const posto = Math.ceil((p / 100) * ordenada.length) - 1;
  return ordenada[Math.min(Math.max(posto, 0), ordenada.length - 1)];
}

function media(valores: number[]): number | null {
  if (valores.length === 0) return null;
  let soma = 0;
  for (const v of valores) soma += v;
  return Math.round((soma / valores.length) * 10) / 10;
}

/**
 * Resumo de uma amostra de durações, em minutos.
 *
 * A MEDIANA vem antes da média na tela, e as duas convivem aqui de propósito: um
 * chamado esquecido três dias no fim de semana levanta a média de todo o período
 * e não mexe na mediana. Quem precisa saber "como foi o atendimento típico" lê a
 * mediana; quem precisa saber "alguém foi esquecido" lê o p90.
 */
function resumo(valores: number[]) {
  const ordenada = [...valores].sort((a, b) => a - b);
  return {
    p50: percentil(ordenada, 50),
    p90: percentil(ordenada, 90),
    media: media(ordenada),
    n: ordenada.length,
  };
}

const emMinutos = (de: Date, ate: Date) => Math.max(0, Math.round((+ate - +de) / MINUTO));

/* ------------------------------------------------------------------ *
 *  Contagem por intervalo
 * ------------------------------------------------------------------ */

/**
 * Conta, por balde, quantos intervalos estavam ABERTOS no último instante dele.
 *
 * É assim que a curva da fila é reconstruída sem varrer todos os chamados uma
 * vez por balde: cada intervalo `[inicio, fim)` vira um +1 no primeiro balde
 * cujo FIM cai dentro dele e um -1 no primeiro balde cujo fim cai fora, e a
 * soma corrida no final resolve todos de uma vez.
 *
 * "No último instante do balde" e não "em algum momento do balde": a pergunta
 * que a curva responde é "quanto sobrou de trabalho no fim do dia", e um chamado
 * que abriu e foi resolvido na mesma tarde não sobrou.
 */
function porIntervalo(fins: number[], intervalos: Array<[number, number]>): number[] {
  const delta = new Array<number>(fins.length + 1).fill(0);

  // Primeiro balde cujo fim é >= `t`. `fins` é crescente, então busca binária.
  const primeiroFimApos = (t: number): number => {
    let lo = 0;
    let hi = fins.length;
    while (lo < hi) {
      const meio = (lo + hi) >> 1;
      if (fins[meio] >= t) hi = meio;
      else lo = meio + 1;
    }
    return lo;
  };

  for (const [inicio, fim] of intervalos) {
    const i0 = primeiroFimApos(inicio);
    const i1 = primeiroFimApos(fim);
    if (i0 >= fins.length) continue;
    delta[i0] += 1;
    delta[Math.min(i1, fins.length)] -= 1;
  }

  const saida = new Array<number>(fins.length).fill(0);
  let corrente = 0;
  for (let i = 0; i < fins.length; i++) {
    corrente += delta[i];
    saida[i] = corrente;
  }
  return saida;
}

/* ------------------------------------------------------------------ *
 *  Linha do tempo de um chamado
 * ------------------------------------------------------------------ */

type Transicao = { de: Situacao; para: Situacao; em: number };

type LinhaDoTempo = {
  /** Trechos em que o chamado estava na fila, por situação. */
  trechos: Array<{ situacao: Situacao; inicio: number; fim: number }>;
  transicoes: Transicao[];
};

/**
 * Reconstrói por quais situações o chamado passou, e quando.
 *
 * Começa sempre em `aberto` na `dataAbertura` - é o default da coluna e o único
 * estado em que um chamado pode nascer. Depois aplica as mudanças registradas.
 *
 * O CASO CHATO, e ele existe de verdade: chamado sem nenhuma linha em
 * `MudancaSituacao` cuja `situacao` atual não é `aberto`. Acontece com o que foi
 * alterado por SQL, com o que existia antes da tabela de auditoria, e com
 * qualquer importação futura. Aqui isso não é descartado nem tratado como se o
 * chamado ainda estivesse aberto: fecha-se a lacuna com uma transição sintética
 * em `atualizadoEm`, que é a melhor data disponível para "quando isso mudou". A
 * alternativa - confiar na linha do tempo e ignorar `situacao` - deixaria o
 * chamado na curva da fila para sempre, e a fila cresceria sozinha na tela.
 */
function linhaDoTempo(
  abertura: number,
  situacaoAtual: Situacao,
  atualizadoEm: number,
  transicoes: Transicao[]
): LinhaDoTempo {
  const ordenadas = [...transicoes].sort((a, b) => a.em - b.em);
  const trechos: LinhaDoTempo['trechos'] = [];

  let estado: Situacao = 'aberto';
  let desde = abertura;

  for (const t of ordenadas) {
    // Transição anterior à abertura não existe no mundo real; se aparecer
    // (relógio torto, importação), vale a abertura.
    const em = Math.max(t.em, desde);
    if (naFila(estado)) trechos.push({ situacao: estado, inicio: desde, fim: em });
    estado = t.para;
    desde = em;
  }

  if (estado !== situacaoAtual) {
    const em = Math.max(atualizadoEm, desde);
    if (naFila(estado)) trechos.push({ situacao: estado, inicio: desde, fim: em });
    ordenadas.push({ de: estado, para: situacaoAtual, em });
    estado = situacaoAtual;
    desde = em;
  }

  // O último trecho fica ABERTO, e não termina em `agora`.
  //
  // A diferença é de um instante e apareceu na tela: `porIntervalo` conta o
  // balde cujo fim cai DENTRO de `[inicio, fim)`, e o fim do último balde é o
  // próprio `ate` - que numa janela até agora vale exatamente `agora`. Fechar o
  // trecho em `agora` deixava esse instante de fora por meio-aberto, e a curva
  // da fila despencava para zero no último ponto enquanto `agora.fila` dizia
  // 35. "Ainda na fila" não é "saiu da fila neste instante".
  if (naFila(estado)) {
    trechos.push({ situacao: estado, inicio: desde, fim: Number.MAX_SAFE_INTEGER });
  }

  return { trechos, transicoes: ordenadas };
}

export function registrarRotasDeSeries(app: FastifyInstance): void {
  app.get<{ Querystring: { desde?: string; ate?: string; balde?: Balde; tz?: number } }>(
    '/internal/series',
    {
      onRequest: exigirToken('Acesso negado à série do dashboard'),
      schema: { querystring: QUERY, response: { 200: RESPOSTA } },
    },
    async (req, reply) => {
      const agora = Date.now();

      const analisar = (valor: string | undefined, campo: string): number | null | undefined => {
        if (valor === undefined || valor === '') return null;
        const instante = new Date(valor).getTime();
        if (Number.isNaN(instante)) {
          void reply.status(400).send({ erro: `${campo} não é uma data ISO-8601 válida` });
          return undefined;
        }
        return instante;
      };

      const desdePedido = analisar(req.query.desde, 'desde');
      if (desdePedido === undefined) return reply;
      const atePedido = analisar(req.query.ate, 'ate');
      if (atePedido === undefined) return reply;

      const tzMin = req.query.tz ?? 0;
      const ate = atePedido ?? agora;
      // Sem `desde`, 30 dias. É a janela que o seletor do painel abre por
      // padrão, e devolver "desde o começo dos tempos" transformaria o primeiro
      // acesso numa varredura do histórico inteiro.
      const desde = desdePedido ?? ate - 30 * DIA;

      if (desde >= ate) {
        return reply.status(400).send({ erro: 'desde precisa ser anterior a ate' });
      }

      const balde: Balde = req.query.balde ?? baldePadrao(ate - desde);

      // --- os baldes -------------------------------------------------------
      const inicios: number[] = [];
      for (let t = inicioDoBalde(desde, balde, tzMin); t < ate; t = proximoBalde(t, balde, tzMin)) {
        inicios.push(t);
      }
      // Janela menor que um balde ainda tem um ponto: o balde que a contém.
      if (inicios.length === 0) inicios.push(inicioDoBalde(desde, balde, tzMin));

      // O fim de cada balde é o início do seguinte; o do último é o fim da
      // janela, e não o início do balde seguinte - senão o último ponto contaria
      // trabalho que ainda não aconteceu.
      const fins = inicios.map((inicio, i) =>
        i + 1 < inicios.length ? inicios[i + 1] : Math.min(proximoBalde(inicio, balde, tzMin), ate)
      );

      const n = inicios.length;
      const zeros = () => new Array<number>(n).fill(0);

      const aberturas = zeros();
      const saidas = zeros();
      const resolucoes = zeros();
      const cancelamentos = zeros();
      const reaberturas = zeros();
      const recebidas = zeros();
      const enviadas = zeros();

      /** Em que balde cai o instante, ou -1 se fora da janela. */
      const baldeDe = (t: number): number => {
        if (t < inicios[0] || t >= fins[n - 1]) return -1;
        let lo = 0;
        let hi = n - 1;
        while (lo < hi) {
          const meio = (lo + hi + 1) >> 1;
          if (inicios[meio] <= t) lo = meio;
          else hi = meio - 1;
        }
        return lo;
      };

      // --- chamados --------------------------------------------------------
      //
      // O filtro é o que impede isto de ler a tabela inteira: só interessa o
      // chamado que PODE ter estado na fila durante a janela. Um chamado
      // encerrado há meses e nunca mais tocado tem `situacao` encerrada e
      // `atualizadoEm` anterior a `desde`, e fica fora.
      //
      // Se um dia o volume crescer o bastante para isto pesar, o caminho é
      // materializar a fila por dia numa tabela própria - não trocar por SQL
      // crua, que neste projeto já quebrou duas vezes na comparação de data com
      // o SQLite (ver o comentário do model `Mensagem`).
      const linhas = await prisma.chamado.findMany({
        where: {
          dataAbertura: { lte: new Date(ate) },
          OR: [{ situacao: { in: [...NA_FILA] } }, { atualizadoEm: { gte: new Date(desde) } }],
        },
        select: {
          id: true,
          situacao: true,
          dataAbertura: true,
          atualizadoEm: true,
          primeiroAtendimentoEm: true,
          resolvidoEm: true,
          prazoEm: true,
          responsavelId: true,
          setorId: true,
          tipo: true,
          avaliacaoNota: true,
        },
      });

      // As transições de todos eles. Sem `chamadoId: { in: [...] }`: a lista de
      // ids pode passar do limite de variáveis por consulta do SQLite, e o
      // filtro em JS custa menos que uma consulta partida em lotes.
      const idsRelevantes = new Set(linhas.map((l) => l.id));
      const mudancasCruas = await prisma.mudancaSituacao.findMany({
        where: { criadoEm: { lte: new Date(ate) } },
        select: { chamadoId: true, de: true, para: true, criadoEm: true },
        orderBy: { criadoEm: 'asc' },
      });

      const porChamado = new Map<number, Transicao[]>();
      for (const m of mudancasCruas) {
        if (!idsRelevantes.has(m.chamadoId)) continue;
        const lista = porChamado.get(m.chamadoId);
        const t: Transicao = { de: m.de, para: m.para, em: +m.criadoEm };
        if (lista) lista.push(t);
        else porChamado.set(m.chamadoId, [t]);
      }

      // --- a fila, por situação -------------------------------------------
      const trechosAberto: Array<[number, number]> = [];
      const trechosAndamento: Array<[number, number]> = [];
      const trechosAguardando: Array<[number, number]> = [];

      // Amostras de duração da janela, para `desempenho`.
      const atendimentoJanela: number[] = [];
      const resolucaoJanela: number[] = [];
      // E por balde, para as duas linhas de percentil.
      const atendimentoPorBalde: number[][] = Array.from({ length: n }, () => []);
      const resolucaoPorBalde: number[][] = Array.from({ length: n }, () => []);

      const agoraContagem = {
        fila: 0,
        aguardandoPrimeiro: 0,
        semResponsavel: 0,
        semClassificacao: 0,
        vencidos: 0,
        venceEm24h: 0,
        porSituacao: {
          aberto: 0,
          em_andamento: 0,
          aguardando_resposta: 0,
          resolvido: 0,
          fechado: 0,
          cancelado: 0,
        } as Record<Situacao, number>,
      };

      const prazo = { dentro: 0, fora: 0, semPrazo: 0 };
      const notas: number[] = [];
      const distribuicaoNota = [0, 0, 0, 0, 0];

      type AcumuladorSetor = {
        id: number | null;
        fila: number;
        resolucoes: number;
        atendimento: number[];
        dentro: number;
        fora: number;
        notas: number[];
      };
      const setores = new Map<number | null, AcumuladorSetor>();
      const setorDe = (id: number | null): AcumuladorSetor => {
        let a = setores.get(id);
        if (!a) {
          a = { id, fila: 0, resolucoes: 0, atendimento: [], dentro: 0, fora: 0, notas: [] };
          setores.set(id, a);
        }
        return a;
      };

      for (const l of linhas) {
        const abertura = +l.dataAbertura;
        const linha = linhaDoTempo(
          abertura,
          l.situacao,
          +l.atualizadoEm,
          porChamado.get(l.id) ?? []
        );

        for (const t of linha.trechos) {
          const par: [number, number] = [t.inicio, t.fim];
          if (t.situacao === 'aberto') trechosAberto.push(par);
          else if (t.situacao === 'em_andamento') trechosAndamento.push(par);
          else trechosAguardando.push(par);
        }

        const iAbertura = baldeDe(abertura);
        if (iAbertura >= 0) aberturas[iAbertura] += 1;

        for (const t of linha.transicoes) {
          const i = baldeDe(t.em);
          if (i < 0) continue;
          const saiu = naFila(t.de) && !naFila(t.para);
          if (saiu) saidas[i] += 1;
          if (saiu && (t.para === 'resolvido' || t.para === 'fechado')) resolucoes[i] += 1;
          if (saiu && t.para === 'cancelado') cancelamentos[i] += 1;
          if (!naFila(t.de) && naFila(t.para)) reaberturas[i] += 1;
        }

        // As durações são baldeadas pelo instante do MARCO, não pela abertura:
        // a pergunta é "quanto demorou o que foi atendido nesta terça", e um
        // chamado aberto na segunda e atendido na terça pertence à terça.
        if (l.primeiroAtendimentoEm) {
          const dur = emMinutos(l.dataAbertura, l.primeiroAtendimentoEm);
          const i = baldeDe(+l.primeiroAtendimentoEm);
          if (i >= 0) {
            atendimentoPorBalde[i].push(dur);
            atendimentoJanela.push(dur);
            setorDe(l.setorId).atendimento.push(dur);
          }
        }

        if (l.resolvidoEm) {
          const dur = emMinutos(l.dataAbertura, l.resolvidoEm);
          const i = baldeDe(+l.resolvidoEm);
          if (i >= 0) {
            resolucaoPorBalde[i].push(dur);
            resolucaoJanela.push(dur);
            setorDe(l.setorId).resolucoes += 1;

            // Cumprimento de prazo: só faz sentido perguntar de chamado
            // resolvido, e só de quem tinha prazo combinado. "Sem prazo" é a
            // terceira coluna porque não é nem cumprido nem descumprido - e
            // somá-lo a um dos dois inventaria um percentual.
            if (l.prazoEm) {
              const dentro = +l.resolvidoEm <= +l.prazoEm;
              if (dentro) {
                prazo.dentro += 1;
                setorDe(l.setorId).dentro += 1;
              } else {
                prazo.fora += 1;
                setorDe(l.setorId).fora += 1;
              }
            } else {
              prazo.semPrazo += 1;
            }
          }
        }

        if (l.avaliacaoNota !== null && l.avaliacaoNota >= 1 && l.avaliacaoNota <= 5) {
          notas.push(l.avaliacaoNota);
          distribuicaoNota[l.avaliacaoNota - 1] += 1;
          setorDe(l.setorId).notas.push(l.avaliacaoNota);
        }

        // --- o instante presente ------------------------------------------
        agoraContagem.porSituacao[l.situacao] += 1;
        if (naFila(l.situacao)) {
          agoraContagem.fila += 1;
          setorDe(l.setorId).fila += 1;
          if (l.primeiroAtendimentoEm === null) agoraContagem.aguardandoPrimeiro += 1;
          if (l.responsavelId === null) agoraContagem.semResponsavel += 1;
          if (l.tipo === null || l.setorId === null) agoraContagem.semClassificacao += 1;
          if (l.prazoEm) {
            const restante = +l.prazoEm - agora;
            if (restante < 0) agoraContagem.vencidos += 1;
            else if (restante <= DIA) agoraContagem.venceEm24h += 1;
          }
        }
      }

      const filaAberto = porIntervalo(fins, trechosAberto);
      const filaAndamento = porIntervalo(fins, trechosAndamento);
      const filaAguardando = porIntervalo(fins, trechosAguardando);

      // --- mensagens -------------------------------------------------------
      //
      // Três consultas em vez de uma sobre a tabela toda: `Mensagem` é a maior
      // tabela do banco (cada pergunta do bot é uma linha), e as três são
      // limitadas pela janela.
      const [msgRecebidas, msgEnviadas, msgParaPendencia] = await Promise.all([
        prisma.mensagem.findMany({
          where: {
            remetente: 'usuario',
            timestamp: { gte: new Date(desde), lte: new Date(ate) },
          },
          select: { timestamp: true },
        }),
        prisma.mensagem.findMany({
          where: {
            remetente: 'sistema',
            enviadaEm: { gte: new Date(desde), lte: new Date(ate) },
          },
          select: { enviadaEm: true },
        }),
        // Para a curva de pendência preciso das linhas cujo intervalo "esperando
        // envio" toca a janela: as que ainda não saíram (independente de quando
        // nasceram) e as que saíram DENTRO da janela. As que já tinham saído
        // antes de `desde` não tocam nenhum balde.
        prisma.mensagem.findMany({
          where: {
            remetente: 'sistema',
            timestamp: { lte: new Date(ate) },
            OR: [{ enviadaEm: null }, { enviadaEm: { gte: new Date(desde) } }],
          },
          select: { timestamp: true, enviadaEm: true },
        }),
      ]);

      for (const m of msgRecebidas) {
        const i = baldeDe(+m.timestamp);
        if (i >= 0) recebidas[i] += 1;
      }
      for (const m of msgEnviadas) {
        if (!m.enviadaEm) continue;
        const i = baldeDe(+m.enviadaEm);
        if (i >= 0) enviadas[i] += 1;
      }

      const envioPendenteFim = porIntervalo(
        fins,
        msgParaPendencia.map(
          (m) =>
            [+m.timestamp, m.enviadaEm ? +m.enviadaEm : Number.MAX_SAFE_INTEGER] as [number, number]
        )
      );

      const [envioPendente, envioComFalha, conversasEmAndamento] = await Promise.all([
        prisma.mensagem.count({ where: { remetente: 'sistema', enviadaEm: null } }),
        // Uma tentativa é normal - a primeira. Da SEGUNDA em diante houve falha,
        // e é isso que este número precisa dizer para não disparar a cada envio.
        prisma.mensagem.count({
          where: { remetente: 'sistema', enviadaEm: null, tentativas: { gte: 2 } },
        }),
        prisma.sessaoConversa.count(),
      ]);

      // --- rótulos de setor ------------------------------------------------
      // Inativos entram, como em `/internal/metricas`: setor desativado ontem
      // continua com histórico, e sumir da tabela faria a soma por setor não
      // bater com o total.
      const setoresCadastrados = await prisma.setor.findMany({
        select: { id: true, codigo: true, nome: true },
      });
      const rotuloSetor = new Map(setoresCadastrados.map((s) => [s.id, s]));

      const porSetor = [...setores.values()]
        .map((a) => {
          const r = a.id === null ? null : rotuloSetor.get(a.id);
          return {
            id: r ? a.id : null,
            codigo: r ? r.codigo : 'sem_setor',
            rotulo: r ? r.nome : 'Sem setor',
            fila: a.fila,
            resolucoes: a.resolucoes,
            atendimentoP50: percentil(
              [...a.atendimento].sort((x, y) => x - y),
              50
            ),
            dentro: a.dentro,
            fora: a.fora,
            nota: media(a.notas),
            notaN: a.notas.length,
          };
        })
        // Pela fila e depois pelas resoluções: a tabela é lida para decidir onde
        // faltam mãos, e quem tem mais trabalho parado precisa estar no topo.
        .sort((x, y) => y.fila - x.fila || y.resolucoes - x.resolucoes);

      return reply.send({
        janela: {
          desde: new Date(desde).toISOString(),
          ate: new Date(ate).toISOString(),
          balde,
          tz: tzMin,
        },
        baldes: inicios.map((inicio, i) => {
          const at = resumo(atendimentoPorBalde[i]);
          const re = resumo(resolucaoPorBalde[i]);
          return {
            inicio: new Date(inicio).toISOString(),
            aberturas: aberturas[i],
            saidas: saidas[i],
            resolucoes: resolucoes[i],
            cancelamentos: cancelamentos[i],
            reaberturas: reaberturas[i],
            filaFim: filaAberto[i] + filaAndamento[i] + filaAguardando[i],
            filaAberto: filaAberto[i],
            filaEmAndamento: filaAndamento[i],
            filaAguardando: filaAguardando[i],
            recebidas: recebidas[i],
            enviadas: enviadas[i],
            envioPendenteFim: envioPendenteFim[i],
            atendimentoP50: at.p50,
            atendimentoP90: at.p90,
            atendimentoN: at.n,
            resolucaoP50: re.p50,
            resolucaoP90: re.p90,
            resolucaoN: re.n,
          };
        }),
        agora: {
          ...agoraContagem,
          envioPendente,
          envioComFalha,
          conversasEmAndamento,
        },
        desempenho: {
          atendimento: resumo(atendimentoJanela),
          resolucao: resumo(resolucaoJanela),
          prazo,
          avaliacao: { media: media(notas), n: notas.length, distribuicao: distribuicaoNota },
        },
        porSetor,
      });
    }
  );
}
