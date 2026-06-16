# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a portfolio of 11 independent full-stack projects, each self-contained with its own dependencies, tooling, and deployment. There is no shared root-level `package.json`, `requirements.txt`, or build system. All commands must be run from within the specific project directory.

Projects use one of three primary stacks:
- **Next.js + TypeScript + TailwindCSS** (frontend) + **Go** (backend API)
- **Python + Streamlit** (data apps / AI apps)
- **Python + Django** (ERP / full-stack web)

---

## Project Map

| Directory | Description | Stack |
|-----------|-------------|-------|
| `analise_de_combustiveis/` | Fuel price analytics platform | Python pipeline + Go API + Next.js |
| `collab_canvas/` | Real-time multiplayer pixel art | Go WebSocket + Next.js |
| `documind_local/` | Local document AI assistant | Go + Python + Mistral AI + Vanilla JS |
| `finanças/` | Personal ERP (finance, POS, inventory) | Django + SQLite + Bootstrap 5 |
| `gerador_roteiros/` | AI travel itinerary generator | Python + Streamlit + Mistral/Gemini |
| `neon_drift/` | Game backend + frontend | Go + Frontend |
| `neon_snake/` | Arcade game | Go + Frontend |
| `news_sentiment_radar/` | News sentiment analysis dashboard | Go + Dashboard |
| `plataforma_rifas/` | Raffle management system | Python + Streamlit + SQLite + Docker |
| `pricetrack-ai/` | E-commerce price tracker with AI | Python + Streamlit + Gemini + SQLAlchemy |
| `sorteador_rifa_app/` | Raffle draw app | Python + Streamlit + Docker |
| `wealthmap_analytics/` | Wealth / portfolio management | Go + Next.js |

---

## Commands by Stack

### Next.js Projects (frontend directories)

```bash
npm install        # install dependencies
npm run dev        # start dev server (usually :3000)
npm run build      # production build
npm run lint       # ESLint check
```

TypeScript config: strict mode, `moduleResolution: bundler`, `@/*` path alias maps to project root.

**Important:** The Next.js version used may have breaking API changes. Before writing any Next.js code, check `node_modules/next/dist/docs/` for the actual API of the installed version.

### Go Projects (backend directories)

```bash
go run ./cmd/api/main.go      # start the API server
go build ./...                # compile all packages
go test ./...                 # run all tests
go test ./internal/...        # run tests in a specific package
```

Go backends default to port `8080`. The fuel analytics API uses DuckDB (via `go-duckdb`). The collab_canvas backend uses `gorilla/websocket`.

### Python / Streamlit Projects

```bash
pip install -r requirements.txt     # install dependencies
streamlit run app.py                # start the app (or 🏠_Home.py for multi-page)
python -m pytest                    # run tests
python -m pytest tests/test_foo.py  # run a single test file
```

For projects using Docker:
```bash
docker-compose up --build           # build and start all services
docker-compose down                 # stop services
```

### Django Project (`finanças/`)

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver          # dev server on :8000
python manage.py createsuperuser
```

Secrets go in `.env` (see `.env.example`). The project also ships a `run.bat` / `run_app.py` launcher for Windows .exe distribution via PyInstaller.

---

## Architecture Patterns

### Fuel Analytics (`analise_de_combustiveis/`)

Three-tier pipeline:
1. **Python data pipeline** — downloads ANP fuel data, processes with Polars/PyArrow, writes Parquet → DuckDB warehouse.
2. **Go REST API** (`cmd/api/main.go`) — reads from DuckDB/JSON snapshots, calls Mistral AI for narrative insights, exposes endpoints consumed by the frontend.
3. **Next.js dashboard** — SSR + client-side charts (Recharts), Zustand store for filters/state, server-side data fetching via `lib/api.ts`.

### CollabCanvas (`collab_canvas/`)

- **Go backend**: mutex-protected pixel matrix, WebSocket broadcast (new client gets full state snapshot, then receives/sends delta updates).
- **Next.js frontend**: custom hook `useWebSocketBoard` manages state, HTML5 Canvas for rendering, color palette + cooldown UI on top.

### Streamlit Projects

All share the same pattern:
- `app.py` is the entry point; multi-page apps use numbered files in `pages/` (e.g., `01_Overview.py`).
- `st.session_state` for in-session persistence.
- `core/` for business logic, `utils/` for helpers.
- API keys managed via `.streamlit/secrets.toml` (never committed) or environment variables.

### Go Internal Layout (all Go backends)

```
cmd/api/main.go          ← entry point
internal/
  config/                ← env/config loading
  domain/                ← core structs/interfaces
  http/
    router.go            ← chi router setup
    handlers.go          ← request handlers
  repository/            ← data access (DuckDB, files)
  service/               ← business logic
```

### Django ERP (`finanças/`)

App-oriented structure: `core/`, `app_pdv/`, `app_estoque/`, `app_fiscal/` — each is a Django app with its own `views.py`, `urls.py`, `models.py`. Templates live in `templates/`. Static assets in `static/`.

---

## Environment Variables & Secrets

- AI API keys: `MISTRAL_API_KEY`, `GEMINI_API_KEY`
- Database: `DATABASE_URL`
- Streamlit secrets: `.streamlit/secrets.toml`
- Django: `.env` file (see `.env.example` in `finanças/`)
- Next.js: `NEXT_PUBLIC_API_URL` for the Go backend URL

Projects use a dual-provider AI strategy: Mistral AI as primary, Google Gemini as fallback.

---

## Code Quality & CI

### Python (enforced in CI for `gerador_roteiros/` and `plataforma_rifas/`)

```bash
black .              # formatting
isort .              # import sorting
ruff check .         # fast linting (plataforma_rifas)
flake8 .             # linting (gerador_roteiros)
mypy .               # type checking
bandit -r src/       # security scan
```

### GitHub Actions

- `gerador_roteiros/.github/workflows/ci.yml`: tests across Python 3.8–3.12 matrix, lint/format/type-check/security, pytest with coverage, Docker build+push on `main`.
- `plataforma_rifas/.github/workflows/ci.yml`: ruff + black + isort + Docker build.

---

## Key Conventions

- **Language**: project names and most code comments are in Portuguese (Brazilian); variable names inside code may be English or Portuguese depending on the project.
- **Python style**: Loguru for structured logging (`from loguru import logger`), Pydantic for data validation, SQLAlchemy 2.x ORM.
- **Go style**: standard library preferred; chi for routing; `internal/` package for all non-public code.
- **TypeScript**: strict mode throughout; `clsx`/`tailwind-merge`/`class-variance-authority` for conditional class composition.
- **Data**: Polars (not pandas) + Parquet for any data pipeline work; DuckDB for OLAP queries.
- **Timezone**: `TZ=America/Sao_Paulo` used in Docker deployments.
