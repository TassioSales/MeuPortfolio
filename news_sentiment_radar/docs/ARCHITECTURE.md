# Architecture

O projeto usa Go para backend e um frontend estatico sem build step.

```txt
backend/
  cmd/server       servidor HTTP
  internal/news    coleta RSS e armazenamento em memoria
  internal/analyzer sentimento, setores e entidades
frontend/
  index.html
  src/
```

Fluxo:

1. O backend carrega fontes RSS configuradas.
2. Cada item e normalizado para `Article`.
3. O analisador atribui sentimento, setor e entidades.
4. O dashboard consome `/api/summary` e `/api/articles`.

A V1 mantem dados em memoria. Evolucoes naturais:

- persistir em DuckDB/PostgreSQL;
- agendar coleta com Windows Task Scheduler;
- adicionar deduplicacao por hash persistente;
- trocar heuristica por modelo local ou API de IA;
- exportar relatorios PDF/CSV.
