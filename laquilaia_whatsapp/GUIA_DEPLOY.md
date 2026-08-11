# Guia de Deploy — Fase 17

Como subir a stack, migrar o banco e popular dados de exemplo.

---

## 1. Subir tudo

```bash
cp .env.example .env       # preencha ANTHROPIC_API_KEY e SECRET_KEY
./run.sh                   # Windows: run.bat
```

O `run.sh` sobe PostgreSQL, Redis, backend e frontend, espera os dois
compilarem e abre `http://localhost:3000`.

| Serviço | Porta | Para quê |
|---|---|---|
| frontend | 3000 | Painel web |
| backend | 8000 | API + WebSocket (`/docs` traz o Swagger) |
| postgres | 5432 | Dados |
| redis | 6379 | Cache de métricas e histórico |

`./run.sh stop` derruba; `./run.sh clean` derruba e apaga os volumes.

---

## 2. Migrações

O schema é do **Alembic**, não da aplicação. O `docker-compose` roda
`alembic upgrade head` antes de iniciar o servidor, então em uso normal não há
passo manual.

```bash
cd backend
alembic upgrade head          # aplica o que falta
alembic current               # em que revisão o banco está
alembic history               # lista as revisões
alembic downgrade -1          # volta uma
```

Depois de mudar um model:

```bash
alembic revision --autogenerate -m "descrição da mudança"
# LEIA a revisão gerada antes de aplicar — o autogenerate erra em
# renomeações (vê como drop + create) e não detecta mudança de tipo servidor.
alembic upgrade head
```

> **Por que a aplicação não cria mais as tabelas.** Até a Fase 16, `init_db()`
> chamava `Base.metadata.create_all()`. Isso cria o que falta, mas **nunca
> altera tabela existente** — então uma coluna nova simplesmente não apareceria,
> e o erro só surgiria quando alguma query a usasse em produção. Com Alembic a
> migração pendente falha no boot, que é onde se quer descobrir.

A URL do banco vem de `DATABASE_URL` (ver `get_url()` em `alembic/env.py`), não
do `alembic.ini`: o `.ini` é versionado e a URL carrega senha.

---

## 3. Dados de exemplo

```bash
cd backend
python scripts/seed.py
```

Cria um usuário, um agente, 5 colunas de funil e 6 leads espalhados pelas
etapas e pelos últimos dias — o suficiente para o Kanban e os gráficos terem o
que mostrar sem uma instância do WhatsApp.

```
e-mail: demo@example.com
senha:  demo12345
```

É idempotente: rodar de novo não duplica. **Nunca rode em produção** — a senha
é pública.

---

## 4. Variáveis de ambiente

Documentadas em `.env.example`. As que precisam de atenção:

| Variável | Obrigatória | Nota |
|---|---|---|
| `SECRET_KEY` | **Sim** em produção | Assina os JWT. O default é de desenvolvimento e precisa ser trocado |
| `ANTHROPIC_API_KEY` | Sim | Sem ela o agente não responde |
| `DATABASE_URL` | Sim | Usada pela aplicação **e** pelo Alembic |
| `CLAUDE_MODEL` | Não | Default `claude-sonnet-5` |
| `EVOLUTION_API_KEY` | Só com WhatsApp | Integração da Evolution API |
| `WEBHOOK_SECRET` | **Sim** em produção | HMAC do webhook. Sem ele o endpoint recusa tudo quando `DEBUG=False` |
| `FRONTEND_URL` / `ALLOWED_ORIGINS` | Sim em produção | CORS |
| `NEXT_PUBLIC_API_URL` | Sim | Lida pelo **browser**, então é o endereço público da API, não o host interno do container |

---

## 5. Checklist de produção

Itens que o setup de desenvolvimento deixa em aberto:

- [ ] Trocar `SECRET_KEY` por um valor aleatório
- [ ] `DEBUG=False` (em `True` o engine usa `NullPool`, adequado a teste, não a carga)
- [ ] Restringir `ALLOWED_ORIGINS` ao domínio real
- [ ] HTTPS: os cookies de sessão só ganham a flag `secure` sob TLS
- [ ] Backup do PostgreSQL — não há rotina configurada
- [ ] Conferir `"redis": "ok"` em `GET /health`: sem Redis o serviço sobe, mas sem cache e com o limite de uso valendo por réplica
- [ ] Definir `WEBHOOK_SECRET` e configurar o mesmo valor na Evolution API
- [ ] Trocar os `Dockerfile` de desenvolvimento por builds de produção (o frontend usa `next dev`; produção quer `next build` + `next start`)

---

## 6. O que foi e o que não foi verificado

A stack **já subiu junta**, com backend, frontend, PostgreSQL 16 e Redis 7 ao
mesmo tempo, e o fluxo foi percorrido no Chromium contra o backend real. Isso
derrubou três bugs que a verificação em separado não pegava (o `lib/` fora do
repositório, o locale do initdb e o e-mail do seed).

Foi feito **fora de container**, com as versões que o compose declara e
injetando exatamente as variáveis que ele passa ao serviço `backend` — nada
além, para reproduzir o que o container enxerga.

| Item | Como |
|---|---|
| 253 testes do backend | PostgreSQL e Redis reais, incluindo os de autorização |
| 117 testes do frontend | Jest, com typecheck e `next build` de produção |
| Migração Alembic | Banco recriado do zero, `alembic upgrade head` limpo |
| Seed | Rodado sobre o banco migrado; o usuário criado entra pela tela de login |
| Boot do backend | Lifespan, conexão com o banco e com o Redis, scheduler de métricas |
| API | Auth, agentes, Kanban, 6 endpoints de métricas, chat, pausa humana |
| Autorização cruzada | Agente e conversa de outro dono respondem 404 |
| UI ponta a ponta | Login → dashboard → agentes, Kanban, métricas e playground, com dados do seed |
| Pausa humana pela tela | Assumir e devolver no painel, conferindo o `status` da conversa direto no PostgreSQL |
| WebSocket | Conecta e autentica: o Kanban mostra "atualizando em tempo real" |
| Limite de uso entre processos | Um processo separado registrou uso e o backend leu os mesmos números pelo endpoint |
| Queda e volta do Redis | Com o Redis parado o serviço segue respondendo, `/health` acusa `unavailable` e o log avisa; ao voltar, reconecta sem reiniciar |

### O que continua sem verificação

**A camada de container.** Não houve `docker compose up`: o ambiente usado
tinha Docker, mas a política de egress bloqueia o CDN de blobs do Docker Hub
(`production.cloudfront.docker.com` responde 403), então nenhuma imagem pôde
ser puxada. Segue em aberto, e com ele:

- os `Dockerfile` de fato construírem;
- o `depends_on: service_healthy` esperando o healthcheck de verdade;
- os bind mounts e o volume anônimo de `node_modules`;
- a resolução de `postgres`/`redis` por nome de serviço na rede do compose.

**A integração com a Evolution API e o Claude** — não houve chave real nem
instância de WhatsApp. O webhook foi exercitado apenas nas respostas de
recusa (401/503), não num fluxo de mensagem completo.

**O arrastar do Kanban** — a movimentação é coberta por teste na camada do
hook, mas o gesto com `@dnd-kit` não foi feito no browser.

---

## 7. Segurança do webhook

`POST /api/v1/webhook/messages` exige HMAC-SHA256 do corpo no cabeçalho
`x-hub-signature-256`, no formato `sha256=<hex>`, com a chave `WEBHOOK_SECRET`.

| Situação | Resposta |
|---|---|
| Assinatura correta | 200 |
| Assinatura ausente ou inválida | 401 |
| Corpo alterado após assinar | 401 |
| `WEBHOOK_SECRET` vazio e `DEBUG=False` | 503 |
| `WEBHOOK_SECRET` vazio e `DEBUG=True` | 200, com aviso no log |

A conferência é feita sobre o **corpo cru**, antes de qualquer parse: validar
depois do Pydantic deixaria requisição não assinada exercitar o parser, e o
HMAC é calculado sobre os bytes exatos que chegaram. A comparação usa
`hmac.compare_digest`, porque `==` sai no primeiro byte diferente e esse tempo
vaza quanto do prefixo estava certo.

Sem segredo configurado o endpoint fica aberto **apenas em `DEBUG=true`**. Em
produção ele recusa, para um deploy que esqueceu de definir a variável falhar
de forma visível em vez de aceitar tudo em silêncio.

`GET /api/v1/webhook/health` informa se a validação está ligada. Antes ele
chamava um stub que devolvia `True` sempre, então dizia "ok" mesmo sem
proteção nenhuma.

---

## 8. Pendências conhecidas

**Nenhuma chamada real ao Claude foi feita.** O SDK está em
`anthropic==0.121.0` e o corpo da requisição foi conferido byte a byte com
`httpx.MockTransport`, mas sem `ANTHROPIC_API_KEY` de verdade nada chegou à
API da Anthropic. A lista de modelos que aceitam `temperature`
(`MODELOS_QUE_ACEITAM_TEMPERATURA`, em `app/services/llm_service.py`) vem da
documentação, não de uma consulta à Models API — se o primeiro deploy com
chave devolver 400 de parâmetro, é ali que se ajusta.

**Pausa humana: a tela existe** em `/dashboard/conversations`. O operador vê a
fila de atendimentos, lê a conversa e assume; a IA para de responder e as
mensagens do cliente continuam sendo registradas.

| Endpoint | Método | Efeito |
|---|---|---|
| `/api/v1/agents/{id}/conversations` | GET | Fila de atendimentos, da mais recente para a mais antiga |
| `/api/v1/conversations/{id}/messages` | GET | Transcrição, com o estado da automação junto |
| `/api/v1/conversations/{id}/pause` | POST | Humano assume; a IA para de responder |
| `/api/v1/conversations/{id}/resume` | POST | Devolve a conversa à IA |
| `/api/v1/conversations/{id}/status` | GET | Se a IA está respondendo |

Os dois primeiros nasceram com a tela: os de pausa recebem um
`conversation_id` que o operador não tinha por onde descobrir, então eram
inalcançáveis pelo painel.

**O que a tela ainda não faz: responder ao cliente.** Assumir a conversa só
cala a IA — mandar a mensagem continua sendo fora do sistema, porque não há
endpoint de envio avulso pela Evolution API. É a continuação natural do
trabalho.

**`stream_response` sem consumidor.** Virou gerador assíncrono junto com o
limitador de uso, mas nenhum endpoint o chama — só os testes. Se o streaming
for para a interface, o caminho ainda precisa ser construído.
