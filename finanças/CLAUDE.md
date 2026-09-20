# CLAUDE.md — finanças

Guidance for Claude Code when working in this Django project.

## Project Overview

Full-stack personal finance ERP built with Django 5.1.4. Single Django app (`core`) with multi-model financial management: transactions, budgets, investments (variable + fixed income + FX), goals, recurring transactions, and PDF/CSV reports.

The project also ships as a standalone Windows executable via PyInstaller + Waitress.

## Stack

| Layer | Technology |
|-------|-----------|
| Framework | Django 5.1.4 |
| Database | SQLite (default) or PostgreSQL (env vars) |
| Forms | django-crispy-forms + crispy-bootstrap5 |
| PDF | xhtml2pdf |
| Market data | yfinance + manual Yahoo Finance fallback |
| Logging | Loguru |
| Static files | WhiteNoise |
| WSGI server | Waitress (production) |
| Build | PyInstaller (Windows .exe) |

## Commands

```bash
# Install
pip install -r requirements.txt

# Database setup
python manage.py migrate

# Run dev server
python manage.py runserver

# Create superuser
python manage.py createsuperuser

# Run tests
python -m pytest
# or
python manage.py test core

# Reset sample data
python manage.py reset_data

# Build Windows executable
build.bat
```

## Directory Structure

```
finanças/
├── core/                      # Main Django app
│   ├── models.py              # 6 models: Category, Transaction, RecurringTransaction,
│   │                          #            Budget, Investment, Goal
│   ├── views.py               # Thin re-export aggregator — DO NOT add logic here
│   ├── views_dashboard.py     # register, dashboard, calendar_view
│   ├── views_categories.py    # Category CRUD
│   ├── views_transactions.py  # Transaction CRUD + import_transactions
│   ├── views_budgets.py       # Budget CRUD
│   ├── views_reports.py       # reports, export_csv, export_pdf
│   ├── views_investments.py   # investment_dashboard, safe_haven_dashboard,
│   │                          # search_ticker, Investment CRUD
│   ├── views_goals.py         # Goal CRUD
│   ├── views_shared.py        # fix_ssl(), get_price_manual() — shared helpers
│   ├── forms.py               # 6 forms with Brazilian currency cleaning
│   ├── services.py            # process_recurring_transactions()
│   ├── market_data.py         # BCB API wrappers (SELIC, CDI, FX rates)
│   ├── templatetags/
│   │   └── core_extras.py     # Custom template filters
│   └── urls.py                # 54 URL routes
├── finance_project/
│   ├── settings.py            # Main settings
│   └── urls.py                # Project router
├── templates/                 # All HTML templates
├── static/                    # CSS + favicon
├── manage.py
├── run_app.py                 # PyInstaller entry point
└── requirements.txt
```

## Key Conventions

### Views
- Views are split into focused modules (`views_*.py`) — never add to `views.py` itself.
- Always use `LoginRequiredMixin` for class-based views and `@login_required` for FBVs.
- All querysets must filter by `user=request.user` to prevent cross-user data leakage.

### Models
- Monetary fields use `DecimalField` with `max_digits=15, decimal_places=2`.
- `Investment.total_cost` is a property (`quantity × purchase_price`), not a stored field.
- `RecurringTransaction.next_run_date` is updated by `services.process_recurring_transactions()`.

### Forms
- Brazilian currency format (1.234,56) is cleaned by `clean_currency_value()` in `forms.py`.
- Always call this helper for `DecimalField` inputs — do not parse manually.

### Market Data
- `views_shared.fix_ssl()` must run at import time to work around certifi path issues on Windows.
- `get_price_manual()` is the last-resort fallback when yfinance fails.
- For real-time FX/SELIC data, use functions from `core/market_data.py` (BCB SGSA API).
- **Cache yfinance calls** — Yahoo Finance rate-limits aggressively; avoid calling it per request.

### Templates
- All templates extend `templates/base.html`.
- Use `{% load core_extras %}` to access custom filters (e.g., `|brl_currency`).
- PDF templates (e.g., `reports_pdf.html`) must use inline CSS — xhtml2pdf does not support external sheets.

### Security
- Never hardcode SECRET_KEY — load from environment via `python-decouple` or `os.environ`.
- `ALLOWED_HOSTS` must not be `["*"]` in production.
- All investment/transaction writes must validate `request.user` ownership before saving.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (hardcoded fallback) | Django secret key — always override in production |
| `django_debug` | `True` | Set to `False` in production |
| `DB_NAME` | — | PostgreSQL database name (leave blank for SQLite) |
| `DB_USER` | — | PostgreSQL user |
| `DB_PASSWORD` | — | PostgreSQL password |
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `SQLITE_DB_PATH` | `db.sqlite3` | Custom SQLite path |

## Tests

Test files are split by feature:

| File | Coverage |
|------|---------|
| `core/tests.py` | General model + view tests |
| `core/tests_alerts.py` | Budget alert logic |
| `core/tests_calendar.py` | Calendar view |
| `core/tests_goals.py` | Goal progress |
| `core/tests_import.py` | CSV import |
| `core/tests_recurrence.py` | Recurring transaction generation |

Run all: `python manage.py test core`

## Common Pitfalls

- `views_shared.fix_ssl()` is called at module import — importing `views_shared` twice is safe (idempotent env vars).
- `market_data.py` makes HTTP requests to the BCB API — mock these in tests to avoid network dependency.
- PyInstaller builds (`dist/`) are excluded from git via `.gitignore`.
