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

### 1. Clone e Configure

```bash
cd laquilaia_whatsapp
cp .env.example .env
```

### 2. Configure as Variáveis de Ambiente

Edite o arquivo `.env`:

```env
# Database
DB_USER=laquilaia
DB_PASSWORD=laquilaia_dev_pwd
DB_NAME=laquilaia_db

# Redis
REDIS_URL=redis://redis:6379

# Security
SECRET_KEY=your-super-secret-key-change-in-production
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key

# AI/LLM
CLAUDE_MODEL=claude-3-5-sonnet-20241022
TEMPERATURE=0.7

# WhatsApp/Evolution
EVOLUTION_API_KEY=your-evolution-api-key
EVOLUTION_INSTANCE_NAME=laquilaia
```

### 3. Inicie os Serviços

```bash
docker-compose up -d
```

Isso iniciará:
- PostgreSQL em `localhost:5432`
- Redis em `localhost:6379`
- FastAPI Backend em `http://localhost:8000`

### 4. Verifique a Saúde

```bash
curl http://localhost:8000/health
```

Resposta esperada:
```json
{
  "status": "ok",
  "service": "laquilaia-backend",
  "version": "0.1.0"
}
```

### 5. Acesse a Documentação da API

Abra no navegador:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

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
- [x] Estrutura de pastas
- [x] Docker Compose (PostgreSQL + Redis)
- [x] FastAPI com logging e CORS
- [x] Schema Prisma (11 tabelas)
- [x] Configuração de ambiente
- [ ] Migrações Prisma executadas

**Próximo:** Fase 2 - Autenticação & Segurança

### Fase 2: Autenticação & Segurança (TODO)
- [ ] Modelo User com bcrypt
- [ ] Endpoints: `/auth/register`, `/auth/login`, `/auth/refresh`
- [ ] Middleware JWT
- [ ] Testes de autenticação

### Fase 3: CRUD de Agentes (TODO)
- [ ] Rotas: GET/POST/PUT/DELETE `/agents`
- [ ] Modelo Agent com system_prompt
- [ ] Testes

### Fase 4: Integração Claude (TODO)
- [ ] LLMService com Anthropic SDK
- [ ] Suporte a temperature, max_tokens
- [ ] Rate limiting
- [ ] Testes unitários

### Fase 5: Webhook WhatsApp (TODO)
- [ ] Endpoint `/webhook/whatsapp`
- [ ] Validação de assinatura Evolution
- [ ] Orquestrador de fluxo IA
- [ ] Testes

**... (Fases 6-17 seguem o plano)**

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

- **Plano Geral:** Ver `/root/.claude/plans/preciso-que-me-explique-deep-duckling.md`
- **Schema do DB:** `backend/app/schemas/schema.prisma`
- **Configuração:** `backend/app/config.py`

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
