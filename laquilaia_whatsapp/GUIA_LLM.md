# Guia de Integração Claude LLM - L'Aquila AI

## 🤖 Integração Claude 3.5 Sonnet

O backend integra o modelo Claude 3.5 Sonnet via API oficial da Anthropic. Cada mensagem é processada com o prompt específico do agente e contexto de conversa.

## 📋 Endpoints de Chat

Todos os endpoints estão sob `/api/v1/agents/{agent_id}` e requerem autenticação Bearer token.

### 1. Chat com Contexto Completo
**POST** `/api/v1/agents/{agent_id}/chat`

Envia mensagem para agente, usa histórico de conversa para contexto, salva conversa no banco.

#### Request
```json
{
  "message": "Olá, gostaria de saber o preço do produto X",
  "conversation_id": "optional-conversation-uuid"
}
```

#### Response (200 OK)
```json
{
  "response": "Olá! O produto X custa R$ 99,90. Posso ajudá-lo com mais informações?",
  "tokens_used": {
    "input_tokens": 156,
    "output_tokens": 28,
    "total_tokens": 184
  },
  "timestamp": "2026-08-10T21:00:00Z",
  "model": "claude-3-5-sonnet-20241022"
}
```

#### Validações
- `message`: 1-4000 caracteres
- `conversation_id`: UUID válido (opcional)

#### Erros
- `401`: Não autenticado
- `404`: Agente não encontrado
- `422`: Validação falhou
- `429`: Rate limit excedido

---

### 2. Teste de Agente (Sem Salvar)
**POST** `/api/v1/agents/{agent_id}/test`

Testa agente sem histórico de conversa. Ideal para validar sistema prompt antes de deployment.

#### Request
```json
{
  "message": "Olá, como você funciona?"
}
```

#### Response (200 OK)
```json
{
  "response": "Sou um assistente IA treinado para ajudá-lo. Como posso colaborar?",
  "tokens_used": {
    "input_tokens": 45,
    "output_tokens": 18,
    "total_tokens": 63
  },
  "timestamp": "2026-08-10T21:00:00Z",
  "model": "claude-3-5-sonnet-20241022"
}
```

**Características:**
- ✅ Sem histórico de conversa
- ✅ Sem salvamento em banco
- ✅ Teste rápido e iterativo
- ✅ Perfeito para validar prompts

#### Erros
- `401`: Não autenticado
- `404`: Agente não encontrado
- `422`: Validação falhou

---

### 3. Status de Rate Limit
**GET** `/api/v1/agents/{agent_id}/rate-limit-status`

Verifica uso atual de tokens e chamadas API.

#### Request
```bash
GET /api/v1/agents/agent-uuid-123/rate-limit-status
Authorization: Bearer <token>
```

#### Response (200 OK)
```json
{
  "calls_used": 12,
  "calls_limit": 60,
  "tokens_used": 3500,
  "tokens_limit": 40000,
  "calls_remaining": 48,
  "tokens_remaining": 36500
}
```

---

## 🔧 Fluxo de Processamento de Mensagem

```
User Request
    │
    ├─→ Valida autenticação (JWT)
    │
    ├─→ Verifica propriedade do agente
    │
    ├─→ Recupera histórico de conversa (ultimas 5 msgs)
    │
    ├─→ Constrói prompt:
    │   ├─ System Prompt (do agente)
    │   ├─ Conversation History
    │   └─ User Message (atual)
    │
    ├─→ Verifica rate limits
    │
    ├─→ Chama Claude API
    │
    ├─→ Conta tokens usados
    │
    ├─→ Salva mensagens no PostgreSQL:
    │   ├─ Message (user)
    │   └─ Message (assistant)
    │
    └─→ Retorna resposta + token usage
```

## 📊 Estrutura de Token Usage

```json
{
  "input_tokens": 156,      // Tokens na entrada (prompt + history + message)
  "output_tokens": 28,      // Tokens na resposta Claude
  "total_tokens": 184       // Total para cálculo de rate limit
}
```

**Exemplo de Cálculo:**
- System prompt (agente): ~80 tokens
- Histórico 5 mensagens: ~250 tokens
- Mensagem do usuário: ~20 tokens
- **Total input: 350 tokens**
- Claude responde com: ~40 tokens
- **Total dessa chamada: 390 tokens** (contagem contra rate limit)

## ⚡ Rate Limiting

Janela deslizante de 60 segundos, em duas dimensões, **por conta**
(`agent.user_id`) — o uso de um cliente não consome a cota de outro.

O estado fica no **Redis** (`app/services/rate_limiter.py`), não no processo:
com mais de uma réplica do backend, contadores em memória dariam a cada uma o
seu balde e o limite efetivo seria `N × limite`. São dois sorted sets por
conta, `ratelimit:calls:{user_id}` e `ratelimit:tokens:{user_id}`, com o
instante da chamada como score — assim o corte da janela é um
`ZREMRANGEBYSCORE`, sem varrer o conjunto.

### Limite 1: Chamadas por Minuto
- **Default:** 60 chamadas/minuto
- **Config:** `LLM_MAX_CALLS_PER_MINUTE`
- **Erro:** `ValidationException` se ultrapassado

### Limite 2: Tokens por Minuto
- **Default:** 40.000 tokens/minuto
- **Config:** `LLM_MAX_TOKENS_PER_MINUTE`
- **Erro:** `ValidationException` se ultrapassado

### Sem Redis

O limitador cai para a memória do processo e registra um `WARNING`. Isso é
exatamente o comportamento antigo — cada réplica com o seu balde —, escolhido
por ser melhor tanto que recusar todas as chamadas quanto que deixá-las passar
sem medição. `GET /health` traz `"redis": "unavailable"` nesse estado.

A queda é por chamada, não definitiva: o cliente do redis-py reconecta
sozinho, então uma instabilidade momentânea não condena o processo a contar em
memória até reiniciar.

### Precisão

`check` roda antes da chamada e `track` depois, quando o total de tokens
finalmente é conhecido. Duas requisições simultâneas podem, portanto, passar
pela verificação antes de qualquer uma registrar o seu uso, e a janela estoura
um pouco. Não há como reservar antecipadamente o que ainda não se sabe quanto
vai custar; o objetivo é conter o uso, não cravar o teto no token exato.

### Exemplo de Limite Atingido
```json
{
  "status_code": 422,
  "detail": "Rate limit exceeded: 40000 tokens per minute"
}
```

### Monitoramento
```bash
# Verificar status atual
curl -X GET http://localhost:8000/api/v1/agents/agent-id-123/rate-limit-status \
  -H "Authorization: Bearer <token>"

# Response
{
  "calls_used": 45,
  "calls_limit": 60,
  "tokens_used": 38500,
  "tokens_limit": 40000,
  "calls_remaining": 15,
  "tokens_remaining": 1500
}
```

---

## 📝 Exemplos de Uso

### Exemplo 1: Chat Simples
```bash
curl -X POST http://localhost:8000/api/v1/agents/agent-uuid-123/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Qual é o seu horário de funcionamento?"
  }'
```

### Exemplo 2: Chat com Conversa Existente
```bash
curl -X POST http://localhost:8000/api/v1/agents/agent-uuid-123/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "E qual é o seu email?",
    "conversation_id": "conversation-uuid-456"
  }'
```

### Exemplo 3: Teste de Agente
```bash
curl -X POST http://localhost:8000/api/v1/agents/agent-uuid-123/test \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Você é um assistente inteligente?"
  }'
```

### Exemplo 4: Verificar Rate Limit
```bash
curl -X GET http://localhost:8000/api/v1/agents/agent-uuid-123/rate-limit-status \
  -H "Authorization: Bearer <token>"
```

---

## 🔑 Configuração de Ambiente

### Variáveis Obrigatórias
```bash
# API Key da Anthropic (obrigatória para produção)
ANTHROPIC_API_KEY=sk-ant-...

# Modelo Claude
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Default quando agent não especifica
TEMPERATURE=0.7
MAX_TOKENS=1024
```

### Variáveis de Rate Limit (Opcional)
```bash
# Chamadas por minuto
LLM_MAX_CALLS_PER_MINUTE=60

# Tokens por minuto
LLM_MAX_TOKENS_PER_MINUTE=40000
```

---

## 🧪 Testando Endpoints

### Swagger UI (Recomendado)
1. Acesse http://localhost:8000/docs
2. Clique em "Authorize" e cole seu access_token
3. Expanda "chat" e teste endpoints

### Rodar Testes
```bash
# Todos os testes de LLM
docker-compose exec backend pytest tests/test_llm_service.py -v

# Um teste específico
docker-compose exec backend pytest tests/test_llm_service.py::TestGenerateResponse::test_generate_response_success -v

# Com cobertura
docker-compose exec backend pytest tests/test_llm_service.py --cov=app.services.llm_service
```

---

## 💡 Boas Práticas

### ✅ Faça
- ✅ Use histórico de conversa para contexto (máx 5 mensagens)
- ✅ Valide mensagem do usuário antes de enviar
- ✅ Monitore token usage via endpoint rate-limit-status
- ✅ Implemente retry logic com backoff exponencial para timeouts
- ✅ Use POST /test para validar novo prompt antes de ir para production
- ✅ Log todas as chamadas LLM com tokens usados
- ✅ Implemente cache de respostas frequentes

### ❌ NÃO Faça
- ❌ Não inclua histórico completo (economia de tokens é crítica)
- ❌ Não ignore rate limits
- ❌ Não coloque API key no código
- ❌ Não use temperatura 2.0 sem testar
- ❌ Não faça requisições concorrentes sem limite
- ❌ Não guarde conversas completas sem limpeza periódica

---

## 🐛 Troubleshooting

### "ANTHROPIC_API_KEY não configurada"
**Causa:** Variável de ambiente não definida
**Solução:** 
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
# ou adicione em .env
```

### "Rate limit exceeded"
**Causa:** Muitas chamadas ou tokens em curto período
**Solução:** 
- Aguarde 1 minuto para reset
- Verifique `/rate-limit-status`
- Reduza histórico de conversa (use menos mensagens)

### "Conversation not found"
**Causa:** Conversation ID inválido ou pertence a outro agente
**Solução:** 
- Verifique o UUID da conversa
- Crie nova conversa sem `conversation_id`

### "Token limit exceeded in system prompt"
**Causa:** System prompt muito longo
**Solução:**
- Reduza tamanho do prompt
- Use variáveis (ex: {{NOME_EMPRESA}}) ao invés de texto completo

---

## 📊 Métricas & Monitoramento

### Campos Importantes do Response
```json
{
  "response": "...",           // Resposta para usuário
  "tokens_used": {
    "input_tokens": 150,       // Para billing e rate limiting
    "output_tokens": 30,
    "total_tokens": 180
  },
  "timestamp": "...",          // Para auditing
  "model": "claude-3-5-sonnet-20241022"  // Para tracking versão
}
```

### Log de Exemplo
```
✅ Claude response generated for agent agent-123 (tokens: 184)
✅ Chat message processed: agent=agent-123, conversation=conv-456, tokens=184
📊 Usage tracked: 12 calls, 3500 tokens in last minute
```

---

## 🔒 Segurança

- ✅ Cada usuário só pode acessar agentes que possui
- ✅ Histórico de conversa isolado por agent_id
- ✅ Rate limits impedem abuso (DoS mitigation)
- ✅ API key não é retornada em responses
- ✅ Conversas salvas em PostgreSQL (criptografado em produção)

---

## 📚 Próximos Passos (Fases 5-7)

- **Fase 5**: Webhook WhatsApp (receber mensagens do Evolution API)
- **Fase 6**: Memory Service (recuperar histórico de conversas)
- **Fase 7**: Lead Processing (extrair estrutura JSON de Claude)
- **Fase 8**: Kanban Backend (mover leads entre colunas)

---

**Última Atualização:** 2026-08-10  
**Status:** Fase 4 - Claude LLM Integration ✅
