# Encurtador URL

A full-stack URL shortener built with **Go** (backend) and **Next.js + Tailwind CSS** (frontend).

## Stack

| Layer    | Tech                                          |
|----------|-----------------------------------------------|
| Backend  | Go 1.22, chi router, SQLite (modernc/sqlite)  |
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Recharts|

## Project Structure

```
encurtador_url/
├── backend/
│   ├── cmd/api/main.go          # Entry point
│   └── internal/
│       ├── shortener/service.go # Base62 short-code generation
│       ├── storage/sqlite.go    # SQLite repository
│       ├── analytics/tracker.go # Click recording
│       └── http/                # Router + handlers
├── frontend/
│   ├── app/                     # Next.js App Router pages
│   ├── components/              # ShortenForm, URLCard, ClicksChart
│   └── lib/api.ts               # Typed fetch helpers
├── .env.example
└── start_encurtador.bat         # Windows quick-start
```

## Running locally

### Backend

```bash
cd backend
go run ./cmd/api
# Listens on :8080
```

Environment variables (see `.env.example`):

| Variable   | Default              | Description          |
|------------|----------------------|----------------------|
| `PORT`     | `8080`               | HTTP port            |
| `DB_PATH`  | `./encurtador.db`    | SQLite database path |
| `BASE_URL` | `http://localhost:8080` | Used in responses |

### Frontend

```bash
cd frontend
npm install
npm run dev
# Listens on :3000
```

Requests to `/api/*` and `/r/*` are proxied to the Go backend via `next.config.ts`.

### Windows one-click

Double-click **`start_encurtador.bat`** — it opens two terminal windows (backend + frontend).

## API Endpoints

| Method | Path                      | Description                    |
|--------|---------------------------|--------------------------------|
| POST   | `/api/shorten`            | Create a short URL             |
| GET    | `/r/{code}`               | Redirect to original URL       |
| GET    | `/api/urls`               | List all URLs with click count |
| GET    | `/api/urls/{code}/stats`  | Daily clicks (last 30 days)    |
| GET    | `/api/health`             | Health check                   |
