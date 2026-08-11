# Guia do Frontend — Fase 10 (Layout Base & Autenticação)

Base do painel web da L'Aquila AI: Next.js 14 (App Router) + TypeScript + TailwindCSS,
com autenticação JWT, renovação automática de token e proteção de rotas.

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
│       └── page.tsx            # Home do painel
├── components/
│   ├── Button.tsx              # 4 variantes + estado de loading
│   ├── Input.tsx               # Label, erro e hint acessíveis
│   ├── LoadingSpinner.tsx      # Spinner + FullPageLoader
│   ├── Navbar.tsx              # Identificação do usuário + logout
│   └── Sidebar.tsx             # Navegação (itens de fases futuras desabilitados)
├── hooks/
│   └── useAuth.ts              # Store Zustand + hook useAuth()
├── lib/
│   ├── api.ts                  # Cliente HTTP com refresh automático
│   ├── auth.ts                 # login / register / logout / getCurrentUser
│   ├── constants.ts            # Nomes de cookie (sem dependências)
│   ├── tokens.ts               # Leitura/escrita dos cookies
│   └── utils.ts                # cn() — merge de classes Tailwind
├── types/index.ts              # Tipos espelhando os schemas do backend
├── __tests__/                  # 25 testes (api, auth, middleware)
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

> **`GET /api/v1/auth/me` foi adicionado nesta fase.** O `/login` devolve apenas
> tokens, sem dados do usuário; sem esse endpoint a Navbar não teria nome nem
> e-mail para exibir, e a sessão não poderia ser revalidada ao recarregar a página.

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

**25 testes, 3 suítes:**

| Suíte | Testes | Cobre |
|---|---|---|
| `__tests__/api.test.ts` | 8 | URL base, header Bearer, `skipAuth`, conversão de erro, refresh em 401, limpeza de sessão quando o refresh falha |
| `__tests__/auth.test.ts` | 11 | login/register/logout, formato do payload, estados do store, `loadSession` com token válido/inválido/ausente |
| `__tests__/middleware.test.ts` | 6 | Redirecionamento de rota privada, parâmetro `?next=`, rota pública, usuário logado em `/login` |

`middleware.test.ts` roda com `@jest-environment node` porque `next/server`
depende dos globais `Request`/`Response`, que o jsdom não implementa — é o mesmo
ambiente do edge runtime.

---

## 7. Decisões e limitações

**Itens de navegação desabilitados.** Sidebar e cards do dashboard já listam
Agentes, Chat, Kanban e Métricas marcados como "Em breve". As rotas não existem
ainda; são entregues nas fases 11–14.

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
| 11 | Painel de agentes | `api`, `useAuth`, `Button`, `Input` |
| 12 | Chat de teste | `api`, layout do dashboard |
| 13 | Kanban CRM | `api`, layout do dashboard |
| 14 | Dashboards & gráficos | `api` + endpoints da Fase 9 |
