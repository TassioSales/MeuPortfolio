# CLAUDE.md — L'Aquila AI (WhatsApp)

Orientações para trabalhar neste projeto. Leia antes de mexer no código.

Plataforma SaaS de agentes de IA no WhatsApp: qualificação automática de leads,
CRM Kanban e dashboard de métricas.

**Stack:** FastAPI + SQLAlchemy 2.x async + PostgreSQL + Redis + Anthropic SDK ·
Next.js 14 (App Router) + TypeScript + TailwindCSS + Zustand · Evolution API.

---

## 1. Rodar os testes

**Backend precisa de PostgreSQL e de um virtualenv.** Instalar no Python do
sistema falha por conflito com pacotes Debian:

```bash
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt
createdb laquilaia_test_db          # ou docker compose up -d postgres
.venv/bin/python -m pytest tests/ -q
```

O `conftest.py` aponta para `laquilaia_test_db`, recria o schema por sessão e
esvazia as tabelas entre testes. Também força `DEBUG=true`, o que faz o engine
usar `NullPool` — **necessário**: com pool, as conexões asyncpg ficam presas ao
event loop que as abriu e o `TestClient` cria um loop por request.

```bash
cd frontend && npm ci && npm test && npm run typecheck && npm run build
```

CI: `.github/workflows/laquilaia-ci.yml` **na raiz do repositório**. Workflow em
subpasta não é executado pelo GitHub — outros projetos deste portfólio têm
`ci.yml` dentro da própria pasta e por isso nunca rodaram.

Estado atual: **226 testes no backend, 101 no frontend.**

---

## 2. Estrutura

```
backend/app/
  routers/     auth, agents, chat (+conversations), webhook, kanban, metrics
  services/    llm, memory, whatsapp, lead_processor, message_orchestrator, metrics, agent, auth
  db/          models.py (SQLAlchemy), database.py, redis_client.py
  ws/          manager.py — canal de tempo real por agente
  jobs/        metrics_aggregator.py (APScheduler)
  utils/       auth_middleware, webhook_security, exceptions, logger
  alembic/     migrações — o schema é daqui, não da aplicação

frontend/
  app/dashboard/  agents · chat-test · kanban · metrics
  components/     + charts/ (theme.ts tem a paleta validada)
  hooks/          useAuth, useAgents, useChat, useKanban, useMetrics, useAgentEvents
  lib/            api.ts (refresh em 401), auth, agents, chat, kanban, metrics, tokens
  middleware.ts   proteção de rotas no edge
```

**Guias:** `GUIA_TESTES.md`, `GUIA_DEPLOY.md`, `GUIA_FRONTEND.md`, e um por
área do backend (LLM, webhook, memory, lead processing, Kanban, métricas).

---

## 3. Decisões já tomadas — não relitigar

**Autorização.** Todo endpoint que recebe `agent_id` exige token **e** escopa
pelo dono (`Agent.user_id == user_id`), respondendo **404, não 403**, para não
revelar que o agente existe. Vale também para o WebSocket, recusado antes do
`accept()`. `tests/test_authorization.py` cobre os 12 endpoints em três
cenários.

**Schema é do Alembic.** `init_db()` não cria tabelas. `create_all` cria o que
falta mas nunca altera tabela existente — mascararia migração pendente até uma
query quebrar em produção.

**Tokens em cookies, não localStorage.** O `middleware.ts` roda no servidor e só
enxerga cookies. Duas camadas: o middleware confere a *presença*; o
`DashboardLayout` valida via `GET /auth/me`.

**Estado local, não global, por agente.** `useChat` e `useKanban` guardam estado
na página (diferente de `useAgents`/`useAuth`, que usam Zustand). Store global
arriscaria vazar a conversa de um agente para a tela de outro. Os componentes
remontam com `key` ao trocar de agente.

**Eventos WebSocket são emitidos depois do commit**, e o de mensagem **não
carrega o conteúdo** — quem precisa dele busca pela API, que checa o dono.

**Gráficos:** as cores em `components/charts/theme.ts` passaram pelo validador
de paleta (luminosidade, croma, daltonismo, contraste) nos dois modos. Não troque
um hex sem revalidar o conjunto. Eixo Y de contagem trava em zero.

**`@dnd-kit`, não `react-beautiful-dnd`** (arquivado pela Atlassian, problemas
com StrictMode do React 18).

---

## 4. Armadilhas que já morderam

Estes bugs foram encontrados e corrigidos — não os reintroduza.

| Armadilha | O que acontece |
|---|---|
| `except Exception` sem `except HTTPException: raise` antes | Engole o 404/400 deliberado e devolve 500. Aconteceu em 27 pontos |
| Parâmetro de query chamado `status` | Sombreia o módulo `status` do FastAPI; use `alias="status"` |
| `AsyncMock()` para resultado de query | `result.scalars()` vira corrotina; no SQLAlchemy real é síncrono. Use `MagicMock()` |
| Mock de mensagens em ordem cronológica | As queries usam `ORDER BY timestamp DESC`; o mock precisa ordenar igual ao banco |
| `Conversation(data_criacao=...)` | O campo é `data_inicio` |
| Coluna chamada `metadata` | Reservado pelo Declarative API; use `Column("metadata", ...)` com outro nome de atributo |
| `Field(regex=...)` / `Query(regex=...)` | Removido no Pydantic v2; é `pattern` |
| Criar conversa de teste com telefone fixo | Há `UniqueConstraint(agent_id, phone_number)`; reaproveite |
| `Number("")` em campo numérico do formulário | Vira `0` e envia valor que o usuário não escolheu |
| Passar argumento posicional em `_generate_cache_key` | Cai no slot de `custom_range` e tenta desempacotar |

**Padrão geral:** as três falhas de autorização (Kanban, métricas, WebSocket)
só apareceram quando o cliente que consome o endpoint foi construído. Ao
adicionar endpoint, escreva o teste de acesso anônimo e cruzado junto.

---

## 5. Contrato com o frontend

Os campos ficam **em português** (`nome`, `senha`, `conteudo`) porque espelham
`backend/app/models/schemas.py`. `types/index.ts` é o espelho — mudar um lado
exige mudar o outro. O mesmo vale para os nomes de evento em `ws/manager.py` e
`hooks/useAgentEvents.ts`.

---

## 6. Pendências

1. **A stack completa nunca subiu junta** — não houve `docker compose up` de
   ponta a ponta. É o teste que mais falta.
2. **Tela da pausa humana** — os endpoints existem (`/api/v1/conversations/{id}/pause`),
   a IA respeita a pausa, mas não há UI.
3. **`anthropic==0.7.0`** desatualizado — atualizar quebra os testes de erro,
   que dependem das assinaturas de exceção da versão atual.
4. **Rate limiting é por conta, mas em memória** — com mais de uma réplica
   do backend cada uma tem seu próprio balde. Mover para o Redis resolveria.

`GUIA_DEPLOY.md` tem o checklist de produção completo.

---

## 7. Convenções

- Comentários e mensagens de commit em **português**; nomes de código em inglês,
  exceto os campos que espelham a API.
- Comentário explica **por quê**, não o quê.
- Nada de `create_all` novo: mudança de schema passa por `alembic revision --autogenerate`,
  e a revisão gerada **deve ser lida** antes de aplicar (o autogenerate vê
  renomeação como drop + create).
- Ao entregar, dizer o que **não** foi verificado, não só o que passou.
