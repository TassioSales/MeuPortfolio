/**
 * Tipos compartilhados do frontend.
 *
 * Os nomes de campos seguem exatamente o contrato do backend FastAPI
 * (`backend/app/models/schemas.py`), por isso ficam em português.
 */

// ========== Autenticação ==========

export interface User {
  id: string;
  email: string;
  nome: string;
  status: string;
  /**
   * `admin` configura os agentes; `operador` atende.
   *
   * O painel usa isto para decidir o que mostrar no menu. Quem decide o que é
   * permitido continua sendo o backend, em cada rota — esconder o link evita o
   * 404, não é a autorização.
   */
  papel: Papel;
  data_criacao: string;
}

export type Papel = "admin" | "operador";

export interface LoginRequest {
  email: string;
  senha: string;
}

export interface RegisterRequest {
  email: string;
  nome: string;
  senha: string;
}

/** Corpo de `POST /api/v1/auth/users` — o administrador criando um acesso. */
export interface NovoAcesso {
  email: string;
  nome: string;
  senha: string;
  papel: Papel;
}

/**
 * Corpo de `PATCH /api/v1/auth/users/{id}` (schema `UserUpdateByAdmin`).
 *
 * Senha não está aqui: o backend não deixa administrador trocar a senha de
 * outro, porque quem troca a senha de alguém consegue entrar como ele.
 */
export interface AlteracaoDeAcesso {
  papel?: Papel;
  status?: "ativo" | "inativo";
}

/** Corpo de `POST /api/v1/auth/password` — a pessoa trocando a própria. */
export interface TrocaDeSenha {
  senha_atual: string;
  senha_nova: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string | null;
  token_type: string;
  expires_in: number;
}

// ========== Agentes ==========

export interface Agent {
  id: string;
  user_id: string;
  nome: string;
  /**
   * Como o agente se apresenta ao cliente no WhatsApp.
   *
   * Diferente de `nome`, que é o rótulo interno: ninguém deve ouvir "meu nome
   * é Triagem trabalhista". Nulo é normal — aí ele se apresenta como o
   * escritório, sem inventar nome próprio.
   */
  nome_atendente: string | null;
  descricao: string | null;
  system_prompt: string;
  temperatura: number;
  max_tokens: number;
  /** Se o agente lê imagem, PDF e áudio que o cliente manda. */
  anexos_habilitados: boolean;
  status: string;
  data_criacao: string;
  data_atualizacao: string;
}

/** Corpo de `POST /api/v1/agents` (schema `AgentCreate`). */
export interface AgentInput {
  nome: string;
  nome_atendente?: string | null;
  descricao?: string | null;
  system_prompt: string;
  temperatura: number;
  max_tokens: number;
  anexos_habilitados?: boolean;
}

/** Corpo de `PUT /api/v1/agents/{id}` — todos os campos são opcionais. */
export type AgentUpdateInput = Partial<AgentInput>;

/** Limites validados pelo backend em `agent_service.create_agent`. */
export const AGENT_LIMITS = {
  temperaturaMin: 0,
  temperaturaMax: 2,
  maxTokensMin: 1,
  maxTokensMax: 4096,
  nomeMaxLength: 255,
} as const;

// ========== Erros ==========

export interface ApiErrorBody {
  detail?: string;
  error_code?: string;
}

// ========== Chat / Playground ==========

export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

/** Resposta de `POST /api/v1/agents/{id}/chat`. */
export interface ChatResponse {
  response: string;
  conversation_id: string | null;
  tokens_used: TokenUsage;
  timestamp: string;
  model: string;
}

/**
 * Quem escreveu.
 *
 * `operador` é gente do escritório digitando pelo painel. Para o modelo ele
 * conta como o escritório falando (junto com `assistant`); para quem lê a
 * transcrição depois, a diferença importa: "o escritório disse" não é "a IA
 * disse".
 */
export type Remetente = "user" | "assistant" | "operador";

/** Mensagem persistida, como vem de `GET .../chat/history`. */
export interface ChatHistoryMessage {
  id: string;
  remetente: Remetente;
  conteudo: string;
  timestamp: string;
}

export interface ChatHistoryResponse {
  conversation_id: string | null;
  messages: ChatHistoryMessage[];
}

/**
 * Mensagem na tela. Difere de `ChatHistoryMessage` porque o balão do usuário
 * aparece antes de o backend responder e ainda não tem id nem timestamp.
 */
export interface ChatBubble {
  id: string;
  remetente: Remetente;
  conteudo: string;
  /** true enquanto a resposta do agente não chegou. */
  pending?: boolean;
  tokens?: number;
}

// ========== Atendimentos / pausa humana ==========

/** Uma conversa na fila do operador (`ConversationListItem` no backend). */
export interface ConversationSummary {
  id: string;
  phone_number: string;
  status: string;
  /** false quando a conversa está pausada e um humano assumiu. */
  ia_ativa: boolean;
  lead_nome: string | null;
  lead_status_funil: string | null;
  data_ultima_msg: string | null;
  total_mensagens: number;
  ultima_mensagem: string | null;
  ultimo_remetente: string | null;
}

/** Transcrição de `GET /api/v1/conversations/{id}/messages`. */
export interface ConversationTranscript {
  conversation_id: string;
  status: string;
  ia_ativa: boolean;
  phone_number: string;
  lead_nome: string | null;
  /** Parecer preliminar em markdown. Interno: nunca vai ao cliente. */
  analise_preliminar: string | null;
  /** Assuntos deste contato, do mais recente para o mais antigo. */
  casos: CasoDoContato[];
  messages: ChatHistoryMessage[];
}

/** Um assunto trazido pelo contato (`CasoDoContato` no backend). */
export interface CasoDoContato {
  id: string;
  area: string | null;
  resumo: string | null;
  /** Preenchido só quando a parte não é quem manda as mensagens. */
  titular: string | null;
  score_qualificacao: number;
  /** Faixa em reais, do parecer. Nula quando não deu para dimensionar. */
  valor_estimado_min: number | null;
  valor_estimado_max: number | null;
  viabilidade: Viabilidade;
  data_abertura: string | null;
  analise_preliminar: string | null;
}

/**
 * O veredito do parecer sobre o porte do caso.
 *
 * `indeterminado` não é sinônimo de inviável: é caso que ninguém dimensionou
 * ainda, e o que ele pede é uma pergunta, não um descarte.
 */
export type Viabilidade =
  | "acima_do_piso"
  | "abaixo_do_piso"
  | "indeterminado"
  | "nao_se_aplica";

/** Resposta de `pause`, `resume` e `status`. */
export interface ConversationStatus {
  conversation_id: string;
  status: string;
  ia_ativa: boolean;
}

// ========== Alertas ==========

/**
 * De quem é a resposta que não veio.
 *
 * Separados porque a ação é diferente: `ia_sem_resposta` é defeito (modelo
 * fora do ar, cota estourada) e `humano_sem_resposta` é gente ocupada. Um
 * alerta só juntaria "a IA caiu" com "o operador foi almoçar".
 */
export type TipoDeAlerta = "ia_sem_resposta" | "humano_sem_resposta";

export interface ClienteEsperando {
  tipo: TipoDeAlerta;
  conversation_id: string;
  phone_number: string;
  lead_nome: string | null;
  ultima_mensagem: string;
  desde: string;
  minutos_esperando: number;
}

export interface AlertasResponse {
  agent_id: string;
  minutos: number;
  /** Contagem completa — a lista vem truncada, estes números não. */
  total_ia: number;
  total_humano: number;
  conversas: ClienteEsperando[];
}

// ========== Kanban ==========

/** Card de lead no board (`LeadCardResponse` no backend). */
export interface KanbanCard {
  id: string;
  nome: string;
  email: string | null;
  phone_number: string;
  score_qualificacao: number;
  status_funil: string;
  ordem: number;
  /**
   * Onde a pessoa trabalhava e o que fazia lá.
   *
   * Num caso trabalhista, essas duas linhas são a identidade do caso —
   * "Supermercado Tático · Repositor" diz a um advogado o que um score de 85
   * não diz. Vêm da triagem, então existem desde que o card nasce.
   */
  empresa: string | null;
  cargo: string | null;
  /** Do parecer. Nulos nos primeiros minutos, enquanto ele não rodou. */
  valor_estimado_min: number | null;
  valor_estimado_max: number | null;
  viabilidade: Viabilidade | null;
  /**
   * Há quantos dias o card não muda de coluna.
   *
   * É o contador que sobrevive ao uso: num board de verdade, "ligações 0/5"
   * fica zerado para sempre porque ninguém para de atender para registrar
   * ligação — mas o tempo passa sozinho. Zero quer dizer "moveu hoje" ou
   * "não sei", e nos dois casos não há nada a cobrar.
   */
  dias_parado: number;
}

/** Resposta de `GET /agents/{id}/kanban/leads/{leadId}` (`LeadDossie`). */
export interface LeadDossie {
  lead_id: string;
  nome: string | null;
  email: string | null;
  phone_number: string;
  status_funil: string | null;
  score_qualificacao: number;
  data_criacao: string | null;
  conversation_id: string | null;
  dados_economicos: string | null;
  documentos_em_maos: string | null;
  inconsistencias: string | null;
  problemas_detectados: string | null;
  recomendacoes: string | null;
  analise_preliminar: string | null;
  casos: CasoDoContato[];
}

export interface KanbanColumn {
  id: string;
  nome: string;
  ordem: number;
  cor_hex: string;
  cards: KanbanCard[];
}

export interface KanbanBoard {
  agent_id: string;
  columns: KanbanColumn[];
}

/** Corpo de `POST /agents/{id}/kanban/move`. */
export interface MoveCardRequest {
  lead_id: string;
  target_column_id: string;
  new_order: number;
}

// ========== Finalizados ==========

/**
 * Por que o caso acabou.
 *
 * `sem_retorno` não é o mesmo que inviável: é a pessoa que parou de responder
 * antes de a triagem dimensionar qualquer coisa. Juntar os dois esconderia a
 * métrica que diz se o atendimento perde gente no meio da conversa.
 */
export type MotivoDeFim =
  | "abaixo_do_piso"
  | "fora_da_area"
  | "sem_retorno"
  | "outro";

export interface CasoFinalizado {
  lead_id: string;
  nome: string | null;
  phone_number: string;
  empresa_ou_resumo: string | null;
  valor_estimado_min: number | null;
  valor_estimado_max: number | null;
  arquivado_em: string | null;
  /** Nulo quando foi a triagem. */
  arquivado_por: string | null;
}

export interface GrupoFinalizado {
  motivo: MotivoDeFim;
  rotulo: string;
  total: number;
  casos: CasoFinalizado[];
}

export interface FinalizadosResponse {
  agent_id: string;
  dias: number;
  total: number;
  grupos: GrupoFinalizado[];
}

// ========== Histórico ==========

/** Um movimento na trilha do lead (`Movimento` no backend). */
export interface Movimento {
  id: string;
  lead_id: string;
  lead_nome: string | null;
  phone_number: string;
  status_anterior: string | null;
  status_novo: string;
  motivo: string | null;
  /** Nulo quando foi a IA — é a distinção que o histórico existe para mostrar. */
  responsavel: string | null;
  quando: string;
}

export interface HistoricoResponse {
  agent_id: string;
  total: number;
  pagina: number;
  por_pagina: number;
  movimentos: Movimento[];
}

// ========== Escritório ==========

/**
 * Os dados que o agente usa para responder sobre o escritório.
 *
 * Todos opcionais: escritório com nada preenchido é o estado inicial, e o
 * agente simplesmente não fala do que não sabe.
 */
export interface Escritorio {
  nome: string | null;
  cnpj: string | null;
  oab_responsavel: string | null;
  fundador: string | null;
  endereco: string | null;
  email: string | null;
  telefone: string | null;
  /** Número dado a quem **já é cliente** e escreveu no comercial por engano. */
  telefone_suporte: string | null;
  horario_atendimento: string | null;
  site: string | null;
  instagram: string | null;
}

// ========== Clientes ==========

/** Uma linha da lista de contatos (`ClienteNaLista` no backend). */
export interface ClienteNaLista {
  lead_id: string;
  nome: string | null;
  phone_number: string;
  email: string | null;
  empresa: string | null;
  cargo: string | null;
  score_qualificacao: number;
  /** A coluna do board. Nulo em lead criado antes de o funil existir. */
  etapa: string | null;
  dias_parado: number | null;
  data_criacao: string | null;
  conversation_id: string | null;
}

export interface ClientesResponse {
  agent_id: string;
  /** Total da **busca**, não da base — é o que a paginação precisa. */
  total: number;
  pagina: number;
  por_pagina: number;
  clientes: ClienteNaLista[];
}

// ========== Métricas ==========

export interface MetricsSummary {
  agent_id: string;
  periodo: string;
  atendimentos_totais: number;
  taxa_qualificacao: number;
  tempo_medio_resposta_seg: number;
  leads_por_status: LeadDistribution;
  timestamp: string;
}

export interface LeadDistribution {
  novo: number;
  em_qualificacao: number;
  qualificado: number;
  agendado: number;
  arquivado: number;
  total: number;
}

export interface ResponseTimeMetrics {
  tempo_medio_seg: number;
  p50_seg: number;
  p95_seg: number;
  min_seg: number;
  max_seg: number;
  total_trocas: number;
  timestamp: string;
}

export interface TimeseriesPoint {
  data: string;
  atendimentos: number;
  leads_qualificados: number;
}

export interface TimeseriesResponse {
  agent_id: string;
  dias: number;
  pontos: TimeseriesPoint[];
}

/** Uma etapa do funil (`EtapaDoFunil` no backend). */
export interface EtapaDoFunil {
  nome: string;
  ordem: number;
  /** Quantos estão nesta coluna agora. */
  parados_aqui: number;
  /** Quantos chegaram até aqui — esta coluna e todas as seguintes. */
  chegaram: number;
  percentual_do_topo: number;
  /** Sobre a etapa anterior. Diz onde o funil aperta; o topo é sempre 100. */
  conversao_da_etapa: number;
  com_intervencao_humana: number;
}

export interface FunilResponse {
  agent_id: string;
  dias: number | null;
  total_de_leads: number;
  /** Fora da cadeia: quem foi arquivado no primeiro contato não avançou. */
  arquivados: number;
  etapas: EtapaDoFunil[];
}

export type MetricsPeriod = "day" | "week" | "month";

// ========== Conexão do WhatsApp ==========

/**
 * Estado da instância na Evolution (`EstadoDaConexao` no backend).
 *
 * `indisponivel` é a Evolution fora do ar; `desconectado` é o número caído.
 * São problemas diferentes, com donos diferentes — por isso não viram um só.
 */
export type EstadoDaInstancia =
  | "conectado"
  | "conectando"
  | "desconectado"
  | "inexistente"
  | "indisponivel"
  | "desconhecido";

export interface EstadoDaConexao {
  estado: EstadoDaInstancia;
  instancia: string;
  detalhe: string | null;
}

export interface QrCode {
  /** Já vem com o prefixo `data:image/png;base64,`. */
  qrcode: string | null;
  /** Código de pareamento, para quem não consegue ler o QR. */
  codigo: string | null;
  detalhe: string | null;
}

/**
 * Resposta de `POST /api/v1/whatsapp/desconectar`.
 *
 * `desconectado: false` quer dizer que o número **continua no ar** — o pior
 * desfecho possível é a tela dizer que parou de atender enquanto as mensagens
 * seguem chegando.
 */
export interface ResultadoDaDesconexao {
  desconectado: boolean;
  detalhe: string | null;
}
