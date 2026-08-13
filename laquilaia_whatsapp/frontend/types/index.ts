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
  descricao: string | null;
  system_prompt: string;
  temperatura: number;
  max_tokens: number;
  status: string;
  data_criacao: string;
  data_atualizacao: string;
}

/** Corpo de `POST /api/v1/agents` (schema `AgentCreate`). */
export interface AgentInput {
  nome: string;
  descricao?: string | null;
  system_prompt: string;
  temperatura: number;
  max_tokens: number;
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

/** Mensagem persistida, como vem de `GET .../chat/history`. */
export interface ChatHistoryMessage {
  id: string;
  remetente: "user" | "assistant";
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
  remetente: "user" | "assistant";
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

export type MetricsPeriod = "day" | "week" | "month";
