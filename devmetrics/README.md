# DevMetrics — Dashboard de Analytics para GitHub

Dashboard de análise de perfis do GitHub com insights gerados por Inteligência Artificial (Mistral AI). Pesquise qualquer usuário e visualize métricas detalhadas sobre repositórios, linguagens de programação e atividade ao longo dos anos.

## Funcionalidades

- Busca de qualquer perfil público do GitHub
- Exibição de avatar, bio, empresa e localização do desenvolvedor
- Cards com totais de repositórios, estrelas e forks
- Gráfico de distribuição de linguagens (donut chart interativo)
- Grid com os 6 repositórios mais estrelados
- Timeline de repositórios criados por ano
- Insights gerados pela Mistral AI sobre o perfil do desenvolvedor

## Stack Tecnológica

### Backend
- **Go 1.22** com `net/http` nativo
- **Chi v5** — roteador HTTP leve e performático
- **GitHub REST API** — coleta dados de usuários e repositórios
- **Mistral AI API** — geração de insights com `mistral-small-latest`

### Frontend
- **Next.js 15** com App Router
- **React 19** com TypeScript
- **Tailwind CSS 3** — tema dark inspirado no GitHub
- **Recharts** — gráfico de pizza/donut para linguagens
- **Lucide React** — ícones

## Estrutura do Projeto

```
devmetrics/
├── backend/
│   ├── cmd/api/main.go          # Ponto de entrada do servidor
│   ├── internal/
│   │   ├── github/client.go     # Cliente HTTP para a GitHub API
│   │   ├── metrics/analyzer.go  # Cálculo de métricas e agregações
│   │   ├── ai/insights.go       # Integração com Mistral AI
│   │   └── http/
│   │       ├── router.go        # Definição de rotas Chi
│   │       └── handlers.go      # Handlers HTTP e lógica de negócio
│   └── go.mod
└── frontend/
    ├── app/
    │   ├── layout.tsx           # Layout raiz com metadados
    │   ├── page.tsx             # Página principal com busca e resultados
    │   └── globals.css          # Estilos globais com Tailwind
    ├── components/
    │   ├── StatsCard.tsx        # Card de estatística individual
    │   ├── LanguageChart.tsx    # Gráfico de linguagens (Recharts)
    │   ├── ActivityHeatmap.tsx  # Link para atividade no GitHub
    │   └── AIInsights.tsx       # Painel de insights da Mistral AI
    └── lib/api.ts               # Funções de fetch tipadas
```

## Como Rodar Localmente

### Pré-requisitos

- Go 1.22+
- Node.js 18+
- Chave de API da Mistral AI (obtenha em [console.mistral.ai](https://console.mistral.ai))
- Token do GitHub (opcional, aumenta o rate limit de 60 para 5.000 req/hora)

### Configuração

1. Clone o repositório e entre na pasta:
   ```bash
   cd devmetrics
   ```

2. Crie o arquivo de variáveis de ambiente:
   ```bash
   cp .env.example .env
   ```

3. Edite o `.env` com suas chaves:
   ```env
   MISTRAL_API_KEY=sua_chave_mistral_aqui
   GITHUB_TOKEN=seu_token_github_opcional
   PORT=8080
   NEXT_PUBLIC_API_URL=http://localhost:8080
   ```

### Backend (Go)

```bash
cd backend
go mod tidy
go run ./cmd/api/main.go
```

O servidor iniciará em `http://localhost:8080`.

### Frontend (Next.js)

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

O frontend estará disponível em `http://localhost:3000`.

### Windows (Atalho)

Execute `start_devmetrics.bat` para iniciar backend e frontend automaticamente em janelas separadas.

## API Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/health` | Verificação de saúde do servidor |
| `GET` | `/api/user/{username}` | Perfil do usuário + métricas completas |
| `GET` | `/api/user/{username}/languages` | Distribuição de linguagens |
| `GET` | `/api/user/{username}/insights` | Insights gerados pela Mistral AI |

### Exemplo de Resposta — `/api/user/torvalds`

```json
{
  "user": {
    "login": "torvalds",
    "name": "Linus Torvalds",
    "avatar_url": "https://avatars.githubusercontent.com/u/1024025?v=4",
    "bio": "Just a software developer",
    "followers": 248000,
    "following": 0
  },
  "metrics": {
    "total_repos": 10,
    "total_stars": 215000,
    "total_forks": 65000,
    "most_used_language": "C",
    "languages": [
      { "language": "C", "bytes": 12500000, "percentage": 72.5 }
    ],
    "top_repos": [...],
    "repos_by_year": [...]
  }
}
```

## Variáveis de Ambiente

| Variável | Obrigatório | Descrição |
|----------|-------------|-----------|
| `MISTRAL_API_KEY` | Sim (para IA) | Chave da API Mistral AI |
| `GITHUB_TOKEN` | Não | Token GitHub para maior rate limit |
| `PORT` | Não | Porta do backend (padrão: `8080`) |
| `NEXT_PUBLIC_API_URL` | Não | URL base do backend (padrão: `http://localhost:8080`) |

## Licença

MIT
