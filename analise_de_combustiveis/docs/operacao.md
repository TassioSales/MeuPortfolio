# Operacao Local

## Objetivo

Este projeto entrega uma plataforma local de analise de combustiveis com tres blocos:

- `data-pipeline-python`: baixa, normaliza e materializa dados da ANP
- `backend-go`: expoe a API consumida pelo dashboard
- `frontend-next`: interface analitica

## Fluxo recomendado

1. Atualizar os artefatos:

```powershell
& .\data-pipeline-python\.venv\Scripts\python.exe -m fuel_analytics.cli run
```

2. Subir a API:

```powershell
cd backend-go
go run ./cmd/api
```

3. Subir o frontend:

```powershell
cd frontend-next
npm run dev
```

## Script unico

Para desenvolvimento local no Windows, use:

```powershell
.\run.bat
```

Ele:

- garante a venv do pipeline
- sincroniza dependencias Python, Go e Node
- roda o pipeline completo
- inicia backend e frontend
- grava logs em `logs/`

## Logs

- bootstrap: `logs/run.log`
- pipeline: `logs/pipeline.stdout.log`
- backend: `logs/backend.log`
- frontend: `logs/frontend.log`

## Previsoes

- o forecast e materializado em `models/forecasts.json`
- o horizonte atual e diario para os proximos `15 dias`
- a previsao sempre comeca em `amanha`, nunca em `hoje`

## Mistral

Para habilitar os briefings:

- definir `MISTRAL_API_KEY`
- opcionalmente definir `MISTRAL_MODEL`

O backend le `.env.local` e `.env.local.example` como fallback operacional.

## Estado atual do produto

Hoje o projeto esta pronto para:

- rodar localmente ponta a ponta
- atualizar dados da ANP
- gerar previsoes curtas
- servir dashboards por combustivel, historico, comparacao e mercado

Pendencias de produto mais avancado:

- mapa real por UF com geometrias oficiais
- testes E2E do frontend
- estrategia de deploy padronizada
