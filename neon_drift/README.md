# Neon Drift

Jogo single-player arcade com backend Go para configuracao e leaderboard.

## Como rodar

```bat
start_neon_drift.bat
```

Abra:

```txt
http://localhost:8090
```

Para parar:

```bat
stop_neon_drift.bat
```

## Estrutura

```txt
backend/   API Go e servidor dos arquivos estaticos
frontend/  Jogo em HTML5 Canvas, CSS e JavaScript modular
docs/      Planejamento e arquitetura
```

## API

- `GET /api/health`
- `GET /api/config`
- `GET /api/leaderboard`
- `POST /api/scores`
