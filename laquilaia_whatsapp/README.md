# L'Aquila AI - WhatsApp Clone Platform

Uma plataforma SaaS omnichannel para gerenciamento de agentes virtuais inteligentes no WhatsApp com qualificação automática de leads, CRM integrado (Kanban) e dashboards de desempenho.

## 🎯 Stack Tecnológico

- **Frontend:** React/Next.js 14 + TypeScript + TailwindCSS + shadcn/ui
- **Backend:** Python + FastAPI + AsyncIO
- **Database:** PostgreSQL 16 + Redis 7
- **LLM:** Claude 3.5 Sonnet (Anthropic)
- **WhatsApp Gateway:** Evolution API
- **Autenticação:** JWT (PyJWT)
- **Deploy:** Docker Compose

## 📋 Pré-requisitos

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- npm ou yarn
- Chave API Anthropic (para Claude)

## 🚀 Quick Start

### Opção 1: Scripts Launcher (Recomendado)

#### Windows
```bash
cd laquilaia_whatsapp

# Setup inicial (criar .env)
setup.bat

# Editar .env com suas chaves API
notepad .env

# Iniciar todos os serviços
run.bat

# Outros comandos
run.bat logs    # Ver logs em tempo real
run.bat stop    # Parar serviços
run.bat clean   # Resetar volumes Docker
```

#### Linux/Mac
```bash
cd laquilaia_whatsapp

# Tornar scripts executáveis
chmod +x setup.sh run.sh

# Setup inicial (criar .env)
./setup.sh

# Editar .env com suas chaves API
nano .env

# Iniciar todos os serviços
./run.sh

# Outros comandos
./run.sh logs   # Ver logs em tempo real
./run.sh stop   # Parar serviços
./run.sh clean  # Resetar volumes Docker
```

### Opção 2: Docker Compose Manual

```bash
cd laquilaia_whatsapp

# 1. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas chaves API

# 2. Inicie os serviços
docker-compose up -d

# 3. Verifique a saúde
curl http://localhost:8000/health

# 4. Acesse documentação
# Abra: http://localhost:8000/docs
```

### Configuração de Variáveis de Ambiente

Edite o arquivo `.env`:

```env
# Database (PostgreSQL)
DATABASE_URL=postgresql://laquilaia:laquilaia_dev_pwd@postgres:5432/laquilaia_db

# Redis Cache (com TTL para Memory Service)
REDIS_URL=redis://redis:6379
REDIS_CACHE_TTL=3600  # 1 hora

# Security
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256

# AI/LLM (Claude)
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key
CLAUDE_MODEL=claude-3-5-sonnet-20241022
TEMPERATURE=0.7
MAX_TOKENS=1024

# Rate Limiting
LLM_MAX_CALLS_PER_MINUTE=60
LLM_MAX_TOKENS_PER_MINUTE=40000

# WhatsApp/Evolution
EVOLUTION_API_KEY=your-evolution-api-key
EVOLUTION_INSTANCE_NAME=laquilaia
EVOLUTION_WEBHOOK_URL=http://localhost:8000/api/v1/webhook/messages

# Frontend
FRONTEND_URL=http://localhost:3000
```

### Serviços Iniciados

```
PostgreSQL:     localhost:5432
Redis:          localhost:6379
FastAPI:        http://localhost:8000
Documentation:  http://localhost:8000/docs
```

## 📁 Estrutura do Projeto

```
laquilaia_whatsapp/
├── backend/                          # FastAPI + Python
│   ├── app/
│   │   ├── main.py                   # Entrada FastAPI
│   │   ├── config.py                 # Configuração
│   │   ├── models/                   # Pydantic models
│   │   ├── schemas/                  # Prisma schema + DB models
│   │   ├── routers/                  # Rotas (auth, agents, etc)
│   │   ├── services/                 # Lógica de negócio
│   │   ├── db/                       # Database e Redis
│   │   └── utils/                    # Logger, exceptions, validators
│   ├── tests/                        # Testes unitários
│   ├── requirements.txt              # Dependências Python
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                         # Next.js + React (TODO: Fase 10+)
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── hooks/
│   └── package.json
│
├── docker-compose.yml                # Orquestração local
├── .env.example                      # Template de variáveis
└── README.md                         # Este arquivo
```

## 🔄 Fluxo de Desenvolvimento por Fase

### Fase 1: ✅ Infraestrutura & DB (COMPLETA)
- [x] Estrutura de pastas e Docker Compose
- [x] PostgreSQL + Redis setup
- [x] FastAPI com logging e CORS
- [x] Schema com 11+ tabelas (SQLAlchemy)
- [x] Configuração de ambiente

### Fase 2: ✅ Autenticação & Segurança (COMPLETA)
- [x] Modelo User com bcrypt
- [x] Endpoints: `/auth/register`, `/auth/login`, `/auth/refresh`
- [x] Middleware JWT com validação
- [x] 22+ testes de autenticação

### Fase 3: ✅ CRUD de Agentes (COMPLETA)
- [x] Rotas: GET/POST/PUT/DELETE `/agents`
- [x] Modelo Agent com system_prompt e variáveis
- [x] 32+ testes de agentes
- [x] Ownership validation

### Fase 4: ✅ Integração Claude LLM (COMPLETA)
- [x] LLMService com Anthropic SDK
- [x] generate_response() com contexto
- [x] Streaming de respostas
- [x] Token counting e rate limiting
- [x] 31+ testes de LLM
- [x] Documentação: GUIA_LLM.md

### Fase 5: ✅ Webhook WhatsApp (COMPLETA)
- [x] Endpoint `/api/v1/webhook/messages`
- [x] Orquestrador de fluxo end-to-end
- [x] WhatsAppService (Evolution API)
- [x] Suporte a conversas + histórico
- [x] 16+ testes de webhook
- [x] Documentação: GUIA_WEBHOOK.md

### Fase 6: ✅ Memory Service + Launcher Scripts (COMPLETA)
- [x] MemoryService: histórico da conversa em ordem cronológica
- [x] get_conversation_history(), lendo do banco a cada turno
- [x] Cache Redis **removido**: guardava o histórico por uma hora sem
      invalidar na escrita, e o agente reperguntava o que já sabia
      (ver `GUIA_MEMORY_SERVICE.md` §3)
- [x] Teste de dois turnos pelo orquestrador, que é o que o cache quebrava
- [x] Scripts launcher: run.bat, run.sh
- [x] Scripts setup: setup.bat, setup.sh
- [x] .env.example com 40+ variáveis documentadas
- [x] Documentação: GUIA_MEMORY_SERVICE.md

### Fase 7: ✅ Lead Processing com Function Calling (COMPLETA)
- [x] LeadProcessor com extração de JSON
- [x] Validação de schema de qualificação
- [x] Criação automática de Lead no DB
- [x] Rastreamento em LeadTimeline
- [x] Movimentação automática em Kanban
- [x] 20+ testes de qualificação
- [x] Integração no Message Orchestrator
- [x] Documentação: GUIA_LEAD_PROCESSING.md

### Fase 8: ✅ Kanban CRM Backend (COMPLETA)
- [x] CRUD completo de leads via Kanban
- [x] 5 endpoints REST (board, move, columns, init, stats)
- [x] 5 colunas padrão (Novo, Qualificação, Qualificado, Agendado, Arquivado)
- [x] Movimentação entre colunas com atualização de status
- [x] Timeline de mudanças para auditoria
- [x] Estatísticas e métricas por coluna
- [x] 15+ testes de board e movimentação
- [x] Documentação: GUIA_KANBAN.md

**Próximo:** Fase 9 - Dashboard de Métricas

### Fase 9: Dashboard de Métricas (TODO)
- [ ] Endpoints para gráficos
- [ ] Taxa de qualificação por período
- [ ] Tempo médio no funnel
- [ ] KPIs de performance

**... (Fases 10-17: Frontend, WebSocket, Deploy)**

## 🧪 Testes

### Rodar Testes do Backend

```bash
docker-compose exec backend pytest -v
```

### Rodar com Cobertura

```bash
docker-compose exec backend pytest --cov=app tests/
```

## 📊 API Endpoints (Fase 1 - Stub)

### Health & Status
- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc documentation

### WebSocket (Live Updates)
- `WS /ws/{conversation_id}` - Real-time updates para conversas

### Stubs (Implementação Completa em Fases 2+)
- `GET /api/v1/agents` - Listar agentes
- `POST /api/v1/agents` - Criar agente
- `POST /webhook/whatsapp` - Webhook Evolution API

## 🔐 Segurança

- Senhas hashidas com bcrypt
- JWT para autenticação stateless
- CORS configurado para frontend
- Rate limiting (implementar em Fase 5)
- Validação de entrada com Pydantic
- Logging de segurança
- HTTPS recomendado para produção

## 📝 Logs

Logs são salvos em:
- `logs/app.log` - Todos os eventos
- `logs/error.log` - Apenas erros

Acesse os logs:
```bash
docker-compose logs -f backend
```

## 🐛 Troubleshooting

### PostgreSQL não conecta
```bash
docker-compose down -v  # Remove volumes
docker-compose up -d
```

### Redis não conecta
```bash
docker-compose logs redis
docker-compose restart redis
```

### Porta já em uso
```bash
# Mude a porta em docker-compose.yml
# ou libere a porta:
lsof -i :8000  # Encontre o processo
kill -9 <PID>  # Termine o processo
```

## 📚 Documentação

### Guias Principais (Fases 4-8)
- **GUIA_LLM.md** - Integração Claude LLM & Chat Endpoints (Fase 4)
- **GUIA_WEBHOOK.md** - Integração Evolution API & Webhook WhatsApp (Fase 5)
- **GUIA_MEMORY_SERVICE.md** - Memory Service & Cache Redis (Fase 6)
- **GUIA_LEAD_PROCESSING.md** - Qualificação de Leads com JSON (Fase 7)
- **GUIA_KANBAN.md** - CRM Kanban com Drag-and-Drop Backend (Fase 8)

### Referência Técnica
- **Plano Geral:** Ver `/root/.claude/plans/preciso-que-me-explique-deep-duckling.md`
- **Schema do DB:** `backend/app/schemas/schema.prisma`
- **Configuração:** `backend/app/config.py`
- **Docker:** `docker-compose.yml`

## 🚢 Deploy para Produção

(Implementar em Fase 17)

```bash
# Build imagens
docker build -t laquilaia-backend:1.0 ./backend
docker build -t laquilaia-frontend:1.0 ./frontend

# Push para registry
docker push your-registry/laquilaia-backend:1.0
docker push your-registry/laquilaia-frontend:1.0

# Deploy em K8s, Docker Swarm, ou Heroku
```

## 👥 Contribuição

Trabalhe sempre em branches feature:
```bash
git checkout -b feature/sua-feature
git commit -m "feat: descrição"
git push origin feature/sua-feature
```

## 📄 Licença

Proprietário - Não distribuir sem permissão.

## 📧 Contato

Para dúvidas, contate: tassiosales@example.com

---

**Status do Projeto:** Em Desenvolvimento (Fase 1/17 ✅)  
**Última Atualização:** 2026-08-10
