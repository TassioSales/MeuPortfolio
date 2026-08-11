# CLAUDE.md — L'Aquila AI (WhatsApp)

Orientações para trabalhar neste projeto. Leia antes de mexer no código.

Plataforma SaaS de agentes de IA no WhatsApp: qualificação automática de leads,
CRM Kanban e dashboard de métricas.

**Stack:** FastAPI + SQLAlchemy 2.x async + PostgreSQL + Redis + Anthropic SDK
(com Gemini de reserva) ·
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

Estado atual: **282 testes no backend, 117 no frontend.**

Os testes do limite de uso precisam do **Redis** (`redis-server` local ou
`docker compose up -d redis`). Sem ele eles se pulam, e a CI trata pulo como
falha — na CI o serviço existe, então um pulo significa conexão quebrada.

---

## 2. Estrutura

```
backend/app/
  routers/     auth, agents, chat (+conversations), webhook, kanban, metrics
  services/    llm (+ gemini_client, reserva), rate_limiter, memory, whatsapp,
               lead_processor, message_orchestrator, metrics, agent, auth
  db/          models.py (SQLAlchemy), database.py, redis_client.py
  ws/          manager.py — canal de tempo real por agente
  jobs/        metrics_aggregator.py (APScheduler)
  utils/       auth_middleware, webhook_security, exceptions, logger
  alembic/     migrações — o schema é daqui, não da aplicação

frontend/
  app/dashboard/  agents · conversations (pausa humana) · chat-test · kanban · metrics
  components/     + charts/ (theme.ts tem a paleta validada)
  hooks/          useAuth, useAgents, useChat, useConversations, useKanban, useMetrics, useAgentEvents
  lib/            api.ts (refresh em 401), auth, agents, chat, conversations, kanban, metrics, tokens
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
| Padrão de `.gitignore` sem barra inicial | `lib/` (do template Python) casa em qualquer profundidade e engoliu `frontend/lib/` inteiro — o clone limpo não tinha o cliente HTTP |
| E-mail de teste em `.local` ou `.test` | O seed grava direto pelo SQLAlchemy e aceita, mas o `EmailStr` recusa como TLD de uso especial: o usuário existe e não consegue logar (422) |
| `--locale=pt_BR.UTF-8` em imagem alpine | musl não traz locales além de C/C.UTF-8; o `initdb` morre e o healthcheck nunca passa |
| Variável no `.env` que o compose não repassa | O container não a enxerga e cai no default do `config.py` — foi o que deixou o webhook em 503 |
| Cliente de infra criado mas nunca conectado | `redis_client.connect()` não era chamado no lifespan: `self.redis` ficava `None`, todo cache estourava `AttributeError` e o `except` de cada método engolia. O Redis existia no compose e nunca foi usado |
| `aclose()` no redis-py 5.0.0 | Só existe a partir do 5.0.1. Dentro de um `except Exception` vira "Redis indisponível" e os testes se pulam em silêncio |
| Passar `user_id` opcional e esquecer de passá-lo | `get_rate_limit_status()` sem argumento lia o balde compartilhado e devolvia sempre zero |
| `docker compose` sem `.env` | Não falha: substitui cada `${VAR}` por string vazia e sobe uma stack sem chave de API nem segredo de webhook. O aviso passa despercebido no meio do log |
| Caractere não-ASCII em `.bat` | O `cmd.exe` lê em cp850, não em UTF-8: um travessão vira `ÔÇö` na tela |
| `)` sem `^` dentro de bloco `( )` no batch | Fecha o bloco antes da hora; o resto vira erro de sintaxe ou roda sem condição |
| `%errorlevel%` dentro de bloco `( )` | O bloco é expandido inteiro antes de executar: traz o valor de *antes* do comando. Use `!errorlevel!` com `enabledelayedexpansion` |
| `if cond set X=1 & shift` | O `&` separa a linha, não o `if`: o `shift` roda sempre. Quebrou `run.bat stop/logs/clean` |
| Checar o binário e não o daemon | `where docker` passa com o Docker Desktop fechado; o erro só aparece depois, disfarçado de falha ao baixar imagem |
| Tocar relacionamento preguiçoso em contexto async | `lead.lead_details` e `lead.kanban_card` estouram `greenlet_spawn has not been called`. Busque por `select()` explícito. Isso bloqueava **toda** a qualificação de leads |
| Mock que responde ao atributo que o banco não responderia | O teste do `lead_details` passava justamente porque o mock devolvia o relacionamento sem IO — o defeito só apareceu com PostgreSQL de verdade |
| Recurso provisionado só por endpoint que ninguém chama | Agente criado pela tela nascia sem colunas de Kanban: o lead era qualificado e o card não tinha onde entrar |
| Mandar a resposta crua do modelo ao cliente | O bloco ```json de qualificação ia junto no WhatsApp — o cliente recebia o próprio score e as objeções detectadas |
| Mandar histórico no formato do Claude para o Gemini | Não dá erro: o papel é `model` e o texto vai em `parts`, então o turno é ignorado em silêncio e a resposta vem sem contexto |
| `maxOutputTokens` do Gemini sem folga | O raciocínio da série 3 sai do mesmo orçamento e não é desligável (`thinkingBudget: 0` dá 400). Com 100 tokens, 93 foram pensar e a frase saiu cortada |
| Ignorar `thoughtsTokenCount` | É cobrado e entra no total: o limitador contaria 5 onde a API cobrou 174 |
| Relançar o erro da reserva no lugar do erro do principal | "GEMINI_API_KEY inválida" quando a causa é um 529 da Anthropic manda investigar o lado errado |
| Mandar `temperature` para modelo novo | Sonnet 5, Opus 5 e Opus 4.7+ recusam parâmetro de amostragem com **400**. Com o default `claude-sonnet-5`, *nenhuma* chamada ao Claude podia dar certo. Ver `MODELOS_QUE_ACEITAM_TEMPERATURA` |

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

1. **A stack em container nunca subiu.** Fora de container ela já rodou
   inteira (ver `GUIA_DEPLOY.md` §6), mas falta o `docker compose up`: os
   `Dockerfile`, o healthcheck do `depends_on` e a rede do compose seguem sem
   exercício.
2. **Nenhuma chamada real ao Claude.** O SDK está em `anthropic==0.121.0` e o
   corpo da requisição foi conferido com `httpx.MockTransport`, mas sem chave
   de verdade nada chegou à API. A lista de modelos que aceitam `temperature`
   veio da documentação, não da Models API.
3. **O operador não responde pelo painel.** Ele assume a conversa e a IA para,
   mas mandar a mensagem ao cliente ainda é fora do sistema — não há endpoint
   de envio avulso pela Evolution API.
4. **`stream_response` não tem consumidor.** Virou gerador assíncrono junto
   com o limitador, mas nenhum endpoint o usa — só os testes.

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
