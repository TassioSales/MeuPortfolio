# Arquitetura do Banco de Dados - L'Aquila AI

## 📊 Diagrama de Entidades

```
┌──────────────────────────────────────────────────────────┐
│                       SISTEMA L'AQUILA AI                │
└──────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      CAMADA DE USUÁRIOS                         │
├─────────────────────────────────────────────────────────────────┤
│ users                  │ api_keys                               │
│ • id (PK)              │ • id (PK)                              │
│ • email (UNIQUE)       │ • user_id (FK)                         │
│ • nome                 │ • chave (UNIQUE)                       │
│ • senha_hash           │ • is_active                            │
│ • status               │ • criado_em                            │
│ • data_criacao         │ • expira_em                            │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      CAMADA DE AGENTES IA                       │
├─────────────────────────────────────────────────────────────────┤
│ agents                 │ agent_variables                        │
│ • id (PK)              │ • id (PK)                              │
│ • user_id (FK)         │ • agent_id (FK)                        │
│ • nome                 │ • nome_variavel                        │
│ • descricao            │ • descricao                            │
│ • system_prompt        │ • tipo                                 │
│ • modelo               │ • valor_padrao                         │
│ • temperatura          │ • opcoes                               │
│ • max_tokens           │ • data_criacao                         │
│ • status               │                                        │
│ • data_criacao         │                                        │
│ • data_atualizacao     │                                        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   CAMADA DE CONVERSAS (CORE)                    │
├─────────────────────────────────────────────────────────────────┤
│ conversations          │ messages           │ function_calls    │
│ • id (PK)              │ • id (PK)          │ • id (PK)         │
│ • agent_id (FK)        │ • conversation_id  │ • message_id (FK) │
│ • phone_number         │ • remetente        │ • conversation_id │
│ • status               │ • conteudo         │ • nome_funcao     │
│ • data_inicio          │ • tokens_usados    │ • parametros_json │
│ • data_ultima_msg      │ • timestamp        │ • resultado_json  │
│ • metadata             │ • metadata         │ • timestamp       │
│                        │                    │                   │
│ INDEX: phone_number    │ INDEX: conversation│ INDEX: conversation│
│ UNIQUE: agent+phone    │        _id         │        _id        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   CAMADA DE LEADS (CRM)                         │
├─────────────────────────────────────────────────────────────────┤
│ leads                  │ lead_details       │ lead_timeline     │
│ • id (PK)              │ • id (PK)          │ • id (PK)         │
│ • phone_number (UNIQUE)│ • lead_id (UNIQUE) │ • lead_id (FK)    │
│ • conversation_id (FK) │ • inconsistencias  │ • status_anterior │
│ • nome                 │ • problemas        │ • status_novo     │
│ • email                │ • score_qualif     │ • mudado_por (FK) │
│ • status_funil         │ • dados_json       │ • motivo          │
│ • data_criacao         │ • data_atualizacao │ • timestamp       │
│ • data_atualizacao     │                    │                   │
│                        │                    │ INDEX: lead_id    │
│                        │                    │ INDEX: timestamp  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   CAMADA DE KANBAN/CRM                          │
├─────────────────────────────────────────────────────────────────┤
│ kanban_columns         │ kanban_cards                           │
│ • id (PK)              │ • id (PK)                              │
│ • agent_id (FK)        │ • column_id (FK)                       │
│ • nome                 │ • lead_id (UNIQUE FK)                  │
│ • ordem                │ • ordem                                │
│ • cor_hex              │ • data_movimentacao                    │
│ • data_criacao         │                                        │
│                        │ INDEX: column_id                       │
│ UNIQUE: agent+nome     │                                        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   CAMADA DE MÉTRICAS                            │
├─────────────────────────────────────────────────────────────────┤
│ conversation_metrics   │ daily_stats                            │
│ • id (PK)              │ • id (PK)                              │
│ • agent_id (FK)        │ • data                                 │
│ • data                 │ • agent_id                             │
│ • total_atendimentos   │ • mensagens_recebidas                  │
│ • taxa_qualificacao    │ • mensagens_enviadas                   │
│ • tempo_medio_min      │ • leads_criados                        │
│ • mensagens_recebidas  │ • leads_qualificados                   │
│ • mensagens_enviadas   │                                        │
│ • leads_qualificados   │ UNIQUE: data                           │
│                        │ INDEX: data                            │
│ UNIQUE: agent+data     │                                        │
│ INDEX: data            │                                        │
└─────────────────────────────────────────────────────────────────┘
```

## 🔑 Relações Principais

### 1. User → Agent (1:N)
- Um usuário pode ter múltiplos agentes IA
- Quando usuário é deletado, seus agentes são deletados (CASCADE)

### 2. Agent → Conversation (1:N)
- Um agente pode ter múltiplas conversas
- Conversas são rastreadas por agent_id + phone_number (UNIQUE)

### 3. Conversation → Message (1:N)
- Uma conversa tem múltiplas mensagens
- Cada mensagem tem remetente (user/agent) e conteúdo

### 4. Message → FunctionCall (1:N)
- Uma mensagem pode ter múltiplas chamadas de função
- Usado para rastrear calls Claude (qualificação, agendamento, etc)

### 5. Conversation → Lead (1:1)
- Cada conversa pode gerar um lead
- Lead rastreia qualificação e status do funil

### 6. Lead → LeadDetails (1:1)
- Detalhes de qualificação do lead
- Score, inconsistências, dados JSON

### 7. Lead → LeadTimeline (1:N)
- Histórico de mudanças de status do lead
- Rastreia quem moveu o lead e quando

### 8. KanbanColumn → KanbanCard (1:N)
- Cada coluna Kanban tem múltiplos cards
- Um card por lead (UNIQUE lead_id)

### 9. Agent → ConversationMetrics (1:N)
- Métricas diárias por agente
- Um registro por agent_id + data

## 📝 Fluxo de Dados

### 1. Recebimento de Mensagem
```
WhatsApp → Evolution API → webhook/whatsapp → Conversation + Message
```

### 2. Processamento com IA
```
Message → Claude LLM → Response + FunctionCall (se qualificação)
```

### 3. Criação de Lead
```
FunctionCall (qualificação) → Lead + LeadDetails → Atualiza Kanban
```

### 4. Movimento no Kanban
```
Lead.status_funil muda → KanbanCard muda de column → LeadTimeline registra
```

### 5. Cálculo de Métricas
```
Conversations + Messages + Leads → ConversationMetrics diárias → Dashboard
```

## 📐 Indexação para Performance

```sql
-- Conversas (busca por phone_number)
CREATE UNIQUE INDEX idx_conversation_agent_phone 
  ON conversations(agent_id, phone_number);

-- Mensagens (busca por conversa)
CREATE INDEX idx_message_conversation 
  ON messages(conversation_id);

-- Mensagens (análise de série temporal)
CREATE INDEX idx_message_timestamp 
  ON messages(timestamp);

-- Leads (busca por phone)
CREATE UNIQUE INDEX idx_lead_phone 
  ON leads(phone_number);

-- Timeline (auditoria)
CREATE INDEX idx_lead_timeline_lead 
  ON lead_timeline(lead_id);

CREATE INDEX idx_lead_timeline_timestamp 
  ON lead_timeline(timestamp);

-- Kanban (busca por coluna)
CREATE INDEX idx_kanban_card_column 
  ON kanban_cards(column_id);

-- Métricas (queries do dashboard)
CREATE INDEX idx_conversation_metrics_agent_data 
  ON conversation_metrics(agent_id, data);

CREATE INDEX idx_daily_stats_data 
  ON daily_stats(data);
```

## 🔐 Constraints de Integridade

### Unique Constraints
- `users.email` - Um usuário por email
- `api_keys.chave` - Uma chave por ID
- `agent_variables(agent_id, nome_variavel)` - Variável única por agente
- `conversations(agent_id, phone_number)` - Uma conversa por agent/phone
- `leads.phone_number` - Um lead por phone
- `lead_details.lead_id` - Um detalhe por lead
- `kanban_columns(agent_id, nome)` - Uma coluna por nome/agente
- `conversation_metrics(agent_id, data)` - Uma métrica por agent/data
- `daily_stats.data` - Uma estatística por data

### Foreign Keys
- `api_keys.user_id` → `users.id` (CASCADE DELETE)
- `agents.user_id` → `users.id` (CASCADE DELETE)
- `conversations.agent_id` → `agents.id` (CASCADE DELETE)
- `messages.conversation_id` → `conversations.id` (CASCADE DELETE)
- `function_calls.message_id` → `messages.id` (CASCADE DELETE)
- `function_calls.conversation_id` → `conversations.id` (CASCADE DELETE)
- `leads.conversation_id` → `conversations.id` (CASCADE DELETE)
- `lead_details.lead_id` → `leads.id` (CASCADE DELETE)
- `lead_timeline.lead_id` → `leads.id` (CASCADE DELETE)
- `lead_timeline.mudado_por` → `users.id` (SET NULL)
- `kanban_columns.agent_id` → `agents.id` (CASCADE DELETE)
- `kanban_cards.column_id` → `kanban_columns.id` (CASCADE DELETE)
- `kanban_cards.lead_id` → `leads.id` (CASCADE DELETE)
- `conversation_metrics.agent_id` → `agents.id` (CASCADE DELETE)

## 📋 Exemplo de Query Comum

### Buscar últimas 10 mensagens de uma conversa
```sql
SELECT * FROM messages
WHERE conversation_id = $1
ORDER BY timestamp DESC
LIMIT 10;
```

### Buscar leads não qualificados
```sql
SELECT l.*, ld.* 
FROM leads l
LEFT JOIN lead_details ld ON l.id = ld.lead_id
WHERE l.status_funil = 'novo'
ORDER BY l.data_criacao DESC;
```

### Métricas do dia
```sql
SELECT 
  agent_id,
  COUNT(DISTINCT phone_number) as total_conversas,
  COUNT(DISTINCT CASE WHEN l.status_funil = 'qualificado' THEN l.id END) as leads_qualificados,
  COUNT(*) as total_mensagens
FROM messages m
INNER JOIN conversations c ON m.conversation_id = c.id
LEFT JOIN leads l ON c.id = l.conversation_id
WHERE DATE(m.timestamp) = CURRENT_DATE
GROUP BY c.agent_id;
```

## 🔄 Plano de Evolução do Schema

### Fase 1 (Atual)
- ✅ Schema base definido em Prisma
- ⏳ Migrações Prisma a executar

### Fase 2
- Adicionar índices de performance
- Adicionar trigge rs para audit log
- Adicionar particionamento por data (messages)

### Fase 3
- Schema de webhooks/integrações
- Schema de configurações de rate limiting
- Schema de templates de mensagens

### Fase 4
- Analytics avançado (heatmaps, funnels)
- Schema de A/B testing
- Schema de campanhas

---

**Última Atualização:** 2026-08-10  
**Status:** Fase 1 - Schema Design Completo
