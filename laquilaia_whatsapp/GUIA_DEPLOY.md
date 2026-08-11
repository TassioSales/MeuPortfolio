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
e-mail: demo@laquilaia.local
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
- [ ] Definir `WEBHOOK_SECRET` e configurar o mesmo valor na Evolution API
- [ ] Trocar os `Dockerfile` de desenvolvimento por builds de produção (o frontend usa `next dev`; produção quer `next build` + `next start`)

---

## 6. O que não foi verificado

**A stack completa nunca subiu junta.** Backend e frontend foram verificados
separadamente, e cada fase do frontend foi percorrida no Chromium contra um
backend simulado. Não houve um `docker compose up` de ponta a ponta — o
ambiente onde o projeto foi desenvolvido não tem Docker.

O que **foi** verificado de verdade:

| Item | Como |
|---|---|
| 208 testes do backend | PostgreSQL real, incluindo os de autorização |
| 101 testes do frontend | Jest, com typecheck e build de produção |
| Migração Alembic | Aplicada num banco limpo; `autogenerate` seguinte não detectou diferença, ou seja, cobre os models |
| Seed | Executado contra o banco migrado; login com o usuário criado confere |
| Fluxos da UI | Chromium contra backend simulado (agentes, chat, arrasto no Kanban, dashboard) |

O primeiro `docker compose up` numa máquina com Docker é o teste que falta.

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

**SDK Anthropic desatualizado.** `anthropic==0.7.0` é bem antigo. O modelo
default já é `claude-sonnet-5`, mas atualizar o SDK é mudança maior: os testes
de tratamento de erro dependem das assinaturas de exceção da versão atual.

**Fase 16 (pausa humana) não implementada.** Estava marcada como opcional no
plano — o operador ainda não consegue assumir uma conversa e pausar a IA.

**Sem rate limiting por usuário na API.** O `llm_service` limita chamadas ao
Claude no processo inteiro, não por conta.
