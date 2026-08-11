# Guia de Gerenciamento de Agentes - L'Aquila AI

## 🤖 Sistema de Agentes IA

Um agente é uma entidade IA configurável que gerencia conversas no WhatsApp. Cada agente tem seu próprio prompt, temperatura, modelo e variáveis personalizadas.

## 📋 Endpoints de Agentes

Todos os endpoints estão sob `/api/v1/agents` e requerem autenticação Bearer token.

### 1. Criar Agente
**POST** `/api/v1/agents`

Cria um novo agente para o usuário autenticado.

#### Request
```json
{
  "nome": "Vendedor Autômato",
  "descricao": "Agente especializado em venda de produtos",
  "system_prompt": "Você é um agente de vendas assistente. Sua função é:\n1. Cumprimentar o cliente\n2. Entender suas necessidades\n3. Sugerir produtos\n4. Qualificar o lead",
  "temperatura": 0.7,
  "max_tokens": 2048
}
```

#### Response (201 Created)
```json
{
  "id": "agent-uuid-123",
  "user_id": "user-uuid-456",
  "nome": "Vendedor Autômato",
  "descricao": "Agente especializado em venda de produtos",
  "system_prompt": "Você é um agente de vendas...",
  "temperatura": 0.7,
  "max_tokens": 2048,
  "status": "ativo",
  "data_criacao": "2026-08-10T21:00:00Z",
  "data_atualizacao": "2026-08-10T21:00:00Z"
}
```

#### Validações
- `nome`: 1-255 caracteres
- `system_prompt`: Não pode estar vazio
- `temperatura`: 0 a 2 (0=determinístico, 2=muito criativo)
- `max_tokens`: 1 a 4096

#### Erros
- `401`: Não autenticado
- `422`: Validação falhou

---

### 2. Listar Agentes
**GET** `/api/v1/agents`

Lista todos os agentes do usuário autenticado.

#### Query Parameters
```
skip=0        (padrão: 0) - Quantos agentes pular
limit=100     (padrão: 100, máx: 1000) - Quantidade a retornar
status=ativo  (opcional) - Filtrar por status (ativo, inativo, em_teste)
```

#### Request
```bash
GET /api/v1/agents?skip=0&limit=10&status=ativo
Authorization: Bearer <token>
```

#### Response (200 OK)
```json
[
  {
    "id": "agent-uuid-123",
    "user_id": "user-uuid-456",
    "nome": "Vendedor Autômato",
    "descricao": "Agente especializado em venda",
    "system_prompt": "Você é um agente de vendas...",
    "temperatura": 0.7,
    "max_tokens": 2048,
    "status": "ativo",
    "data_criacao": "2026-08-10T21:00:00Z",
    "data_atualizacao": "2026-08-10T21:00:00Z"
  },
  {
    "id": "agent-uuid-789",
    ...
  }
]
```

---

### 3. Obter Agente Específico
**GET** `/api/v1/agents/{agent_id}`

Obtém detalhes de um agente específico.

#### Request
```bash
GET /api/v1/agents/agent-uuid-123
Authorization: Bearer <token>
```

#### Response (200 OK)
```json
{
  "id": "agent-uuid-123",
  "user_id": "user-uuid-456",
  "nome": "Vendedor Autômato",
  "descricao": "Agente especializado em venda",
  "system_prompt": "Você é um agente de vendas...",
  "temperatura": 0.7,
  "max_tokens": 2048,
  "status": "ativo",
  "data_criacao": "2026-08-10T21:00:00Z",
  "data_atualizacao": "2026-08-10T21:00:00Z"
}
```

#### Erros
- `401`: Não autenticado
- `404`: Agente não encontrado ou não pertence ao usuário

---

### 4. Atualizar Agente
**PUT** `/api/v1/agents/{agent_id}`

Atualiza um agente existente. Apenas campos fornecidos são atualizados.

#### Request
```json
{
  "nome": "Vendedor Inteligente V2",
  "temperatura": 0.8,
  "system_prompt": "Novo prompt aqui..."
}
```

#### Response (200 OK)
```json
{
  "id": "agent-uuid-123",
  "nome": "Vendedor Inteligente V2",
  "temperatura": 0.8,
  ...
}
```

#### Validações
- Mesmo sistema de validação que criação
- Todos os campos são opcionais

#### Erros
- `401`: Não autenticado
- `404`: Agente não encontrado
- `422`: Validação falhou

---

### 5. Deletar Agente
**DELETE** `/api/v1/agents/{agent_id}`

Deleta um agente e todos seus dados associados (conversas, leads, etc).

#### Request
```bash
DELETE /api/v1/agents/agent-uuid-123
Authorization: Bearer <token>
```

#### Response (200 OK)
```json
{
  "message": "Agent deleted successfully",
  "agent_id": "agent-uuid-123"
}
```

#### Aviso
⚠️ **Ação irreversível**: Deleta agente + todas as conversas + todos os leads

#### Erros
- `401`: Não autenticado
- `404`: Agente não encontrado

---

### 6. Adicionar Variável ao Agente
**POST** `/api/v1/agents/{agent_id}/variables`

Adiciona uma variável dinâmica ao agente (ex: {{NOME_CLIENTE}}).

#### Request
```json
{
  "nome_variavel": "NOME_CLIENTE",
  "tipo": "texto",
  "descricao": "Nome do cliente para personalização",
  "valor_padrao": "Visitante",
  "opcoes": null
}
```

Tipos suportados:
- `texto`: String livre
- `numero`: Números
- `booleano`: Verdadeiro/Falso
- `enum`: Valores pré-definidos

#### Response (201 Created)
```json
{
  "id": "variable-uuid-123",
  "agent_id": "agent-uuid-123",
  "nome_variavel": "NOME_CLIENTE",
  "tipo": "texto"
}
```

#### Erros
- `401`: Não autenticado
- `404`: Agente não encontrado

---

### 7. Listar Variáveis do Agente
**GET** `/api/v1/agents/{agent_id}/variables`

Lista todas as variáveis associadas ao agente.

#### Request
```bash
GET /api/v1/agents/agent-uuid-123/variables
Authorization: Bearer <token>
```

#### Response (200 OK)
```json
[
  {
    "id": "variable-uuid-123",
    "nome_variavel": "NOME_CLIENTE",
    "descricao": "Nome do cliente para personalização",
    "tipo": "texto",
    "valor_padrao": "Visitante"
  },
  {
    "id": "variable-uuid-456",
    "nome_variavel": "STATUS_LEAD",
    "descricao": "Status atual do lead",
    "tipo": "enum",
    "valor_padrao": "novo"
  }
]
```

---

## 📝 Exemplos de Uso

### Exemplo 1: Criar Agente de Suporte
```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Agente de Suporte",
    "descricao": "Responde dúvidas dos clientes",
    "system_prompt": "Você é um agente de atendimento ao cliente...",
    "temperatura": 0.5,
    "max_tokens": 1024
  }'
```

### Exemplo 2: Listar Agentes com Paginação
```bash
curl -X GET "http://localhost:8000/api/v1/agents?skip=0&limit=5" \
  -H "Authorization: Bearer <token>"
```

### Exemplo 3: Atualizar System Prompt
```bash
curl -X PUT http://localhost:8000/api/v1/agents/agent-uuid-123 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "system_prompt": "Novo prompt com mais contexto..."
  }'
```

### Exemplo 4: Adicionar Variável
```bash
curl -X POST http://localhost:8000/api/v1/agents/agent-uuid-123/variables \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "nome_variavel": "NOME_EMPRESA",
    "tipo": "texto",
    "valor_padrao": "Nossa Empresa"
  }'
```

---

## 🔑 Estrutura de um Agente

```
┌─────────────────────────────────────┐
│            AGENTE IA                │
├─────────────────────────────────────┤
│ id: string (UUID)                   │
│ nome: string (max 255 chars)        │
│ descricao: string (opcional)        │
│                                     │
│ ┌─ CONFIGURAÇÃO LLM ─────────────┐  │
│ │ modelo: claude-3-5-sonnet      │  │
│ │ system_prompt: text            │  │
│ │ temperatura: float (0-2)       │  │
│ │ max_tokens: int (1-4096)       │  │
│ └────────────────────────────────┘  │
│                                     │
│ status: ativo|inativo|em_teste     │
│ data_criacao: timestamp            │
│ data_atualizacao: timestamp        │
│                                     │
│ ┌─ VARIÁVEIS ────────────────────┐  │
│ │ {{NOME_CLIENTE}}               │  │
│ │ {{TIPO_CONTRATO}}              │  │
│ │ {{DATA_CONTRATACAO}}           │  │
│ └────────────────────────────────┘  │
└─────────────────────────────────────┘
```

---

## 🧪 Testando Agentes

### Swagger UI (Recomendado)
1. Acesse http://localhost:8000/docs
2. Clique em "Authorize" e cole seu access_token
3. Teste cada endpoint na UI

### Rodar Testes
```bash
# Todos os testes de agentes
docker-compose exec backend pytest tests/test_agents.py -v

# Um teste específico
docker-compose exec backend pytest tests/test_agents.py::TestAgentCreation::test_create_agent_success -v

# Com cobertura
docker-compose exec backend pytest tests/test_agents.py --cov=app.services.agent_service
```

---

## 💡 Boas Práticas

### ✅ Faça
- ✅ Use nomes descritivos para agentes
- ✅ Escreva system prompts claros e específicos
- ✅ Teste o agente antes de colocar em produção
- ✅ Ajuste temperatura conforme necessidade (0.5 para precisão, 1.5 para criatividade)
- ✅ Use variáveis para personalizar respostas
- ✅ Documente o propósito do agente

### ❌ NÃO Faça
- ❌ Não use prompts muito genéricos
- ❌ Não coloque informações sensíveis no prompt
- ❌ Não mude temperatura para valores extremos sem testar
- ❌ Não crie muitas variáveis desnecessárias
- ❌ Não deixe agentes inúteis bloqueando a conta

---

## 🔒 Segurança

- ✅ Cada usuário só vê seus próprios agentes
- ✅ Agentes não podem acessar dados de outros usuários
- ✅ Prompts são privados do usuário
- ✅ Validação de entrada em todos os campos

---

## 📊 Relacionamentos

Um agente pode ter:
- **Múltiplas conversas** - Uma por número de telefone
- **Múltiplas variáveis** - Para personalização
- **Múltiplos leads** - Gerados das conversas
- **Múltiplas métricas** - Performance diária

```
User
  ↓ (pode ter)
Agent
  ├─→ Conversation (um por phone)
  │     ├─→ Message (histórico)
  │     ├─→ FunctionCall (ações IA)
  │     └─→ Lead (se qualificado)
  │           └─→ LeadDetails (qualificação)
  ├─→ AgentVariable (customização)
  ├─→ KanbanColumn (CRM)
  └─→ ConversationMetrics (analytics)
```

---

## ⏰ Ciclo de Vida de um Agente

```
1. CRIAÇÃO
   └─→ Agent criado em estado "ativo"

2. TESTE
   └─→ Status muda para "em_teste"
   └─→ Testar no Playground (Fase 12)

3. PRODUÇÃO
   └─→ Status volta para "ativo"
   └─→ Começam as conversas

4. MELHORIAS
   └─→ Atualizar prompt, temperatura, etc
   └─→ Manter histórico de versões (Fase 4+)

5. APOSENTADORIA
   └─→ Status muda para "inativo"
   └─→ Ou deletar completamente
```

---

## 🐛 Troubleshooting

### "Agente não encontrado"
**Causa**: Agent ID inválido ou agente pertence a outro usuário
**Solução**: Verifique o ID e se está autenticado corretamente

### "Validação falhou"
**Causa**: Dados inválidos (temperatura fora do range, prompt vazio, etc)
**Solução**: Revise os validadores acima

### "Não autenticado"
**Causa**: Token não fornecido ou expirado
**Solução**: Faça login novamente

---

## 📚 Próximos Passos

- **Fase 4**: Integração Claude LLM (usar agente em conversas)
- **Fase 5**: Webhook WhatsApp (receber mensagens)
- **Fase 12**: Playground de teste (UI)
- **Fase 13**: Kanban de leads

---

**Última Atualização:** 2026-08-10  
**Status:** Fase 3 - CRUD de Agentes Implementado ✅
