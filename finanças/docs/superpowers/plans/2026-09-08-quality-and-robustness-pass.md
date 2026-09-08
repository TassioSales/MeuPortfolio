# Passada de Qualidade e Robustez (finanças) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the security, correctness, performance, logging, and frontend-consistency issues found in the full-system audit of `finanças/` (Django personal-finance ERP), and redesign the login/register pages — without adding new product features.

**Architecture:** No architectural change. Same Django 5.1 app (`core`), same Bootstrap 5 + Loguru + SQLite/Postgres stack. Each task is an isolated, independently testable fix inside the existing module layout (`views_*.py`, `forms.py`, `models.py`, `templates/`, `static/`).

**Tech Stack:** Django 5.1.4, python-decouple, Loguru, Bootstrap 5.3, Chart.js, crispy-forms, SQLite (dev) / Postgres (optional), pytest via `python manage.py test`.

## Global Constraints

- No new product features — only fixes to existing behavior (logging, security, correctness, performance, frontend consistency) plus the explicitly-requested login/register redesign.
- Do not break the PyInstaller/Windows `.exe` packaging path (`run_app.py`, `build.bat`).
- All querysets that touch user data must stay scoped to `request.user` — never regress this.
- Keep Bootstrap 5 + the existing `static/css/custom.css` design tokens (`--brand-gradient`, `--brand-glow`, `.glass-card`, `--bg-mesh`, `--radius-*`) — no new CSS framework, no new JS framework.
- Money fields use `Decimal`; never introduce float rounding for stored amounts.
- Run `python manage.py test core` after every task — it must stay green throughout.
- Brazilian Portuguese stays the UI/user-facing language; code/comments can be English or Portuguese matching the surrounding file.

---

### Task 1: Remove duplicate Django logging config (keep Loguru as the single sink)

**Files:**
- Modify: `finance_project/settings.py:233-274`

**Interfaces:**
- Produces: no code-level interface change — pure config cleanup. Behavior: every `logger.info/warning/error` call (Loguru or intercepted stdlib `logging`) must be written exactly once to stderr and once to `logs/finance.log`.

- [ ] **Step 1: Reproduce the duplicate-log bug manually**

Run: `python manage.py shell -c "import logging; logging.getLogger('core').warning('duplicate-test-marker')"`
Expected: the string `duplicate-test-marker` appears **twice** in the terminal output (once via the `LOGGING` dict's `console` handler, once via `InterceptHandler` → Loguru's stderr sink), and twice across `logs/debug.log` + `logs/finance.log` combined.

- [ ] **Step 2: Remove the traditional `LOGGING` dict**

In `finance_project/settings.py`, delete the entire block from the `# Logging Configuration` comment (line 233) through the end of the `LOGGING = {...}` dict (line 274), i.e. remove:

```python
# Logging Configuration
import os

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOGS_DIR, 'debug.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'core': {  # App specific logger
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

Keep everything above it (the Loguru setup: `logger.remove()`, the two `logger.add(...)` calls, `InterceptHandler`, and `logging.basicConfig(handlers=[InterceptHandler()], level=0)`) untouched — that block is the single active logging path from now on. Since `LOGGING` no longer exists, Django will not call `logging.config.dictConfig`, so it will not attach its own `console`/`file` handlers to the `django`/`core` loggers — they keep propagating to the root logger, which `InterceptHandler` forwards into Loguru.

- [ ] **Step 3: Confirm `debug.log` is no longer written and the duplicate disappears**

Run: `del logs\debug.log` (if it exists) then `python manage.py shell -c "import logging; logging.getLogger('core').warning('duplicate-test-marker')"`
Expected: `duplicate-test-marker` appears **exactly once** in the terminal, and `logs/debug.log` is **not** recreated (only `logs/finance.log` receives it).

- [ ] **Step 4: Run the full test suite**

Run: `python manage.py test core`
Expected: all existing tests still pass (this is a config-only change).

- [ ] **Step 5: Commit**

```bash
git add finance_project/settings.py
git commit -m "fix: remove duplicate Django LOGGING config, Loguru is now the single log sink"
```

---

### Task 2: Standardize on Loguru + log the currently-silent exceptions

**Files:**
- Modify: `core/views_reports.py:1-24` (swap stdlib `logging` for Loguru)
- Modify: `core/market_data.py:1-8` (swap stdlib `logging` for Loguru)
- Modify: `core/views_investments.py` (log 5 silent `except` blocks)
- Modify: `core/views_transactions.py:219-220` (log skipped import rows)
- Modify: `core/forms.py` (hoist `import yfinance as yf` to module level; log the bare `except:`)
- Test: `core/tests_market_data.py` (new)

**Interfaces:**
- Produces: `core.forms` now has a module-level `yf` name (was previously a local import inside `InvestmentForm.clean()`), so it can be mocked as `core.forms.yf.Ticker` in tests.

- [ ] **Step 1: Swap `views_reports.py` to Loguru**

In `core/views_reports.py`, replace:

```python
import csv
import io
import json
import logging
from datetime import timedelta
```

with:

```python
import csv
import io
import json
from datetime import timedelta
```

and replace:

```python
logger = logging.getLogger("core")
```

with:

```python
from loguru import logger
```

(keep this new import near the other imports, right after the `from xhtml2pdf import pisa` line). No other line in the file changes — `logger.info(...)` calls already read the same way in Loguru.

- [ ] **Step 2: Swap `market_data.py` to Loguru**

In `core/market_data.py`, replace:

```python
import logging
import os
import requests
import yfinance as yf
from datetime import datetime, timedelta
from functools import lru_cache

logger = logging.getLogger('core')
```

with:

```python
import os
import requests
import yfinance as yf
from datetime import datetime, timedelta
from functools import lru_cache
from loguru import logger
```

- [ ] **Step 3: Log the silent exceptions in `views_investments.py`**

In `core/views_investments.py`, add `from loguru import logger as log` to the imports (below `from .views_shared import get_price_manual`).

Replace each silent `except Exception: pass` (or equivalent) with a logged version:

```python
    try:
        ticker = yf.Ticker(symbol)
        fi = ticker.fast_info
        result["price"] = getattr(fi, "last_price", None)
        result["currency"] = getattr(fi, "currency", "BRL") or "BRL"
        result["previous_close"] = getattr(fi, "previous_close", None)
        result["day_high"] = getattr(fi, "day_high", None)
        result["day_low"] = getattr(fi, "day_low", None)
        result["year_high"] = getattr(fi, "year_high", None)
        result["year_low"] = getattr(fi, "year_low", None)
    except Exception as e:
        log.warning(f"yfinance fast_info failed for {symbol}: {e}")

    if result["price"] is None:
        try:
            hist1d = ticker.history(period="1d")
            if not hist1d.empty:
                result["price"] = float(hist1d["Close"].iloc[-1])
        except Exception as e:
            log.warning(f"yfinance 1d history failed for {symbol}: {e}")

    try:
        hist = ticker.history(period="6mo")
        if not hist.empty:
            result["history"] = hist
            result["chart_dates"] = [d.strftime("%d/%m/%Y") for d in hist.index]
            result["chart_prices"] = [round(float(v), 4) for v in hist["Close"]]
    except Exception as e:
        log.warning(f"yfinance 6mo history failed for {symbol}: {e}")
```

(this replaces the three bare `except Exception: pass` blocks inside `_cached_ticker_fetch`).

In `investment_dashboard` view, replace:

```python
            try:
                fetched = _cached_ticker_fetch(symbol)
                current_price = fetched["price"]
                ticker_currency = fetched["currency"] or "BRL"

                if current_price is None:
                    current_price, _ = get_price_manual(symbol)

                if current_price is not None and ticker_currency == "USD":
                    current_price *= usd_brl_rate

                if current_price is None:
                    current_price = avg_price
            except Exception:
                current_price = avg_price
```

with:

```python
            try:
                fetched = _cached_ticker_fetch(symbol)
                current_price = fetched["price"]
                ticker_currency = fetched["currency"] or "BRL"

                if current_price is None:
                    current_price, _ = get_price_manual(symbol)

                if current_price is not None and ticker_currency == "USD":
                    current_price *= usd_brl_rate

                if current_price is None:
                    current_price = avg_price
            except Exception as e:
                log.warning(f"Price lookup failed for {symbol}, using avg_price as fallback: {e}")
                current_price = avg_price
```

In `InvestmentDetailView.get_context_data`, replace:

```python
        except Exception as e:
            context["error"] = str(e)
```

with:

```python
        except Exception as e:
            log.error(f"Failed to build investment detail context for {symbol}: {e}")
            context["error"] = str(e)
```

- [ ] **Step 2: Log skipped rows in `import_transactions`**

In `core/views_transactions.py`, add `from loguru import logger as log` to the imports.

Replace:

```python
            try:
                date = datetime.date.fromisoformat(r["date"])
                amount = float(r["amount"])
                type_ = "RECEITA" if amount > 0 else "DESPESA"
                category = None
                if r.get("category"):
                    category, _ = Category.objects.get_or_create(
                        user=request.user,
                        name=r["category"],
                        defaults={"type": type_},
                    )
                Transaction.objects.create(
                    user=request.user,
                    date=date,
                    description=r["description"],
                    amount=abs(amount),
                    type=type_,
                    category=category,
                )
                count += 1
            except Exception:
                continue
```

with:

```python
            try:
                date = datetime.date.fromisoformat(r["date"])
                amount = float(r["amount"])
                type_ = "RECEITA" if amount > 0 else "DESPESA"
                category = None
                if r.get("category"):
                    category, _ = Category.objects.get_or_create(
                        user=request.user,
                        name=r["category"],
                        defaults={"type": type_},
                    )
                Transaction.objects.create(
                    user=request.user,
                    date=date,
                    description=r["description"],
                    amount=abs(amount),
                    type=type_,
                    category=category,
                )
                count += 1
            except Exception as e:
                log.warning(f"Skipped import row {r.get('row', '?')} for user {request.user.username}: {e}")
                continue
```

- [ ] **Step 3: Hoist the yfinance import and log the bare `except:` in `forms.py`**

In `core/forms.py`, add near the top of the file (after `from decimal import Decimal`):

```python
import yfinance as yf
from loguru import logger as log
```

In `InvestmentForm.clean()`, replace:

```python
            # Name fetch logic (simplified here, but can be triggered by JS too)
            if not cleaned_data.get('name'):
                try:
                    import yfinance as yf
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    cleaned_data['name'] = info.get('shortName') or info.get('longName') or symbol
                except:
                    pass
```

with:

```python
            # Name fetch logic (simplified here, but can be triggered by JS too)
            if not cleaned_data.get('name'):
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    cleaned_data['name'] = info.get('shortName') or info.get('longName') or symbol
                except Exception as e:
                    log.warning(f"yfinance name lookup failed for {symbol}: {e}")
```

- [ ] **Step 4: Write the regression test proving the fix logs instead of swallowing**

Create `core/tests_market_data.py`:

```python
from unittest.mock import patch

from django.test import TestCase

from .forms import InvestmentForm


class InvestmentFormLoggingTests(TestCase):
    def test_yfinance_lookup_failure_is_logged_not_swallowed(self):
        with patch("core.forms.yf.Ticker", side_effect=RuntimeError("yfinance down")):
            with self.assertLogs("core.forms", level="WARNING") as captured:
                form = InvestmentForm(data={
                    "category_type": "VARIABLE",
                    "symbol": "PETR4",
                    "name": "",
                    "quantity": "10",
                    "purchase_price": "R$ 30,00",
                    "date": "2026-01-10",
                    "create_transaction": True,
                })
                form.is_valid()

        self.assertTrue(any("yfinance" in message for message in captured.output))
```

- [ ] **Step 5: Run the new test**

Run: `python manage.py test core.tests_market_data -v 2`
Expected: `InvestmentFormLoggingTests` passes.

- [ ] **Step 6: Run the full suite**

Run: `python manage.py test core`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add core/views_reports.py core/market_data.py core/views_investments.py core/views_transactions.py core/forms.py core/tests_market_data.py
git commit -m "fix: standardize on Loguru and log previously-silent exceptions"
```

---

### Task 3: Fix BCB series cache (no TTL today) and log the indicator fallback

**Files:**
- Modify: `core/market_data.py`
- Test: `core/tests_market_data.py` (append)

**Interfaces:**
- Produces: `get_bcb_series(code, start_date_str=None)` — same signature, now backed by `django.core.cache` with a 6-hour TTL instead of an unbounded `functools.lru_cache`.

- [ ] **Step 1: Write the failing test**

Append to `core/tests_market_data.py`:

```python
from django.core.cache import cache

from .market_data import get_bcb_series, get_latest_indicator


class BcbSeriesCacheTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("core.market_data.requests.get")
    def test_series_is_cached_and_not_refetched_within_ttl(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [{"data": "01/01/2026", "valor": "1.0"}]

        first = get_bcb_series(999, "01/01/2026")
        second = get_bcb_series(999, "01/01/2026")

        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(first, second)

    @patch("core.market_data.get_bcb_series", return_value=[])
    def test_get_latest_indicator_logs_when_falling_back_to_zero(self, mock_series):
        with self.assertLogs("core.market_data", level="WARNING") as captured:
            value = get_latest_indicator(432)
        self.assertEqual(value, 0.0)
        self.assertTrue(any("no data" in message.lower() or "sem dados" in message.lower() for message in captured.output))
```

- [ ] **Step 2: Run it to see it fail**

Run: `python manage.py test core.tests_market_data -v 2`
Expected: `BcbSeriesCacheTests` fails — `get_bcb_series` still uses `lru_cache`, so `django.core.cache` is never touched, and `get_latest_indicator` currently logs nothing on fallback.

- [ ] **Step 3: Replace `lru_cache` with `django.core.cache` (6-hour TTL) and log the fallback**

By this point (after Task 2), `core/market_data.py`'s import block reads:

```python
import os
import requests
import yfinance as yf
from datetime import datetime, timedelta
from functools import lru_cache
from loguru import logger
```

Replace it with (drop the now-unused `lru_cache` import, add the Django cache import, keep the `loguru` import from Task 2 untouched):

```python
import os
import requests
import yfinance as yf
from datetime import datetime, timedelta
from django.core.cache import cache
from loguru import logger
```

Replace:

```python
@lru_cache(maxsize=32)
def get_bcb_series(code, start_date_str=None):
    """Fetch series from BCB SGSA API. start_date_str: DD/MM/YYYY."""
    try:
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json"
        if start_date_str:
            url += f"&dataInicial={start_date_str}"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            logger.warning(f"BCB API returned status {response.status_code} for code {code}")
            return []
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching BCB series {code}: {e}")
        return []
```

with:

```python
_BCB_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours — BCB series update at most daily


def get_bcb_series(code, start_date_str=None):
    """Fetch series from BCB SGSA API. start_date_str: DD/MM/YYYY. Cached for 6h."""
    cache_key = f"bcb_series_{code}_{start_date_str or 'all'}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json"
        if start_date_str:
            url += f"&dataInicial={start_date_str}"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            logger.warning(f"BCB API returned status {response.status_code} for code {code}")
            return []
        data = response.json()
        cache.set(cache_key, data, timeout=_BCB_CACHE_TTL_SECONDS)
        return data
    except Exception as e:
        logger.error(f"Error fetching BCB series {code}: {e}")
        return []
```

Replace:

```python
def get_latest_indicator(code):
    """Get the most recent value from a BCB series."""
    start_date = (datetime.now() - timedelta(days=60)).strftime('%d/%m/%Y')
    series = get_bcb_series(code, start_date)
    if series:
        return float(series[-1]['valor'])
    return 0.0
```

with:

```python
def get_latest_indicator(code):
    """Get the most recent value from a BCB series."""
    start_date = (datetime.now() - timedelta(days=60)).strftime('%d/%m/%Y')
    series = get_bcb_series(code, start_date)
    if series:
        return float(series[-1]['valor'])
    logger.warning(f"No data returned for BCB series {code}; falling back to 0.0")
    return 0.0
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `python manage.py test core.tests_market_data -v 2`
Expected: both new tests pass.

- [ ] **Step 5: Run the full suite**

Run: `python manage.py test core`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add core/market_data.py core/tests_market_data.py
git commit -m "fix: cache BCB series with a 6h TTL instead of an unbounded lru_cache, log zero-fallback"
```

---

### Task 4: Scope `category` querysets to the logged-in user (cross-tenant leak fix)

**Files:**
- Modify: `core/forms.py` (`TransactionForm`, `BudgetForm`)
- Modify: `core/views_transactions.py` (`TransactionCreateView`, `TransactionUpdateView`)
- Modify: `core/views_budgets.py` (`BudgetCreateView`, `BudgetUpdateView`)
- Test: `core/tests_security.py` (new)

**Interfaces:**
- Produces: `TransactionForm.__init__(self, *args, user=None, **kwargs)` and `BudgetForm.__init__(self, *args, user=None, **kwargs)` — both filter `self.fields['category'].queryset` to `Category.objects.filter(user=user)` when `user` is provided.

- [ ] **Step 1: Write the failing regression test**

Create `core/tests_security.py`:

```python
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Category


class CrossUserCategoryLeakTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username="alice", password="pass12345")
        self.user_b = User.objects.create_user(username="bob", password="pass12345")
        self.category_b = Category.objects.create(user=self.user_b, name="Categoria do Bob", type="DESPESA")
        self.client.login(username="alice", password="pass12345")

    def test_transaction_form_excludes_other_users_categories(self):
        response = self.client.get(reverse("transaction_add"))
        form = response.context["form"]
        self.assertNotIn(self.category_b, form.fields["category"].queryset)

    def test_cannot_attach_transaction_to_other_users_category(self):
        response = self.client.post(reverse("transaction_add"), {
            "category": self.category_b.pk,
            "type": "DESPESA",
            "amount": "50,00",
            "date": "2026-01-10",
            "payment_method": "DINHEIRO",
            "description": "Tentativa de vazamento",
            "installments": 1,
        })
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_budget_form_excludes_other_users_categories(self):
        response = self.client.get(reverse("budget_add"))
        form = response.context["form"]
        self.assertNotIn(self.category_b, form.fields["category"].queryset)
```

- [ ] **Step 2: Run it to see it fail**

Run: `python manage.py test core.tests_security -v 2`
Expected: all three tests fail — today `form.fields['category'].queryset` is the unfiltered `Category.objects.all()`-equivalent default.

- [ ] **Step 3: Scope `TransactionForm` and `BudgetForm` by user**

In `core/forms.py`, add to `TransactionForm` (right after the `Meta` class, before `clean_amount`):

```python
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['category'].queryset = Category.objects.filter(user=user)
```

Add to `BudgetForm` (right after the `Meta` class, before `clean_limit`):

```python
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['category'].queryset = Category.objects.filter(user=user)
```

- [ ] **Step 4: Pass `user` into the form from the class-based views**

In `core/views_transactions.py`, replace:

```python
class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "core/form.html"
    success_url = reverse_lazy("transaction_list")

    def form_valid(self, form):
```

with:

```python
class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "core/form.html"
    success_url = reverse_lazy("transaction_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
```

and replace:

```python
class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "core/form.html"
    success_url = reverse_lazy("transaction_list")

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)
```

with:

```python
class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "core/form.html"
    success_url = reverse_lazy("transaction_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)
```

In `core/views_budgets.py`, replace:

```python
class BudgetCreateView(LoginRequiredMixin, CreateView):
    model = Budget
    form_class = BudgetForm
    template_name = "core/form.html"
    success_url = reverse_lazy("budget_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)
```

with:

```python
class BudgetCreateView(LoginRequiredMixin, CreateView):
    model = Budget
    form_class = BudgetForm
    template_name = "core/form.html"
    success_url = reverse_lazy("budget_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)
```

and replace:

```python
class BudgetUpdateView(LoginRequiredMixin, UpdateView):
    model = Budget
    form_class = BudgetForm
    template_name = "core/form.html"
    success_url = reverse_lazy("budget_list")

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)
```

with:

```python
class BudgetUpdateView(LoginRequiredMixin, UpdateView):
    model = Budget
    form_class = BudgetForm
    template_name = "core/form.html"
    success_url = reverse_lazy("budget_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)
```

(note: Task 12 later replaces `BudgetListView.get_context_data` and its `get_queryset` in this same file — `BudgetCreateView`/`BudgetUpdateView` are untouched by that task, so this edit stays intact.)

- [ ] **Step 5: Run the tests to see them pass**

Run: `python manage.py test core.tests_security -v 2`
Expected: all three tests pass.

- [ ] **Step 6: Run the full suite**

Run: `python manage.py test core`
Expected: all green — no other view instantiates `TransactionForm`/`BudgetForm` directly, so this cannot regress any other flow.

- [ ] **Step 7: Commit**

```bash
git add core/forms.py core/views_transactions.py core/views_budgets.py core/tests_security.py
git commit -m "fix: scope TransactionForm/BudgetForm category queryset to the logged-in user"
```

---

### Task 5: Restrict `settings_view` to staff users + make the `.env` write atomic

**Files:**
- Modify: `core/views_settings.py`
- Test: `core/tests_settings.py` (new)

**Interfaces:**
- Produces: `settings_view` now returns a redirect to `dashboard` (with an error message) for any authenticated non-staff user, instead of rendering the page.

- [ ] **Step 1: Write the failing test**

Create `core/tests_settings.py`:

```python
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class SettingsAccessTests(TestCase):
    def test_non_staff_user_is_redirected_away(self):
        User.objects.create_user(username="karl", password="pass12345")
        self.client.login(username="karl", password="pass12345")
        response = self.client.get(reverse("settings"), follow=True)
        self.assertRedirects(response, reverse("dashboard"))

    def test_staff_user_can_access_settings(self):
        User.objects.create_user(username="laura", password="pass12345", is_staff=True)
        self.client.login(username="laura", password="pass12345")
        response = self.client.get(reverse("settings"))
        self.assertEqual(response.status_code, 200)
```

- [ ] **Step 2: Run it to see it fail**

Run: `python manage.py test core.tests_settings -v 2`
Expected: `test_non_staff_user_is_redirected_away` fails — today any logged-in user gets a `200`.

- [ ] **Step 3: Add the staff check and make the `.env` write atomic**

In `core/views_settings.py`, replace:

```python
def _write_env(env: dict) -> None:
    env_path = _find_env_path()
    lines = [f"{k}={v}" for k, v in env.items()]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@login_required
def settings_view(request):
    env = _read_env()
```

with:

```python
def _write_env(env: dict) -> None:
    """Write .env atomically: write to a temp file, then rename over the target."""
    env_path = _find_env_path()
    lines = [f"{k}={v}" for k, v in env.items()]
    content = "\n".join(lines) + "\n"
    tmp_path = env_path.with_suffix(env_path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(env_path)


@login_required
def settings_view(request):
    if not request.user.is_staff:
        messages.error(request, "Você não tem permissão para acessar as configurações do sistema.")
        return redirect("dashboard")

    env = _read_env()
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `python manage.py test core.tests_settings -v 2`
Expected: both tests pass.

- [ ] **Step 5: Run the full suite**

Run: `python manage.py test core`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add core/views_settings.py core/tests_settings.py
git commit -m "fix: restrict settings_view to staff users, write .env atomically"
```

**Manual note for the user:** after this change, only accounts with `is_staff=True` can reach `/settings/`. Promote your own account if needed: `python manage.py shell -c "from django.contrib.auth.models import User; u = User.objects.get(username='YOUR_USERNAME'); u.is_staff = True; u.save()"`.

---

### Task 6: Validate upload size/type for CSV/XLSX and OFX imports

**Files:**
- Modify: `core/forms.py` (`ImportFileForm`)
- Modify: `core/views_ofx.py` (`import_ofx`)
- Test: `core/tests_uploads.py` (new)

**Interfaces:**
- Produces: `ImportFileForm.clean_file()` rejects non-`.csv`/`.xlsx` files and files over 5 MB with a form error on the `file` field.

- [ ] **Step 1: Write the failing tests**

Create `core/tests_uploads.py`:

```python
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse


class ImportUploadValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ivan", password="pass12345")
        self.client.login(username="ivan", password="pass12345")

    def test_rejects_disallowed_extension(self):
        bad_file = SimpleUploadedFile("extrato.exe", b"conteudo qualquer", content_type="application/octet-stream")
        response = self.client.post(reverse("transaction_import"), {"file": bad_file})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)

    def test_rejects_oversized_file(self):
        big_content = b"a" * (6 * 1024 * 1024)
        big_file = SimpleUploadedFile("extrato.csv", big_content, content_type="text/csv")
        response = self.client.post(reverse("transaction_import"), {"file": big_file})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)


class OfxUploadValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="julia", password="pass12345")
        self.client.login(username="julia", password="pass12345")

    def test_rejects_disallowed_extension(self):
        bad_file = SimpleUploadedFile("extrato.txt", b"not ofx", content_type="text/plain")
        response = self.client.post(reverse("import_ofx"), {"ofx_file": bad_file}, follow=True)
        page_messages = list(response.context["messages"])
        self.assertTrue(any(".ofx" in str(m) for m in page_messages))

    def test_rejects_oversized_file(self):
        big_content = b"a" * (6 * 1024 * 1024)
        big_file = SimpleUploadedFile("extrato.ofx", big_content, content_type="application/x-ofx")
        response = self.client.post(reverse("import_ofx"), {"ofx_file": big_file}, follow=True)
        page_messages = list(response.context["messages"])
        self.assertTrue(any("grande" in str(m) for m in page_messages))
```

- [ ] **Step 2: Run them to see them fail**

Run: `python manage.py test core.tests_uploads -v 2`
Expected: all four tests fail — no size/type validation exists yet.

- [ ] **Step 3: Add validation to `ImportFileForm`**

In `core/forms.py`, replace:

```python
class ImportFileForm(forms.Form):
    file = forms.FileField(
        label="Arquivo de Extrato",
        help_text="Formatos aceitos: CSV ou XLSX",
    )
```

with:

```python
class ImportFileForm(forms.Form):
    MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
    ALLOWED_EXTENSIONS = ('.csv', '.xlsx')

    file = forms.FileField(
        label="Arquivo de Extrato",
        help_text="Formatos aceitos: CSV ou XLSX (máx. 5 MB)",
    )

    def clean_file(self):
        uploaded = self.cleaned_data['file']
        name = uploaded.name.lower()
        if not name.endswith(self.ALLOWED_EXTENSIONS):
            raise forms.ValidationError("Envie um arquivo .csv ou .xlsx.")
        if uploaded.size > self.MAX_UPLOAD_SIZE:
            raise forms.ValidationError("Arquivo muito grande (máximo 5 MB).")
        return uploaded
```

- [ ] **Step 4: Add manual validation to `import_ofx`**

In `core/views_ofx.py`, replace:

```python
@login_required
def import_ofx(request):
    if request.method == "POST":
        uploaded = request.FILES.get("ofx_file")
        if not uploaded:
            messages.error(request, "Nenhum arquivo enviado.")
            return redirect("import_ofx")

        try:
```

with:

```python
MAX_OFX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_OFX_EXTENSIONS = (".ofx", ".qfx")


@login_required
def import_ofx(request):
    if request.method == "POST":
        uploaded = request.FILES.get("ofx_file")
        if not uploaded:
            messages.error(request, "Nenhum arquivo enviado.")
            return redirect("import_ofx")

        if not uploaded.name.lower().endswith(ALLOWED_OFX_EXTENSIONS):
            messages.error(request, "Envie um arquivo .ofx ou .qfx.")
            return redirect("import_ofx")

        if uploaded.size > MAX_OFX_UPLOAD_SIZE:
            messages.error(request, "Arquivo muito grande (máximo 5 MB).")
            return redirect("import_ofx")

        try:
```

- [ ] **Step 5: Run the tests to see them pass**

Run: `python manage.py test core.tests_uploads -v 2`
Expected: all four tests pass.

- [ ] **Step 6: Run the full suite**

Run: `python manage.py test core`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add core/forms.py core/views_ofx.py core/tests_uploads.py
git commit -m "fix: validate size/type of CSV, XLSX, and OFX statement uploads"
```

---

### Task 7: Harden `SECRET_KEY`/`DEBUG` defaults for the packaged entry point (`run_app.py`)

**Files:**
- Modify: `run_app.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `run_app.py` sets `os.environ["DEBUG"] = "False"` (unless already set) and guarantees `os.environ["SECRET_KEY"]` is populated (from `.env`, from a persisted `.secret_key` file, or freshly generated) before `django.setup()` runs. `manage.py runserver` is untouched — it keeps `DEBUG` defaulting to `True` per `settings.py`.

**Important interaction with WhiteNoise:** `whitenoise.middleware.WhiteNoiseMiddleware` only serves files from `STATIC_ROOT` when `DEBUG=False` — today it silently also serves straight from `STATICFILES_DIRS` (the `static/` source folder) because `DEBUG` defaults to `True` for `run_app.py`. `build.bat` already runs `collectstatic` before packaging the `.exe`, so the frozen path is unaffected — but the everyday `run.bat` → `python run_app.py` path (used throughout this conversation) never runs `collectstatic`. Forcing `DEBUG=False` without also fixing this would make every static asset (including the `static/js/charts.js` added in Task 17) 404 the moment this task lands. Step 3 below adds an automatic `collectstatic` call, mirroring the existing `migrate` call already in `run_app.py`, so this can never regress regardless of which entry point is used.

- [ ] **Step 1: Reproduce the current insecure default**

Run: `cd /d "%~dp0" && python -c "import os; os.environ.pop('DEBUG', None); os.environ.pop('SECRET_KEY', None); import django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_project.settings'); django.setup(); from django.conf import settings; print(settings.DEBUG, settings.SECRET_KEY[:20])"`
Expected: prints `True django-insecure-hux^5!#g^za` (or similar) — confirms `run_app.py`'s production entry point currently inherits the insecure dev defaults whenever `.env` doesn't override them.

- [ ] **Step 2: Add the hardening block to `run_app.py`**

In `run_app.py`, replace:

```python
    # ── Environment variables (must be set BEFORE django.setup()) ─────────────
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finance_project.settings")

    # Point the SQLite database to a writable location beside the exe
    db_path = data_dir / "patrimonio.db"
    os.environ.setdefault("SQLITE_DB_PATH", str(db_path))

    # ── Django bootstrap ──────────────────────────────────────────────────────
    import django
    django.setup()
```

with:

```python
    # ── Environment variables (must be set BEFORE django.setup()) ─────────────
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finance_project.settings")

    # Point the SQLite database to a writable location beside the exe
    db_path = data_dir / "patrimonio.db"
    os.environ.setdefault("SQLITE_DB_PATH", str(db_path))

    # ── Production hardening ───────────────────────────────────────────────────
    # run_app.py (whether launched via run.bat or as the packaged .exe) is the
    # real "production" entry point of this app — manage.py runserver stays the
    # only place that keeps the permissive dev defaults from settings.py.
    os.environ.setdefault("DEBUG", "False")

    if not os.environ.get("SECRET_KEY"):
        env_path = data_dir / ".env"
        existing_key = _read_env_value(env_path, "SECRET_KEY")
        if existing_key:
            os.environ["SECRET_KEY"] = existing_key
        else:
            secret_key_file = data_dir / ".secret_key"
            if secret_key_file.exists():
                os.environ["SECRET_KEY"] = secret_key_file.read_text(encoding="utf-8").strip()
            else:
                from django.core.management.utils import get_random_secret_key
                new_key = get_random_secret_key()
                secret_key_file.write_text(new_key, encoding="utf-8")
                os.environ["SECRET_KEY"] = new_key

    # ── Django bootstrap ──────────────────────────────────────────────────────
    import django
    django.setup()
```

Add the helper function above `def main():`:

```python
def _read_env_value(env_path: Path, key: str) -> str | None:
    """Read a single KEY=value line from a .env-style file without importing decouple."""
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return None
```

- [ ] **Step 3: Make `run_app.py` always run `collectstatic` before serving (required once `DEBUG=False`)**

In `run_app.py`, replace:

```python
    from django.core.management import call_command

    print("Verificando banco de dados...")
    try:
        call_command("migrate", verbosity=0)
    except Exception as exc:
        print(f"Aviso ao migrar: {exc}")
```

with:

```python
    from django.core.management import call_command

    print("Verificando banco de dados...")
    try:
        call_command("migrate", verbosity=0)
    except Exception as exc:
        print(f"Aviso ao migrar: {exc}")

    print("Verificando arquivos estáticos...")
    try:
        call_command("collectstatic", verbosity=0, interactive=False)
    except Exception as exc:
        print(f"Aviso ao coletar arquivos estáticos: {exc}")
```

(WhiteNoise only serves from `STATIC_ROOT` when `DEBUG=False`, which this task just made the default here — running `collectstatic` on every startup keeps `STATIC_ROOT` in sync with `static/` regardless of whether `build.bat` was ever run, and is idempotent/cheap enough to run unconditionally on a desktop app's startup.)

- [ ] **Step 4: Ignore the generated secret-key file and collected static files in git**

In `.gitignore`, under the `# Environment` section, add a new line after `.env`:

```
.secret_key
```

(`staticfiles/` — the `collectstatic` output directory from Step 3 — is already ignored by the existing `staticfiles/` line under the `# Django` section.)

- [ ] **Step 5: Run the app and confirm it still starts, with static files intact**

Run: `python run_app.py` (let it start, then leave it running)
Expected console output: `Verificando banco de dados...`, then the new `Verificando arquivos estáticos...` line, then the usual startup banner on port 8080. A `.secret_key` file appears next to `manage.py` (only if `.env` had no `SECRET_KEY`), and a `staticfiles/` folder is populated with `css/custom.css`, `js/charts.js` (once Task 17 lands), etc.

With the app still running, open `http://127.0.0.1:8080/login/` in a browser and confirm the page is fully styled (gradients, fonts, glass-card look) — this specifically proves `DEBUG=False` + the new `collectstatic` call didn't break WhiteNoise's static serving. Stop the server with `Ctrl+C`.

- [ ] **Step 6: Run the full test suite**

Run: `python manage.py test core`
Expected: all green — `manage.py test` goes through `manage.py`, not `run_app.py`, so `DEBUG`/`SECRET_KEY` defaults for the test runner are unaffected.

- [ ] **Step 7: Commit**

```bash
git add run_app.py .gitignore
git commit -m "fix: force DEBUG=False and a persisted SECRET_KEY for the run_app.py production entry point"
```

---

### Task 8: Reject negative/zero monetary values (model validators + form checks)

**Files:**
- Modify: `core/models.py` (`Transaction.amount`, `Budget.limit`, `Goal.target_amount`, `Goal.current_amount`, `Goal.monthly_target`)
- Modify: `core/forms.py` (`TransactionForm.clean_amount`, `BudgetForm.clean_limit`, `GoalForm.clean_target_amount`/`clean_current_amount`/`clean_monthly_target`, `GoalDepositForm.clean_amount`)
- Create: `core/migrations/0011_add_min_value_validators.py` (generated by `makemigrations`)
- Test: `core/tests_validation.py` (new)

**Interfaces:**
- Produces: posting a transaction/budget/goal with an amount ≤ 0 now returns the form re-rendered with a field error, instead of silently saving a negative value that corrupts dashboard aggregates.

- [ ] **Step 1: Write the failing tests**

Create `core/tests_validation.py`:

```python
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Category


class NegativeAmountValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="dora", password="pass12345")
        self.client.login(username="dora", password="pass12345")
        self.category = Category.objects.create(user=self.user, name="Mercado", type="DESPESA")

    def test_transaction_rejects_negative_amount(self):
        response = self.client.post(reverse("transaction_add"), {
            "category": self.category.pk,
            "type": "DESPESA",
            "amount": "-50,00",
            "date": "2026-01-10",
            "payment_method": "DINHEIRO",
            "description": "Valor inválido",
            "installments": 1,
        })
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_transaction_rejects_zero_amount(self):
        response = self.client.post(reverse("transaction_add"), {
            "category": self.category.pk,
            "type": "DESPESA",
            "amount": "0",
            "date": "2026-01-10",
            "payment_method": "DINHEIRO",
            "description": "Valor zero",
            "installments": 1,
        })
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_budget_rejects_negative_limit(self):
        response = self.client.post(reverse("budget_add"), {
            "category": self.category.pk,
            "limit": "-100,00",
            "period": "MENSAL",
            "start_date": "2026-01-01",
        })
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("limit", form.errors)

    def test_goal_rejects_negative_target(self):
        response = self.client.post(reverse("goal_add"), {
            "name": "Viagem",
            "target_amount": "-1000,00",
            "current_amount": "0",
            "deadline": "2026-12-31",
            "description": "",
        })
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("target_amount", form.errors)
```

- [ ] **Step 2: Run them to see them fail**

Run: `python manage.py test core.tests_validation -v 2`
Expected: all four tests fail — negative/zero amounts currently save successfully (302 redirect, not a re-rendered form with errors).

- [ ] **Step 3: Add form-level rejections**

In `core/forms.py`, replace:

```python
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        # If the field is already a Decimal (Django might have tried its own cleaning), handle it
        if isinstance(amount, Decimal):
            return amount
        # Otherwise clean the string
        return clean_currency_value(self.data.get('amount'))
```

(inside `TransactionForm`) with:

```python
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        # If the field is already a Decimal (Django might have tried its own cleaning), handle it
        if isinstance(amount, Decimal):
            value = amount
        else:
            value = clean_currency_value(self.data.get('amount'))
        if value is not None and value <= 0:
            raise forms.ValidationError("O valor deve ser maior que zero.")
        return value
```

Replace (inside `BudgetForm`):

```python
    def clean_limit(self):
        return clean_currency_value(self.data.get('limit'))
```

with:

```python
    def clean_limit(self):
        value = clean_currency_value(self.data.get('limit'))
        if value is not None and value <= 0:
            raise forms.ValidationError("O limite deve ser maior que zero.")
        return value
```

Replace (inside `GoalForm`):

```python
    def clean_target_amount(self):
        return clean_currency_value(self.data.get('target_amount'))

    def clean_current_amount(self):
        return clean_currency_value(self.data.get('current_amount'))

    def clean_monthly_target(self):
        val = self.data.get('monthly_target', '').strip()
        if not val:
            return None
        return clean_currency_value(val)
```

with:

```python
    def clean_target_amount(self):
        value = clean_currency_value(self.data.get('target_amount'))
        if value is not None and value <= 0:
            raise forms.ValidationError("O valor alvo deve ser maior que zero.")
        return value

    def clean_current_amount(self):
        value = clean_currency_value(self.data.get('current_amount'))
        if value is not None and value < 0:
            raise forms.ValidationError("O valor guardado não pode ser negativo.")
        return value

    def clean_monthly_target(self):
        val = self.data.get('monthly_target', '').strip()
        if not val:
            return None
        value = clean_currency_value(val)
        if value is not None and value <= 0:
            raise forms.ValidationError("O aporte mensal deve ser maior que zero.")
        return value
```

Replace (inside `GoalDepositForm`):

```python
    def clean_amount(self):
        return clean_currency_value(self.data.get('amount'))
```

with:

```python
    def clean_amount(self):
        value = clean_currency_value(self.data.get('amount'))
        if value is not None and value <= 0:
            raise forms.ValidationError("O valor do aporte deve ser maior que zero.")
        return value
```

- [ ] **Step 4: Add model-level `MinValueValidator`s as a defense-in-depth backstop**

In `core/models.py`, add the import at the top:

```python
from django.core.validators import MinValueValidator
```

Change `Transaction.amount`:

```python
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Valor')
```

to:

```python
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name='Valor')
```

Change `Budget.limit`:

```python
    limit = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Limite')
```

to:

```python
    limit = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name='Limite')
```

Change `Goal.target_amount`, `Goal.current_amount`, `Goal.monthly_target`:

```python
    target_amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Valor Alvo')
    current_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Valor Atual')
    monthly_target = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, verbose_name='Aporte Mensal Planejado')
```

to:

```python
    target_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name='Valor Alvo')
    current_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))], verbose_name='Valor Atual')
    monthly_target = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.01'))], verbose_name='Aporte Mensal Planejado')
```

- [ ] **Step 5: Generate and apply the migration**

Run: `python manage.py makemigrations core -n add_min_value_validators`
Expected: creates `core/migrations/0011_add_min_value_validators.py` with `AlterField` operations for the five fields above (validators are metadata-only, so this migration is a no-op at the database level — safe to apply on existing data even if some legacy row already has amount `0`, since `MinValueValidator` only runs at `full_clean()`/form time, not on every `save()`).

Run: `python manage.py migrate core`
Expected: `Applying core.0011_add_min_value_validators... OK`.

- [ ] **Step 6: Run the tests to see them pass**

Run: `python manage.py test core.tests_validation -v 2`
Expected: all four tests pass.

- [ ] **Step 7: Run the full suite**

Run: `python manage.py test core`
Expected: all green.

- [ ] **Step 8: Commit**

```bash
git add core/models.py core/forms.py core/migrations/0011_add_min_value_validators.py core/tests_validation.py
git commit -m "fix: reject non-positive amounts in transaction/budget/goal forms and models"
```

---

### Task 9: Wrap `transfer_create` and `loan_make_payment` in `transaction.atomic()`

**Files:**
- Modify: `core/views_accounts.py`
- Modify: `core/views_loans.py`
- Test: `core/tests_atomicity.py` (new)

**Interfaces:**
- Produces: no signature change — both views now guarantee all-or-nothing writes across `BankAccount`/`Transfer`/`AuditLog` (transfer) and `LoanPayment`/`Loan`/`Transaction`/`AuditLog` (loan payment).

- [ ] **Step 1: Write the failing tests**

Create `core/tests_atomicity.py`:

```python
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import BankAccount, Loan, Transaction, Transfer


class TransferAtomicityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="eve", password="pass12345")
        self.client.login(username="eve", password="pass12345")
        self.acc_a = BankAccount.objects.create(user=self.user, name="Conta A", balance=Decimal("100.00"))
        self.acc_b = BankAccount.objects.create(user=self.user, name="Conta B", balance=Decimal("50.00"))

    def test_failed_transfer_does_not_partially_update_balances(self):
        with patch("core.views_accounts.AuditLog.objects.create", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse("transfer_create"), {
                    "from_account": self.acc_a.pk,
                    "to_account": self.acc_b.pk,
                    "amount": "30,00",
                    "date": "2026-01-10",
                    "description": "Teste",
                })
        self.acc_a.refresh_from_db()
        self.acc_b.refresh_from_db()
        self.assertEqual(self.acc_a.balance, Decimal("100.00"))
        self.assertEqual(self.acc_b.balance, Decimal("50.00"))
        self.assertEqual(Transfer.objects.count(), 0)


class LoanPaymentAtomicityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="fred", password="pass12345")
        self.client.login(username="fred", password="pass12345")
        self.loan = Loan.objects.create(
            user=self.user, name="Empréstimo Teste", lender="Banco X",
            loan_type="REDUCAO_SALDO", principal=Decimal("1000.00"),
            interest_rate=Decimal("1.0"), interest_period="MENSAL",
            start_date=timezone.now().date(), current_balance=Decimal("1000.00"),
        )

    def test_failed_payment_does_not_change_loan_balance(self):
        with patch("core.views_loans.AuditLog.objects.create", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse("loan_pay", args=[self.loan.pk]), {
                    "payment_date": "2026-01-10",
                    "amount_paid": "50,00",
                    "notes": "",
                })
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.current_balance, Decimal("1000.00"))
        self.assertEqual(self.loan.payments.count(), 0)
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 0)
```

- [ ] **Step 2: Run them to see them fail**

Run: `python manage.py test core.tests_atomicity -v 2`
Expected: both tests fail — today, the `Transfer`/balance updates and the `LoanPayment`/`Loan` updates already committed to the database *before* the mocked `AuditLog.objects.create` raises, so the refreshed objects show the partially-applied state instead of the pre-transfer/pre-payment values.

- [ ] **Step 3: Wrap `transfer_create` in `transaction.atomic()`**

In `core/views_accounts.py`, add to the imports:

```python
from django.db import transaction
```

Replace:

```python
@login_required
def transfer_create(request):
    if request.method == "POST":
        form = TransferForm(request.user, request.POST)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.user = request.user
            transfer.save()
            # Update account balances
            transfer.from_account.balance -= transfer.amount
            transfer.from_account.save()
            transfer.to_account.balance += transfer.amount
            transfer.to_account.save()
            AuditLog.objects.create(
                user=request.user, action="CREATE", model_name="Transfer",
                object_id=transfer.pk,
                description=f"Transferência R$ {transfer.amount} de {transfer.from_account} para {transfer.to_account}"
            )
            messages.success(request, "Transferência realizada com sucesso!")
            return redirect("account_list")
    else:
        form = TransferForm(request.user)
    return render(request, "core/transfer_form.html", {"form": form})
```

with:

```python
@login_required
def transfer_create(request):
    if request.method == "POST":
        form = TransferForm(request.user, request.POST)
        if form.is_valid():
            with transaction.atomic():
                transfer = form.save(commit=False)
                transfer.user = request.user
                transfer.save()
                # Update account balances
                transfer.from_account.balance -= transfer.amount
                transfer.from_account.save()
                transfer.to_account.balance += transfer.amount
                transfer.to_account.save()
                AuditLog.objects.create(
                    user=request.user, action="CREATE", model_name="Transfer",
                    object_id=transfer.pk,
                    description=f"Transferência R$ {transfer.amount} de {transfer.from_account} para {transfer.to_account}"
                )
            messages.success(request, "Transferência realizada com sucesso!")
            return redirect("account_list")
    else:
        form = TransferForm(request.user)
    return render(request, "core/transfer_form.html", {"form": form})
```

- [ ] **Step 4: Wrap `loan_make_payment` in `transaction.atomic()`**

In `core/views_loans.py`, add to the imports:

```python
from django.db import transaction
```

Replace:

```python
            payment = form.save(commit=False)
            payment.loan = loan
            payment.interest_paid = round(interest_paid, 2)
            payment.principal_paid = round(principal_paid, 2)
            payment.balance_after = round(balance_after, 2)
            payment.save()

            loan.current_balance = Decimal(str(round(balance_after, 2)))
            if loan.current_balance <= 0:
                loan.is_active = False
            loan.save()

            category, _ = Category.objects.get_or_create(
                user=request.user, name="Pagamento de Empréstimo",
                defaults={"type": "DESPESA"}
            )
            Transaction.objects.create(
                user=request.user,
                category=category,
                type="DESPESA",
                amount=Decimal(str(amount)),
                date=form.cleaned_data['payment_date'],
                description=f"Pagamento — {loan.name} (juros: R$ {interest_paid:.2f} / amort: R$ {principal_paid:.2f})",
            )

            AuditLog.objects.create(
                user=request.user, action="UPDATE", model_name="Loan",
                object_id=loan.pk,
                description=f"Pagamento R$ {amount:.2f} em {loan.name}. Saldo: R$ {balance_after:.2f}"
            )
```

with:

```python
            with transaction.atomic():
                payment = form.save(commit=False)
                payment.loan = loan
                payment.interest_paid = round(interest_paid, 2)
                payment.principal_paid = round(principal_paid, 2)
                payment.balance_after = round(balance_after, 2)
                payment.save()

                loan.current_balance = Decimal(str(round(balance_after, 2)))
                if loan.current_balance <= 0:
                    loan.is_active = False
                loan.save()

                category, _ = Category.objects.get_or_create(
                    user=request.user, name="Pagamento de Empréstimo",
                    defaults={"type": "DESPESA"}
                )
                Transaction.objects.create(
                    user=request.user,
                    category=category,
                    type="DESPESA",
                    amount=Decimal(str(amount)),
                    date=form.cleaned_data['payment_date'],
                    description=f"Pagamento — {loan.name} (juros: R$ {interest_paid:.2f} / amort: R$ {principal_paid:.2f})",
                )

                AuditLog.objects.create(
                    user=request.user, action="UPDATE", model_name="Loan",
                    object_id=loan.pk,
                    description=f"Pagamento R$ {amount:.2f} em {loan.name}. Saldo: R$ {balance_after:.2f}"
                )
```

(the `if balance_after <= 0: messages.success(...)` block right after stays outside the `atomic()` block, unchanged — it only reads `balance_after`, a local variable, so it's safe to run after the commit).

- [ ] **Step 5: Run the tests to see them pass**

Run: `python manage.py test core.tests_atomicity -v 2`
Expected: both tests pass.

- [ ] **Step 6: Run the full suite**

Run: `python manage.py test core`
Expected: all green — happy-path transfer and loan-payment behavior is byte-identical, only the failure path changed.

- [ ] **Step 7: Commit**

```bash
git add core/views_accounts.py core/views_loans.py core/tests_atomicity.py
git commit -m "fix: wrap transfer_create and loan_make_payment in transaction.atomic()"
```

---

### Task 10: Fix `Investment.save()` double-save on create

**Files:**
- Modify: `core/models.py` (`Investment.save`)
- Test: `core/tests_investments.py` (new)

**Interfaces:**
- Produces: `Investment.save()` — same signature and same external behavior (auto-creates a linked `Transaction` on create unless `_skip_transaction` is set, keeps the linked transaction in sync on update) — but issues one fewer `UPDATE` query on create.

- [ ] **Step 1: Write the failing test**

Create `core/tests_investments.py`:

```python
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from .models import Investment


class InvestmentSaveQueryCountTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="carla", password="pass12345")

    def test_create_does_not_issue_extra_update_on_investment(self):
        with CaptureQueriesContext(connection) as ctx:
            inv = Investment.objects.create(
                user=self.user,
                category_type="VARIABLE",
                symbol="PETR4.SA",
                quantity=Decimal("10"),
                purchase_price=Decimal("30.00"),
                date=datetime.date.today(),
            )
        update_queries = [
            q["sql"] for q in ctx.captured_queries
            if q["sql"].upper().startswith("UPDATE") and "core_investment" in q["sql"].lower()
        ]
        self.assertEqual(len(update_queries), 0, f"Expected no UPDATEs on core_investment during create, got: {update_queries}")
        self.assertIsNotNone(inv.transaction)
        self.assertEqual(inv.transaction.amount, inv.total_cost)
```

- [ ] **Step 2: Run it to see it fail**

Run: `python manage.py test core.tests_investments -v 2`
Expected: fails — today's `Investment.save()` issues one `UPDATE` on `core_investment` during create (from the recursive `self.save()` call after the linked transaction is created).

- [ ] **Step 3: Rewrite `Investment.save()` to create the linked transaction before the (single) insert**

In `core/models.py`, replace:

```python
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Check if we should skip transaction creation
        if getattr(self, '_skip_transaction', False):
            return

        # Create or update associated transaction
        if not self.transaction:
            # Find or create 'Investimentos' category
            category, _ = Category.objects.get_or_create(
                user=self.user, 
                name='Investimentos', 
                defaults={'type': 'DESPESA'}
            )
            
            transaction = Transaction.objects.create(
                user=self.user,
                category=category,
                type='DESPESA',
                amount=self.total_cost,
                date=self.date,
                description=f"Compra de {self.symbol} ({self.quantity} un.)"
            )
            self.transaction = transaction
            self.save()
        else:
            # Update existing transaction
            self.transaction.amount = self.total_cost
            self.transaction.date = self.date
            self.transaction.description = f"Compra de {self.symbol} ({self.quantity} un.)"
            self.transaction.save()
```

with:

```python
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        skip_transaction = getattr(self, '_skip_transaction', False)

        if is_new and not skip_transaction:
            # Create the linked transaction first (it needs no FK back to this
            # Investment row) so the Investment itself only needs a single INSERT
            # with transaction_id already populated — no extra UPDATE afterwards.
            category, _ = Category.objects.get_or_create(
                user=self.user,
                name='Investimentos',
                defaults={'type': 'DESPESA'}
            )
            self.transaction = Transaction.objects.create(
                user=self.user,
                category=category,
                type='DESPESA',
                amount=self.total_cost,
                date=self.date,
                description=f"Compra de {self.symbol} ({self.quantity} un.)"
            )
            super().save(*args, **kwargs)
            return

        super().save(*args, **kwargs)

        if skip_transaction:
            return

        if self.transaction_id:
            # Keep the linked transaction in sync on update
            self.transaction.amount = self.total_cost
            self.transaction.date = self.date
            self.transaction.description = f"Compra de {self.symbol} ({self.quantity} un.)"
            self.transaction.save()
```

- [ ] **Step 4: Run the test to see it pass**

Run: `python manage.py test core.tests_investments -v 2`
Expected: passes.

- [ ] **Step 5: Run the full suite**

Run: `python manage.py test core`
Expected: all green — `InvestmentUpdateView` (the only place `_skip_transaction` is set) and the plain-update path both go through the unchanged second half of the function.

- [ ] **Step 6: Commit**

```bash
git add core/models.py core/tests_investments.py
git commit -m "fix: create Investment's linked transaction before the single insert, avoid extra UPDATE"
```

---

### Task 11: Collapse dashboard income/expense aggregates into one query per period

**Files:**
- Modify: `core/views_dashboard.py`
- Test: `core/tests_dashboard.py` (new)

**Interfaces:**
- Produces: `_income_expense_totals(queryset)` — module-level helper in `views_dashboard.py`, takes any `Transaction` queryset, returns `(income_total, expense_total)` via a single conditional-aggregate query.

- [ ] **Step 1: Write the failing test**

Create `core/tests_dashboard.py`:

```python
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Transaction
from .views_dashboard import _income_expense_totals


class IncomeExpenseTotalsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="hank", password="pass12345")
        today = datetime.date.today()
        Transaction.objects.create(user=self.user, type="RECEITA", amount=Decimal("500.00"), date=today)
        Transaction.objects.create(user=self.user, type="RECEITA", amount=Decimal("200.00"), date=today)
        Transaction.objects.create(user=self.user, type="DESPESA", amount=Decimal("150.00"), date=today)

    def test_totals_computed_in_a_single_query(self):
        qs = Transaction.objects.filter(user=self.user)
        with self.assertNumQueries(1):
            income, expense = _income_expense_totals(qs)
        self.assertEqual(income, Decimal("700.00"))
        self.assertEqual(expense, Decimal("150.00"))

    def test_totals_are_zero_for_empty_queryset(self):
        qs = Transaction.objects.filter(user=self.user, date__lt=datetime.date(2000, 1, 1))
        income, expense = _income_expense_totals(qs)
        self.assertEqual(income, 0)
        self.assertEqual(expense, 0)
```

- [ ] **Step 2: Run it to see it fail**

Run: `python manage.py test core.tests_dashboard -v 2`
Expected: fails with `ImportError` / `AttributeError` — `_income_expense_totals` does not exist yet.

- [ ] **Step 3: Add the helper and use it in `dashboard()`**

In `core/views_dashboard.py`, change the import line:

```python
from django.db.models import Sum
```

to:

```python
from django.db.models import Q, Sum
```

Add the helper function right after the imports (before `def register(request):`):

```python
def _income_expense_totals(queryset):
    """Sum RECEITA/DESPESA amounts for a Transaction queryset in a single query."""
    totals = queryset.aggregate(
        income=Sum("amount", filter=Q(type="RECEITA")),
        expense=Sum("amount", filter=Q(type="DESPESA")),
    )
    return totals["income"] or 0, totals["expense"] or 0
```

Replace:

```python
    monthly_income = (
        Transaction.objects.filter(
            user=request.user, type="RECEITA", date__range=[start_date, end_date]
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )
    monthly_expense = (
        Transaction.objects.filter(
            user=request.user, type="DESPESA", date__range=[start_date, end_date]
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )

    prev_month_end = start_date - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    previous_income_for_change = (
        Transaction.objects.filter(
            user=request.user,
            type="RECEITA",
            date__range=[prev_month_start, prev_month_end],
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )
    previous_expense_for_change = (
        Transaction.objects.filter(
            user=request.user,
            type="DESPESA",
            date__range=[prev_month_start, prev_month_end],
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )
```

with:

```python
    monthly_income, monthly_expense = _income_expense_totals(
        Transaction.objects.filter(user=request.user, date__range=[start_date, end_date])
    )

    prev_month_end = start_date - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    previous_income_for_change, previous_expense_for_change = _income_expense_totals(
        Transaction.objects.filter(user=request.user, date__range=[prev_month_start, prev_month_end])
    )
```

Replace:

```python
    previous_income = (
        Transaction.objects.filter(
            user=request.user, type="RECEITA", date__lt=start_date
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )
    previous_expense = (
        Transaction.objects.filter(
            user=request.user, type="DESPESA", date__lt=start_date
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )
```

with:

```python
    previous_income, previous_expense = _income_expense_totals(
        Transaction.objects.filter(user=request.user, date__lt=start_date)
    )
```

- [ ] **Step 4: Run the test to see it pass**

Run: `python manage.py test core.tests_dashboard -v 2`
Expected: passes.

- [ ] **Step 5: Run the full suite (including the existing dashboard view test)**

Run: `python manage.py test core`
Expected: all green, including `ViewTests.test_dashboard_view` in `core/tests.py` — the computed values are identical, just fetched with 3 queries instead of 6.

- [ ] **Step 6: Commit**

```bash
git add core/views_dashboard.py core/tests_dashboard.py
git commit -m "perf: collapse dashboard income/expense aggregates into one query per period"
```

---

### Task 12: Fix budget-vs-actual N+1 in dashboard, budget list, and reports

**Files:**
- Modify: `core/services.py` (add `budget_spent_map`)
- Modify: `core/views_dashboard.py` (use `budget_spent_map` in the alerts loop)
- Modify: `core/views_budgets.py` (use `budget_spent_map` in `BudgetListView`)
- Modify: `core/views_reports.py` (separate inline collapse — different semantics, see rationale below)
- Test: `core/tests_budgets.py` (new)

**Interfaces:**
- Produces: `budget_spent_map(user, budgets) -> dict[int, Decimal]` in `core/services.py` — given any iterable of `Budget` objects for `user`, returns `{budget.id: spent_this_period}` using at most 2 grouped queries (one for `MENSAL` budgets, one for `ANUAL`), instead of one query per budget.

**Rationale for the two separate fixes:** `views_dashboard.py` and `BudgetListView` both compute "how much was spent in the budget's *own* period (this month / this year)" — that's what `budget_spent_map` encodes. `views_reports.py`'s budget-vs-actual chart instead computes "how much was spent within the *report's own* date-range filter, regardless of the budget's period field" — a genuinely different query, so it gets its own inline fix rather than reusing `budget_spent_map`.

- [ ] **Step 1: Write the failing test for `budget_spent_map`**

Create `core/tests_budgets.py`:

```python
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Budget, Category, Transaction
from .services import budget_spent_map


class BudgetSpentMapTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="gina", password="pass12345")
        self.cat_food = Category.objects.create(user=self.user, name="Comida", type="DESPESA")
        self.cat_fun = Category.objects.create(user=self.user, name="Lazer", type="DESPESA")
        today = datetime.date.today()
        Transaction.objects.create(user=self.user, category=self.cat_food, type="DESPESA", amount=Decimal("120.00"), date=today)
        Transaction.objects.create(user=self.user, category=self.cat_fun, type="DESPESA", amount=Decimal("40.00"), date=today)
        self.budget_food = Budget.objects.create(user=self.user, category=self.cat_food, limit=Decimal("300.00"), period="MENSAL")
        self.budget_fun = Budget.objects.create(user=self.user, category=self.cat_fun, limit=Decimal("100.00"), period="ANUAL")

    def test_spent_map_returns_correct_totals_per_period(self):
        result = budget_spent_map(self.user, [self.budget_food, self.budget_fun])
        self.assertEqual(result[self.budget_food.id], Decimal("120.00"))
        self.assertEqual(result[self.budget_fun.id], Decimal("40.00"))

    def test_spent_map_uses_two_queries_regardless_of_budget_count(self):
        cat_extra = Category.objects.create(user=self.user, name="Transporte", type="DESPESA")
        budget_extra = Budget.objects.create(user=self.user, category=cat_extra, limit=Decimal("200.00"), period="MENSAL")
        budgets = [self.budget_food, self.budget_fun, budget_extra]
        with self.assertNumQueries(2):
            budget_spent_map(self.user, budgets)

    def test_budget_with_no_transactions_returns_zero(self):
        cat_empty = Category.objects.create(user=self.user, name="Vazia", type="DESPESA")
        budget_empty = Budget.objects.create(user=self.user, category=cat_empty, limit=Decimal("50.00"), period="MENSAL")
        result = budget_spent_map(self.user, [budget_empty])
        self.assertEqual(result[budget_empty.id], Decimal("0"))
```

- [ ] **Step 2: Run it to see it fail**

Run: `python manage.py test core.tests_budgets -v 2`
Expected: `ImportError` — `budget_spent_map` doesn't exist yet.

- [ ] **Step 3: Add `budget_spent_map` to `core/services.py`**

In `core/services.py`, add to the imports:

```python
from decimal import Decimal
from django.db.models import Sum
```

Add at the end of the file:

```python
def budget_spent_map(user, budgets):
    """
    Given an iterable of Budget objects belonging to `user`, return
    {budget.id: spent_amount} computed with at most 2 grouped queries
    (one for MENSAL budgets, one for ANUAL) instead of one query per budget.
    """
    budgets = list(budgets)
    today = timezone.now().date()
    result = {b.id: Decimal('0') for b in budgets}

    mensal = [b for b in budgets if b.period == 'MENSAL']
    anual = [b for b in budgets if b.period == 'ANUAL']

    if mensal:
        totals = (
            Transaction.objects.filter(
                user=user, type='DESPESA',
                category_id__in=[b.category_id for b in mensal],
                date__year=today.year, date__month=today.month,
            )
            .values('category_id')
            .annotate(total=Sum('amount'))
        )
        by_category = {t['category_id']: t['total'] for t in totals}
        for b in mensal:
            result[b.id] = by_category.get(b.category_id) or Decimal('0')

    if anual:
        totals = (
            Transaction.objects.filter(
                user=user, type='DESPESA',
                category_id__in=[b.category_id for b in anual],
                date__year=today.year,
            )
            .values('category_id')
            .annotate(total=Sum('amount'))
        )
        by_category = {t['category_id']: t['total'] for t in totals}
        for b in anual:
            result[b.id] = by_category.get(b.category_id) or Decimal('0')

    return result
```

- [ ] **Step 4: Run the test to see it pass**

Run: `python manage.py test core.tests_budgets -v 2`
Expected: all three pass.

- [ ] **Step 5: Use `budget_spent_map` in the dashboard alerts loop**

In `core/views_dashboard.py`, add `budget_spent_map` to the existing services import:

```python
from .services import process_recurring_transactions
```

becomes:

```python
from .services import budget_spent_map, process_recurring_transactions
```

Replace:

```python
    alerts = []
    budgets = Budget.objects.filter(user=request.user, period="MENSAL")
    for budget in budgets:
        expense_sum = (
            Transaction.objects.filter(
                user=request.user,
                category=budget.category,
                type="DESPESA",
                date__range=[start_date, end_date],
            ).aggregate(Sum("amount"))["amount__sum"]
            or 0
        )
        if budget.limit > 0:
            percent_used = (expense_sum / budget.limit) * 100
            if percent_used >= 90:
                alerts.append({
                    "category": budget.category.name,
                    "percent": int(percent_used),
                    "limit": budget.limit,
                    "used": expense_sum,
                    "level": "danger" if percent_used >= 100 else "warning",
                })
```

with:

```python
    alerts = []
    budgets = Budget.objects.filter(user=request.user, period="MENSAL").select_related("category")
    spent_map = budget_spent_map(request.user, budgets)
    for budget in budgets:
        expense_sum = spent_map.get(budget.id) or 0
        if budget.limit > 0:
            percent_used = (expense_sum / budget.limit) * 100
            if percent_used >= 90:
                alerts.append({
                    "category": budget.category.name,
                    "percent": int(percent_used),
                    "limit": budget.limit,
                    "used": expense_sum,
                    "level": "danger" if percent_used >= 100 else "warning",
                })
```

- [ ] **Step 6: Use `budget_spent_map` in `BudgetListView`**

In `core/views_budgets.py`, replace the imports:

```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import BudgetForm
from .models import Budget, Transaction
```

with (both `Sum` and `timezone` become unused once the per-budget query loop is removed below; `Transaction` is no longer imported directly since `budget_spent_map` now owns that query):

```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import BudgetForm
from .models import Budget
from .services import budget_spent_map
```

Replace:

```python
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        budgets = context["budgets"]
        today = timezone.now().date()

        for budget in budgets:
            if budget.period == "MENSAL":
                transactions = Transaction.objects.filter(
                    user=self.request.user,
                    category=budget.category,
                    type="DESPESA",
                    date__year=today.year,
                    date__month=today.month,
                )
            else:
                transactions = Transaction.objects.filter(
                    user=self.request.user,
                    category=budget.category,
                    type="DESPESA",
                    date__year=today.year,
                )

            spent = transactions.aggregate(Sum("amount"))["amount__sum"] or 0
            budget.spent = spent
            budget.percentage = (spent / budget.limit) * 100 if budget.limit > 0 else 0

            if budget.percentage >= 100:
                budget.status_color = "danger"
            elif budget.percentage >= 75:
                budget.status_color = "warning"
            else:
                budget.status_color = "success"

        return context
```

with:

```python
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        budgets = context["budgets"]
        spent_map = budget_spent_map(self.request.user, budgets)

        for budget in budgets:
            spent = spent_map.get(budget.id) or 0
            budget.spent = spent
            budget.percentage = (spent / budget.limit) * 100 if budget.limit > 0 else 0

            if budget.percentage >= 100:
                budget.status_color = "danger"
            elif budget.percentage >= 75:
                budget.status_color = "warning"
            else:
                budget.status_color = "success"

        return context
```

Also add `.select_related("category")` to the queryset just above:

```python
    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)
```

becomes:

```python
    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user).select_related("category")
```

- [ ] **Step 7: Fix the separate N+1 in `views_reports.py`'s budget-vs-actual chart**

In `core/views_reports.py`, replace:

```python
    budgets = Budget.objects.filter(user=request.user)
    budget_labels = []
    budget_limits = []
    budget_actuals = []
    for budget in budgets:
        actual = (
            transactions.filter(
                category=budget.category, type="DESPESA"
            ).aggregate(Sum("amount"))["amount__sum"]
            or 0
        )
        budget_labels.append(budget.category.name)
        budget_limits.append(float(budget.limit))
        budget_actuals.append(float(actual))
```

with:

```python
    budgets = Budget.objects.filter(user=request.user).select_related("category")
    budget_category_ids = [b.category_id for b in budgets]
    actual_totals = (
        transactions.filter(type="DESPESA", category_id__in=budget_category_ids)
        .values("category_id")
        .annotate(total=Sum("amount"))
    )
    actual_by_category = {t["category_id"]: (t["total"] or 0) for t in actual_totals}

    budget_labels = []
    budget_limits = []
    budget_actuals = []
    for budget in budgets:
        actual = actual_by_category.get(budget.category_id) or 0
        budget_labels.append(budget.category.name)
        budget_limits.append(float(budget.limit))
        budget_actuals.append(float(actual))
```

- [ ] **Step 8: Run the full suite**

Run: `python manage.py test core`
Expected: all green, including `core/tests_alerts.py` (dashboard budget alerts) and `core/tests.py::test_reports_view`.

- [ ] **Step 9: Commit**

```bash
git add core/services.py core/views_dashboard.py core/views_budgets.py core/views_reports.py core/tests_budgets.py
git commit -m "perf: eliminate N+1 budget-vs-actual queries in dashboard, budget list, and reports"
```

---

### Task 13: Add `select_related` to transaction list/export views; dedupe `core_extras` filters

**Files:**
- Modify: `core/views_transactions.py` (`TransactionListView`)
- Modify: `core/views_reports.py` (`_filter_transactions`)
- Modify: `core/templatetags/core_extras.py`

**Interfaces:**
- Produces: `multiply`/`mul` collapse into a single filter named `mul` (the name actually used in templates — see Step 3 below).

- [ ] **Step 1: Confirm which of `multiply`/`mul` is actually used in templates**

Run: `git grep -n "|multiply" -- 'templates/*'`
Run: `git grep -n "|mul" -- 'templates/*'`
Expected: this tells you which filter name to keep. (If both are used, keep both names but have `mul` be a plain alias calling the same implementation — no template changes needed either way, since Step 3 below preserves both registered names.)

- [ ] **Step 2: Add `select_related` to `TransactionListView`**

In `core/views_transactions.py`, replace:

```python
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).order_by("-date")
```

with:

```python
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).select_related("category", "account").order_by("-date")
```

- [ ] **Step 3: Add `select_related` to the shared report/export queryset**

In `core/views_reports.py`, replace:

```python
def _filter_transactions(request, start_date, end_date, category_id):
    qs = Transaction.objects.filter(user=request.user).order_by("-date")
```

with:

```python
def _filter_transactions(request, start_date, end_date, category_id):
    qs = Transaction.objects.filter(user=request.user).select_related("category").order_by("-date")
```

(this also speeds up `export_csv`, `export_pdf`, and `export_xlsx`, which all call `_filter_transactions` and then access `t.category.name` per row).

- [ ] **Step 4: Dedupe the `multiply`/`mul` filter implementation**

In `core/templatetags/core_extras.py`, replace:

```python
@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='mul')
def mul(value, arg):
    return multiply(value, arg)
```

with:

```python
@register.filter(name='multiply')
@register.filter(name='mul')
def multiply(value, arg):
    """Multiply two template values; registered under both 'multiply' and 'mul' since both are used across templates."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
```

(this keeps both template-facing names working — no template files need to change — while removing the duplicated function body).

- [ ] **Step 5: Run the full suite**

Run: `python manage.py test core`
Expected: all green.

- [ ] **Step 6: Manual smoke check**

Run the app (`python manage.py runserver`) and open `/transactions/`, `/reports/`, and `/reports/export/` (CSV/PDF/XLSX) — confirm category names still render correctly (this is a pure query-optimization change, output must be identical).

- [ ] **Step 7: Commit**

```bash
git add core/views_transactions.py core/views_reports.py core/templatetags/core_extras.py
git commit -m "perf: select_related category/account on transaction list & export views; dedupe multiply/mul filter"
```

---

### Task 14: Fix XSS-prone `innerHTML` in the investment ticker search widget

**Files:**
- Modify: `templates/core/investment_dashboard.html`

**Interfaces:**
- Produces: a small `escapeHtml(str)` JS helper local to this template's `<script>` block.

- [ ] **Step 1: Confirm the vector**

Run: `python manage.py runserver`, log in, go to `/investments/`, and type `<img src=x onerror=alert(1)>` into the ticker search box, then submit.
Expected (before the fix): the JSON response from `/investments/search/` echoes the raw string back as `"symbol"`, and the browser executes the injected `onerror` handler — confirms the reflected-XSS vector through `search_ticker`'s echo of `ticker_symbol` combined with the template's raw `innerHTML` interpolation.

- [ ] **Step 2: Add an escaping helper and use it for `d.symbol`/`d.name`**

In `templates/core/investment_dashboard.html`, locate the `runSearch` function and, right above it, add:

```javascript
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str ?? '';
    return div.innerHTML;
}
```

Replace:

```javascript
                document.getElementById('searchResult').innerHTML = `
                    <div class="widget-result glass-card p-3 border-0 bg-light-soft">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <div>
                                <h4 class="fw-bold mb-0">${d.symbol}</h4>
                                <small class="text-muted">${d.name || ''}</small>
                            </div>
```

with:

```javascript
                document.getElementById('searchResult').innerHTML = `
                    <div class="widget-result glass-card p-3 border-0 bg-light-soft">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <div>
                                <h4 class="fw-bold mb-0">${escapeHtml(d.symbol)}</h4>
                                <small class="text-muted">${escapeHtml(d.name || '')}</small>
                            </div>
```

- [ ] **Step 3: Verify the fix manually**

Repeat Step 1's search with `<img src=x onerror=alert(1)>`.
Expected: the text is now rendered literally (as escaped text inside the `<h4>`), no script/handler executes.

- [ ] **Step 4: Run the full suite**

Run: `python manage.py test core`
Expected: all green (this is a template/JS-only change, no Python behavior changed).

- [ ] **Step 5: Commit**

```bash
git add templates/core/investment_dashboard.html
git commit -m "fix: escape ticker symbol/name before innerHTML interpolation in investment search widget"
```

---

### Task 15: Standardize currency formatting on the `|brl` filter

**Files:**
- Modify: `templates/core/investment_dashboard.html`
- Modify: `templates/core/investment_list.html`
- Modify: `templates/core/cash_flow.html`
- Modify: `templates/core/reports.html`
- Modify: `templates/core/reports_pdf.html`
- Modify: `templates/core/safe_haven_dashboard.html`
- Modify: `templates/core/import_preview.html`

**Interfaces:**
- No code interface change — pure template text substitution using the existing `{% load core_extras %}` / `{{ value|brl }}` filter (already defined in `core/templatetags/core_extras.py`, already used correctly in `dashboard.html`/`transaction_list.html`).

- [ ] **Step 1: Add `{% load core_extras %}` to the templates that don't have it yet**

Run: `git grep -L "load core_extras" -- templates/core/investment_dashboard.html templates/core/investment_list.html templates/core/cash_flow.html templates/core/safe_haven_dashboard.html templates/core/reports_pdf.html`
Expected: lists all 5 (confirmed missing during the audit).

In each of `templates/core/investment_dashboard.html`, `templates/core/investment_list.html`, `templates/core/safe_haven_dashboard.html`, replace the first line:

```
{% extends 'base.html' %}
```

with:

```
{% extends 'base.html' %}
{% load core_extras %}
```

In `templates/core/cash_flow.html`, replace the first line:

```
{% extends "base.html" %}
```

with:

```
{% extends "base.html" %}
{% load core_extras %}
```

In `templates/core/reports_pdf.html`, add `{% load core_extras %}` as the very first line of the file (it currently starts with `<!DOCTYPE html>` and has no `{% load %}` tags at all):

```
{% load core_extras %}
<!DOCTYPE html>
```

(`reports.html` and `import_preview.html` already have `{% load core_extras %}` — no change needed there.)

- [ ] **Step 2: Replace hardcoded formatting in `investment_dashboard.html`**

Replace each of the following exact lines:

```
                    <h2 class="fw-bold mb-0">R$ {{ total_invested|floatformat:2 }}</h2>
```
→
```
                    <h2 class="fw-bold mb-0">{{ total_invested|brl }}</h2>
```

```
                    <h2 class="fw-bold text-primary mb-0">R$ {{ total_current_value|floatformat:2 }}</h2>
```
→
```
                    <h2 class="fw-bold text-primary mb-0">{{ total_current_value|brl }}</h2>
```

```
                        {% if roi >= 0 %}+{% endif %}R$ {{ roi|floatformat:2 }}
```
→
```
                        {% if roi >= 0 %}+{% endif %}{{ roi|brl }}
```

```
                        <td class="text-muted" data-label="Preço Médio">R$ {{ item.investment.purchase_price|floatformat:2 }}</td>
```
→
```
                        <td class="text-muted" data-label="Preço Médio">{{ item.investment.purchase_price|brl }}</td>
```

```
                            <div class="fw-bold">R$ {{ item.current_value|floatformat:2 }}</div>
```
→
```
                            <div class="fw-bold">{{ item.current_value|brl }}</div>
```

```
                            <small class="text-muted">Cotação: R$ {{ item.current_price|floatformat:2 }}</small>
```
→
```
                            <small class="text-muted">Cotação: {{ item.current_price|brl }}</small>
```

```
                                {% if item.profit_loss >= 0 %}+{% endif %}R$ {{ item.profit_loss|floatformat:2 }}
```
→
```
                                {% if item.profit_loss >= 0 %}+{% endif %}{{ item.profit_loss|brl }}
```

- [ ] **Step 3: Replace hardcoded formatting in `investment_list.html`**

Replace:

```
                        <td>R$ {{ investment.purchase_price|floatformat:2 }}</td>
```
→
```
                        <td>{{ investment.purchase_price|brl }}</td>
```

- [ ] **Step 4: Replace hardcoded formatting in `cash_flow.html`**

Replace each exact line:

```
            R$ {{ current_balance|floatformat:2 }}
```
→
```
            {{ current_balance|brl }}
```

The exact substring `R$ {{ proj_income|floatformat:2 }}` appears 3 times in this file, byte-identical each time (lines 38, 56, 60) — replace it **with `replace_all: true`** in one Edit call:
```
R$ {{ proj_income|floatformat:2 }}
```
→
```
{{ proj_income|brl }}
```

```
          <div class="fs-4 fw-bold text-danger">R$ {{ proj_expense|floatformat:2 }}</div>
```
→
```
          <div class="fs-4 fw-bold text-danger">{{ proj_expense|brl }}</div>
```

```
                <td class="text-end text-success">R$ {{ m.income|floatformat:2 }}</td>
```
→
```
                <td class="text-end text-success">{{ m.income|brl }}</td>
```

```
                <td class="text-end text-danger">R$ {{ m.expense|floatformat:2 }}</td>
```
→
```
                <td class="text-end text-danger">{{ m.expense|brl }}</td>
```

```
                  R$ {{ m.balance|floatformat:2 }}
```
→
```
                  {{ m.balance|brl }}
```

```
    Recorrentes cadastradas: receita <strong>R$ {{ recurring_income|floatformat:2 }}</strong> /
    despesa <strong>R$ {{ recurring_expense|floatformat:2 }}</strong> (equiv. mensal).
```
→
```
    Recorrentes cadastradas: receita <strong>{{ recurring_income|brl }}</strong> /
    despesa <strong>{{ recurring_expense|brl }}</strong> (equiv. mensal).
```

- [ ] **Step 5: Replace hardcoded formatting in `reports.html`**

Replace each exact line:

```
                <h3 class="fw-bold text-success mb-0">R$ {{ total_income|floatformat:2 }}</h3>
```
→
```
                <h3 class="fw-bold text-success mb-0">{{ total_income|brl }}</h3>
```

```
                <h3 class="fw-bold text-danger mb-0">R$ {{ total_expense|floatformat:2 }}</h3>
```
→
```
                <h3 class="fw-bold text-danger mb-0">{{ total_expense|brl }}</h3>
```

```
                    R$ {{ net_balance|floatformat:2 }}
```
→
```
                    {{ net_balance|brl }}
```

```
                                    R$ {{ expense.amount|floatformat:2 }}
```
→
```
                                    {{ expense.amount|brl }}
```

- [ ] **Step 6: Replace hardcoded formatting in `reports_pdf.html`**

Replace:

```
        <p><strong>Total Receitas:</strong> <span class="text-success">R$ {{ total_income|floatformat:2 }}</span></p>
        <p><strong>Total Despesas:</strong> <span class="text-danger">R$ {{ total_expense|floatformat:2 }}</span></p>
        <p><strong>Saldo Líquido:</strong> R$ {{ net_balance|floatformat:2 }}</p>
```
→
```
        <p><strong>Total Receitas:</strong> <span class="text-success">{{ total_income|brl }}</span></p>
        <p><strong>Total Despesas:</strong> <span class="text-danger">{{ total_expense|brl }}</span></p>
        <p><strong>Saldo Líquido:</strong> {{ net_balance|brl }}</p>
```

Replace:

```
                <td>R$ {{ t.amount|floatformat:2 }}</td>
```
→
```
                <td>{{ t.amount|brl }}</td>
```

- [ ] **Step 7: Replace hardcoded formatting in `safe_haven_dashboard.html`**

Replace each exact line:

```
                    <span class="fs-4 fw-bold">R$ {{ usd_rate|floatformat:2 }}</span>
```
→
```
                    <span class="fs-4 fw-bold">{{ usd_rate|brl }}</span>
```

```
                    <span class="fs-4 fw-bold">R$ {{ eur_rate|floatformat:2 }}</span>
```
→
```
                    <span class="fs-4 fw-bold">{{ eur_rate|brl }}</span>
```

```
                                <td class="text-muted" data-label="Investido">R$ {{ item.investment.total_cost|floatformat:2 }}</td>
```
→
```
                                <td class="text-muted" data-label="Investido">{{ item.investment.total_cost|brl }}</td>
```

```
                                <td class="fw-bold" data-label="Saldo Estimado">R$ {{ item.current_value|floatformat:2
                                    }}</td>
```
→
```
                                <td class="fw-bold" data-label="Saldo Estimado">{{ item.current_value|brl }}</td>
```

Replace (this one changes from an unconditional "+" to a sign-aware one, since `item.gain` can in principle be negative):

```
                                    <div class="fw-bold text-success">+ R$ {{ item.gain|floatformat:2 }}</div>
```
→
```
                                    <div class="fw-bold text-success">{% if item.gain >= 0 %}+{% endif %}{{ item.gain|brl }}</div>
```

```
                                <td class="text-muted">R$ {{ total_fixed_invested|floatformat:2 }}</td>
```
→
```
                                <td class="text-muted">{{ total_fixed_invested|brl }}</td>
```

```
                                <td class="text-primary fs-5">R$ {{ total_fixed_current|floatformat:2 }}</td>
```
→
```
                                <td class="text-primary fs-5">{{ total_fixed_current|brl }}</td>
```

```
                                <td class="text-muted" data-label="Preço Médio">R$ {{ item.investment.purchase_price|floatformat:2 }}</td>
```
→
```
                                <td class="text-muted" data-label="Preço Médio">{{ item.investment.purchase_price|brl }}</td>
```

```
                                <td data-label="Cotação">R$ {{ item.current_price|floatformat:2 }}</td>
```
→
```
                                <td data-label="Cotação">{{ item.current_price|brl }}</td>
```

```
                                <td class="pe-4 text-end fw-bold" data-label="Valor em BRL">R$ {{ item.current_value|floatformat:2 }}</td>
```
→
```
                                <td class="pe-4 text-end fw-bold" data-label="Valor em BRL">{{ item.current_value|brl }}</td>
```

- [ ] **Step 8: Replace hardcoded formatting in `import_preview.html`**

Replace:

```
                            {% if r.amount >= 0 %}+{% endif %}R$ {{ r.amount|floatformat:2 }}
```
→
```
                            {% if r.amount >= 0 %}+{% endif %}{{ r.amount|brl }}
```

- [ ] **Step 9: Run the full suite**

Run: `python manage.py test core`
Expected: all green — `core/tests.py::test_transaction_list_view` already asserts `'50,00'` appears in the rendered page via the `brl`-formatted `transaction_list.html`, confirming the filter's output format is unchanged.

- [ ] **Step 10: Manual smoke check**

Run the app and open `/investments/`, `/investments/list/`, `/cash-flow/`, `/reports/`, `/reports/export/pdf/`, `/investments/safe/`, and a CSV/XLSX import preview — confirm every currency figure now renders as `R$ 1.234,56` (with thousands separator) consistently, including negative values showing `- R$ ...`.

- [ ] **Step 11: Commit**

```bash
git add templates/core/investment_dashboard.html templates/core/investment_list.html templates/core/cash_flow.html templates/core/reports.html templates/core/reports_pdf.html templates/core/safe_haven_dashboard.html templates/core/import_preview.html
git commit -m "fix: standardize currency formatting on the |brl filter across all templates"
```

---

### Task 16: Accessibility — label/input pairing and modal ARIA attributes

**Files:**
- Modify: `templates/core/transaction_list.html`
- Modify: `templates/base.html`
- Modify: `templates/core/goal_list.html`

- [ ] **Step 1: Pair filter-form labels with their inputs in `transaction_list.html`**

Replace:

```html
            <div class="col-md-3">
                <label class="form-label small fw-bold text-muted text-uppercase mb-2">Busca inteligente</label>
                <div class="input-group">
                    <span class="input-group-text border-0 bg-transparent text-muted"><i
                            class="bi bi-search"></i></span>
                    <input type="text" class="form-control border-0 bg-light-soft rounded-3" name="search"
                        value="{{ filter_search }}" placeholder="Pagar aluguel...">
                </div>
            </div>

            <div class="col-md-4">
                <label class="form-label small fw-bold text-muted text-uppercase mb-2">Período</label>
                <div class="d-flex gap-2">
                    <input type="date" class="form-control border-0 bg-light-soft rounded-3" name="start_date"
                        value="{{ filter_start_date }}">
                    <input type="date" class="form-control border-0 bg-light-soft rounded-3" name="end_date"
                        value="{{ filter_end_date }}">
                </div>
            </div>

            <div class="col-md-2">
                <label class="form-label small fw-bold text-muted text-uppercase mb-2">Tipo</label>
                <select class="form-select border-0 bg-light-soft rounded-3" name="type">
                    <option value="">Todos</option>
                    <option value="RECEITA" {% if filter_type == 'RECEITA' %}selected{% endif %}>Receitas</option>
                    <option value="DESPESA" {% if filter_type == 'DESPESA' %}selected{% endif %}>Despesas</option>
                </select>
            </div>

            <div class="col-md-2">
                <label class="form-label small fw-bold text-muted text-uppercase mb-2">Categoria</label>
                <select class="form-select border-0 bg-light-soft rounded-3" name="category">
                    <option value="">Todas</option>
                    {% for cat in categories %}
                    <option value="{{ cat.id }}" {% if filter_category == cat.id|stringformat:"s" %}selected{% endif %}>{{ cat.name }}</option>
                    {% endfor %}
                </select>
            </div>
```

with:

```html
            <div class="col-md-3">
                <label for="filter-search" class="form-label small fw-bold text-muted text-uppercase mb-2">Busca inteligente</label>
                <div class="input-group">
                    <span class="input-group-text border-0 bg-transparent text-muted"><i
                            class="bi bi-search"></i></span>
                    <input type="text" id="filter-search" class="form-control border-0 bg-light-soft rounded-3" name="search"
                        value="{{ filter_search }}" placeholder="Pagar aluguel...">
                </div>
            </div>

            <div class="col-md-4">
                <label for="filter-start-date" class="form-label small fw-bold text-muted text-uppercase mb-2">Período</label>
                <div class="d-flex gap-2">
                    <input type="date" id="filter-start-date" class="form-control border-0 bg-light-soft rounded-3" name="start_date"
                        value="{{ filter_start_date }}">
                    <input type="date" class="form-control border-0 bg-light-soft rounded-3" name="end_date"
                        value="{{ filter_end_date }}" aria-label="Data final">
                </div>
            </div>

            <div class="col-md-2">
                <label for="filter-type" class="form-label small fw-bold text-muted text-uppercase mb-2">Tipo</label>
                <select id="filter-type" class="form-select border-0 bg-light-soft rounded-3" name="type">
                    <option value="">Todos</option>
                    <option value="RECEITA" {% if filter_type == 'RECEITA' %}selected{% endif %}>Receitas</option>
                    <option value="DESPESA" {% if filter_type == 'DESPESA' %}selected{% endif %}>Despesas</option>
                </select>
            </div>

            <div class="col-md-2">
                <label for="filter-category" class="form-label small fw-bold text-muted text-uppercase mb-2">Categoria</label>
                <select id="filter-category" class="form-select border-0 bg-light-soft rounded-3" name="category">
                    <option value="">Todas</option>
                    {% for cat in categories %}
                    <option value="{{ cat.id }}" {% if filter_category == cat.id|stringformat:"s" %}selected{% endif %}>{{ cat.name }}</option>
                    {% endfor %}
                </select>
            </div>
```

- [ ] **Step 2: Add ARIA attributes to the quick-add modal in `base.html`**

Replace:

```html
<div class="modal fade" id="quickAddModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content glass-card border-0 shadow-lg">
            <div class="modal-header border-0">
                <h5 class="modal-title fw-bold">Lançamento Rápido</h5>
```

with:

```html
<div class="modal fade" id="quickAddModal" tabindex="-1" role="dialog" aria-modal="true" aria-labelledby="quickAddModalLabel">
    <div class="modal-dialog">
        <div class="modal-content glass-card border-0 shadow-lg">
            <div class="modal-header border-0">
                <h5 class="modal-title fw-bold" id="quickAddModalLabel">Lançamento Rápido</h5>
```

- [ ] **Step 3: Add ARIA attributes to the deposit modal in `goal_list.html`**

Replace:

```html
        <div class="modal fade" id="depositModal{{ goal.pk }}" tabindex="-1">
            <div class="modal-dialog modal-sm">
                <div class="modal-content glass-card border-0 shadow-lg">
                    <div class="modal-header border-0">
                        <h6 class="modal-title fw-bold">Aporte — {{ goal.name }}</h6>
```

with:

```html
        <div class="modal fade" id="depositModal{{ goal.pk }}" tabindex="-1" role="dialog" aria-modal="true" aria-labelledby="depositModalLabel{{ goal.pk }}">
            <div class="modal-dialog modal-sm">
                <div class="modal-content glass-card border-0 shadow-lg">
                    <div class="modal-header border-0">
                        <h6 class="modal-title fw-bold" id="depositModalLabel{{ goal.pk }}">Aporte — {{ goal.name }}</h6>
```

- [ ] **Step 4: Run the full suite**

Run: `python manage.py test core`
Expected: all green (attribute-only HTML changes).

- [ ] **Step 5: Manual smoke check**

Open `/transactions/`, tab through the filter form with keyboard-only navigation and confirm each label reads correctly with a screen reader (or browser dev tools' Accessibility panel). Open the quick-add modal (floating `+` button) and the goal deposit modal, confirm both show up correctly in the Accessibility tree with a labelled dialog role.

- [ ] **Step 6: Commit**

```bash
git add templates/core/transaction_list.html templates/base.html templates/core/goal_list.html
git commit -m "fix: pair filter-form labels with inputs, add ARIA roles to Bootstrap modals"
```

---

### Task 17: Create a shared `static/js/charts.js` helper (theme-aware colors, BRL tick formatter, safe JSON parsing)

**Files:**
- Create: `static/js/charts.js`
- Modify: `templates/base.html` (include the new script)

**Interfaces:**
- Produces: three global helpers used by Task 18 — `chartTheme()` returns `{isDark, gridColor, textColor}`; `brlTick(value, decimals=0)` returns a `"R$ 1.234"`-style string for Chart.js tick callbacks; `parseChartJson(elementId, fallback=[])` reads and JSON-parses the text content of a `<script type="application/json">` tag produced by Django's `json_script` filter, returning `fallback` if the element is missing or parsing fails.

- [ ] **Step 1: Create `static/js/charts.js`**

```javascript
/* Shared Chart.js helpers — theme-aware colors, BRL tick formatting, safe JSON reading. */

function chartTheme() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    return {
        isDark,
        gridColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        textColor: isDark ? '#94a3b8' : '#64748b',
    };
}

function brlTick(value, decimals = 0) {
    return 'R$ ' + Number(value).toLocaleString('pt-BR', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    });
}

function parseChartJson(elementId, fallback = []) {
    const el = document.getElementById(elementId);
    if (!el) return fallback;
    try {
        return JSON.parse(el.textContent);
    } catch (e) {
        console.warn(`parseChartJson: failed to parse #${elementId}`, e);
        return fallback;
    }
}
```

- [ ] **Step 2: Include the script once in `base.html`**

Replace:

```html
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
```

with:

```html
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>

    <!-- Shared chart helpers -->
    <script src="{% static 'js/charts.js' %}?v=1"></script>
```

(`{% load static %}` is already present earlier in `base.html`, right before the `custom.css` link — no need to load it a second time. This edit also pins the Chart.js version, folding in part of Task 19 since it's the same line — see Task 19 for the remaining Toastify cleanup on this file.)

- [ ] **Step 3: Manual verification**

Run the app, open `/` (dashboard) and confirm `chartTheme`, `brlTick`, and `parseChartJson` are defined in the browser console (`typeof chartTheme === 'function'`).

- [ ] **Step 4: Run the full suite**

Run: `python manage.py test core`
Expected: all green (no Python changes; `collectstatic`/`STATICFILES_DIRS` already serves `static/js/` automatically since `STATICFILES_DIRS = [BASE_DIR / 'static']`).

- [ ] **Step 5: Commit**

```bash
git add static/js/charts.js templates/base.html
git commit -m "feat(internal): add shared static/js/charts.js helper, pin Chart.js version"
```

---

### Task 18: Convert chart JSON injection to `json_script` + the new helper (6 templates)

**Files:**
- Modify: `core/views_dashboard.py` (drop manual `json.dumps`, use context objects directly with `json_script`)
- Modify: `core/views_investments.py` (same, for `investment_dashboard` and `InvestmentDetailView`)
- Modify: `core/views_reports.py` (same, for `reports`)
- Modify: `core/views_loans.py` (same, for `loan_detail`)
- Modify: `templates/core/dashboard.html`
- Modify: `templates/core/investment_dashboard.html`
- Modify: `templates/core/investment_detail.html`
- Modify: `templates/core/reports.html`
- Modify: `templates/core/loan_detail.html`
- Modify: `templates/core/cash_flow.html` (only the `brlTick` tick-formatter swap in Step 7 — its chart *data* injection stays on the current bare-literal pattern; see Step 6)
- Modify: `templates/core/loan_add_funds.html` (only the `brlTick` swap in Step 7 — no chart JSON in this file)

**Interfaces:**
- Produces: none new — consumes `chartTheme()`/`brlTick()`/`parseChartJson()` from Task 17's `static/js/charts.js`.

**Why this matters:** today several templates parse chart data with `JSON.parse('{{ chart_labels|safe }}'.replace(/'/g, '"'))` — this silently breaks (falls back to `[]`, or throws) the moment any label contains an apostrophe (e.g. an asset name like `"Investor's Fund"`). Django's `json_script` filter renders the value inside a `<script type="application/json">` tag with proper HTML-escaping, so `JSON.parse` never has to fight with quote-mangling.

- [ ] **Step 1: Dashboard chart (`dashboard.html` / `views_dashboard.py`)**

In `core/views_dashboard.py`, remove the now-unused import (nothing else in this file calls `json.dumps`/`json.loads` once the line below is changed):

```python
"""Dashboard, registration, and calendar views."""
import calendar
import json
from datetime import timedelta
```

becomes:

```python
"""Dashboard, registration, and calendar views."""
import calendar
from datetime import timedelta
```

The context currently does:

```python
        "chart_labels": json.dumps(labels),
        "chart_income": json.dumps(data_income),
        "chart_expense": json.dumps(data_expense),
```

Change to pass the raw Python lists (no `json.dumps` — `json_script` does its own serialization):

```python
        "chart_labels": labels,
        "chart_income": data_income,
        "chart_expense": data_expense,
```

In `templates/core/dashboard.html`, the chart section currently reads (note the `<script>` tag opens exactly here — the `json_script` tags below must land **before** this opening `<script>` tag, never inside it, or the browser closes the block early at the first `</script>` it meets):

```html
<script>
    document.addEventListener('DOMContentLoaded', function () {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const ctx = document.getElementById('cashFlowChart').getContext('2d');
        const labels = JSON.parse('{{ chart_labels|safe }}');
        const dataIncome = JSON.parse('{{ chart_income|safe }}');
        const dataExpense = JSON.parse('{{ chart_expense|safe }}');
```

Replace it with:

```html
{{ chart_labels|json_script:"dashboard-chart-labels" }}
{{ chart_income|json_script:"dashboard-chart-income" }}
{{ chart_expense|json_script:"dashboard-chart-expense" }}
<script>
    document.addEventListener('DOMContentLoaded', function () {
        const { isDark } = chartTheme();
        const ctx = document.getElementById('cashFlowChart').getContext('2d');
        const labels = parseChartJson('dashboard-chart-labels');
        const dataIncome = parseChartJson('dashboard-chart-income');
        const dataExpense = parseChartJson('dashboard-chart-expense');
```

- [ ] **Step 2: Investment dashboard pie chart (`investment_dashboard.html` / `views_investments.py`)**

In `core/views_investments.py`, remove the now-unused import (nothing else in this file calls `json.dumps`/`json.loads` once the lines below are changed):

```python
"""Investment views: dashboard, safe haven, ticker search, and CRUD."""
import json

import yfinance as yf
```

becomes:

```python
"""Investment views: dashboard, safe haven, ticker search, and CRUD."""
import yfinance as yf
```

In `investment_dashboard` view, change:

```python
        "chart_labels": json.dumps(labels),
        "chart_data": json.dumps(data_values),
```

to:

```python
        "chart_labels": labels,
        "chart_data": data_values,
```

In `templates/core/investment_dashboard.html`, this file has exactly one `<script>` tag covering both the pie chart and the ticker-search widget from Task 14. It currently opens like this (the `json_script` tags below must land **before** this opening `<script>` tag, never inside it):

```html
<script>
    document.addEventListener('DOMContentLoaded', function () {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

        // Distribution Chart
        const pieCtx = document.getElementById('portfolioPieChart');
        if (pieCtx) {
            const labels = JSON.parse('{{ chart_labels|safe }}'.replace(/'/g, '"') || '[]');
            const data = JSON.parse('{{ chart_data|safe }}'.replace(/'/g, '"') || '[]');
```

Replace it with:

```html
{{ chart_labels|json_script:"portfolio-chart-labels" }}
{{ chart_data|json_script:"portfolio-chart-data" }}
<script>
    document.addEventListener('DOMContentLoaded', function () {
        const { isDark } = chartTheme();

        // Distribution Chart
        const pieCtx = document.getElementById('portfolioPieChart');
        if (pieCtx) {
            const labels = parseChartJson('portfolio-chart-labels');
            const data = parseChartJson('portfolio-chart-data');
```

- [ ] **Step 3: Investment detail history chart (`investment_detail.html` / `views_investments.py`)**

In `core/views_investments.py`, `InvestmentDetailView.get_context_data`, change:

```python
            context["chart_labels"] = json.dumps(fetched.get("chart_dates", []))
            context["chart_data"] = json.dumps(fetched.get("chart_prices", []))
```

to:

```python
            context["chart_labels"] = fetched.get("chart_dates", [])
            context["chart_data"] = fetched.get("chart_prices", [])
```

In `templates/core/investment_detail.html`, replace:

```html
{% if chart_labels != "[]" %}
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
(function () {
    const ctx = document.getElementById('historyChart').getContext('2d');
    const labels = JSON.parse('{{ chart_labels|safe }}');
    const data   = JSON.parse('{{ chart_data|safe }}');
```

with (this also drops the redundant, unpinned second `chart.js` load — `base.html` already loads the pinned 4.4.0 build from Task 17; the `json_script` tags must sit **before** the `<script>` tag opens, never inside an already-open `<script>` block, or the browser closes that block early at the first `</script>` it meets):

```html
{% if chart_labels != "[]" %}
{{ chart_labels|json_script:"history-chart-labels" }}
{{ chart_data|json_script:"history-chart-data" }}
<script>
(function () {
    const ctx = document.getElementById('historyChart').getContext('2d');
    const labels = parseChartJson('history-chart-labels');
    const data   = parseChartJson('history-chart-data');
```

- [ ] **Step 4: Reports charts (evolution/daily/budget) — `reports.html` / `views_reports.py`**

In `core/views_reports.py`, `reports` view, change:

```python
        "evolution_labels": json.dumps(evolution_labels),
        "evolution_income": json.dumps(evolution_income),
        "evolution_expense": json.dumps(evolution_expense),
        "daily_labels": json.dumps(daily_labels),
        "daily_expenses": json.dumps(daily_expenses),
        "budget_labels": json.dumps(budget_labels),
        "budget_limits": json.dumps(budget_limits),
        "budget_actuals": json.dumps(budget_actuals),
```

to:

```python
        "evolution_labels": evolution_labels,
        "evolution_income": evolution_income,
        "evolution_expense": evolution_expense,
        "daily_labels": daily_labels,
        "daily_expenses": daily_expenses,
        "budget_labels": budget_labels,
        "budget_limits": budget_limits,
        "budget_actuals": budget_actuals,
```

In `templates/core/reports.html`, replace:

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
    // Helper to parse JSON safely
    function safeJson(value, defaultValue = []) {
        try {
            return JSON.parse(value || JSON.stringify(defaultValue));
        } catch (e) {
            return defaultValue;
        }
    }

    Chart.defaults.font.family = "'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', sans-serif";
```

with (this also drops the redundant, unpinned second `chart.js` load — `base.html` already loads the pinned 4.4.0 build from Task 17):

```html
<script>
    {{ evolution_labels|json_script:"evolution-labels" }}
    {{ evolution_income|json_script:"evolution-income" }}
    {{ evolution_expense|json_script:"evolution-expense" }}
    {{ daily_labels|json_script:"daily-labels" }}
    {{ daily_expenses|json_script:"daily-expenses" }}
    {{ budget_labels|json_script:"budget-labels" }}
    {{ budget_limits|json_script:"budget-limits" }}
    {{ budget_actuals|json_script:"budget-actuals" }}

    Chart.defaults.font.family = "'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', sans-serif";
```

(the `{{ ...|json_script:"..." }}` tags render their own `<script type="application/json">` elements regardless of where they sit inside this outer `<script>` block's surrounding HTML, so this placement — right at the top, before `Chart.defaults...` — makes them available to every `if (ctxEvolution)`/`if (ctxDaily)`/`if (ctxBudget)` block further down in the same file.)

Replace:

```javascript
        const labels = safeJson('{{ evolution_labels|safe }}');
        const incomeData = safeJson('{{ evolution_income|safe }}');
        const expenseData = safeJson('{{ evolution_expense|safe }}');
```

with:

```javascript
        const labels = parseChartJson('evolution-labels');
        const incomeData = parseChartJson('evolution-income');
        const expenseData = parseChartJson('evolution-expense');
```

Replace:

```javascript
        const labels = safeJson('{{ daily_labels|safe }}');
        const data = safeJson('{{ daily_expenses|safe }}');
```

with:

```javascript
        const labels = parseChartJson('daily-labels');
        const data = parseChartJson('daily-expenses');
```

Replace:

```javascript
        const labels = safeJson('{{ budget_labels|safe }}');
        const limits = safeJson('{{ budget_limits|safe }}');
        const actuals = safeJson('{{ budget_actuals|safe }}');
```

with:

```javascript
        const labels = parseChartJson('budget-labels');
        const limits = parseChartJson('budget-limits');
        const actuals = parseChartJson('budget-actuals');
```

- [ ] **Step 5: Loan detail chart (`loan_detail.html` / `views_loans.py`)**

In `core/views_loans.py`, remove the now-unused import (nothing else in this file calls `json.dumps`/`json.loads` once the lines below are changed):

```python
"""Loan management views — create, track, and simulate loans with full amortization."""
import json
from decimal import Decimal
```

becomes:

```python
"""Loan management views — create, track, and simulate loans with full amortization."""
from decimal import Decimal
```

In `loan_detail` view, change:

```python
        "chart_labels": json.dumps(chart_labels),
        "chart_balance": json.dumps(chart_balance),
        "chart_interest": json.dumps(chart_interest),
        "chart_principal": json.dumps(chart_principal),
        "chart_sim_balance": json.dumps(chart_sim_balance) if chart_sim_balance else "null",
```

to:

```python
        "chart_labels": chart_labels,
        "chart_balance": chart_balance,
        "chart_interest": chart_interest,
        "chart_principal": chart_principal,
        "chart_sim_balance": chart_sim_balance,
```

In `templates/core/loan_detail.html`, replace:

```html
{% block scripts %}
<script>
const labels = {{ chart_labels|safe }};
const balances = {{ chart_balance|safe }};
const simBalances = {{ chart_sim_balance|safe }};
```

with:

```html
{% block scripts %}
{{ chart_labels|json_script:"loan-chart-labels" }}
{{ chart_balance|json_script:"loan-chart-balance" }}
{{ chart_sim_balance|json_script:"loan-chart-sim-balance" }}
<script>
const labels = parseChartJson('loan-chart-labels');
const balances = parseChartJson('loan-chart-balance');
const simBalances = parseChartJson('loan-chart-sim-balance', null);
```

- [ ] **Step 6: Leave `cash_flow.html` on its current bare-literal pattern**

`cash_flow.html` injects `{{ chart_labels|safe }}` etc. as bare (unquoted) JS array/number literals, not inside a string that gets `JSON.parse`'d — this pattern is not subject to the apostrophe-breaking bug the other 5 templates have, so it is lower priority and out of scope for this task to avoid touching the cash-flow forecast view's five separate chart-data variables (`chart_labels`, `chart_balances`, `chart_split`, `proj_labels`, `proj_income_list`, `proj_expense_list`) without a matching audit of `views_cash_flow.py`'s output shapes. Leave as-is.

- [ ] **Step 7: Apply the shared `brlTick()` helper to the duplicated BRL tick-formatters**

These four spots duplicate the same `'R$ ' + value.toLocaleString('pt-BR', {...})` logic that `brlTick()` (from Task 17's `static/js/charts.js`) now centralizes:

In `templates/core/investment_detail.html`, replace:

```javascript
                    callbacks: {
                        label: ctx => 'R$ ' + ctx.parsed.y.toLocaleString('pt-BR', {minimumFractionDigits:2, maximumFractionDigits:2})
                    }
```

with:

```javascript
                    callbacks: {
                        label: ctx => brlTick(ctx.parsed.y, 2)
                    }
```

and replace:

```javascript
                        callback: v => 'R$ ' + v.toLocaleString('pt-BR', {minimumFractionDigits:2, maximumFractionDigits:2})
```

with:

```javascript
                        callback: v => brlTick(v, 2)
```

In `templates/core/cash_flow.html`, replace:

```javascript
      y: { ticks: { callback: v => 'R$ ' + v.toLocaleString('pt-BR', {minimumFractionDigits:2}) } },
```

with:

```javascript
      y: { ticks: { callback: v => brlTick(v, 2) } },
```

and replace:

```javascript
      y: { ticks: { callback: v => 'R$ ' + v.toLocaleString('pt-BR') } },
```

with:

```javascript
      y: { ticks: { callback: v => brlTick(v) } },
```

In `templates/core/loan_detail.html`, replace:

```javascript
                ticks: { callback: v => 'R$ ' + v.toLocaleString('pt-BR', {minimumFractionDigits:0}) }
```

with:

```javascript
                ticks: { callback: v => brlTick(v) }
```

In `templates/core/loan_add_funds.html`, replace:

```javascript
function fmt(v) {
    return 'R$ ' + v.toLocaleString('pt-BR', {minimumFractionDigits:2, maximumFractionDigits:2});
}
```

with:

```javascript
function fmt(v) {
    return brlTick(v, 2);
}
```

(keep the `fmt` name and signature — it's called elsewhere in this same file's simulator script; only its body changes.)

- [ ] **Step 8: Run the full suite**

Run: `python manage.py test core`
Expected: all green — `core/tests.py::test_reports_view` and `core/tests_dashboard.py` both render these templates and would fail on a template syntax error.

- [ ] **Step 9: Manual smoke check**

Open `/` (dashboard), `/investments/`, `/investments/<symbol>/` for any existing investment, `/reports/`, `/loans/<id>/` for any existing loan, `/loans/<id>/add-funds/`, and `/cash-flow/`. Confirm every chart still renders with real data and every BRL-formatted axis/tooltip value looks identical to before (open browser dev tools console, confirm no JS errors).

- [ ] **Step 10: Commit**

```bash
git add core/views_dashboard.py core/views_investments.py core/views_reports.py core/views_loans.py templates/core/dashboard.html templates/core/investment_dashboard.html templates/core/investment_detail.html templates/core/reports.html templates/core/loan_detail.html templates/core/cash_flow.html templates/core/loan_add_funds.html
git commit -m "fix: use Django's json_script + shared chart helpers instead of fragile JSON.parse(|safe) and duplicated BRL formatting"
```

---

### Task 19: Remove unused Toastify; move duplicated `.bg-light-soft` CSS into `custom.css`

**Files:**
- Modify: `templates/base.html` (remove Toastify)
- Modify: `static/css/custom.css` (add `.bg-light-soft` once)
- Modify: `templates/core/dashboard.html`, `templates/core/investment_dashboard.html`, `templates/core/safe_haven_dashboard.html`, `templates/core/transaction_list.html` (remove the duplicated rule, keep any other rules in the same `<style>` block)
- Modify: `templates/core/loan_add_funds.html`, `templates/core/loan_form.html`, `templates/core/loan_list.html`, `templates/core/loan_detail.html` (remove the now-fully-redundant `<style>` block, or just the duplicated rule where other rules remain)

- [ ] **Step 1: Confirm Toastify is dead code**

Run: `git grep -n "Toastify" -- templates/`
Expected: the only two hits are the `<link>`/`<script>` includes in `base.html` — no template ever calls `Toastify(...)`.

- [ ] **Step 2: Remove Toastify from `base.html`**

Replace:

```html
    <!-- Bootstrap Icons -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <!-- Toastify -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/toastify-js/src/toastify.min.css">
    <script src="https://cdn.jsdelivr.net/npm/toastify-js"></script>

    <!-- Custom CSS -->
```

with:

```html
    <!-- Bootstrap Icons -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">

    <!-- Custom CSS -->
```

- [ ] **Step 3: Add `.bg-light-soft` to `custom.css` once**

In `static/css/custom.css`, add near the other utility/glass classes (right after the `.glass-card:hover` rule, around line 100):

```css
/* Shared soft background used across list/table rows and search widgets */
.bg-light-soft {
    background: rgba(0, 0, 0, 0.02);
}

[data-theme="dark"] .bg-light-soft {
    background: rgba(255, 255, 255, 0.03);
}
```

- [ ] **Step 4: Remove the duplicated rule from templates that have other rules in the same block**

In `templates/core/dashboard.html`, replace:

```html
<style>
    .bg-light-soft {
        background: rgba(0, 0, 0, 0.02);
    }

    [data-theme="dark"] .bg-light-soft {
        background: rgba(255, 255, 255, 0.03);
    }

    .hover-translate:hover {
        transform: translateX(5px);
    }
```

with:

```html
<style>
    .hover-translate:hover {
        transform: translateX(5px);
    }
```

In `templates/core/investment_dashboard.html`, replace:

```html
<style>
    .bg-light-soft {
        background: rgba(0, 0, 0, 0.02);
    }

    [data-theme="dark"] .bg-light-soft {
        background: rgba(255, 255, 255, 0.03);
    }
</style>
```

with nothing — delete the entire `<style>...</style>` block (it contained only this now-shared rule).

In `templates/core/safe_haven_dashboard.html`, replace:

```html
<style>
    .bg-light-soft {
        background: rgba(0, 0, 0, 0.02);
    }

    [data-theme="dark"] .bg-light-soft {
        background: rgba(255, 255, 255, 0.03);
    }

    #simulatorForm input::-webkit-outer-spin-button,
    #simulatorForm input::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }
</style>
```

with:

```html
<style>
    #simulatorForm input::-webkit-outer-spin-button,
    #simulatorForm input::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }
</style>
```

In `templates/core/transaction_list.html`, replace:

```html
<style>
    .bg-light-soft {
        background: rgba(0, 0, 0, 0.02);
    }

    [data-theme="dark"] .bg-light-soft {
        background: rgba(255, 255, 255, 0.03);
    }

    .dropdown-item {
        font-size: 0.9rem;
        font-weight: 500;
```

with:

```html
<style>
    .dropdown-item {
        font-size: 0.9rem;
        font-weight: 500;
```

- [ ] **Step 5: Remove the fully-redundant `<style>` blocks from the 4 loan templates**

In `templates/core/loan_add_funds.html`, replace:

```html
<style>
.bg-light-soft { background: rgba(0,0,0,0.03); }
[data-theme="dark"] .bg-light-soft { background: rgba(255,255,255,0.04); }
</style>
```

with nothing (delete the block entirely).

In `templates/core/loan_form.html`, replace:

```html
<style>
.bg-light-soft { background: rgba(0,0,0,0.03); }
[data-theme="dark"] .bg-light-soft { background: rgba(255,255,255,0.04); }
</style>
```

with nothing (delete the block entirely).

In `templates/core/loan_detail.html`, replace:

```html
<style>
.bg-light-soft { background: rgba(0,0,0,0.03); }
[data-theme="dark"] .bg-light-soft { background: rgba(255,255,255,0.04); }
</style>
```

with nothing (delete the block entirely).

In `templates/core/loan_list.html`, replace:

```html
<style>
.bg-light-soft { background: rgba(0,0,0,0.03); }
[data-theme="dark"] .bg-light-soft { background: rgba(255,255,255,0.04); }
.opacity-60 { opacity: 0.6; }
</style>
```

with:

```html
<style>
.opacity-60 { opacity: 0.6; }
</style>
```

- [ ] **Step 6: Run the full suite**

Run: `python manage.py test core`
Expected: all green (CSS-only change).

- [ ] **Step 7: Manual smoke check**

Open every page that uses `.bg-light-soft` (`/`, `/investments/`, `/investments/safe/`, `/transactions/`, `/loans/`, `/loans/<id>/`, `/loans/<id>/pay/`, `/loans/add/`, and — newly fixed — `/goals/add/` and `/settings/`, which previously had **no** styling on that class at all). Confirm the soft background now appears consistently (subtly lighter/darker depending on theme) on all of them, including the two that were previously unstyled.

- [ ] **Step 8: Commit**

```bash
git add templates/base.html static/css/custom.css templates/core/dashboard.html templates/core/investment_dashboard.html templates/core/safe_haven_dashboard.html templates/core/transaction_list.html templates/core/loan_add_funds.html templates/core/loan_form.html templates/core/loan_detail.html templates/core/loan_list.html
git commit -m "fix: remove unused Toastify dependency, dedupe .bg-light-soft into custom.css (fixes 2 pages missing it)"
```

---

### Task 20: Fix stale `CLAUDE.md` reference to a deleted file

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Confirm the file no longer exists**

Run: `git ls-files | git grep -l "investment_dashboard.html.bak" || echo "not tracked"`
Run: `ls templates/core/investment_dashboard.html.bak 2>/dev/null || echo "not on disk"` (PowerShell: `Test-Path templates/core/investment_dashboard.html.bak`)
Expected: both confirm the file is gone.

- [ ] **Step 2: Remove the stale line from `CLAUDE.md`**

In `CLAUDE.md`, find and remove the line:

```
- The `.bak` template file (`investment_dashboard.html.bak`) is leftover and should not be used.
```

(it lives in the "Common Pitfalls" section).

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: remove stale reference to deleted investment_dashboard.html.bak"
```

---

### Task 21: Redesign the login/register pages with a dedicated auth layout

**Files:**
- Create: `templates/base_auth.html`
- Modify: `templates/registration/login.html`
- Modify: `templates/registration/register.html`

**Interfaces:**
- Produces: `base_auth.html` — a minimal layout (no sidebar, no floating quick-add button, no quick-add modal) with a `{% block content %}` like `base.html`, reusing the same theme toggle (`localStorage` key `theme`, same `applyTheme`/`toggleTheme` functions) and the same CDN assets (Bootstrap 5.3.0, Bootstrap Icons, Google Fonts, `custom.css`).

**Bug this also fixes:** today `login.html`/`register.html` extend the full `base.html`, so an unauthenticated visitor sees the entire app sidebar (every nav link, the floating "+" button, the quick-add modal) on the login screen — all of which just redirect back to login. The new `base_auth.html` removes all of that.

- [ ] **Step 1: Create `templates/base_auth.html`**

```html
<!DOCTYPE html>
<html lang="pt-br" data-theme="light">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Entrar{% endblock %} — Patrimônio</title>

    <!-- Fonts -->
    <link
        href="https://fonts.googleapis.com/css?family=Nunito:200,200i,300,300i,400,400i,600,600i,700,700i,800,800i,900,900i"
        rel="stylesheet">

    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Bootstrap Icons -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">

    <!-- Custom CSS -->
    {% load static %}
    <link href="{% static 'css/custom.css' %}?v=2" rel="stylesheet">

    <!-- Favicon Fix -->
    <link rel="icon" href="data:,">

    <style>
        body.auth-body {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem 1rem;
        }

        .auth-theme-toggle {
            position: fixed;
            top: 1.5rem;
            right: 1.5rem;
            z-index: 10;
        }

        .auth-card {
            width: 100%;
            max-width: 440px;
        }

        .auth-brand-icon {
            width: 56px;
            height: 56px;
            font-size: 1.75rem;
        }
    </style>
</head>

<body id="page-top" class="auth-body">

    <div class="auth-theme-toggle">
        <button type="button" class="btn btn-sm glass-card border-0 px-3 py-2" onclick="toggleTheme()">
            <i class="bi bi-moon-stars-fill" id="theme-icon"></i>
        </button>
    </div>

    <div class="auth-card">
        <div class="text-center mb-4">
            <div class="brand-icon brand-icon-logo auth-brand-icon mx-auto mb-3">
                <i class="bi bi-gem"></i>
            </div>
            <span class="brand-name">Patrimônio</span>
        </div>

        {% if messages %}
        {% for message in messages %}
        <div class="alert alert-{{ message.tags }} alert-dismissible fade show shadow-sm border-0 mb-4" role="alert">
            <div class="d-flex align-items-center">
                <i class="bi bi-info-circle-fill me-2 fs-5"></i>
                <div>{{ message }}</div>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        {% endfor %}
        {% endif %}

        {% block content %}{% endblock %}
    </div>

    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        const html = document.documentElement;
        const themeIcon = document.getElementById('theme-icon');
        const savedTheme = localStorage.getItem('theme') || 'light';

        const applyTheme = (theme) => {
            html.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
            if (themeIcon) {
                themeIcon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
            }
        };

        applyTheme(savedTheme);

        function toggleTheme() {
            const current = html.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            applyTheme(next);
        }
    </script>
    {% block scripts %}{% endblock %}
</body>

</html>
```

- [ ] **Step 2: Rewrite `login.html` to extend `base_auth.html` with a nicer card**

Replace the entire contents of `templates/registration/login.html` with:

```html
{% extends 'base_auth.html' %}
{% load crispy_forms_tags %}

{% block title %}Entrar{% endblock %}

{% block content %}
<div class="card glass-card border-0 shadow-lg">
    <div class="card-body p-4 p-md-5">
        <h3 class="fw-bold text-center mb-1">Bem-vindo de volta</h3>
        <p class="text-muted text-center mb-4">Entre para continuar gerenciando suas finanças.</p>

        <form method="post">
            {% csrf_token %}
            {{ form|crispy }}
            <div class="form-check mb-3">
                <input class="form-check-input" type="checkbox" id="showPassword">
                <label class="form-check-label" for="showPassword">
                    Mostrar senha
                </label>
            </div>
            <button type="submit" class="btn-premium w-100 justify-content-center">Entrar</button>
        </form>
    </div>
    <div class="card-footer text-center border-0 bg-transparent pb-4">
        Não tem uma conta? <a href="{% url 'register' %}">Cadastre-se aqui</a>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    document.getElementById('showPassword').addEventListener('change', function () {
        var passwordInput = document.getElementById('id_password');
        if (this.checked) {
            passwordInput.type = 'text';
        } else {
            passwordInput.type = 'password';
        }
    });
</script>
{% endblock %}
```

- [ ] **Step 3: Rewrite `register.html` to extend `base_auth.html` with the same card style**

Replace the entire contents of `templates/registration/register.html` with:

```html
{% extends 'base_auth.html' %}
{% load crispy_forms_tags %}

{% block title %}Criar Conta{% endblock %}

{% block content %}
<div class="card glass-card border-0 shadow-lg">
    <div class="card-body p-4 p-md-5">
        <h3 class="fw-bold text-center mb-1">Criar conta</h3>
        <p class="text-muted text-center mb-4">Comece a organizar suas finanças em minutos.</p>

        <form method="post">
            {% csrf_token %}
            {{ form|crispy }}
            <div class="form-check mb-3">
                <input class="form-check-input" type="checkbox" id="showPassword">
                <label class="form-check-label" for="showPassword">
                    Mostrar senhas
                </label>
            </div>
            <button type="submit" class="btn-premium w-100 justify-content-center">Cadastrar</button>
        </form>
    </div>
    <div class="card-footer text-center border-0 bg-transparent pb-4">
        <p class="mb-0">Já tem uma conta? <a href="{% url 'login' %}">Entrar</a></p>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    document.getElementById('showPassword').addEventListener('change', function () {
        var pass1 = document.getElementById('id_password1');
        var pass2 = document.getElementById('id_password2');
        var type = this.checked ? 'text' : 'password';
        if (pass1) pass1.type = type;
        if (pass2) pass2.type = type;
    });
</script>
{% endblock %}
```

- [ ] **Step 4: Run the full suite**

Run: `python manage.py test core`
Expected: all green — no existing test asserts on `login.html`'s old markup (`core/tests.py` only tests authenticated views via `self.client.login`, which does not render the login template).

- [ ] **Step 5: Manual smoke check**

Run the app, log out, open `/login/` and `/register/`:
- Confirm neither page shows the app sidebar, the floating "+" button, or the quick-add modal.
- Confirm the theme toggle (top-right) switches light/dark and it's remembered on reload.
- Confirm "Mostrar senha(s)" still toggles password visibility.
- Confirm both forms still submit and redirect correctly (login → dashboard, register → login with a success message).

- [ ] **Step 6: Commit**

```bash
git add templates/base_auth.html templates/registration/login.html templates/registration/register.html
git commit -m "feat(internal): redesign login/register with a dedicated auth layout, fixes sidebar leaking onto login page"
```

---

### Task 22: Final verification pass

**Files:** none (verification only)

- [ ] **Step 1: Run the entire test suite one more time**

Run: `python manage.py test core -v 2`
Expected: every test across `tests.py`, `tests_alerts.py`, `tests_calendar.py`, `tests_goals.py`, `tests_import.py`, `tests_recurrence.py`, `tests_security.py`, `tests_validation.py`, `tests_atomicity.py`, `tests_investments.py`, `tests_dashboard.py`, `tests_budgets.py`, `tests_uploads.py`, `tests_settings.py`, `tests_market_data.py` passes.

- [ ] **Step 2: Run Django's system checks**

Run: `python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3: Confirm migrations are consistent**

Run: `python manage.py makemigrations --check --dry-run`
Expected: exits 0 with no output (no missing migrations after Task 8's `0011_add_min_value_validators`).

- [ ] **Step 4: Manual smoke checklist (run the app with `python run_app.py` or `python manage.py runserver`)**

- [ ] Login page looks like the new design; register page matches it; both work end to end.
- [ ] Dashboard loads, chart renders, budget alerts still show correctly.
- [ ] Add a transaction with a negative amount → rejected with a clear error.
- [ ] Add a transaction, assign a category you own → works; the category dropdown never shows another (test) user's categories.
- [ ] Import a `.csv`/`.xlsx` bank statement → works; try a `.exe` or an oversized file → rejected with a clear message.
- [ ] Import an `.ofx` file → works; try a `.txt` file → rejected with a clear message.
- [ ] `/settings/` — as a non-staff user, redirected to dashboard with a message; as a staff user, can save the BRAPI token.
- [ ] Transfer money between two accounts → balances update correctly.
- [ ] Make a loan payment → loan balance, payment history, and dashboard loan summary all update correctly.
- [ ] Investments dashboard: search a ticker (including a deliberately weird string like `<b>x</b>`) → renders as literal text, not executed HTML.
- [ ] Every currency figure across dashboard, transactions, investments, safe-haven, reports, and PDF export shows as `R$ 1.234,56` consistently.
- [ ] `logs/finance.log` shows each log line exactly once (no duplicates) and `logs/debug.log` is no longer being written to.

- [ ] **Step 5: Report completion**

No commit for this task — it's a verification pass. If any manual check fails, go back to the relevant task, fix, re-test, and re-commit before considering the plan complete.
