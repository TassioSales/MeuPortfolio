# CLAUDE.md — AdvogAi (WhatsApp)

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

Estado atual: **424 testes no backend, 173 no frontend.**

Os testes do limite de uso precisam do **Redis** (`redis-server` local ou
`docker compose up -d redis`). Sem ele eles se pulam, e a CI trata pulo como
falha — na CI o serviço existe, então um pulo significa conexão quebrada.

---

## 2. Estrutura

```
backend/app/
  routers/     auth, agents, chat (+conversations), webhook, kanban, metrics,
               whatsapp (estado da conexão e QR, só admin)
  services/    llm (+ gemini_client, reserva), legal_analyst (parecer interno,
               com jurisprudência, provas e porte econômico),
               caso_service (um contato, vários casos),
               rate_limiter, memory, whatsapp, lead_processor,
               message_orchestrator, metrics, agent, auth
  models/      schemas.py, llm_models.py, caso_schemas.py (o caso nas telas)
  prompts/     triagem_juridica.py — o texto que o cliente encontra, versionado
  scripts/     seed.py, aplicar_prompt.py (grava o prompt canônico num agente),
               sondar_evolution.py (prova o QR contra a Evolution de verdade)
  db/          models.py (SQLAlchemy), database.py, redis_client.py
  ws/          manager.py — canal de tempo real por agente
  jobs/        metrics_aggregator.py (APScheduler)
  utils/       auth_middleware, webhook_security, exceptions, logger
  alembic/     migrações — o schema é daqui, não da aplicação

frontend/
  app/dashboard/  agents · whatsapp (conexão) · conversations (pausa humana)
                  chat-test · kanban · metrics
  components/     + charts/ (theme.ts tem a paleta validada)
                  Logo · icons · SeletorDeTema · LeadDossie · ParecerPreliminar
  hooks/          useAuth, useAgents, useChat, useConversations, useKanban, useMetrics, useAgentEvents
  lib/            api.ts (refresh em 401), auth, agents, chat, conversations,
                  kanban, metrics, tokens, tema, telefone
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

**O caso é a unidade, não o contato.** `Lead` é quem manda mensagem; `Caso` é
o assunto que ela traz, e um contato pode ter mais de um — inclusive de
terceiro (o irmão que pergunta pelo divórcio da irmã). A área é o critério de
identidade do caso, porque é o que o sistema reconhece sozinho. O parecer
arquiva o caso pela `## Ficha`, que por isso é a **segunda** seção do prompt:
no fim da lista ela seria a primeira coisa perdida quando o modelo estoura o
teto de saída.

**O porte econômico etiqueta, não descarta.** O parecer estima uma faixa em
reais e a compara com `CASO_VALOR_MINIMO` (R$ 15.000 por padrão), sempre pelo
**piso** da faixa. `indeterminado` não é sinônimo de inviável: um pede
pergunta, o outro mandaria descartar. Nada disso mexe no funil — o veredito é
para o advogado discordar.

**Anexos: o agente decide, o webhook não.** Imagem, PDF e áudio entram sempre
na conversa; ler o arquivo é configuração por agente (`anexos_habilitados`,
desligada por padrão — cada anexo é uma chamada a mais à Evolution e tokens a
mais no modelo). Desligado, o agente pede que a pessoa escreva, em vez de
ignorar em silêncio. Áudio vai direto ao Gemini: a Anthropic não aceita áudio
de entrada.

**Papéis: admin configura, operador atende.** O cadastro público fecha no
primeiro usuário, que vira administrador — é o que resolve o bootstrap sem
script nem senha em variável de ambiente. Os demais acessos saem de
`POST /auth/users`, só para admin. Criar, editar e excluir agente, e o chat de
teste, exigem admin; listar continua liberado, porque a tela de atendimentos
tem uma aba por agente. O papel é lido do banco a cada requisição, não do
token: rebaixar alguém precisa valer na hora, não daqui a trinta minutos.

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

**Identidade: tinta e latão.** A moldura (lateral, telas de entrada) é
`ink`; o acento é `brass`, reservado à marca e ao item ativo da navegação — um
acento em tudo deixa de ser acento. As ações primárias são `ink-900`, não o
azul de antes. A escala `brand` continua onde estava porque é a cor dos dados:
gráficos e colunas do Kanban usam hexes que passaram pelo validador de
contraste e daltonismo, e moldura nova não é motivo para revalidar paleta de
dados. Ícones de navegação são SVG em `components/icons.tsx` — emoji é
desenhado pelo sistema, muda entre Windows e Mac e não herda a cor do texto.

**Tema: token, nunca cor literal.** `bg-surface`, `text-fg`, `text-fg-muted`
e afins saem de variáveis CSS que trocam com o tema (`globals.css`). Não escreva
`bg-white` nem `text-gray-900` em componente: com dois temas, cada literal
precisaria de um par `dark:` escrito à mão, e o que faltasse viraria texto
cinza-claro em cartão branco — o defeito que ninguém vê no tema em que
trabalha. O tema vem de uma classe no `<html>`, posta por um script inline
antes da primeira pintura; sem ele a página nasce clara e vira escura ao montar.

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
| Assumir o formato do payload sem ver um real | A Evolution v2 manda `messageType: "conversation"` (irmão de `message`, não filho) e o texto em `message.conversation` — não `textMessage`/`messageBody`. Toda mensagem real virava "[non-text message]" e era descartada com 200 |
| Cabeçalho customizado no webhook da Evolution | A v2.3.7 self-hosted **grava** e não envia. Só a query string chega |
| Deixar `WEBHOOK_GLOBAL_ENABLED=true` | O webhook global dispara antes do da instância e não repassa credencial nenhuma: 401 em tudo |
| Responder mensagem de grupo | O `@g.us` no remoteJid: sem filtro, o agente responde ao grupo inteiro e qualifica o grupo como lead |
| `textMessage` no envio da Evolution | É o nome da v1. A v2 responde `instance requires property "text"` e devolve 400 — depois de a chamada ao LLM já ter sido paga |
| Arrancar o DDI do número antes de enviar | O `remoteJid` chega com `55` e é o identificador do contato: sem ele a resposta vai para outra pessoa. E mutilava DDD 55 (Santa Maria/RS) |
| Middleware conferindo só o access token | Ele expira em 30 min e o cookie some: o middleware expulsava para o login com refresh válido por 7 dias, antes de o `api.ts` ter chance de renovar |
| Modelar a pessoa e o assunto na mesma tabela | `Lead` era contato **e** caso. Quebra no primeiro cliente que volta com outro assunto, e pior quando o assunto é de terceiro: o card fica com o nome de quem escreveu, não de quem é parte |
| Janela de contexto curta demais para o caso de uso | Com 5 mensagens, uma triagem perdia o relato antes de terminar, e quem voltava dias depois ouvia "seu caso é sobre o quê?" de novo. Contexto é decisão de produto, não default |
| Deixar o parecer interno chegar ao cliente | A análise jurídica é insumo do escritório: sai por rota autenticada, nunca pelo WhatsApp. O modelo já inventou um ajuizamento que não houve — texto assim na mão do cliente é dano, não ruído |
| Supor que o emissor do webhook assina o corpo | A Evolution API não calcula HMAC — só repassa cabeçalhos fixos. Com HMAC puro ela é recusada com 401 em toda mensagem; existe `WEBHOOK_STATIC_TOKEN` para isso |
| Esperar `agentId` no payload da Evolution | Ela não sabe que agentes existem. Sem `EVOLUTION_DEFAULT_AGENT_ID`, todo webhook real morre com "Missing agent_id" |
| Comparar segredo sem checar se está vazio | `"" == ""` autorizaria qualquer requisição sem cabeçalho |
| Variável do `.env` que o `Settings` não declara | O pydantic-settings v2 recusa o extra e o backend **não sobe**. Dez variáveis do `.env.example` faziam isso — mas só quando o processo enxergava o arquivo, o que depende do diretório de onde se sobe o uvicorn |
| `localhost` ou `127.0.0.1` na lista de CORS | Não são origens: o navegador manda `esquema://host:porta`. Abrir o painel por 127.0.0.1 dava CORS no login |
| Tocar relacionamento preguiçoso em contexto async | `lead.lead_details` e `lead.kanban_card` estouram `greenlet_spawn has not been called`. Busque por `select()` explícito. Isso bloqueava **toda** a qualificação de leads |
| Mock que responde ao atributo que o banco não responderia | O teste do `lead_details` passava justamente porque o mock devolvia o relacionamento sem IO — o defeito só apareceu com PostgreSQL de verdade |
| Recurso provisionado só por endpoint que ninguém chama | Agente criado pela tela nascia sem colunas de Kanban: o lead era qualificado e o card não tinha onde entrar |
| Mandar a resposta crua do modelo ao cliente | O bloco ```json de qualificação ia junto no WhatsApp — o cliente recebia o próprio score e as objeções detectadas |
| Mandar histórico no formato do Claude para o Gemini | Não dá erro: o papel é `model` e o texto vai em `parts`, então o turno é ignorado em silêncio e a resposta vem sem contexto |
| `maxOutputTokens` do Gemini sem folga | O raciocínio da série 3 sai do mesmo orçamento e não é desligável (`thinkingBudget: 0` dá 400). Com 100 tokens, 93 foram pensar e a frase saiu cortada |
| Ignorar `thoughtsTokenCount` | É cobrado e entra no total: o limitador contaria 5 onde a API cobrou 174 |
| Relançar o erro da reserva no lugar do erro do principal | "GEMINI_API_KEY inválida" quando a causa é um 529 da Anthropic manda investigar o lado errado |
| Mandar `temperature` para modelo novo | Sonnet 5, Opus 5 e Opus 4.7+ recusam parâmetro de amostragem com **400**. Com o default `claude-sonnet-5`, *nenhuma* chamada ao Claude podia dar certo. Ver `MODELOS_QUE_ACEITAM_TEMPERATURA` |
| Ler `response.content[0].text` | A resposta é lista de blocos **tipados**. O Opus 5 raciocina por padrão e manda um `ThinkingBlock` na frente, que não tem `.text`: `AttributeError` antes de qualquer resposta sair. Filtre por `type == "text"` — ver `texto_da_resposta()` |
| Qualificar o lead antes de responder ao cliente | A qualificação dispara o parecer jurídico, que é outra chamada ao modelo: **2 minutos** no Opus 5, medido. O cliente ficava esperando por um texto que ele nunca vai ler |
| Pôr a seção que classifica no fim do parecer | É a primeira coisa que se perde quando o modelo estoura o teto. O Opus 5 escreveu 19 mil caracteres, foi cortado, e devolveu análise excelente sem a `## Ficha` — caso que o sistema não consegue arquivar. Ordem por fragilidade, não por elegância |
| Coluna nova com default só do lado do Python | `default=` do SQLAlchemy vale para linha nova; as que já existem ficam `NULL`. Aí o painel tem dois jeitos de dizer a mesma coisa — `NULL` e `'indeterminado'` — que é como nasce um `if` errado. A migração precisa do `UPDATE` |
| Escopar recurso por `agent_id` que a tabela não tem | `Lead` não guarda `agent_id` — o vínculo passa pela conversa, e o telefone é único no sistema inteiro, não por agente. Filtrar o dossiê só por `Lead.id` daria o contato a quem tem o id |
| Semear `User` antes de `criar_acesso()` nos testes | O cadastro público fecha no primeiro usuário: o helper não acha administrador e recusa. Faça login primeiro, semeie depois — e semeie o agente sob o id de quem logou |
| Mapear papel do histórico por igualdade com `"assistant"` | Todo remetente que não fosse exatamente `assistant` virava `user`. Com a fala do operador no banco, o modelo leria a resposta do próprio escritório como pergunta e responderia a ela — o atendimento conversando sozinho. Cliente é `user`; **o resto** é o escritório |
| Coluna `NOT NULL` sem `server_default` na migração | O autogenerate não o põe. Em tabela com linhas, o ALTER falha: o Postgres não sabe o que escrever nas existentes |
| Descartar tipo de mensagem no webhook | Imagem e PDF eram descartados antes de qualquer decisão, e a mensagem sumia da conversa. Quem decide se o anexo é **lido** é o agente; o webhook só decide se ele **entra** |
| Folga fixa de raciocínio no Gemini | Os 1024 tokens serviam para um turno de WhatsApp. No parecer, o modelo gastou **3433 tokens só pensando** e o texto morreu no meio da lista de documentos. A folga tem que acompanhar o tamanho do pedido |

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

Em ordem de valor, e a primeira vale mais que as outras juntas.

1. **Nenhuma conversa real rodou com o prompt novo.** O prompt de triagem está
   em `app/prompts/triagem_juridica.py` e **não** foi aplicado ao agente que
   atende — o do banco ainda é o antigo. Aplique com
   `python -m scripts.aplicar_prompt --agente <id>` e converse pelo WhatsApp de
   verdade. Tudo o que veio depois dele (os números que dimensionam o caso, o
   porte econômico, o dossiê do card) é alimentado por essa conversa; se a
   triagem não coletar como se espera, o resto está resolvendo o problema
   errado.

2. **A tela de conexão existe, mas nunca falou com a Evolution de verdade.**
   `/dashboard/whatsapp` mostra estado e QR, e os testes usam transporte
   mockado — provam que **nós** lemos a resposta certa, não que a Evolution
   manda uma. Há um histórico de versões devolvendo `{"count": 0}` sem QR e sem
   erro (issues #2380 e #2385, nas 2.0.10 a 2.2.3; estamos na 2.3.7). Rode
   `python -m scripts.sondar_evolution` antes de confiar na tela.

4. **O áudio depende do Gemini.** A API da Anthropic não aceita áudio de
   entrada, então o roteamento manda áudio direto para a reserva. Sem
   `GEMINI_API_KEY`, áudio não é lido — o agente pede que a pessoa escreva.

5. **A stack em container nunca subiu.** Fora de container ela já rodou inteira
   (ver `GUIA_DEPLOY.md` §6), mas falta o `docker compose up`: os `Dockerfile`,
   o healthcheck do `depends_on` e a rede do compose seguem sem exercício.

6. **`stream_response` não tem consumidor.** Virou gerador assíncrono junto com
   o limitador, mas nenhum endpoint o usa — só os testes.

### O que foi conferido contra a API, e o que não foi

O Claude responde de verdade: `claude-sonnet-5` no atendimento e
`claude-opus-5` no parecer, os dois medidos. O parecer completo sai em ~5 mil
tokens de saída e ~90 segundos, custando cerca de US$ 0,14 por lead
qualificado. As citações do primeiro parecer real (Súmulas 32, 338 e 389 do
TST; arts. 482 "i", 477 §8º e 818, II da CLT) foram conferidas uma a uma.

O que **não** foi exercitado com chave real dos dois lados é a queda de
provedor: a passagem para o Gemini só rodou com `httpx.MockTransport`. E a
lista de modelos que aceitam `temperature` continua vindo da documentação, não
da Models API.

Atenção ao Gemini: `gemini-pro-latest` responde 429 com `limit: 0` na camada
gratuita — o modelo aparece em `/models` e não tem cota nenhuma sem faturamento
ativo.

### Do lado visual

Tema claro e escuro foram vistos no navegador em login, painel e agentes. **Não
foram vistos no escuro:** Kanban, Métricas e Atendimentos. Os gráficos são o
risco maior — a paleta deles foi validada para fundo claro. As tarjas coloridas
(verde de "ativo", âmbar do titular, vermelho de erro) continuam em tom claro
no escuro: pequenas e legíveis, mas não o ideal.

O contraste da paleta nova (`ink`/`brass`) foi escolhido a olho, diferente do
da paleta de dados, que passou pelo validador.

---

## 7. Convenções

- Comentários e mensagens de commit em **português**; nomes de código em inglês,
  exceto os campos que espelham a API.
- Comentário explica **por quê**, não o quê.
- Nada de `create_all` novo: mudança de schema passa por `alembic revision --autogenerate`,
  e a revisão gerada **deve ser lida** antes de aplicar (o autogenerate vê
  renomeação como drop + create).
- Ao entregar, dizer o que **não** foi verificado, não só o que passou.
