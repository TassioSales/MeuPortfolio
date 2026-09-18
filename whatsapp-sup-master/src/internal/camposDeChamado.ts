import { Prisma } from '../generated/prisma/client';
import { prisma } from '../db/client';

/**
 * Os campos de classificação de um chamado, declarados UMA vez.
 *
 * Existem dois caminhos que escrevem exatamente estes campos - criar tarefa no
 * painel (`POST /internal/tarefas`) e corrigir a classificação depois
 * (`PATCH /internal/chamados/:id`) -, e antes de este módulo existir eles teriam
 * duas listas de campos, dois conjuntos de limites e duas validações de faixa
 * para manter em sincronia. A segunda cópia é a que erra: um campo aceito na
 * criação e recusado na correção, ou um teto de 200 num lado e 500 no outro.
 *
 * Aqui moram três coisas, e só elas:
 *   - `PROPRIEDADES`: o JSON Schema de cada campo, para o Fastify validar antes
 *     do handler;
 *   - `Corpo`: o tipo TypeScript equivalente;
 *   - `montarDados`: a tradução de corpo para `data` do Prisma, com as regras
 *     que o JSON Schema não sabe expressar (data ISO válida, faixa de nota, FK
 *     que existe de verdade).
 *
 * O que NÃO mora aqui: `situacao` e `categoriaId`. As duas têm rota própria e
 * razão para isso - mudar situação é evento de atendimento (vai para o
 * histórico, pode notificar o usuário no WhatsApp, move marco de SLA) e mudar
 * assunto é correção de menu. Juntá-las neste corpo genérico faria uma correção
 * de digitação disparar mensagem para o cliente.
 */

// Tetos de texto. São generosos de propósito: quem digita "Praça Central, loja 4,
// piso 2" não pode ser barrado por um limite apertado, e o custo de uma coluna
// TEXT no SQLite é o tamanho do que foi escrito, não o do limite.
export const LIMITES_CAMPOS = {
  contato: 200,
  sistemaAfetado: 200,
  franquiaCodigo: 60,
  franquiaNome: 200,
  franqueadoNome: 120,
  franqueadoContato: 200,
  localizacao: 200,
  avaliacaoComentario: 2000,
} as const;

// Um dia em minutos * 365: teto que só existe para barrar o dedo escorregado no
// teclado numérico (`999999999` viraria uma soma sem sentido no relatório de
// produtividade). Não é uma política de jornada.
const MAX_MINUTOS = 525_600;

// R$ 10.000.000,00 em centavos. Mesmo espírito: barra o absurdo, não o caso real.
const MAX_CENTAVOS = 1_000_000_000;

/**
 * ISO-8601, validado com `new Date()` no handler e não com `format: date-time` no
 * schema.
 *
 * O `format` do AJV depende de os formatos estarem carregados, e um prazo
 * silenciosamente ignorado é pior que um 400: o chamado ficaria sem prazo e a
 * tela mostraria "sem prazo combinado", que é uma afirmação falsa.
 */
const DATA_ISO = { type: 'string', minLength: 4, maxLength: 40, nullable: true } as const;

const TEXTO = (max: number) => ({ type: 'string', maxLength: max, nullable: true }) as const;

export const TIPOS_CHAMADO = ['interno', 'franquia'] as const;
export const PRIORIDADES = ['baixa', 'media', 'alta', 'urgente'] as const;
export const CANAIS = ['whatsapp', 'email', 'telefone', 'presencial'] as const;
export const TIPOS_SOLICITACAO = ['duvida', 'bug', 'melhoria', 'tarefa', 'projeto'] as const;
export const IMPACTOS = ['sem_impacto', 'baixo', 'medio', 'alto', 'bloqueia_operacao'] as const;
export const TIPOS_FRANQUIA = [
  'financeiro',
  'suprimentos',
  'sistema_pdv',
  'treinamento',
  'manutencao_predial',
  'marketing_local',
  'juridico_contrato',
] as const;
export const URGENCIAS_COMERCIAIS = ['rotina', 'atencao', 'loja_impactada', 'loja_parada'] as const;

/**
 * `nullable: true` em quase tudo, e isso é uma decisão e não descuido: `null` é a
 * operação "limpe este campo", que é diferente do campo ausente ("não mexa").
 * Sem a distinção, desfazer uma classificação errada seria impossível pela API -
 * só daria para trocar por outra.
 */
export const PROPRIEDADES = {
  // --- comum ---
  tipo: { type: 'string', enum: [...TIPOS_CHAMADO], nullable: true },
  setorId: { type: 'integer', minimum: 1, nullable: true },
  // `prioridade` e `canal` NÃO são nuláveis: a coluna é NOT NULL com default no
  // banco, então "limpar" não é uma operação que exista para elas.
  prioridade: { type: 'string', enum: [...PRIORIDADES] },
  canal: { type: 'string', enum: [...CANAIS] },
  contato: TEXTO(LIMITES_CAMPOS.contato),
  responsavelId: { type: 'integer', minimum: 1, nullable: true },
  prazoEm: DATA_ISO,

  // --- bloco interno ---
  setorOrigemId: { type: 'integer', minimum: 1, nullable: true },
  tipoSolicitacao: { type: 'string', enum: [...TIPOS_SOLICITACAO], nullable: true },
  impacto: { type: 'string', enum: [...IMPACTOS], nullable: true },
  sistemaAfetado: TEXTO(LIMITES_CAMPOS.sistemaAfetado),
  tempoEstimadoMin: { type: 'integer', minimum: 0, maximum: MAX_MINUTOS, nullable: true },
  tempoGastoMin: { type: 'integer', minimum: 0, maximum: MAX_MINUTOS, nullable: true },

  // --- bloco franquia ---
  franquiaCodigo: TEXTO(LIMITES_CAMPOS.franquiaCodigo),
  franquiaNome: TEXTO(LIMITES_CAMPOS.franquiaNome),
  franqueadoNome: TEXTO(LIMITES_CAMPOS.franqueadoNome),
  franqueadoContato: TEXTO(LIMITES_CAMPOS.franqueadoContato),
  localizacao: TEXTO(LIMITES_CAMPOS.localizacao),
  tipoFranquia: { type: 'string', enum: [...TIPOS_FRANQUIA], nullable: true },
  afetaAtendimento: { type: 'boolean' },
  envolveCusto: { type: 'boolean' },
  valorEstimadoCentavos: { type: 'integer', minimum: 0, maximum: MAX_CENTAVOS, nullable: true },
  precisaAprovacao: { type: 'boolean' },
  urgenciaComercial: { type: 'string', enum: [...URGENCIAS_COMERCIAIS], nullable: true },
} as const;

export type Corpo = {
  tipo?: (typeof TIPOS_CHAMADO)[number] | null;
  setorId?: number | null;
  prioridade?: (typeof PRIORIDADES)[number];
  canal?: (typeof CANAIS)[number];
  contato?: string | null;
  responsavelId?: number | null;
  prazoEm?: string | null;
  setorOrigemId?: number | null;
  tipoSolicitacao?: (typeof TIPOS_SOLICITACAO)[number] | null;
  impacto?: (typeof IMPACTOS)[number] | null;
  sistemaAfetado?: string | null;
  tempoEstimadoMin?: number | null;
  tempoGastoMin?: number | null;
  franquiaCodigo?: string | null;
  franquiaNome?: string | null;
  franqueadoNome?: string | null;
  franqueadoContato?: string | null;
  localizacao?: string | null;
  tipoFranquia?: (typeof TIPOS_FRANQUIA)[number] | null;
  afetaAtendimento?: boolean;
  envolveCusto?: boolean;
  valorEstimadoCentavos?: number | null;
  precisaAprovacao?: boolean;
  urgenciaComercial?: (typeof URGENCIAS_COMERCIAIS)[number] | null;
};

/** Campos de texto: os que passam por `trim` e viram `null` quando sobra vazio. */
const TEXTOS = [
  'contato',
  'sistemaAfetado',
  'franquiaCodigo',
  'franquiaNome',
  'franqueadoNome',
  'franqueadoContato',
  'localizacao',
] as const;

/** Campos que vão direto para a coluna, sem tradução nenhuma. */
const DIRETOS = [
  'tipo',
  'prioridade',
  'canal',
  'tipoSolicitacao',
  'impacto',
  'tempoEstimadoMin',
  'tempoGastoMin',
  'tipoFranquia',
  'afetaAtendimento',
  'envolveCusto',
  'valorEstimadoCentavos',
  'precisaAprovacao',
  'urgenciaComercial',
] as const;

/** As três FKs, com a tabela onde cada uma tem de existir. */
const CHAVES = [
  { campo: 'setorId', tabela: 'setor' },
  { campo: 'setorOrigemId', tabela: 'setor' },
  { campo: 'responsavelId', tabela: 'pessoa' },
] as const;

export type Montagem =
  { ok: true; dados: Prisma.ChamadoUncheckedUpdateInput } | { ok: false; erro: string };

/**
 * Traduz o corpo para o `data` do Prisma, aplicando o que o JSON Schema não
 * alcança.
 *
 * Três classes de regra vivem aqui, e todas as três precisam de código:
 *
 *   1. `trim` em texto. `maxLength` conta caracteres crus, então "   " passa pelo
 *      schema; sem o trim, o painel gravaria um contato de três espaços que a tela
 *      mostra como preenchido e ninguém consegue usar. Texto que sobra vazio vira
 *      `null`, e não `''`: "não informado" tem UMA representação no banco.
 *   2. Data ISO. `new Date('bananas')` é `Invalid Date` e o Prisma o gravaria
 *      como `null` sem reclamar - o prazo desapareceria em silêncio.
 *   3. FK que existe. Sem a checagem, um `setorId` inventado estoura como P2003 e
 *      vira 500; quem chama precisa de 400 com o nome do campo errado.
 *
 * `undefined` (campo ausente) nunca entra em `dados`, e é o que faz um PATCH
 * parcial não apagar o que não foi mencionado.
 */
export async function montarDados(corpo: Corpo): Promise<Montagem> {
  const dados: Record<string, unknown> = {};

  for (const campo of DIRETOS) {
    if (corpo[campo] !== undefined) dados[campo] = corpo[campo];
  }

  for (const campo of TEXTOS) {
    const valor = corpo[campo];
    if (valor === undefined) continue;
    if (valor === null) {
      dados[campo] = null;
      continue;
    }
    const limpo = valor.trim();
    dados[campo] = limpo === '' ? null : limpo;
  }

  if (corpo.prazoEm !== undefined) {
    if (corpo.prazoEm === null) {
      dados.prazoEm = null;
    } else {
      const instante = new Date(corpo.prazoEm);
      if (Number.isNaN(instante.getTime())) {
        return { ok: false, erro: 'prazoEm não é uma data ISO-8601 válida' };
      }
      dados.prazoEm = instante;
    }
  }

  for (const { campo, tabela } of CHAVES) {
    const valor = corpo[campo];
    if (valor === undefined) continue;
    if (valor === null) {
      dados[campo] = null;
      continue;
    }

    // O nome da tabela vem de uma lista fechada aqui em cima, então o acesso
    // dinâmico não é uma porta para consulta arbitrária.
    const delegate = (prisma as unknown as Record<string, { findUnique: Function }>)[tabela];
    const existe = await delegate.findUnique({ where: { id: valor }, select: { id: true } });
    if (!existe) return { ok: false, erro: `${campo}: ${tabela} ${valor} não existe` };

    dados[campo] = valor;
  }

  return { ok: true, dados: dados as Prisma.ChamadoUncheckedUpdateInput };
}

/**
 * As colunas que a listagem e o detalhe devolvem, declaradas uma vez.
 *
 * `telefone` NÃO está aqui, e não é esquecimento: é a mesma minimização da view
 * `chamados_para_cards`. O painel roda no navegador de quem atende e não precisa
 * do telefone para nada - quem envia mensagem é o servidor.
 *
 * `franqueadoContato` e `contato` SIM estão: diferente do telefone, eles existem
 * para o atendente ligar de volta, e esconder o contato do solicitante do
 * formulário que o coletou não protegeria nada - só quebraria o campo.
 */
export const CAMPOS_PAINEL = {
  id: true,
  nome: true,
  resumo: true,
  descricao: true,
  situacao: true,
  dataAbertura: true,
  atualizadoEm: true,
  origem: true,
  categoriaId: true,
  primeiroAtendimentoEm: true,
  resolvidoEm: true,

  tipo: true,
  setorId: true,
  prioridade: true,
  canal: true,
  contato: true,
  responsavelId: true,
  prazoEm: true,

  setorOrigemId: true,
  tipoSolicitacao: true,
  impacto: true,
  sistemaAfetado: true,
  tempoEstimadoMin: true,
  tempoGastoMin: true,

  franquiaCodigo: true,
  franquiaNome: true,
  franqueadoNome: true,
  franqueadoContato: true,
  localizacao: true,
  tipoFranquia: true,
  afetaAtendimento: true,
  envolveCusto: true,
  valorEstimadoCentavos: true,
  precisaAprovacao: true,
  urgenciaComercial: true,

  avaliacaoNota: true,
  avaliacaoComentario: true,
  avaliadoEm: true,
} as const;

/**
 * O schema de resposta de um chamado no painel.
 *
 * Toda data sai como string ISO e todo campo opcional é `nullable`, e não
 * ausente: quem consome não deve precisar distinguir "não informado" de "campo
 * que às vezes some". É a mesma regra que os marcos de SLA já seguiam.
 */
export const CHAMADO_NO_PAINEL = {
  type: 'object',
  properties: {
    id: { type: 'integer' },
    nome: { type: 'string' },
    resumo: { type: 'string' },
    descricao: { type: 'string' },
    situacao: { type: 'string' },
    dataAbertura: { type: 'string' },
    atualizadoEm: { type: 'string' },
    // O painel usa isto para NÃO oferecer o aviso ao solicitante numa tarefa:
    // ela não tem telefone, então o pedido seria aceito e nada seria enviado.
    origem: { type: 'string' },
    // O ID, e não o rótulo - o painel já carrega a árvore de assuntos e a lista
    // de setores para montar os seletores, e mandar o texto junto aqui seria a
    // mesma informação em dois lugares, livre para divergir depois de uma
    // renomeação.
    categoriaId: { type: 'integer', nullable: true },
    primeiroAtendimentoEm: { type: 'string', nullable: true },
    resolvidoEm: { type: 'string', nullable: true },

    tipo: { type: 'string', nullable: true },
    setorId: { type: 'integer', nullable: true },
    prioridade: { type: 'string' },
    canal: { type: 'string' },
    contato: { type: 'string', nullable: true },
    responsavelId: { type: 'integer', nullable: true },
    prazoEm: { type: 'string', nullable: true },

    setorOrigemId: { type: 'integer', nullable: true },
    tipoSolicitacao: { type: 'string', nullable: true },
    impacto: { type: 'string', nullable: true },
    sistemaAfetado: { type: 'string', nullable: true },
    tempoEstimadoMin: { type: 'integer', nullable: true },
    tempoGastoMin: { type: 'integer', nullable: true },

    franquiaCodigo: { type: 'string', nullable: true },
    franquiaNome: { type: 'string', nullable: true },
    franqueadoNome: { type: 'string', nullable: true },
    franqueadoContato: { type: 'string', nullable: true },
    localizacao: { type: 'string', nullable: true },
    tipoFranquia: { type: 'string', nullable: true },
    afetaAtendimento: { type: 'boolean' },
    envolveCusto: { type: 'boolean' },
    valorEstimadoCentavos: { type: 'integer', nullable: true },
    precisaAprovacao: { type: 'boolean' },
    urgenciaComercial: { type: 'string', nullable: true },

    avaliacaoNota: { type: 'integer', nullable: true },
    avaliacaoComentario: { type: 'string', nullable: true },
    avaliadoEm: { type: 'string', nullable: true },

    // As etiquetas livres, já como texto: diferente de setor e assunto, tag não
    // tem lista carregada no painel para resolver id -> nome, e o nome É o
    // identificador que a pessoa lê e digita.
    tags: { type: 'array', items: { type: 'string' } },
  },
  required: [
    'id',
    'nome',
    'resumo',
    'descricao',
    'situacao',
    'dataAbertura',
    'atualizadoEm',
    'origem',
    'prioridade',
    'canal',
    'afetaAtendimento',
    'envolveCusto',
    'precisaAprovacao',
  ],
} as const;

type LinhaCrua = Record<string, unknown> & {
  dataAbertura: Date;
  atualizadoEm: Date;
  primeiroAtendimentoEm: Date | null;
  resolvidoEm: Date | null;
  prazoEm: Date | null;
  avaliadoEm: Date | null;
  tags?: { nome: string }[];
};

/**
 * Datas viram ISO aqui, e não no serializador do Fastify.
 *
 * O painel precisa do instante em UTC para calcular "aberto há quanto tempo" e
 * "vence em quanto tempo" no fuso de quem está olhando - uma string já formatada
 * pelo servidor levaria o fuso do servidor junto.
 */
export function paraOPainel(c: LinhaCrua) {
  const { tags, ...resto } = c;
  return {
    ...resto,
    dataAbertura: c.dataAbertura.toISOString(),
    atualizadoEm: c.atualizadoEm.toISOString(),
    primeiroAtendimentoEm: c.primeiroAtendimentoEm?.toISOString() ?? null,
    resolvidoEm: c.resolvidoEm?.toISOString() ?? null,
    prazoEm: c.prazoEm?.toISOString() ?? null,
    avaliadoEm: c.avaliadoEm?.toISOString() ?? null,
    tags: (tags ?? []).map((t) => t.nome),
  };
}
