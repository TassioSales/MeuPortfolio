# Guia de Testes

Como rodar a suíte e o que foi corrigido quando ela passou a rodar pela primeira vez.

---

## 1. Rodando

### Backend (155 testes)

Precisa de PostgreSQL. Com Docker:

```bash
docker compose up -d postgres
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/ -v
```

Com PostgreSQL local (sem Docker):

```bash
createdb laquilaia_test_db
cd backend && .venv/bin/python -m pytest tests/ -v
```

O `conftest.py` aponta para `laquilaia_test_db` e recria o schema a cada
sessão — os dados de desenvolvimento não são tocados. Para usar outro banco:

```bash
DATABASE_URL=postgresql://user:senha@host:5432/outro_db pytest tests/
```

### Frontend (46 testes)

```bash
cd frontend
npm ci
npm test          # jest
npm run typecheck # tsc --noEmit
npm run build     # build de produção
```

### CI

`.github/workflows/laquilaia-ci.yml` (na **raiz** do repositório — workflows em
subpastas não são executados pelo GitHub) roda os dois jobs a cada push ou PR
que toque `laquilaia_whatsapp/**`. O job do backend sobe um serviço PostgreSQL.

---

## 2. Decisões do ambiente de teste

**Banco separado.** `laquilaia_test_db`, com o schema recriado por sessão e as
tabelas esvaziadas a cada teste.

**Limpeza no teardown, não no setup.** O `setup_method` das classes de teste
roda *antes* das fixtures de função, então limpar no setup não adiantaria.

**`DEBUG=true` nos testes** para o engine usar `NullPool`. Com pool, as conexões
asyncpg ficam presas ao event loop que as abriu e o `TestClient` cria um loop
por request — reusar a conexão estoura `attached to a different loop`.

**Isolamento importa.** Vários testes passavam sozinhos e falhavam na suíte
completa, porque um e-mail cadastrado por um teste fazia o cadastro de outro
devolver 400.

---

## 3. Bugs encontrados quando a suíte rodou

A suíte existia desde a Fase 1 mas nunca havia sido executada. Na primeira
execução, o backend não subia — os quatro primeiros itens abaixo impediam até
a importação dos módulos.

### Impediam o backend de iniciar

| # | Onde | Problema |
|---|---|---|
| 1 | `requirements.txt` | `asyncpg` ausente, mas `database.py` usa `create_async_engine` |
| 2 | `requirements.txt` | `email-validator` ausente, exigido pelo tipo `EmailStr` |
| 3 | `db/models.py` | Colunas chamadas `metadata`, nome reservado pelo Declarative API |
| 4 | `models/schemas.py` | `Field(regex=...)` é API do Pydantic v1; o projeto usa v2 |
| 5 | `utils/auth_middleware.py` | `HTTPAuthCredentials` não existe — o nome é `HTTPAuthorizationCredentials` |

O item 5 quebrava o middleware usado por **todas** as rotas protegidas.

### Quebravam funcionalidades em produção

| # | Onde | Problema |
|---|---|---|
| 6 | `db/database.py` | `conn.execute("SELECT 1")` com string crua — o SQLAlchemy 2.x exige `text()`, então `init_db()` falharia no startup |
| 7 | `db/database.py` | `NullPool` junto com `pool_size`/`max_overflow` estoura `TypeError` com `DEBUG=true` |
| 8 | `db/database.py` | `init_db()` só testava conexão; nada criava as tabelas (não há migrações Alembic) |
| 9 | `services/message_orchestrator.py` | `Conversation(data_criacao=...)` — o campo é `data_inicio`. **Toda mensagem recebida do WhatsApp falhava** |
| 10 | `models/webhook_models.py` | `key`/`message`/`owner` obrigatórios faziam eventos legítimos da Evolution API (`connection.update`) receberem 422 em vez de serem ignorados |
| 11 | `routers/webhook.py` | O handler lia campos de mensagem antes de checar o tipo do evento |
| 12 | `services/metrics_service.py` | `_generate_cache_key(..., limit)` passava `limit` na posição de `custom_range`, e o código tentava desempacotar um int. **A análise de problemas nunca funcionou** |
| 13 | `services/lead_processor.py` | O default `em_qualificacao` não constava na lista de status válidos, rejeitando todo payload que omitisse `status_proposto` |
| 14 | `services/memory_service.py` | `cache_conversation` ignorava o retorno de `_save_to_cache` e reportava sucesso mesmo com a gravação falhando |
| 15 | `db/redis_client.py` | O wrapper não expunha `setex`, `keys` nem `delete` com múltiplas chaves, todos usados pelos serviços |
| 16 | `routers/*.py` (27 pontos) | `except Exception` capturava o `HTTPException` levantado no próprio `try` e o convertia em 500 — 404, 400 e 403 deliberados viravam erro de servidor |

O item 16 quebrava o contrato de erros que o frontend consome.

### Corrigidos antes (Fase 11)

| Onde | Problema |
|---|---|
| `routers/agents.py` | O parâmetro de query `status` sombreava o módulo `status` do FastAPI |

---

## 4. Problemas nos próprios testes

| Padrão | Problema |
|---|---|
| Mock de resultado | `AsyncMock()` tornava `result.scalars()` uma corrotina; no SQLAlchemy real é síncrono. Corrigido para `MagicMock()` |
| Ordem das mensagens | Mocks devolviam ordem cronológica, mas a query usa `ORDER BY timestamp DESC`. Agora ordenam como o banco ordenaria |
| Roteamento de mock | `if "KanbanColumn" in str(query)` — o SQL renderizado traz o nome da **tabela** (`kanban_columns`) |
| FK ausente | Testes inseriam `Agent` sem criar o `User` dono |
| Campo inexistente | `Conversation(data_criacao=...)` nos testes, espelhando o bug do código |
| SDK Anthropic | `APIConnectionError`/`APIError` construídos com assinatura de outra versão |
| Modelo fixo | Asserção comparava com a string literal do modelo; agora compara com `settings.claude_model` |

### Reescrita de `test_metrics_service.py`

Os 18 testes da Fase 9 mockavam a `AsyncSession` inteira. O serviço encadeia
várias queries com formatos de retorno diferentes (`scalar`, `first`, `all`), e
um mock único devolvia `MagicMock` onde o código esperava número — os testes
acabavam verificando apenas a presença de chaves no dicionário, sem exercitar
conta nenhuma.

Foram reescritos como testes de integração contra o banco real, conferindo os
números: taxa de qualificação de 2 em 4 leads é 50%, distribuição por status
bate com o que foi inserido, ranking de problemas ordena por frequência. Os
testes de cache seguem unitários com mock — ali o alvo é o Redis, não o SQL.

Foi essa reescrita que revelou o bug 12: com mocks, `get_problem_analysis`
"passava" sem nunca ter executado.

---

## 5. Pendências conhecidas

**SDK Anthropic desatualizado.** `anthropic==0.7.0` é bem antigo. O modelo
default foi atualizado para `claude-sonnet-5`, mas a atualização do SDK é
mudança maior e ficou de fora — os testes de tratamento de erro dependem das
assinaturas de exceção da versão atual.

**Sem migrações Alembic.** O schema nasce de `Base.metadata.create_all()`, que
cria o que falta mas não altera tabelas existentes. Mudanças de schema em um
banco com dados vão precisar de Alembic.

**WebSocket é um echo.** `main.py` devolve a mensagem recebida; a integração
real é a Fase 15.

**A stack completa nunca subiu junta.** Backend e frontend foram verificados
separadamente. Falta um teste com `docker compose up` de ponta a ponta.
