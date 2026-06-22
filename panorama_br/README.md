# Panorama BR — Dashboard de Indicadores Econômicos

Dashboard full-stack de indicadores econômicos brasileiros com coleta automática de dados reais (BCB, yfinance), API Go e frontend Next.js 14.

## Arquitetura

```
panorama_br/
├── pipeline/          Python — coleta + agendamento (30min)
├── api/               Go — REST API com chi
├── frontend/          Next.js 14 — dashboard dark
└── docker-compose.yml orquestração completa
```

## Como rodar

```bash
cd panorama_br
cp .env.example .env
docker-compose up --build
```

- Pipeline coleta dados automaticamente
- API disponível em `http://localhost:8080`
- Dashboard em `http://localhost:3000`

## Pipeline (Python)

Coleta dados de fontes públicas gratuitas:

| Fonte | Dados |
|-------|-------|
| BCB/SGS | SELIC, IPCA, PIB, câmbio BRL/USD, desemprego |
| Yahoo Finance | IBOVESPA, PETR4, VALE3, ITUB4, BBDC4, WEGE3, ABEV3, MGLU3 |
| Estático | PIB per capita, IDH e desemprego dos 27 estados |

Ciclos automáticos a cada **30 minutos** com SIGTERM gracioso.

## API (Go)

| Endpoint | Descrição |
|----------|-----------|
| `GET /macro` | Indicadores macroeconômicos atuais |
| `GET /history/:indicator` | Histórico de um indicador |
| `GET /market` | Dados de mercado (IBOVESPA + ações) |
| `GET /regional` | Dados por estado |
| `GET /status` | Status do pipeline |

## Frontend (Next.js 14)

4 abas no dashboard:

- **Macro** — SELIC, IPCA, PIB, câmbio, desemprego com cards e gráficos de linha
- **Mercado** — IBOVESPA e tabela de ações com variação
- **Regional** — ranking dos estados por PIB per capita
- **Comparativo** — gráfico de barras comparativo entre indicadores

Dark theme: `#0a0e1a` / `#111827` / acento `#3b82f6`

## Stack

- **Python 3.12** + requests + yfinance + loguru
- **Go 1.22** + chi + modernc.org/sqlite (sem CGO)
- **Next.js 14** + TypeScript + Tailwind CSS + Recharts
- **SQLite** compartilhado via volume Docker
- **Docker Compose** para orquestração
