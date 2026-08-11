# Guia de Memory Service Avançado - L'Aquila AI

## 🧠 Memory Service com Cache Redis - Fase 6

Otimização de recuperação de histórico de conversas usando Redis cache para reduzir latência e carga no banco de dados.

## 📋 Visão Geral

O Memory Service gerencia o histórico de conversas com cache automático em Redis. Cada conversa recuperada é armazenada por 1 hora (TTL configurável), evitando queries repetidas ao banco de dados.

### Benefícios
- ⚡ Reduz latência de resposta (cache hit em ~1ms vs DB query em ~100ms)
- 💾 Diminui carga no PostgreSQL
- 🔄 Invalidação automática após TTL
- 🧹 Limpeza automática de conversas expiradas

---

## 🏗️ Arquitetura

```
Request WhatsApp
    │
    ▼
Message Orchestrator
    │
    ├─→ llm_service.get_conversation_history()
    │   │
    │   ├─→ memory_service.get_conversation_history()
    │   │   │
    │   │   ├─→ Cache Hit? (Redis get)
    │   │   │   └─→ Retorna em cache_key:conv-123
    │   │   │
    │   │   ├─→ Cache Miss?
    │   │   │   ├─→ Query PostgreSQL
    │   │   │   ├─→ Salva em Redis com TTL
    │   │   │   └─→ Retorna histórico
    │   │   │
    │   │   └─→ Error?
    │   │       └─→ Fallback para DB diretamente
    │   │
    │   └─→ Retorna histórico formatado
    │
    ├─→ Claude LLM com histórico
    │
    └─→ Resposta e mensagens salvas no DB
```

---

## 💻 Implementação Técnica

### MemoryService (services/memory_service.py)

Classe central para gerenciar cache de conversas.

```python
from app.services.memory_service import memory_service

# Recuperar histórico com cache
history = await memory_service.get_conversation_history(
    conversation_id="conv-123",
    db=db_session,
    limit=5,
    use_cache=True  # Ativa cache Redis
)
# Retorna: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
```

### Métodos Principais

#### 1. get_conversation_history()
Recupera histórico com cache automático.

```python
async def get_conversation_history(
    conversation_id: str,
    db: AsyncSession,
    limit: int = 5,
    use_cache: bool = True,
) -> List[Dict[str, Any]]:
    """
    Fluxo:
    1. Se use_cache=True, tenta Redis
    2. Se cache hit, retorna imediatamente
    3. Se cache miss, query PostgreSQL
    4. Salva resultado em Redis com TTL
    5. Retorna histórico
    
    Args:
        conversation_id: ID da conversa
        db: Sessão do banco
        limit: Máx mensagens (padrão: 5)
        use_cache: Usar Redis cache (padrão: True)
    
    Returns:
        [{"role": "user"|"assistant", "content": "text"}, ...]
    """
```

#### 2. cache_conversation()
Cachear manualmente histórico após nova mensagem.

```python
history = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi!"}
]
await memory_service.cache_conversation("conv-123", history)
# Salva em Redis com TTL = 3600s
```

#### 3. invalidate_cache()
Limpar cache de conversa específica.

```python
await memory_service.invalidate_cache("conv-123")
# Deleta chave: conv_history:conv-123 do Redis
# Próxima get_conversation_history() fará query no DB
```

#### 4. clear_expired_conversations()
Executar periodicamente para limpar conversas antigas.

```python
cleared = await memory_service.clear_expired_conversations(
    db=db_session,
    max_age_days=30  # Limpa conversas > 30 dias
)
print(f"Limpas {cleared} conversas do cache")
```

---

## ⚙️ Configuração

### Variáveis de Ambiente

```bash
# .env
REDIS_URL=redis://localhost:6379
REDIS_CACHE_TTL=3600  # 1 hora (em segundos)
```

### config.py

```python
class Settings(BaseSettings):
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_cache_ttl: int = int(os.getenv("REDIS_CACHE_TTL", "3600"))
```

### Inicialização

O MemoryService é inicializado automaticamente:

```python
from app.services.memory_service import memory_service

# Já está pronto para usar
```

---

## 🔄 Integração com LLM Service

O llm_service.py agora usa memory_service automaticamente:

```python
# Antes (Fase 4): Query direta ao DB
async def get_conversation_history(
    conversation_id: str,
    db: AsyncSession,
    limit: int = 10,
) -> List[dict]:
    # ... query direto ao DB

# Depois (Fase 6): Via memory_service com cache
async def get_conversation_history(
    conversation_id: str,
    db: AsyncSession,
    limit: int = 10,
    use_cache: bool = True,
) -> List[dict]:
    return await memory_service.get_conversation_history(
        conversation_id, db, limit=limit, use_cache=use_cache
    )
```

### Uso no Orquestrador

```python
from app.services.message_orchestrator import orchestrator

# Automaticamente usa cache
history = await llm_service.get_conversation_history(
    conversation_id=conv.id,
    db=db,
    limit=5,
    use_cache=True  # ← Nova opção
)

response, tokens = await llm_service.generate_response(
    agent=agent,
    user_message=message_text,
    conversation_history=history  # ← Com cache otimizado
)
```

---

## 📊 Cache Key Format

Formato da chave Redis:

```
conv_history:{conversation_id}

Exemplos:
- conv_history:conv-123
- conv_history:a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6
```

Estrutura do valor (JSON):

```json
[
  {
    "role": "user",
    "content": "Olá, gostaria de saber sobre seus produtos"
  },
  {
    "role": "assistant",
    "content": "Olá! Somos uma plataforma SaaS para agentes IA..."
  }
]
```

---

## 🧪 Testes

### Executar Testes de Memory Service

```bash
# Todos os testes
docker-compose exec backend pytest tests/test_memory_service.py -v

# Teste específico
docker-compose exec backend pytest tests/test_memory_service.py::TestMemoryServiceCacheHitMiss::test_cache_hit_returns_cached_data -v

# Com cobertura
docker-compose exec backend pytest tests/test_memory_service.py --cov=app.services --cov-report=html
```

### Cobertura de Testes

14 testes implementados:

**TestMemoryServiceCacheHitMiss** (3 testes)
- ✅ Cache hit retorna dados sem query DB
- ✅ Cache miss faz query no DB e cachea
- ✅ use_cache=False sempre query DB

**TestMemoryServiceCacheInvalidation** (3 testes)
- ✅ invalidate_cache remove entrada Redis
- ✅ invalidate_cache retorna False se não existe
- ✅ Invalidação após nova mensagem

**TestMemoryServiceManualCaching** (2 testes)
- ✅ Manual cache_conversation funciona
- ✅ Erro em cache retorna False

**TestMemoryServiceExpiredConversations** (2 testes)
- ✅ clear_expired_conversations limpa old convs
- ✅ Sem conversas antigas = cleared=0

**TestMemoryServiceEmptyHistory** (1 teste)
- ✅ Conversa vazia retorna []

**TestMemoryServiceMessageOrder** (1 teste)
- ✅ Mensagens retornadas em ordem cronológica

**TestMemoryServiceIntegration** (2 testes)
- ✅ Ciclo completo: miss → hit → invalidate → miss
- ✅ Contagem de calls DB validada

---

## 🚀 Scripts Launcher

Fase 6 inclui scripts cross-platform para iniciar a aplicação.

### Windows (run.bat)

```bash
# Iniciar com docker-compose
run.bat

# Ver logs
run.bat logs

# Parar serviços
run.bat stop

# Limpar volumes (reset completo)
run.bat clean
```

Funcionalidades:
- Valida Docker e docker-compose
- Inicia serviços (PostgreSQL, Redis, Backend)
- Health check automático
- Abre browser em http://localhost:8000/docs
- Mostra logs em tempo real

### Linux/Mac (run.sh)

```bash
# Tornar executável
chmod +x run.sh

# Iniciar
./run.sh

# Ver logs
./run.sh logs

# Parar serviços
./run.sh stop

# Limpar volumes
./run.sh clean
```

Mesmas funcionalidades do run.bat, otimizado para Unix.

---

## 🔧 Setup Inicial

### Windows

```bash
# 1. Setup inicial
setup.bat

# 2. Editar .env com suas chaves API
notepad .env

# 3. Iniciar
run.bat
```

### Linux/Mac

```bash
# 1. Setup inicial
chmod +x setup.sh
./setup.sh

# 2. Editar .env com suas chaves API
nano .env

# 3. Iniciar
chmod +x run.sh
./run.sh
```

---

## 📈 Performance

### Cache Hit vs Database Query

```
Latência típica:

Redis Cache (Hit):
- Deserialização JSON: ~0.5ms
- Redis get: ~0.5ms
- Total: ~1ms
- Redução: 99% mais rápido

PostgreSQL Query:
- Conexão: ~10ms
- Query: ~50-100ms
- Formatação: ~10ms
- Total: ~100ms

Economia:
- 100x mais rápido com cache
- Reduz carga DB em ~90%
```

### Recomendações

1. **TTL padrão (3600s = 1 hora)**
   - Bom para conversas ativas
   - Reduz custo de DB queries

2. **Para conversas de longa duração**
   - Aumentar TTL em config.py
   - Exemplo: 7200 (2 horas) ou 86400 (1 dia)

3. **Para dados críticos atualizados frequentemente**
   - Usar use_cache=False em get_conversation_history()
   - Força query ao DB sempre

---

## 🐛 Troubleshooting

### "Cache miss always returns to DB"

**Problema:** Cache não está funcionando, sempre query DB

**Solução:**
```python
# Verificar Redis conectado
docker-compose exec redis redis-cli ping
# Deve retornar: PONG

# Verificar variável de ambiente
grep REDIS_URL .env
# Deve ter: REDIS_URL=redis://redis:6379
```

### "Redis connection refused"

**Problema:** Memory service não consegue conectar Redis

**Solução:**
```bash
# Reiniciar Redis
docker-compose restart redis

# Verificar logs
docker-compose logs redis

# Verificar porta
docker-compose ps redis
# Deve estar UP na porta 6379
```

### "Cache não invalida após nova mensagem"

**Problema:** Histórico antigo é retornado mesmo após nova mensagem

**Solução:**
Após salvar nova mensagem, chamar invalidate_cache:

```python
# Em message_orchestrator.py após db.commit()
await memory_service.invalidate_cache(conversation.id)

# Próxima get_conversation_history() fará query novo
```

### "Memória Redis crescendo demais"

**Problema:** Redis ocupando muita memória

**Solução:**
1. Aumentar frequência de limpeza de conversas expiradas
2. Reduzir TTL em .env:
   ```
   REDIS_CACHE_TTL=1800  # 30 minutos ao invés de 1 hora
   ```
3. Executar cleanup manual:
   ```python
   cleared = await memory_service.clear_expired_conversations(
       db=db_session,
       max_age_days=7  # Limpa conversas > 7 dias
   )
   ```

---

## 📚 Logs Esperados

```
[INFO] 🚀 Starting L'Aquila AI Backend (FastAPI)
[INFO] ✅ Database initialized successfully
[DEBUG] 📦 Cache hit for conversation conv-123 (size: 5 messages)
[DEBUG] 📝 Fetching history from DB for conv-456
[DEBUG] 🗑️ Invalidated cache for conv-123
[INFO] 🧹 Cleared 23 expired conversation caches
[DEBUG] 📊 Usage tracked: 12 calls, 4850 tokens in last minute
```

---

## 🔐 Segurança

### Cache Invalidation

O cache é automaticamente invalidado:
1. Após TTL expirar (padrão: 1 hora)
2. Quando invalidate_cache() é chamado
3. Quando clear_expired_conversations() executa

### Dados em Cache

Nenhum dado sensível é armazenado além do histórico de conversas.

---

## 📊 Monitoramento

### Verificar Estado do Cache

```bash
# Conectar ao Redis
docker-compose exec redis redis-cli

# Listar todas as chaves de cache
KEYS conv_history:*

# Ver conteúdo de uma conversa
GET conv_history:conv-123

# Ver TTL de uma chave
TTL conv_history:conv-123
# Retorna segundos até expiração
```

### Métricas

```python
# Em um endpoint de metrics (Fase 9)
redis_info = await redis_client.info()
cache_memory_mb = redis_info.get("used_memory_mb", 0)
cache_keys = len(await redis_client.keys("conv_history:*"))

return {
    "cache_memory_mb": cache_memory_mb,
    "cache_keys": cache_keys,
    "cache_hit_rate": calculate_hit_rate()
}
```

---

## 🚀 Próximas Fases

### Fase 7: Lead Processing
- Parser JSON de respostas Claude
- Extração de dados de qualificação
- Atualização automática em Kanban

### Fase 8: Kanban CRM Backend
- CRUD de leads
- Movimentação entre colunas
- Timeline de mudanças

### Fase 9: Dashboard de Métricas
- Endpoints para dados de gráficos
- Agregações de uso
- KPIs de performance

---

## 📈 Changelog

### v0.6.0 (Fase 6)
- ✅ Memory Service com Redis cache
- ✅ get_conversation_history() com cache
- ✅ invalidate_cache() e clear_expired_conversations()
- ✅ 14 testes de cache, TTL, invalidação
- ✅ Scripts launcher (run.bat, run.sh)
- ✅ Setup scripts (setup.bat, setup.sh)
- ✅ .env.example atualizado com 40+ variáveis documentadas
- ✅ Integração com llm_service.py

---

**Última Atualização:** 2026-08-11  
**Status:** Fase 6 - Memory Service Avançado ✅

