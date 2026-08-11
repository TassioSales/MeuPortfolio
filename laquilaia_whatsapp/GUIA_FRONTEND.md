# Guia do Frontend — Fases 10 a 13

Painel web da L'Aquila AI: Next.js 14 (App Router) + TypeScript + TailwindCSS.

- **Fase 10** — base, autenticação JWT, renovação automática de token e proteção de rotas.
- **Fase 11** — painel de agentes (listar, criar, editar, excluir).
- **Fase 12** — chat de teste (playground) com histórico e reset.
- **Fase 13** — Kanban CRM com arrastar e soltar.

---

## 1. Visão geral

```
┌──────────────────────────────────────────────────────────────┐
│                        Browser                               │
│                                                              │
│  /login ──login()──┐                                         │
│  /register         │        ┌──────────────────────────┐     │
│  /dashboard ◄──────┴────────│ useAuthStore (Zustand)   │     │
│                             │  user, isLoading, error  │     │
│                             └───────────┬──────────────┘     │
│                                         │                    │
│                             ┌───────────▼──────────────┐     │
│                             │ lib/auth.ts              │     │
│                             │  login/register/logout   │     │
│                             └───────────┬──────────────┘     │
│                                         │                    │
│                             ┌───────────▼──────────────┐     │
│                             │ lib/api.ts               │     │
│                             │  Bearer + refresh em 401 │     │
│                             └───────────┬──────────────┘     │
│                                         │                    │
│   cookies: laquilaia_access_token       │                    │
│            laquilaia_refresh_token      │                    │
└─────────────────────────────────────────┼────────────────────┘
                                          │ HTTP
                              ┌───────────▼──────────────┐
                              │  FastAPI /api/v1/auth/*  │
                              └──────────────────────────┘

        middleware.ts (edge) — barra /dashboard sem cookie
```

Duas camadas de proteção, com papéis distintos:

| Camada | Onde roda | O que verifica | Custo |
|---|---|---|---|
| `middleware.ts` | Servidor (edge) | Se o cookie **existe** | Zero requisições |
| `DashboardLayout` | Browser | Se o token é **válido** (`GET /auth/me`) | 1 requisição |

O middleware evita renderizar a tela para quem claramente não tem sessão; a
validação real é do backend, já que o middleware não consegue conferir a
assinatura do JWT sem a `SECRET_KEY`.

---

## 2. Estrutura de arquivos

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout (lang pt-BR, metadata)
│   ├── page.tsx                # Redireciona para /dashboard ou /login
│   ├── globals.css             # Tailwind + variáveis de tema
│   ├── error.tsx               # Error boundary global
│   ├── not-found.tsx           # 404
│   ├── login/page.tsx          # Formulário de login (honra ?next=)
│   ├── register/page.tsx       # Formulário de cadastro
│   └── dashboard/
│       ├── layout.tsx          # Navbar + Sidebar + guarda de sessão
│       ├── page.tsx            # Home do painel
│       ├── agents/page.tsx     # Painel de agentes (Fase 11)
│       ├── chat-test/page.tsx  # Chat de teste (Fase 12)
│       └── kanban/page.tsx     # Kanban CRM (Fase 13)
├── components/
│   ├── Button.tsx              # 4 variantes + estado de loading
│   ├── Input.tsx               # Label, erro e hint acessíveis
│   ├── Textarea.tsx            # Idem, para o system prompt
│   ├── Modal.tsx               # Diálogo acessível (Esc, backdrop, foco)
│   ├── ConfirmDialog.tsx       # Confirmação de ação destrutiva
│   ├── EmptyState.tsx          # Estado vazio reutilizável
│   ├── AgentForm.tsx           # Formulário de criar/editar agente
│   ├── AgentCard.tsx           # Card de agente na listagem
│   ├── ChatPlayground.tsx      # Conversa de teste com o agente
│   ├── KanbanBoard.tsx         # Board com colunas e drag-and-drop
│   ├── KanbanCard.tsx          # Card de lead arrastável
│   ├── LoadingSpinner.tsx      # Spinner + FullPageLoader
│   ├── Navbar.tsx              # Identificação do usuário + logout
│   └── Sidebar.tsx             # Navegação (itens de fases futuras desabilitados)
├── hooks/
│   ├── useAuth.ts              # Store Zustand + hook useAuth()
│   ├── useAgents.ts            # Store Zustand do CRUD de agentes
│   ├── useChat.ts              # Estado local da conversa de teste
│   └── useKanban.ts            # Board + movimentação otimista
├── lib/
│   ├── api.ts                  # Cliente HTTP com refresh automático
│   ├── auth.ts                 # login / register / logout / getCurrentUser
│   ├── agents.ts               # CRUD de agentes
│   ├── chat.ts                 # Chat, histórico e reset
│   ├── kanban.ts               # Board, colunas padrão e movimentação
│   ├── constants.ts            # Nomes de cookie (sem dependências)
│   ├── tokens.ts               # Leitura/escrita dos cookies
│   └── utils.ts                # cn() — merge de classes Tailwind
├── types/index.ts              # Tipos espelhando os schemas do backend
├── __tests__/                  # 74 testes
├── middleware.ts               # Proteção de rotas no edge
└── Dockerfile                  # Imagem de desenvolvimento
```

---

## 3. Contrato com o backend

Os tipos em `types/index.ts` espelham `backend/app/models/schemas.py`, por isso
os campos ficam **em português** (`nome`, `senha`) — é o que a API espera.

| Endpoint | Método | Corpo | Resposta |
|---|---|---|---|
| `/api/v1/auth/register` | POST | `{nome, email, senha}` | `UserResponse` |
| `/api/v1/auth/login` | POST | `{email, senha}` | `{access_token, refresh_token, token_type, expires_in}` |
| `/api/v1/auth/refresh` | POST | `{refresh_token}` | `TokenResponse` |
| `/api/v1/auth/me` | GET | — (Bearer) | `UserResponse` |

> **`GET /api/v1/auth/me` foi adicionado na Fase 10.** O `/login` devolve apenas
> tokens, sem dados do usuário; sem esse endpoint a Navbar não teria nome nem
> e-mail para exibir, e a sessão não poderia ser revalidada ao recarregar a página.

### Agentes (Fase 11)

| Endpoint | Método | Corpo | Resposta |
|---|---|---|---|
| `/api/v1/agents` | GET | — | `AgentResponse[]` |
| `/api/v1/agents` | POST | `{nome, descricao?, system_prompt, temperatura, max_tokens}` | `AgentResponse` |
| `/api/v1/agents/{id}` | PUT | Campos parciais | `AgentResponse` |
| `/api/v1/agents/{id}` | DELETE | — | `{detail}` |

Limites validados pelo backend (`agent_service.create_agent`) e espelhados em
`AGENT_LIMITS` no frontend: `temperatura` entre 0 e 2, `max_tokens` inteiro
entre 1 e 4096, `system_prompt` não vazio, `nome` até 255 caracteres.

> **Correção no backend na Fase 11.** Em `GET /api/v1/agents` o parâmetro de
> query `status` sombreava o módulo `status` do FastAPI, então qualquer exceção
> no endpoint estourava `AttributeError` em vez de devolver 500. Passou a usar
> `status_filter` com `alias="status"` — a URL pública não mudou.

### Chat / playground (Fase 12)

| Endpoint | Método | Corpo | Resposta |
|---|---|---|---|
| `/api/v1/agents/{id}/chat` | POST | `{message, conversation_id?}` | `{response, conversation_id, tokens_used, timestamp, model}` |
| `/api/v1/agents/{id}/chat/history` | GET | — | `{conversation_id, messages[]}` |
| `/api/v1/agents/{id}/chat/history` | DELETE | — | `{detail, deleted}` |

A conversa do playground fica separada das reais pelo telefone reservado
`test_api` (constante `TEST_PHONE_NUMBER` no router).

### Kanban (Fase 13)

| Endpoint | Método | Corpo | Resposta |
|---|---|---|---|
| `/api/v1/agents/{id}/kanban` | GET | — | `{agent_id, columns[]}` com os cards |
| `/api/v1/agents/{id}/kanban/columns/init` | POST | — | Colunas padrão do funil |
| `/api/v1/agents/{id}/kanban/move` | POST | `{lead_id, target_column_id, new_order}` | `{detail}` |

> **Falha de autorização corrigida nesta fase.** Os routers `kanban.py` e
> `metrics.py` foram escritos **sem nenhuma dependência de autenticação** — os
> 11 endpoints eram públicos. Qualquer requisição anônima lia (e movia) os
> leads de qualquer agente, incluindo nome, e-mail e telefone dos clientes.
>
> Todos passaram a exigir o token e a escopar o agente pelo dono
> (`Agent.user_id == user_id`), respondendo 404 em vez de 403 para não revelar
> que o agente existe. Em métricas a checagem é explícita no router: o
> `metrics_service` valida apenas que o agente existe, então autenticar sem
> conferir o dono ainda deixaria um usuário ler as métricas de outro.
>
> `tests/test_authorization.py` cobre os 11 endpoints em três cenários:
> anônimo, usuário logado tentando agente alheio, e dono legítimo.

> **Duas correções no backend nesta fase.**
>
> 1. `MessageResponse` não devolvia `conversation_id`. Como o cliente não tinha
>    como saber o id da conversa criada, cada mensagem começaria um contexto
>    novo — justamente o que um playground precisa evitar.
> 2. Existe uma constraint única `(agent_id, phone_number)` em `conversations`,
>    e o endpoint criava a conversa de teste com telefone fixo `test_api`. A
>    segunda conversa de teste do mesmo agente violaria a constraint. Agora a
>    conversa é reaproveitada em vez de recriada.

---

## 4. Fluxo de autenticação

### Login

1. Usuário envia e-mail e senha em `/login`.
2. `useAuthStore.login()` chama `lib/auth.login()`.
3. `POST /api/v1/auth/login` retorna os tokens.
4. Tokens vão para cookies (`setStoredToken` / `setStoredRefreshToken`).
5. `GET /api/v1/auth/me` traz o perfil, que popula o store.
6. Redireciona para `?next=` (se for caminho interno) ou `/dashboard`.

### Registro

`POST /register` **não** devolve token. O store faz login logo em seguida, para
o usuário já entrar autenticado em vez de cair de volta na tela de login.

### Renovação automática

`lib/api.ts` intercepta `401`, troca o refresh token por um novo access token e
repete a requisição original — transparente para quem chamou:

```
GET /api/v1/agents  ──►  401
                          │
                    POST /auth/refresh  ──►  novo access_token (salvo no cookie)
                          │
GET /api/v1/agents  ──►  200
```

Requisições simultâneas compartilham o mesmo refresh (`refreshInFlight`), então
cinco chamadas que tomem 401 juntas disparam **um** POST `/auth/refresh`, não cinco.
Se o refresh falhar, os cookies são apagados e o erro sobe — o `DashboardLayout`
manda para `/login`.

### Por que cookies e não localStorage

O `middleware.ts` roda no servidor e enxerga apenas cookies. Com o token em
localStorage, a proteção de rota só existiria depois do JavaScript carregar no
browser. Os cookies usam `sameSite=lax` e `secure` automático em HTTPS.

---

## 5. Rodando

### Local

```bash
cd frontend
npm install
cp .env.local.example .env.local     # ajuste NEXT_PUBLIC_API_URL se necessário
npm run dev                          # http://localhost:3000
```

O backend precisa estar de pé em `http://localhost:8000` para login funcionar.

### Docker (stack completa)

```bash
./run.sh          # sobe postgres + redis + backend + frontend e abre o browser
./run.sh stop     # derruba tudo
```

No Windows: `run.bat`.

### Scripts

| Comando | O que faz |
|---|---|
| `npm run dev` | Servidor de desenvolvimento com hot reload |
| `npm run build` | Build de produção |
| `npm start` | Serve o build de produção |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` | Jest |
| `npm run lint` | ESLint (config do Next) |

---

## 6. Testes

```bash
cd frontend && npm test
```

**74 testes, 8 suítes:**

| Suíte | Testes | Cobre |
|---|---|---|
| `__tests__/api.test.ts` | 8 | URL base, header Bearer, `skipAuth`, conversão de erro, refresh em 401, limpeza de sessão quando o refresh falha |
| `__tests__/auth.test.ts` | 11 | login/register/logout, formato do payload, estados do store, `loadSession` com token válido/inválido/ausente |
| `__tests__/middleware.test.ts` | 6 | Redirecionamento de rota privada, parâmetro `?next=`, rota pública, usuário logado em `/login` |
| `__tests__/agents.test.ts` | 12 | Verbos e corpos do CRUD, ordenação otimista da lista, lista intacta quando a API falha |
| `__tests__/AgentForm.test.tsx` | 9 | Preenchimento na edição, padrões na criação, normalização do payload, validações, erro do backend |
| `__tests__/chat.test.ts` | 7 | Verbos e corpos do chat, envio do `conversation_id` só quando há conversa |
| `__tests__/ChatPlayground.test.tsx` | 10 | Estado vazio, carga de histórico, envio, tokens, continuidade da conversa, reset, recuperação de erro |
| `__tests__/kanban.test.tsx` | 11 | Verbos da API, criação das colunas padrão, movimentação otimista, rollback quando o backend recusa, render do board |

`middleware.test.ts` roda com `@jest-environment node` porque `next/server`
depende dos globais `Request`/`Response`, que o jsdom não implementa — é o mesmo
ambiente do edge runtime.

O arrastar em si não é exercitado no Jest: depende de eventos de ponteiro que
o jsdom não simula fielmente. O que importa e é testável está coberto — a
chamada de movimentação, a atualização otimista e o rollback. O arrasto real
foi verificado no navegador.

### Verificação end-to-end

Cada fase foi percorrida no Chromium contra um backend simulado:

- **Fase 11** — proteção de rota, login com senha errada, login correto voltando para `?next=`, criação/edição/exclusão de agente, persistência após reload, logout.
- **Fase 12** — playground sem agentes, envio, tokens, segunda mensagem mantendo contexto, Enter para enviar, persistência após reload, reset.
- **Fase 13** — board com colunas e cards, **arrasto real** de um card entre colunas com o mouse, e conferência de que o movimento persiste após reload (ou seja, chegou ao backend).

Os scripts ficaram fora do repositório por dependerem do Playwright, que não é
dependência do projeto.

---

## 7. Decisões e limitações

**Itens de navegação desabilitados.** Só Métricas segue marcada como "Em
breve"; a rota chega na Fase 14.

**`@dnd-kit` em vez de `react-beautiful-dnd`.** O plano original citava
`react-beautiful-dnd`, mas a Atlassian arquivou a biblioteca e ela tem
problemas conhecidos com o StrictMode do React 18. O `@dnd-kit` é mantido e
traz suporte a teclado e toque, que a alternativa nativa de HTML5 não tem.

**Movimentação otimista com rollback.** O card muda de coluna antes da resposta
do backend — arrastar precisa parecer instantâneo. Se a chamada falhar, o board
anterior é restaurado e o erro aparece acima das colunas.

**O playground não usa Zustand.** Diferente de `useAgents`, o estado da conversa
é local à página (`useChat`). Uma store global só criaria risco de a conversa de
um agente aparecer na tela de outro — a página remonta o componente com `key`
ao trocar de agente, pelo mesmo motivo.

**Agente selecionado vive na URL** (`?agent=<id>`), para o link do playground
ser compartilhável e sobreviver a um reload.

**Mensagem falha não some.** Se o envio dá erro, os balões temporários são
removidos e o texto volta para a caixa, em vez de o usuário perder o que
escreveu.

**Validação duplicada no formulário de agente.** `AgentForm` repete as regras de
`agent_service.create_agent` para dar retorno imediato, mas o backend continua
sendo a autoridade — o erro que ele devolve é exibido no formulário.

**Faixas numéricas são barradas pelo navegador.** Os inputs de temperatura e max
tokens têm `min`/`max`, então a validação de constraint do HTML impede o submit
antes do JS rodar. A validação em JS cobre o que o navegador deixa passar — em
especial campo vazio, que sem ela viraria `Number("") === 0` e enviaria um valor
que o usuário não escolheu.

**Atualização otimista da lista.** Criar, editar e excluir alteram o store
localmente com a resposta do backend, sem refazer o `GET /agents`. Se outra aba
mudar os dados, a lista só reflete isso no próximo carregamento da página.

**Redirect seguro.** O `?next=` só é aceito se começar com `/` e não com `//`,
para que `?next=https://site-malicioso` não vire um open redirect.

**`useSearchParams` e Suspense.** A página de login envolve o formulário em
`<Suspense>` — exigência do App Router para hooks de search params.

**Cookies não são HttpOnly.** O JavaScript precisa ler o token para montar o
header `Authorization`. Uma alternativa mais segura (cookie HttpOnly definido
pelo backend + proxy nas rotas do Next) exigiria mudanças no backend e ficou
fora do escopo desta fase.

---

## 8. Troubleshooting

| Sintoma | Causa provável | Solução |
|---|---|---|
| `Failed to fetch` no login | Backend fora do ar ou URL errada | Confira `NEXT_PUBLIC_API_URL` e `curl http://localhost:8000/health` |
| Erro de CORS no console | Origem do frontend não liberada | Ajuste `FRONTEND_URL` / `ALLOWED_ORIGINS` no `.env` do backend |
| Loop entre `/login` e `/dashboard` | Cookie presente mas token inválido | `logout()` no console ou limpe os cookies do site |
| Login funciona mas a Navbar fica vazia | `GET /auth/me` falhando | Verifique se o backend foi reiniciado após a Fase 10 |
| Variável `NEXT_PUBLIC_*` não aplicada | Next lê env em build/boot | Reinicie o `npm run dev` |
| `npm run dev` sem estilos | Tailwind não achou os arquivos | Confira `content` em `tailwind.config.ts` |

---

## 9. Próximas fases

| Fase | Entrega | Reaproveita daqui |
|---|---|---|
| 14 | Dashboards & gráficos | `api` + endpoints da Fase 9 |
