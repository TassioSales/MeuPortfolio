# Arquitetura

## Camadas

- Ingestao: `httpx` baixa arquivos da ANP e dados externos.
- Curadoria: `polars` limpa, tipa e padroniza.
- Armazenamento: dados em Parquet e consultas analiticas no DuckDB.
- Forecast: cenarios conservador, realista e agressivo com regressao exogena.
- API: Go consulta o warehouse e opcionalmente a Mistral.
- Frontend: Next.js consome a API e renderiza o dashboard.

## Data Lake

- `data-lake/raw/`: arquivos baixados sem transformacao.
- `data-lake/curated/`: parquet particionado por combustivel, ano e UF.
- `data-lake/warehouse/`: DuckDB e tabelas agregadas.
- `models/`: json de forecast, metricas e metadados.

## Componentes

- Pipeline Python com Prefect para cargas completas e incrementais.
- API Go com `chi` e repositorio DuckDB.
- Frontend com estado global em Zustand.
- Cartograma SVG para visao do Brasil por estado.

