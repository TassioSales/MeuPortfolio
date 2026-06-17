# Fuel Analytics Platform

Plataforma completa para coleta, processamento, forecast e visualizacao de precos de combustiveis no Brasil com base em dados abertos da ANP.

## Stack

- Data engineering: Python, Prefect, DuckDB, Polars, PyArrow, Parquet, HTTPX
- Backend: Go, Chi, DuckDB
- Frontend: Next.js, React, TypeScript, TailwindCSS, Zustand, Recharts, Framer Motion
- IA: Mistral Chat Completions API para insights narrativos

## Estrutura

- `backend-go/`: API de alta performance
- `data-pipeline-python/`: ingestao, curadoria, features e forecast
- `frontend-next/`: dashboard e UX
- `data-lake/`: dados raw, curated e warehouse
- `models/`: artefatos de forecast e metadados
- `docs/`: arquitetura, API e operacao

## Fluxo

1. `data-pipeline-python` baixa lotes reais da ANP e padroniza os dados em Parquet.
2. O pipeline materializa um warehouse local em DuckDB e snapshots JSON para a API.
3. O `backend-go` le os snapshots gerados pelo warehouse e expoe endpoints REST.
4. O `frontend-next` consome a API e renderiza dashboards, comparacoes, historico e previsoes.
5. Insights descritivos e explicativos podem usar Mistral via `MISTRAL_API_KEY`.

## Execucao

### 1. Pipeline Python

```powershell
cd data-pipeline-python
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
python -m fuel_analytics.cli run
```

### 2. API Go

```powershell
cd backend-go
go mod tidy
go run ./cmd/api
```

### 3. Frontend Next

```powershell
cd frontend-next
npm install
npm run dev
```

## Dados

- Fonte principal: serie historica da ANP, atualizada em 6 de abril de 2026 segundo a pagina oficial da agencia.
- O banco analitico local e `data-lake/warehouse/fuel_analytics.duckdb`.
- Snapshots consumidos pela API ficam em `models/overview.json`, `models/history.json`, `models/forecasts.json` e `models/market_signals.json`.
- O projeto nao usa mais dados amostrais no fluxo operacional.
- O forecast atual e diario para os proximos `15 dias` e comeca sempre em `amanha`.

## Banco local

- `DuckDB` e a escolha principal para este projeto porque trabalha muito melhor com Parquet, agregacoes analiticas e grandes volumes locais.
- `SQLite` so faria sentido aqui para configuracoes e metadados operacionais, nao para a camada analitica principal.

## Seguranca

- A chave da Mistral nao foi embutida no codigo.
- Configure `MISTRAL_API_KEY` no ambiente antes de habilitar os insights por IA.
- Como a chave foi compartilhada na conversa, a acao prudente e rotaciona-la no painel da Mistral antes de usar em producao.

## Operacao

- Guia de operacao local: [docs/operacao.md](D:/GithubGit/MeuPortfolio/analise_de_combustiveis/docs/operacao.md)
