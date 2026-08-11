# Guia de Webhook e Integração WhatsApp - L'Aquila AI

## 🔌 Integração Evolution API - Fase 5

Backend recebe mensagens do WhatsApp via webhook da Evolution API, processa com Claude, e responde automaticamente.

## 📋 Endpoints de Webhook

### 1. Receber Mensagens WhatsApp
**POST** `/api/v1/webhook/messages`

Endpoint que recebe mensagens da Evolution API. Processa end-to-end e envia resposta.

#### Request (da Evolution API)
```json
{
  "event": "messages.upsert",
  "data": {
    "key": {
      "remoteJid": "5561999887234@s.whatsapp.net",
      "fromMe": false,
      "agentId": "agent-uuid-123"
    },
    "message": {
      "messageTimestamp": 1691688000,
      "messageType": "textMessage",
      "messageBody": "Olá, gostaria de saber sobre seus produtos"
    },
    "owner": "5561999887234"
  }
}
```

#### Response (200 OK)
```json
{
  "status": "success",
  "conversation_id": "conv-uuid-456",
  "message_id": "msg-uuid-789"
}
```

#### Fluxo de Processamento
1. ✅ Valida evento é `messages.upsert`
2. ✅ Ignora se é mensagem enviada (fromMe=true)
3. ✅ Ignora se não é textMessage
4. ✅ Extrai phone_number do remoteJid
5. ✅ Busca ou cria Conversation
6. ✅ Recupera histórico (ultimas 5 msgs)
7. ✅ Chama Claude LLM
8. ✅ Salva user message no DB
9. ✅ Salva assistant response no DB
10. ✅ Envia resposta via WhatsApp
11. ✅ Retorna resultado

#### Erros
- `404`: Agent não encontrado
- `422`: Validação falhou (missing agent_id, etc)
- Erro de API retorna `status: error` com mensagem

#### Casos Ignorados (retorna 200)
```
{
  "status": "ignored",
  "reason": "non-text message"  // ou "outgoing message", "empty message"
}
```

---

### 2. Health Check de Webhook
**GET** `/api/v1/webhook/health`

Verifica se o backend está pronto para receber webhooks.

#### Request
```bash
GET /api/v1/webhook/health
```

#### Response (200 OK)
```json
{
  "status": "ok",
  "timestamp": "2026-08-10T21:00:00Z"
}
```

---

### 3. Webhook Legacy (Compatibilidade)
**POST** `/api/v1/webhook/whatsapp`

Mantido para compatibilidade com versão anterior. Novo código deve usar `/webhook/messages`.

---

## 🔄 Fluxo Completo End-to-End

```
WhatsApp User
    │ (envia mensagem)
    ▼
Evolution API
    │ (webhook POST)
    ▼
/api/v1/webhook/messages
    │
    ├─→ Valida: evento type, fromMe, messageType
    │
    ├─→ Extrai: phone_number, message_text, agent_id
    │
    ├─→ Orchestrator.process_incoming_message()
    │   │
    │   ├─→ get_or_create_conversation(agent_id, phone)
    │   │   └─→ Busca no DB ou cria nova
    │   │
    │   ├─→ llm_service.get_conversation_history()
    │   │   └─→ Recupera últimas 5 mensagens
    │   │
    │   ├─→ llm_service.generate_response()
    │   │   ├─→ Chama Claude 3.5 Sonnet
    │   │   ├─→ Usa system_prompt do agente
    │   │   └─→ Retorna response + tokens
    │   │
    │   ├─→ Salva Message (user) no PostgreSQL
    │   │
    │   ├─→ Salva Message (assistant) no PostgreSQL
    │   │
    │   ├─→ whatsapp_service.send_message()
    │   │   └─→ Envia via Evolution API
    │   │
    │   └─→ Retorna result (conversation_id, message_id)
    │
    └─→ HTTP 200 Response
         │
         ▼
      Evolution API (reconhece sucesso)
         │
         ▼
      WhatsApp User (recebe resposta)
```

---

## 🌐 Configuração da Evolution API

### 1. Configurar Webhook no Dashboard Evolution
```
Instância: laquilaia
Webhook URL: https://seu-servidor.com/api/v1/webhook/messages
Eventos: messages.upsert, connection.update
```

### 2. Variáveis de Ambiente Necessárias
```bash
# Backend .env
EVOLUTION_API_URL=http://evolution:4000
EVOLUTION_API_KEY=sua-chave-api
EVOLUTION_INSTANCE_NAME=laquilaia
EVOLUTION_WEBHOOK_URL=http://localhost:8000/webhook/messages
```

### 3. Testar Webhook (sem WhatsApp real)
```bash
# Simular mensagem recebida
curl -X POST http://localhost:8000/api/v1/webhook/messages \
  -H "Content-Type: application/json" \
  -d '{
    "event": "messages.upsert",
    "data": {
      "key": {
        "remoteJid": "5561999887234@s.whatsapp.net",
        "fromMe": false,
        "agentId": "agent-uuid-123"
      },
      "message": {
        "messageTimestamp": 1691688000,
        "messageType": "textMessage",
        "messageBody": "Olá teste"
      },
      "owner": "5561999887234"
    }
  }'
```

---

## 🏗️ Arquitetura de Serviços

### Camadas de Processamento

```
┌─────────────────────────────────────────────────────┐
│            Webhook Router (routers/webhook.py)      │
│  ├─ POST /webhook/messages (main entry point)      │
│  ├─ GET /webhook/health                            │
│  └─ POST /webhook/whatsapp (legacy)                │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│     Message Orchestrator (services/msg_orch.py)     │
│  ├─ process_incoming_message()                     │
│  ├─ _get_or_create_conversation()                  │
│  └─ validate_webhook_signature()                   │
└───────────────────┬─────────────────────────────────┘
                    │
         ┌──────────┼──────────┐
         │          │          │
         ▼          ▼          ▼
    ┌────────┐ ┌────────┐ ┌──────────┐
    │  LLM   │ │  WhatsApp  │ │ Conversation │
    │Service │ │  Service   │ │    DB        │
    └────────┘ └────────┘ └──────────┘
```

### Serviços Principais

#### 1. MessageOrchestrator (services/message_orchestrator.py)
```python
orchestrator = MessageOrchestrator()

# Método principal
await orchestrator.process_incoming_message(
    agent_id: str,
    phone_number: str,
    message_text: str,
    db: AsyncSession
) -> Dict[str, Any]
```

**Responsabilidades:**
- Coordena todo o fluxo
- Verifica ownership do agente
- Gerencia conversa (cria ou reutiliza)
- Integra LLM + WhatsApp services
- Persiste mensagens

#### 2. WhatsAppService (services/whatsapp_service.py)
```python
whatsapp_service = WhatsAppService()

# Método principal
await whatsapp_service.send_message(
    phone_number: str,
    message_text: str,
    quoted_message_id: Optional[str] = None
) -> Dict[str, Any]
```

**Responsabilidades:**
- Envia mensagens via Evolution API
- Formata payload corretamente
- Trata erros de API
- Limpa números de telefone

#### 3. LLMService (services/llm_service.py - Fase 4)
Reutilizado da Fase 4 para gerar respostas contextualizadas.

---

## 🧪 Testando Webhook

### Teste Manual com cURL
```bash
# 1. Criar agente (get agent_id)
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Agent Webhook Test",
    "system_prompt": "Você é um assistente.",
    "temperatura": 0.7,
    "max_tokens": 1024
  }'

# 2. Enviar webhook
curl -X POST http://localhost:8000/api/v1/webhook/messages \
  -H "Content-Type: application/json" \
  -d '{
    "event": "messages.upsert",
    "data": {
      "key": {
        "remoteJid": "5561999887234@s.whatsapp.net",
        "fromMe": false,
        "agentId": "AGENT_ID_FROM_STEP_1"
      },
      "message": {
        "messageTimestamp": 1691688000,
        "messageType": "textMessage",
        "messageBody": "Teste webhook"
      },
      "owner": "5561999887234"
    }
  }'
```

### Rodar Testes Unitários
```bash
# Todos os testes de webhook
docker-compose exec backend pytest tests/test_webhook.py -v

# Teste específico
docker-compose exec backend pytest tests/test_webhook.py::TestWebhookIntegration::test_webhook_message_processing -v

# Com cobertura
docker-compose exec backend pytest tests/test_webhook.py --cov=app.services --cov=app.routers
```

### Teste de Integração End-to-End
```bash
# 1. Inicie backend e banco
docker-compose up -d

# 2. Aguarde Health Check
curl http://localhost:8000/health

# 3. Envie webhook de teste
curl -X POST http://localhost:8000/api/v1/webhook/messages \
  -H "Content-Type: application/json" \
  -d @webhook-payload.json

# 4. Verifique logs
docker-compose logs -f backend | grep "webhook\|WhatsApp\|Agent"
```

---

## 💾 Dados Persistidos

### Tabela: conversations
```sql
INSERT INTO conversations (id, agent_id, phone_number, status, data_criacao, data_ultima_msg)
VALUES ('conv-123', 'agent-123', '5561999887234', 'ativa', now(), now());
```

### Tabela: messages
```sql
INSERT INTO messages (id, conversation_id, remetente, conteudo, timestamp)
VALUES 
  ('msg-1', 'conv-123', 'user', 'Olá teste', now()),
  ('msg-2', 'conv-123', 'assistant', 'Olá! Como posso ajudar?', now());
```

---

## 🔐 Segurança & Validação

### Validações Implementadas
✅ Evento deve ser `messages.upsert`
✅ Mensagem não deve ser enviada por nós (fromMe=false)
✅ Apenas textMessage é processada
✅ Message body não pode estar vazio
✅ Agent ID é obrigatório
✅ Phone number é validado e limpo

### Segurança (Roadmap)
- [ ] Validar assinatura de webhook (HMAC-SHA256)
- [ ] Rate limiting por phone number
- [ ] Detecção de spam
- [ ] Logging de todas as requisições
- [ ] Monitoramento de erros

---

## 📊 Monitoramento & Logging

### Logs Esperados
```
🔔 Webhook received: event=messages.upsert, phone=5561999887234, message=...
📨 Processing message from 5561999887234 for agent agent-123
🆕 Creating new conversation for 5561999887234
✅ New conversation created: conv-123
✅ Claude response generated for agent agent-123 (tokens: 85)
✅ Messages saved for conversation conv-123 (tokens: 85)
✅ WhatsApp message sent to 5561999887234 (message_id: msg-uuid-789)
✅ Message processing complete for 5561999887234: sent_id=msg-uuid-789
```

### Métricas para Monitorar
- Tempo de processamento (recebimento → resposta)
- Taxa de sucesso de webhooks
- Tokens usados por webhook
- Tempo médio de resposta Claude
- Falhas de envio WhatsApp

---

## 🐛 Troubleshooting

### "Missing agent_id in webhook"
**Causa:** Payload não contém agentId
**Solução:** Adicione agentId ao data.key da payload

### "Agent not found"
**Causa:** agent_id inválido ou agente deletado
**Solução:** Verifique agent_id existe e está ativo

### "Failed to send message"
**Causa:** Evolution API inacessível ou credenciais incorretas
**Solução:** Verifique EVOLUTION_API_KEY, EVOLUTION_API_URL, instância ativa

### "Webhook keeps retrying"
**Causa:** Backend retornou erro 5xx
**Solução:** Verifique logs, corrija erro, webhook será reenviado

### "Conversation not found"
**Causa:** Conversa foi deletada ou IDs não correspondem
**Solução:** Sistema cria nova conversa automaticamente

---

## 📈 Casos de Uso

### 1. Primeiro Contato (Sem Histórico)
```
Cliente: "Olá"
    ↓
Backend cria conversation
Backend recupera histórico (vazio)
Claude responde com base apenas no system_prompt
    ↓
Cliente recebe resposta imediata
```

### 2. Conversa Contínua (Com Histórico)
```
Cliente: "Qual o preço do produto X?" (msg 1)
    ↓ (agents responde com preço)
    
Cliente: "E se eu comprar em quantidade?" (msg 2)
    ↓
Backend recupera msg 1 como histórico
Claude entende contexto (sabe que é sobre produto X)
    ↓
Cliente recebe resposta contextualizada
```

### 3. Múltiplos Clientes (Separação por Conversa)
```
Cliente A (5561999887234): "Olá"
Cliente B (5561999987654): "Olá"
    ↓
Backend cria 2 conversations separadas
    ↓
Cada um tem seu histórico isolado
```

---

## 🚀 Próximas Fases

### Fase 6: Memory Service Avançado
- [ ] Caching de histórico em Redis
- [ ] Busca semântica (embeddings)
- [ ] Resumo automático de conversas longas

### Fase 7: Lead Processing
- [ ] Claude retorna JSON estruturado
- [ ] Parser de qualificação
- [ ] Movimentação automática no Kanban

### Fase 8: Kanban Backend
- [ ] CRUD de leads
- [ ] Movimentação entre colunas
- [ ] Timeline de mudanças

---

## 📚 Referências

- [Evolution API Docs](https://doc.evolution-api.com/)
- [Guia LLM (Fase 4)](GUIA_LLM.md)
- [Guia Agentes (Fase 3)](laquilaia_whatsapp/GUIA_AGENTES.md)

---

**Última Atualização:** 2026-08-10  
**Status:** Fase 5 - Webhook WhatsApp Integration ✅
