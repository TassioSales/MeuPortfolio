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

Estado atual: **813 testes no backend, 329 no frontend.**

Os testes do limite de uso precisam do **Redis** (`redis-server` local ou
`docker compose up -d redis`). Sem ele eles se pulam, e a CI trata pulo como
falha — na CI o serviço existe, então um pulo significa conexão quebrada.

---

## 2. Estrutura

```
backend/app/
  routers/     auth, agents, chat (+conversations), webhook, kanban, metrics,
               whatsapp (estado da conexão e QR, só admin), contratos,
               assinatura (**público, sem autenticação** — ver §6d)
  services/    llm (+ gemini_client, reserva), legal_analyst (parecer interno,
               com jurisprudência, provas e porte econômico),
               caso_service (um contato, vários casos),
               contrato (lacunas → texto → PDF), assinatura (token e prova),
               cobranca (contrato enviado e não assinado),
               rate_limiter, memory, whatsapp, lead_processor,
               message_orchestrator, metrics, agent, auth
  models/      schemas.py, llm_models.py, caso_schemas.py (o caso nas telas)
  prompts/     triagem_juridica.py — o texto que o cliente encontra, versionado
               modelo_contrato_base.py — rascunho de contrato, sem o percentual
  scripts/     seed.py, aplicar_prompt.py (grava o prompt canônico num agente),
               semear_modelo_contrato.py (põe o rascunho no banco, inativo),
               sondar_evolution.py (prova o QR contra a Evolution de verdade)
  db/          models.py (SQLAlchemy), database.py, redis_client.py
  ws/          manager.py — canal de tempo real por agente
  jobs/        metrics_aggregator.py (APScheduler). O follow-up (5 min) e a
               cobrança de assinatura (15 min) são jobs separados no mesmo
               scheduler — um erro numa rodada de cobrança não pode levar
               junto a cutucada de conversa, que é a que traz cliente.
  utils/       auth_middleware, webhook_security, exceptions, logger, fuso
  alembic/     migrações — o schema é daqui, não da aplicação

frontend/
  app/dashboard/  agents · whatsapp (conexão) · conversations (pausa humana)
                  chat-test · kanban · metrics · contratos (modelos)
  app/assinar/    a página que o cliente abre — fora do painel, sem login
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

**Só trabalhista, e a agente informa.** O escritório atende exclusivamente
direito do trabalho: o menu de sete áreas saiu do prompt, e quem chega com
outro assunto é registrado como `nao_qualificado` e encaminhado a um humano —
não é dispensado na porta.

A regra sobre o que a agente pode dizer **mudou**, e é a decisão mais delicada
do projeto. A versão anterior proibia contar à pessoa o que estava em jogo; o
resultado era um atendimento que só perguntava, e o dono viu um concorrente
fazendo diferente. Agora a agente **informa, sempre atribuindo**: "em casos
assim entram vínculo, FGTS com multa e horas extras — quem confirma o seu, com
os documentos, é o advogado". A atribuição vai na mesma mensagem, não em
outra.

Continua proibido, sem exceção: prometer resultado, garantir ganho, cravar
valor de indenização (nem faixa) e **falar de honorários** — este último
porque é decisão comercial do escritório, não do prompt. Um percentual
inventado aqui vira compromisso assumido com o cliente.

**O porte econômico etiqueta, não descarta.** O parecer estima uma faixa em
reais e a compara com `CASO_VALOR_MINIMO` (R$ 15.000 por padrão), sempre pelo
**piso** da faixa. `indeterminado` não é sinônimo de inviável: um pede
pergunta, o outro mandaria descartar. Nada disso mexe no funil — o veredito é
para o advogado discordar.

**Anexos: o agente decide, o webhook não.** Imagem, PDF e áudio entram sempre
na conversa; ler o arquivo é configuração por agente (`anexos_habilitados`,
desligada por padrão — cada anexo é uma chamada a mais à Evolution e tokens a
mais no modelo). Desligado, o agente pede que a pessoa escreva, em vez de
ignorar em silêncio.

**Áudio é transcrito antes de qualquer coisa, e o texto vira a mensagem.**
Mandar o áudio como anexo da pergunta resolvia só o turno atual: o que ficava
gravado era "[o cliente enviou um áudio]", e o relato se perdia para o resto
do sistema — a memória lia a descrição no turno seguinte, e o parecer, que lê
a transcrição das mensagens, nunca via o que a pessoa contou. Quem transcreve
é o **Gemini**, e não há alternativa: a API da Anthropic não aceita áudio de
entrada, então sem `GEMINI_API_KEY` o agente pede que a pessoa escreva.

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
| Variável no `.env` que o compose não repassa | O container não a enxerga e cai no default do `config.py`, sem erro e sem aviso. Já mordeu **três vezes**: webhook em 503, modelo do parecer virando o do atendimento, e `WEBHOOK_STATIC_TOKEN` deixando o webhook aberto enquanto o `.env` dizia o contrário. `tests/test_compose_repassa_variaveis.py` trava isso |
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
| Número grande vindo do Baileys | A Evolution devolve `size` como `{"low": 6401, "high": 0, "unsigned": true}` — é assim que o JavaScript representa inteiro de 64 bits. Imprimir cru põe o dicionário no log no lugar do número, e conta sobre o valor estoura. Ver `_tamanho_em_bytes` |
| `npm run typecheck` com a saída cortada | `npm run typecheck \| tail -5` mostra só os avisos de versão do npm e **esconde os erros de TypeScript** — dois PRs foram para o `main` com o typecheck vermelho antes de alguém notar. A CI roda `typecheck` e `build`; filtre por `grep "error TS"`, não por `tail` |
| `matchAll` e flag `s` em regex, no frontend | O `target` do tsconfig é anterior a ES2018: os dois compilam no Jest e reprovam no `tsc`. Use `exec` em laço e `[\s\S]` |
| Consultar o banco dentro do laço dos cards | O board fazia `select(Lead)` e `select(LeadDetails)` **por card**: um funil com 150 leads numa coluna passava de trezentas idas ao banco, e cada card novo somava duas. Junte no `join` e agrupe em Python — `tests/test_kanban.py` conta as consultas |
| Tarefa de segundo plano que ninguém espera, em teste | A tarefa abre sessão própria; quando o loop do teste fecha com ela pendente, a transação continua aberta e o `TRUNCATE` do teardown fica esperando por ela — **a suíte inteira trava**, sem erro. Nos testes, ou se espera a tarefa (`asyncio.gather(*_TAREFAS)`) ou se troca `_agendar_analise` pelo mock |
| Campo sem classe de fundo | Sem `bg-`, o navegador pinta o campo com o padrão dele (branco) enquanto `text-fg` no escuro é claro: **texto claro em fundo branco**, e quem digita não lê o que escreve. Aconteceu no campo do chat de teste. `__tests__/tema-escuro.test.ts` trava a regra |
| Tom de escala própria que não existe | `brand` vai só até 900. `bg-brand-950` não gera classe nenhuma — o Tailwind ignora **em silêncio**, o fundo claro fica e o texto escuro vira claro por cima dele. O silêncio é o que torna isto perigoso |
| `HTTPBearer()` com o `auto_error` padrão | Requisição **sem** cabeçalho `Authorization` é recusada pelo FastAPI com **403**, e 403 quer dizer "sei quem você é e você não pode". O `api.ts` só renova a sessão em **401**: como o cookie do access token expira em 30 min e o browser o apaga, a partir daí tudo saía sem cabeçalho e o usuário era deslogado com refresh válido por sete dias. Use `auto_error=False` e levante 401 você mesmo |
| Tratar erro de rede como sessão inválida | O `loadSession` chamava `logout()` — que apaga os cookies — para qualquer exceção. Backend reiniciando, 502 do proxy ou wi-fi piscando destruíam uma sessão perfeitamente válida. Só o servidor encerra sessão: 401 depois da renovação encerra, o resto pede nova tentativa |
| Middleware conferindo só o access token | Ele expira em 30 min e o cookie some: o middleware expulsava para o login com refresh válido por 7 dias, antes de o `api.ts` ter chance de renovar |
| Modelar a pessoa e o assunto na mesma tabela | `Lead` era contato **e** caso. Quebra no primeiro cliente que volta com outro assunto, e pior quando o assunto é de terceiro: o card fica com o nome de quem escreveu, não de quem é parte |
| Janela de contexto curta demais para o caso de uso | Com 5 mensagens, uma triagem perdia o relato antes de terminar, e quem voltava dias depois ouvia "seu caso é sobre o quê?" de novo. Com 20 também: a primeira triagem real levou quase **cinquenta** mensagens, porque no WhatsApp o cliente responde uma ideia por mensagem ("mandaod", "1", "analista"). Contexto é decisão de produto, não default |
| Cache de leitura sem invalidação na escrita | O histórico ficava guardado por uma hora e **nenhum** dos quatro caminhos que gravam mensagem o invalidava. A primeira mensagem da conversa cacheava `[]`, e pela hora seguinte todo turno chegava ao modelo com o histórico congelado: o agente perguntou a data de admissão quatro vezes na mesma conversa. O `invalidate_cache` existia e ninguém chamava — inclusive havia uma seção de troubleshooting no `GUIA_MEMORY_SERVICE.md` com a linha exata que faltava |
| Testar cache com o cliente de infra desconectado | `redis_client.connect()` só roda no lifespan, que o `TestClient` não dispara: `self.redis` era `None`, toda operação estourava `AttributeError` e o `except` engolia. O cache ficava **desligado na suíte inteira**, CI incluída, e ligado em produção — a única configuração onde o defeito aparecia era a única que ninguém exercitava. Teste que passa por causa de uma dependência ausente não testa nada |
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
| Cliente síncrono chamado de dentro de `async` | `Anthropic(...)` (e não `AsyncAnthropic`) chamado direto numa corrotina **para o processo inteiro** enquanto a chamada dura. Nos 5s de uma resposta, nenhum outro webhook era lido e nenhuma tela carregava; nos 2 minutos de um parecer, o backend ficava parado e a segunda mensagem do cliente esperava o parecer da primeira. Aparecia como "demora de minutos" com o servidor aparentemente ocioso. Use `asyncio.to_thread` (ou o cliente assíncrono) |
| Esquecer que o raciocínio sai do mesmo `max_tokens` | Com teto de 8000, o Opus 5 gastou os 8000 inteiros e entregou ~2400 tokens de texto — o resto foi pensar. Os três pareceres das triagens reais terminaram no meio de uma frase e perderam as linhas de porte econômico. Não há erro: chega um parecer bonito, sem a conclusão que o sistema lê. O `stop_reason` vem junto do uso justamente para isso aparecer no log |
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

## 6. Roteiro combinado com o dono

Decidido em conversa, não relitigar a prioridade sem falar com ele.

**Próximo, e é onde está o dinheiro:**

1. ~~Tirar o parecer de dentro da requisição do webhook.~~ **Feito.** Ele roda
   em tarefa própria, com sessão própria, depois do commit.
2. ~~Travar o parecer duplicado.~~ **Já existia** — `if
   details.analise_preliminar: return`. Nas três triagens reais houve 5
   qualificações e apenas 3 pareceres. O que a repetição gera é ruído no banco
   (linha do tempo e movimento de Kanban a mais), não custo de modelo. Faltava
   só a trava de concorrência, para duas qualificações seguidas não largarem
   dois pareceres antes de o primeiro gravar — essa entrou junto.
3. ~~Contato que volta: consultar se já tem card ativo.~~ **Feito.** A nota
   diz a coluna do card e lista os casos já registrados, tudo por `SELECT` em
   chave indexada — nenhuma chamada de modelo. E instrui: assunto diferente é
   caso novo, não continuação.
4. ~~Mais métricas.~~ **Feito**, e virou nove telas — ver §6b.
5. **"Digitando..." no WhatsApp** enquanto o modelo escreve — a Evolution
   expõe presença, e 8 segundos de silêncio parecem travamento.

**Combinado para depois, na ordem em que ele citou:**

6. **Automações no Kanban** (mover card por evento, cobrar retorno, etc.).
7. **Disparo de e-mail** para o lead.
8. ~~**Assinatura de contrato.**~~ **Feita, e sem provedor externo** — ver
   §6d. O dono não tem conta no Autentique e decidiu que o produto assina
   sozinho. Falta a cobrança de quem não assinou, e o disparo automático
   pela IA.
9. **Front mais profissional.** O dono acha que ainda parece protótipo; é
   trabalho de design, não de correção pontual.

---

## 6b. As telas construídas a partir dos prints do concorrente

Nove telas entregues em uma noite (PRs #60 a #68), todas com teste e
**nenhuma aberta por um humano ainda**. Essa é a pendência número um: são
nove telas cuja única verificação foi jsdom e TestClient.

| Tela | O que ela responde |
|------|--------------------|
| Faixa de pendências (em Atendimentos) | quem está esperando resposta agora |
| Kanban com o fluxo do escritório | o que está travado, e há quantos dias |
| Clientes | cadê o fulano (busca por nome, telefone, e-mail) |
| Funil de venda (aba em Métricas) | de cada cem que escrevem, quantos viram caso |
| Escritório | o que o agente responde sobre o escritório |
| Histórico | quem fez o quê, e quando |
| Finalizados | por que cada caso acabou |
| Marketing | quanto custa trazer cada cliente |
| Agendamentos | o que foi combinado e ninguém cumpriu |

**Três colunas que existiam e ninguém preenchia** passaram a ser escritas
neste lote — vale saber, porque o histórico anterior a elas está vazio e
não há como recuperá-lo:

- `lead_timeline` só registrava movimento da IA; arrasto no Kanban e
  tomada de conversa agora entram.
- `messages.tokens_usados` nunca foi escrita; é dela que sai o consumo de
  IA na tela de Marketing.
- `kanban_cards.data_movimentacao` era zerada a cada requalificação,
  porque o card era apagado e recriado mesmo sem mudar de coluna.

**Deliberadamente não feito:** a extração automática de agendamento pela
IA. Mexer no prompt muda o que o agente diz a todo cliente e precisa ser
testado contra conversas reais. A coluna `agendamentos.criado_por` já
aceita nulo para quando isso existir.

**Fora de alcance sem mudar o produto:** a aba "Jornada do Cliente" e o
board "Jurídico" do concorrente dependem de cinco agentes em série
(Closer → Entrevistador → Coletor → Saneador → Redator) e de geração de
peça a partir de 46 modelos por tese. Nós temos um agente e nenhum
gerador de peça.

**Áudio: resolvido no código, pendente de ligar.** A transcrição existe e foi
medida (ver §3). Falta `anexos_habilitados` no agente que atende e
`GEMINI_API_KEY` no ambiente — sem os dois, o agente continua pedindo que a
pessoa escreva.

**Decisão de produto em aberto:** honorários. O atendimento concorrente diz
"30% do que você ganhar, se não ganhar não paga nada"; o nosso prompt **proíbe
falar de honorários**, porque o número é compromisso comercial do escritório e
inventá-lo seria assumir dívida em nome dele. Se o dono passar a regra real,
entra no prompt.

---

## 6c. O contrato

O escritório fecha o caso com um contrato de honorários. O texto preenchido
e o PDF saem daqui; a **assinatura** também, e ela tem seção própria (§6d).

**O texto é do advogado, não do código.** O corpo do contrato é escrito no
painel (Contratos → Modelos) e guardado em `modelos_contrato`. Não está
embutido no código de propósito: as cláusulas — e principalmente o
**percentual de honorários** — são compromisso comercial e profissional do
escritório. Um número que este software inventasse viraria obrigação assumida
em nome de alguém que nunca a escolheu. É a mesma regra que já proíbe o prompt
de falar de honorários com o cliente.

Há um rascunho para a tela não abrir vazia
(`app/prompts/modelo_contrato_base.py`, semeado por
`python -m scripts.semear_modelo_contrato`). Ele nasce **inativo** e o
percentual é lacuna: nenhum contrato sai dele antes de alguém ler, preencher e
ativar.

**O contrato guarda o texto, não uma referência ao modelo.** `contratos.corpo`
é o texto já preenchido. O modelo muda — o advogado corrige uma cláusula em
março — e o contrato assinado em janeiro tem de continuar dizendo o que dizia
em janeiro. Documento que se altera depois de emitido não é documento. Pela
mesma razão, apagar o modelo é `SET NULL`, não `CASCADE`.

**Dado que falta vira `____________`, não string vazia.** "portador do CPF nº "
seguido de nada é o que faz alguém assinar sem reparar; a lacuna obriga a
reparar. Vale também para variável digitada errada: `{{cliente.cpj}}` sai como
lacuna e **não** desaparece do texto. Mas o erro deve aparecer antes disso — o
`POST /modelos` recusa com 422 e nomeia a variável, porque descobrir na hora de
gerar o contrato do cliente é tarde: alguém já prometeu o documento.

**CPF e RG ficam em tabela própria** (`dados_do_contrato`), separada de
`lead_details`. Aquela guarda o que a triagem apurou sobre o **caso**; esta, o
que identifica a **pessoa** num instrumento jurídico. E a triagem não os
pergunta: pedir documento a quem ainda não sabe se vai ser cliente é onde a
conversa morre. Quem preenche é quem atende, no dossiê do card, depois de o
caso ser aceito.

**Permissões divididas:** escrever modelo exige admin; preencher os dados e
emitir o contrato, não. Quem fecha o atendimento emite; quem define a cláusula
é o escritório.

**`escritorio.cidade` virou campo próprio**, apesar de já estar dentro de
`endereco`. O contrato precisa dela isolada em dois lugares — a cláusula de
foro e a linha "Cidade, 20 de agosto de 2026" acima da assinatura — e extrair
cidade de um endereço escrito livremente é adivinhação.

**reportlab, não weasyprint.** O weasyprint precisa de cairo e pango, que a
imagem `python:3.11-slim` não traz. O reportlab é Python puro.

**`{{caso.resumo}}` ainda não serve para contrato.** No primeiro contrato real
ele saiu com o texto da triagem — *"Contato relata contratação CLT como
coordenador de estoque (R$ 4.000), 3 anos, seguida de 'promoção'…"*. É correto
e é escrito **para o advogado ler**; num instrumento jurídico soa a ficha de
atendimento. Ou o modelo usa `{{caso.area}}` e um objeto redigido à mão, ou
alguém escreve um resumo curto próprio para isto.

### O que **não** existe

Nada: a coleta pela IA e o disparo automático entraram — ver §6e. O que
falta é **ligar** (`CONTRATO_AUTOMATICO=true`) e ver rodar com gente.

### O que foi verificado, e o que não foi

Verificado: a migração ensaiada do zero (upgrade → downgrade → upgrade) **com
dados dentro**, incluindo os três `SET NULL`/`CASCADE`; `alembic --autogenerate`
não acusa deriva; 32 testes de backend e 11 de frontend; e um PDF de duas
páginas gerado de verdade a partir do rascunho, com todas as lacunas
substituídas.

**Não verificado:** nenhuma das duas telas foi aberta por um humano — nem a de
modelos, nem a seção de contrato no dossiê. E o PDF nunca foi olhado por um
advogado, que é quem sabe se o texto do rascunho serve.

---

## 6d. A assinatura, feita aqui dentro

O dono não tem conta no Autentique e decidiu que o produto assina sozinho.
Está feito, e o que segue são as decisões que dão a forma — não relitigar sem
falar com ele.

**O que ela vale, sem eufemismo.** É assinatura eletrônica simples/avançada na
classificação da Lei 14.063/2020 — a **mesma categoria** do produto padrão do
Autentique, que também não é ICP-Brasil. Não é downgrade em relação ao que o
concorrente usa. Vale entre as partes que a aceitam, e o que lhe dá peso é a
trilha de prova, não o carimbo.

**O token é a única credencial, e é assim de propósito.** São 256 bits de
`secrets.token_urlsafe`, entregues só no WhatsApp do próprio cliente, com
prazo de 7 dias. Conferir CPF por cima disso pareceria mais seguro e não
seria: **o CPF está impresso no contrato que a página mostra**, então quem tem
o link já tem o CPF. Segundo fator que o próprio documento entrega não é
segundo fator — e cobrá-lo só faria alguém que digitou errado desistir de
assinar.

**Contrato vencido, assinado ou inexistente respondem 404 igual.** Dizer
"existe mas venceu" a um token adivinhado confirma que ele existe. A exceção é
quem **já assinou**: aí o token já provou quem é, e a página mostra a
confirmação — mandar quem assinou para uma tela de erro faria a pessoa achar
que a assinatura se perdeu.

**O contrato é absorvido no ato.** No mesmo commit da assinatura, o PDF com a
folha de auditoria é gerado e gravado em `contratos.pdf_assinado`. Daí em
diante o documento não depende de link, de nuvem nem de a pessoa continuar por
perto — que era exatamente a objeção do dono: *"a pessoa pode assinar e
sumir"*. O endpoint de PDF devolve **o arquivo guardado** quando ele existe, e
só redesenha quando não há assinatura: o que a pessoa viu e aceitou foi
*aquele* arquivo, e documento que se regenera não é documento.

**A folha de auditoria é o que sustenta a assinatura.** Nome digitado, hora de
Brasília, IP, aparelho, id do contrato e SHA-256 do texto. É esse hash que
amarra a assinatura a este texto — e que denunciaria se ele tivesse mudado.

**O botão só habilita depois de a pessoa rolar o contrato até o fim.**
Assinatura de quem não leu é assinatura contestável, e é feio de fazer com um
cliente. Há 40px de folga, porque em celular o último pixel raramente é
alcançado.

**O IP vem de `CF-Connecting-IP`.** Atrás do túnel do Cloudflare — que é como
isto roda hoje — o IP do socket é o do próprio túnel, igual para todo mundo:
sem ler o cabeçalho, a trilha registraria sempre o mesmo endereço. Cabeçalho é
dado do cliente e pode ser forjado; isto é prova de contexto, não credencial, e
nada autoriza coisa alguma com base nele.

**Envio antes do commit; confirmação depois.** Mandar o link segue a regra que
já valia para a resposta do operador — Evolution recusou, nada é gravado, e o
token nem chega a existir. Já a confirmação de que assinou sai em tarefa
própria **depois** do commit: uma Evolution fora do ar não pode fazer uma
assinatura já registrada parecer que falhou.

**`assinatura.py` é o único roteador sem autenticação do sistema.** Ao mexer
nele, lembre que qualquer campo acrescentado à resposta vira campo público. O
que sai hoje é o mínimo: texto do contrato, nome de quem assina, nome do
escritório. Nada do dossiê, nada do parecer, nada do telefone.

### O fluxo, ponta a ponta

1. Contrato gerado no dossiê do card.
2. **Enviar para assinar** → token criado, link no WhatsApp do cliente, e a
   mensagem gravada na conversa.
3. Cliente abre no celular, rola até o fim, digita o nome, aceita.
4. Assinatura registrada, PDF absorvido, token morto.
5. O agente confirma no WhatsApp e a confirmação entra na conversa.

6. Não assinou? O agente cobra — **`cobranca_service`**, três vezes, e a
   segunda **pergunta o motivo**, que foi o pedido do dono: *"tem que
   perguntar por que não assinou, se desistiu"*. Lembrar → perguntar →
   oferecer a saída; três mensagens iguais são três mensagens ignoradas.

**A cobrança e o follow-up de conversa não se atropelam, por construção.** O
follow-up só pega conversas cuja última mensagem é do agente (`remetente ==
"assistant"`), e tudo que a cobrança e o envio gravam entra como `sistema` —
ninguém leva as duas cutucadas. Há teste travando isso.

**A cobrança para quando o cliente escreve.** A pessoa está falando com a
gente; cortar com "assina aí" é o movimento errado. O relógio passa a contar
da fala dela, então a cobrança volta se a conversa esfriar — não some para
sempre.

**Intervalos muito mais largos que o follow-up** (2h, 1 dia, 3 dias, contra
15 min, 2h, 1 dia). Lá se cobra uma resposta de uma linha; aqui a leitura de
um contrato de honorários, que a pessoa vai querer conversar em casa. Quatro
dias no total, dentro dos sete de validade do link — e se alguém alargar um
intervalo no `.env`, a cobrança **renova o link vencido** antes de mandar, em
vez de enviar endereço morto.

**O gatilho automático existe — e nasce desligado.** Ver §6e.

**Decisão sobre o gatilho, já tomada:** quando ele existir, quem dispara será
**regra determinística** — caso qualificado, viabilidade não descartada, dados
completos e modelo ativo —, não o modelo decidindo. Um LLM com poder de mandar
contrato com honorários é um LLM que um dia manda para a pessoa errada. Da
parte do cliente é idêntico: ninguém do escritório encosta.

### O que foi verificado, e o que não foi

Verificado: migração ensaiada do zero com dados dentro (upgrade → downgrade →
upgrade), token duplicado recusado pelo índice único, dois contratos sem token
convivendo (`NULL` não colide), `--autogenerate` sem deriva, 20 testes de
backend e 9 de frontend, e o ciclo inteiro rodado à mão num banco de ensaio —
link, assinatura, PDF absorvido de 3.345 bytes, token morto depois.

**Não verificado:** ninguém abriu a página de assinatura num celular de
verdade, e nenhum link chegou a um WhatsApp real. O envio e a confirmação
foram exercitados com a Evolution mockada — as duas chamadas que de fato
saem para fora nunca saíram.

**Atenção ao downgrade da migração `b7d4e91c25a8`:** ele derruba as colunas, e
com elas os PDFs assinados e a trilha de prova — dado que não existe em nenhum
outro lugar, justamente porque a ideia era não existir em nenhum outro lugar.

---

## 6e. O ciclo rodando sozinho

O dono foi explícito: *"a IA tem que gerar e enviar, não o advogado"*. Está
feito, e **nasce desligado** — `CONTRATO_AUTOMATICO=false`.

**Por que desligado.** Ligado, o próximo lead real recebe um contrato de
honorários sem o dono ter escolhido a hora. Ligar é uma linha no `.env`;
desligar depois de um contrato ter saído para a pessoa errada não desfaz nada.
Antes de ligar: confira que existe um modelo **ativo** com o percentual certo.

**O modelo de linguagem não decide.** Quem dispara é regra checada em Python
sobre dados que já existem: caso qualificado, viabilidade não `abaixo_do_piso`,
conversa `ativa`, fase `triagem`, modelo ativo e nenhum contrato ainda. Um LLM
com poder de emitir contrato com honorários é um LLM que um dia emite para a
pessoa errada, e "o modelo achou que era hora" não é defesa que se dê a um
cliente. Ele conversa e coleta; a decisão de emitir é aritmética.

**O gatilho é depois do parecer, não da qualificação.** É o parecer que
estabelece o porte econômico. Emitir antes significaria mandar contrato para
casos que o próprio escritório recusaria — noventa segundos de diferença que
decidem se o produto é útil ou constrangedor.

**`indeterminado` não barra.** Mesma distinção que o funil já faz: parecer sem
porte não é caso inviável, é caso que ninguém dimensionou. Barrar aqui faria o
gatilho não disparar quase nunca.

### A fase, e por que ela não é o `status`

`Conversation.fase` — `triagem` → `coleta` → `contratado`. O `status` diz
**quem responde** (ativa/pausada/encerrada); a fase diz **o que está sendo
perguntado**, e as duas variam sem se implicar.

É a fase que decide qual bloco de instrução vai anexado ao system prompt. Na
triagem o bloco de coleta **nem chega ao modelo** — e isso é deliberado: pôr
as instruções de coleta no prompt base, mesmo com um "faça isto só quando...",
deixaria o modelo a um mal-entendido de distância de pedir CPF a quem acabou
de dizer "oi", que é onde a conversa morre. Instrução que não deve valer agora
é instrução que não deve estar lá.

A fase atravessa os três caminhos do `generate_response` — Claude, reserva por
queda e reserva por áudio. O cliente não pode ser perguntado sobre o CPF pelo
Claude e receber uma triagem recomeçada do Gemini porque o principal caiu.

### A coleta

A abertura é **texto fixo**, não gerada pelo modelo: ela anuncia que o
escritório aceitou o caso — um compromisso —, e não é hora de descobrir como o
modelo resolveu formular isso hoje. Dali em diante ele assume.

O bloco JSON `dados_contrato` traz **só o que a pessoa disse**. Campo ausente
continua ausente; CPF com número de dígitos errado é descartado com aviso. Um
CPF inventado num contrato é um contrato nulo, e o modelo que inventa não avisa
que inventou.

A gravação é **acumulativa, nunca destrutiva**: o agente manda o bloco a cada
mensagem com dado novo, e um bloco posterior com menos campos não pode apagar
o que um anterior trouxe.

**Obrigatórios: CPF, endereço, cidade, UF.** O RG fica de fora de propósito —
muita gente não sabe de cabeça, e travar o contrato por causa dele é perder o
cliente por um campo que o advogado completa em trinta segundos. Ele sai como
lacuna visível no PDF.

### Duas armadilhas encontradas montando isto

**O follow-up devolvia a própria despedida como pergunta.** Visto em produção
pelo dono: o agente encerrou com *"Por nada, Diego. Fique tranquilo, o advogado
vai te procurar ainda hoje"*, e o follow-up mandou *"Oi, Diego! Ficou faltando
só isto aqui: Por nada, Diego..."*. Sem sentido, e errado no mérito — a bola
estava com o escritório. O follow-up repete a última mensagem do agente, e isso
só funciona quando ela **é** pergunta. Agora exige interrogação, e conversa
fora da fase `triagem` não é dele.

**A `## Ficha` só era lida sem markdown.** O parser exigia `Área: trabalhista`
em linha limpa; um modelo escrevendo `- **Área:** trabalhista` fazia
`ler_ficha` devolver `(None, None)`, o caso não era arquivado e **ninguém
ficava sabendo** — sem erro, só um lead sem caso. Achei isso escrevendo um
parecer de teste de memória, e enfeitei do jeito que o modelo enfeitaria.
Depois que o gatilho passou a ler a viabilidade do caso, ficha enfeitada virou
contrato que nunca sai. O parser agora tolera marcador de lista e negrito.

### O teste que faltava

`tests/test_ciclo_completo.py` percorre webhook → triagem → qualificação →
parecer → coleta → contrato → assinatura numa transação só, com modelo e
Evolution simulados e **todo o resto real**. Os testes de unidade cobriam cada
peça; o que quebrava era a costura, e foi assim que três defeitos passaram.

### Recomeçar do zero

`python -m scripts.limpar_conversas` apaga conversas, mensagens, leads, casos,
cards, contratos e dados civis, e **preserva** usuários, agentes, colunas,
configuração do escritório e modelos. Pede confirmação digitada e avisa em
separado quando há contrato assinado — aquilo é documento, com PDF e trilha de
prova, e não tem cópia.

### Rodou de verdade, com gente

**24/08/2026, primeira vez.** Triagem completa pelo WhatsApp (agressão no
trabalho, cinco anos de casa, R$ 6.500), contrato emitido sozinho, assinado
de um Android e absorvido — IP IPv6 real, hash, comprovante. O ciclo inteiro
funcionou sem ninguém do escritório clicar.

A triagem se comportou: conduziu com perguntas encadeadas, informou o que
costuma entrar no caso **atribuindo ao advogado**, e recusou falar de
honorários quando o cliente perguntou "não tem contrato?" — devolveu ao
advogado, como o prompt manda.

**O que a conversa real revelou, e foi corrigido no mesmo dia:**

- O contrato saiu com o **CONTRATADO em branco** — ninguém tinha preenchido o
  escritório. Não é defeito de código, mas é o primeiro contrato que sai e
  ninguém confere isso antes.
- O objeto trazia o **texto da triagem** (ver §6c).
- **Não tinha assinatura nenhuma** na linha de assinar. Ver abaixo.

### A assinatura desenhada

Juridicamente o rabisco não acrescenta nada: o que prova a assinatura é a
trilha — token individual, hora, IP, aparelho e hash. Mas o dono abriu o
primeiro contrato assinado de verdade e disse *"não assinou nada ali"*. Um
contrato sem nada escrito na linha **não parece assinado**, e quem recebe o
PDF fica sem saber se valeu.

Agora há um `<canvas>` na página pública. Três coisas que não são enfeite:
`touch-none` (sem ele o dedo rola a página em vez de desenhar, e ninguém
assina no celular), Pointer Events em vez de `touch` + `mouse` separados (um
traço vira dois), e redimensionamento por `devicePixelRatio` (senão o traço
sai borrado, e assinatura borrada parece defeito).

**Duas formas: desenhar ou digitar.** É o que Autentique e DocuSign
oferecem, e por um motivo prático: assinar com o dedo sai um garrancho, e
muita gente desiste ou fica com vergonha do resultado. Digitando, a pessoa
escolhe entre três letras cursivas — e o resultado é **o mesmo PNG**, pintado
num canvas no navegador. O backend não sabe (nem precisa saber) se o traço
veio de um dedo ou de uma fonte, e não há um segundo formato para validar,
guardar e desenhar no PDF.

As fontes vêm por `next/font/google`, que **baixa na build e serve do nosso
domínio** — em tempo de execução não há requisição ao Google. E o canvas
espera `document.fonts.load` antes de pintar: sem isso o primeiro desenho sai
na fonte de reserva, e a pessoa assina com o próprio nome em Times.

**Digitar não é o sistema assinando por ninguém.** A pessoa digita o próprio
nome, escolhe como ele aparece e confirma. O que sustenta a assinatura
continua sendo a trilha.

**O desenho é opcional, de propósito.** Navegador sem canvas, mouse ruim, mão
trêmula — a pessoa ainda assina. Travar o botão nele trocaria o essencial pelo
enfeite.

**E é entrada pública, então nada confia nele:** prefixo conferido, tamanho
limitado antes de decodificar (o base64 cresce 4/3 — sem o teto, um POST de
30 KB alocaria dezenas de MB), e os bytes têm de começar com a assinatura do
PNG. Recusa é silenciosa: o contrato vale sem o desenho.

### O que ainda não foi verificado

**O bloco de coleta nunca chegou a rodar** — na conversa real o contrato saiu
antes, porque os dados vieram da triagem. Não se sabe se a agente coleta bem:
se pergunta um dado por vez, se aceita "não sei o RG" sem travar, se recomeça
a triagem por engano.

E a assinatura nunca foi feita com um dedo de verdade numa tela de verdade —
só com Pointer Events sintéticos no jsdom, que não implementa canvas. O mesmo
vale para a digitada: o jsdom não renderiza fonte nenhuma, então **ninguém
viu** como as três letras ficam.

---

## 7. Pendências técnicas

Em ordem de valor, e a primeira vale mais que as outras juntas.

1. **Nenhuma conversa real rodou com o prompt novo.** O prompt de triagem está
   em `app/prompts/triagem_juridica.py` e **não** foi aplicado ao agente que
   atende — o do banco ainda é o antigo. Aplique com
   `python -m scripts.aplicar_prompt --agente <id>` e converse pelo WhatsApp de
   verdade. Tudo o que veio depois dele (os números que dimensionam o caso, o
   porte econômico, o dossiê do card) é alimentado por essa conversa; se a
   triagem não coletar como se espera, o resto está resolvendo o problema
   errado.

2. ~~A tela de conexão nunca falou com a Evolution de verdade.~~ **Falou.** O
   número foi pareado pelo QR do painel, mensagens reais entraram pelo webhook
   e foram respondidas em ~8s. O `logout` também foi exercitado — por comando,
   não pelo botão novo, que continua sem um clique de gente.

4. **Áudio real, em OGG/Opus, nunca passou.** A transcrição foi medida com
   um WAV gerado por `espeak-ng`; o WhatsApp manda `audio/ogg; codecs=opus`.
   A documentação do Gemini lista OGG como suportado, e não houve como
   converter aqui (sem `ffmpeg`). É o primeiro risco a checar.

5. ~~A stack em container nunca subiu.~~ **Subiu**, e é como o dono roda hoje:
   Postgres, Redis, Evolution, backend e frontend pelo compose, com o webhook
   entregando na rede interna.

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

## 8. Convenções

- Comentários e mensagens de commit em **português**; nomes de código em inglês,
  exceto os campos que espelham a API.
- Comentário explica **por quê**, não o quê.
- Nada de `create_all` novo: mudança de schema passa por `alembic revision --autogenerate`,
  e a revisão gerada **deve ser lida** antes de aplicar (o autogenerate vê
  renomeação como drop + create).
- Ao entregar, dizer o que **não** foi verificado, não só o que passou.
