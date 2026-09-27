"""Camada de consulta compartilhada: filtro de transações, KPIs e séries para
gráficos. Dashboard, lista de transações e exportações usam as mesmas regras
daqui — assim um recorte feito no dashboard bate exatamente com a lista.
"""
from __future__ import annotations

import datetime
from collections import OrderedDict
from dataclasses import dataclass, field, replace
from decimal import Decimal
from urllib.parse import urlencode

from django.db.models import Avg, Count, F, Max, Min, Q, Sum
from django.db.models.functions import Coalesce, TruncDay, TruncMonth

from .dates import add_months, iter_months, month_bounds, month_label, parse_date, today
from .models import Category, Investment, Loan, Transaction

ZERO = Decimal("0")

# Paleta categórica (mesma ordem de static/js/charts.js → CATEGORY_PALETTE).
CATEGORY_PALETTE = [
    "#6366f1", "#10b981", "#f59e0b", "#ef4444", "#3b82f6", "#ec4899",
    "#14b8a6", "#8b5cf6", "#f97316", "#84cc16", "#06b6d4", "#a855f7",
]
OTHERS_COLOR = "#94a3b8"

PRESETS = OrderedDict([
    ("month", "Mês"),
    ("3m", "3 meses"),
    ("6m", "6 meses"),
    ("12m", "12 meses"),
    ("year", "Ano"),
    ("all", "Tudo"),
    ("custom", "Personalizado"),
])
PRESET_MONTHS = {"month": 1, "3m": 3, "6m": 6, "12m": 12}

SORT_FIELDS = {
    "date": ("date", "id"),
    "-date": ("-date", "-id"),
    "amount": ("amount", "id"),
    "-amount": ("-amount", "-id"),
    "description": ("description", "id"),
    "-description": ("-description", "-id"),
    "created": (F("created_at").asc(nulls_first=True), "id"),
    "-created": (F("created_at").desc(nulls_last=True), "-id"),
}

PAYMENT_METHODS = dict(Transaction.PAYMENT_METHODS)
ORIGINS = dict(Transaction.ORIGIN_CHOICES)


def color_for(category_id, explicit: str = "") -> str:
    if explicit:
        return explicit
    if not category_id:
        return OTHERS_COLOR
    return CATEGORY_PALETTE[category_id % len(CATEGORY_PALETTE)]


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_decimal(value):
    if value in (None, ""):
        return None
    from .forms import clean_currency_value  # evita import circular
    try:
        return clean_currency_value(str(value))
    except Exception:
        return None


def _bool_param(params, name, default):
    raw = params.get(name)
    if raw is None or raw == "":
        return default
    return raw in ("1", "true", "on", "sim")


def expand_categories(user, ids) -> tuple[int, ...]:
    """Ids selecionados + subcategorias, sempre do próprio usuário."""
    ids = [i for i in ids if i]
    if not ids:
        return ()
    return tuple(
        Category.objects.filter(user=user)
        .filter(Q(id__in=ids) | Q(parent_id__in=ids))
        .values_list("id", flat=True)
    )


def categories_grouped(user, type_=None):
    """[(pai, [filhos])] em ordem alfabética — para <optgroup> nos filtros."""
    qs = Category.objects.filter(user=user).order_by("name")
    if type_:
        qs = qs.filter(type=type_)
    cats = list(qs)
    children = {}
    for c in cats:
        if c.parent_id:
            children.setdefault(c.parent_id, []).append(c)
    roots = [c for c in cats if not c.parent_id or c.parent_id not in {x.id for x in cats}]
    return [(r, children.get(r.id, [])) for r in roots]


@dataclass(frozen=True)
class TxFilter:
    user: object
    preset: str = "all"
    anchor: datetime.date | None = None       # mês de referência dos presets
    start: datetime.date | None = None
    end: datetime.date | None = None
    type: str | None = None
    selected_categories: tuple[int, ...] = ()
    category_ids: tuple[int, ...] = ()        # já expandido com subcategorias
    payment_methods: tuple[str, ...] = ()
    account_id: int | None = None
    origins: tuple[str, ...] = ()
    search: str = ""
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None
    include_loans: bool = True
    include_investments: bool = True
    status: str = "all"                       # all | realized | forecast
    sort: str = "-date"
    defaults: dict = field(default_factory=dict, compare=False, repr=False)

    # ── construção ────────────────────────────────────────────────────────
    @classmethod
    def from_request(cls, request, *, default_preset="all", include_investments=True,
                     include_loans=True, session_key=None):
        params = request.GET
        if session_key:
            # Lembra os filtros entre visitas — mas não o mês navegado: voltar
            # ao dashboard outro dia deve abrir o mês corrente.
            transient = ("page", "tab", "month", "year")
            if any(k not in transient for k in params.keys()):
                keep = params.copy()
                for k in transient:
                    keep.pop(k, None)
                request.session[session_key] = keep.urlencode()
            elif request.session.get(session_key):
                from django.http import QueryDict
                saved = QueryDict(request.session[session_key], mutable=True)
                for k in ("month", "year"):
                    if k in params:
                        saved[k] = params[k]
                params = saved
        return cls.from_params(
            request.user, params, default_preset=default_preset,
            include_investments=include_investments, include_loans=include_loans,
        )

    @classmethod
    def from_params(cls, user, params, *, default_preset="all", include_investments=True,
                    include_loans=True):
        t = today()
        preset = params.get("period") or default_preset
        if preset not in PRESETS:
            preset = default_preset

        year = _to_int(params.get("year"))
        month = _to_int(params.get("month"))
        anchor = t.replace(day=1)
        if year and month and 1 <= month <= 12 and 1900 < year < 3000:
            anchor = datetime.date(year, month, 1)

        start = end = None
        if preset in PRESET_MONTHS:
            n = PRESET_MONTHS[preset]
            start = add_months(anchor, -(n - 1), day=1)
            end = month_bounds(anchor.year, anchor.month)[1]
        elif preset == "year":
            start, end = datetime.date(anchor.year, 1, 1), datetime.date(anchor.year, 12, 31)
        elif preset == "custom":
            start = parse_date(params.get("start_date"))
            end = parse_date(params.get("end_date"))
            if start and end and start > end:
                start, end = end, start
        # Compatibilidade com links antigos (?start_date=...&end_date=... sem period)
        if preset == "all" and (params.get("start_date") or params.get("end_date")):
            start = parse_date(params.get("start_date"))
            end = parse_date(params.get("end_date"))
            if start or end:
                preset = "custom"

        type_ = params.get("type")
        if type_ not in ("RECEITA", "DESPESA"):
            type_ = None

        selected = tuple(dict.fromkeys(
            i for i in (_to_int(v) for v in params.getlist("category")) if i
        ))
        category_ids = expand_categories(user, selected)
        # Categoria de outro usuário (ou inexistente) é descartada.
        valid_selected = tuple(i for i in selected if i in category_ids)

        payment_methods = tuple(v for v in params.getlist("payment") if v in PAYMENT_METHODS)
        origins = tuple(v for v in params.getlist("origin") if v in ORIGINS)

        account_id = _to_int(params.get("account"))
        if account_id and not user.bank_accounts.filter(pk=account_id).exists():
            account_id = None

        status = params.get("status") if params.get("status") in ("realized", "forecast") else "all"
        sort = params.get("sort") if params.get("sort") in SORT_FIELDS else "-date"

        return cls(
            user=user, preset=preset, anchor=anchor, start=start, end=end, type=type_,
            selected_categories=valid_selected,
            category_ids=category_ids if valid_selected else (),
            payment_methods=payment_methods, account_id=account_id, origins=origins,
            search=(params.get("search") or "").strip()[:100],
            min_amount=_to_decimal(params.get("min_amount")),
            max_amount=_to_decimal(params.get("max_amount")),
            include_loans=_bool_param(params, "loans", include_loans),
            include_investments=_bool_param(params, "investments", include_investments),
            status=status, sort=sort,
            defaults={"preset": default_preset, "loans": include_loans,
                      "investments": include_investments},
        )

    # ── aplicação ─────────────────────────────────────────────────────────
    def base_queryset(self):
        return Transaction.objects.filter(user=self.user)

    def apply(self, qs=None, *, period=True, category=True):
        qs = self.base_queryset() if qs is None else qs
        if period:
            if self.start:
                qs = qs.filter(date__gte=self.start)
            if self.end:
                qs = qs.filter(date__lte=self.end)
        if self.type:
            qs = qs.filter(type=self.type)
        if category and self.category_ids:
            qs = qs.filter(category_id__in=self.category_ids)
        if self.payment_methods:
            qs = qs.filter(payment_method__in=self.payment_methods)
        if self.account_id:
            qs = qs.filter(account_id=self.account_id)
        if self.origins:
            qs = qs.filter(origin__in=self.origins)
        if self.search:
            qs = qs.filter(Q(description__icontains=self.search) | Q(category__name__icontains=self.search))
        if self.min_amount is not None:
            qs = qs.filter(amount__gte=self.min_amount)
        if self.max_amount is not None:
            qs = qs.filter(amount__lte=self.max_amount)
        if not self.include_loans:
            qs = qs.exclude(origin=Transaction.ORIGIN_EMPRESTIMO).exclude(
                category__nature=Category.NATURE_DIVIDA)
        if not self.include_investments:
            qs = qs.exclude(origin=Transaction.ORIGIN_INVESTIMENTO).exclude(
                category__nature=Category.NATURE_INVESTIMENTO)
        if self.status == "realized":
            qs = qs.filter(date__lte=today())
        elif self.status == "forecast":
            qs = qs.filter(date__gt=today())
        return qs

    def ordered(self, qs):
        return qs.order_by(*SORT_FIELDS[self.sort])

    # ── navegação ─────────────────────────────────────────────────────────
    @property
    def months_span(self) -> int | None:
        if self.preset in PRESET_MONTHS:
            return PRESET_MONTHS[self.preset]
        if self.preset == "year":
            return 12
        return None

    def shifted(self, direction: int) -> TxFilter | None:
        """Mesmo filtro deslocado um período para trás (-1) ou frente (+1)."""
        span = self.months_span
        if not span or not self.anchor:
            return None
        anchor = add_months(self.anchor, span * direction, day=1)
        start = add_months(self.start, span * direction, day=1)
        end = month_bounds(anchor.year, anchor.month)[1]
        if self.preset == "year":
            start, end = datetime.date(anchor.year, 1, 1), datetime.date(anchor.year, 12, 31)
        return replace(self, anchor=anchor, start=start, end=end)

    def previous_period(self) -> TxFilter | None:
        """Período de mesmo tamanho imediatamente anterior (para variação %)."""
        shifted = self.shifted(-1)
        if shifted:
            return shifted
        if self.start and self.end:
            length = (self.end - self.start).days + 1
            return replace(self, start=self.start - datetime.timedelta(days=length),
                           end=self.start - datetime.timedelta(days=1))
        return None

    @property
    def period_label(self) -> str:
        if self.preset == "month" and self.anchor:
            return month_label(self.anchor, short=False)
        if self.preset == "year" and self.anchor:
            return str(self.anchor.year)
        if self.start and self.end:
            return f"{self.start:%d/%m/%Y} – {self.end:%d/%m/%Y}"
        if self.start:
            return f"desde {self.start:%d/%m/%Y}"
        if self.end:
            return f"até {self.end:%d/%m/%Y}"
        return "Todo o período"

    @property
    def days(self) -> int | None:
        if self.start and self.end:
            return (self.end - self.start).days + 1
        return None

    # ── querystring ───────────────────────────────────────────────────────
    def params(self, **overrides) -> list[tuple[str, str]]:
        data: dict[str, object] = {}
        if self.preset != self.defaults.get("preset", "all"):
            data["period"] = self.preset
        if self.preset in PRESET_MONTHS or self.preset == "year":
            if self.anchor and self.anchor != today().replace(day=1):
                data["month"] = self.anchor.month
                data["year"] = self.anchor.year
        if self.preset == "custom":
            if self.start:
                data["start_date"] = self.start.isoformat()
            if self.end:
                data["end_date"] = self.end.isoformat()
        if self.type:
            data["type"] = self.type
        if self.selected_categories:
            data["category"] = list(self.selected_categories)
        if self.payment_methods:
            data["payment"] = list(self.payment_methods)
        if self.account_id:
            data["account"] = self.account_id
        if self.origins:
            data["origin"] = list(self.origins)
        if self.search:
            data["search"] = self.search
        if self.min_amount is not None:
            data["min_amount"] = str(self.min_amount)
        if self.max_amount is not None:
            data["max_amount"] = str(self.max_amount)
        if self.include_loans != self.defaults.get("loans", True):
            data["loans"] = "1" if self.include_loans else "0"
        if self.include_investments != self.defaults.get("investments", True):
            data["investments"] = "1" if self.include_investments else "0"
        if self.status != "all":
            data["status"] = self.status
        if self.sort != "-date":
            data["sort"] = self.sort
        for k, v in overrides.items():
            if v is None:
                data.pop(k, None)
            else:
                data[k] = v
        items = []
        for k, v in data.items():
            if isinstance(v, (list, tuple)):
                items.extend((k, str(x)) for x in v)
            else:
                items.append((k, str(v)))
        return items

    def querystring(self, **overrides) -> str:
        return urlencode(self.params(**overrides))

    def nav_querystring(self, direction: int) -> str | None:
        shifted = self.shifted(direction)
        if not shifted:
            return None
        return shifted.querystring(month=shifted.anchor.month, year=shifted.anchor.year)

    def active_chips(self) -> list[dict]:
        """Filtros ativos como chips removíveis ({label, remove_qs})."""
        chips = []
        if self.type:
            chips.append({"label": "Receitas" if self.type == "RECEITA" else "Despesas",
                          "qs": self.querystring(type=None)})
        if self.selected_categories:
            names = dict(Category.objects.filter(id__in=self.selected_categories).values_list("id", "name"))
            for cid in self.selected_categories:
                rest = [c for c in self.selected_categories if c != cid]
                chips.append({"label": f"Categoria: {names.get(cid, cid)}",
                              "qs": self.querystring(category=rest or None)})
        for pm in self.payment_methods:
            rest = [p for p in self.payment_methods if p != pm]
            chips.append({"label": PAYMENT_METHODS[pm], "qs": self.querystring(payment=rest or None)})
        for og in self.origins:
            rest = [o for o in self.origins if o != og]
            chips.append({"label": f"Origem: {ORIGINS[og]}", "qs": self.querystring(origin=rest or None)})
        if self.account_id:
            chips.append({"label": "Conta", "qs": self.querystring(account=None)})
        if self.search:
            chips.append({"label": f"“{self.search}”", "qs": self.querystring(search=None)})
        if self.min_amount is not None:
            chips.append({"label": f"≥ R$ {self.min_amount}", "qs": self.querystring(min_amount=None)})
        if self.max_amount is not None:
            chips.append({"label": f"≤ R$ {self.max_amount}", "qs": self.querystring(max_amount=None)})
        if self.status != "all":
            chips.append({"label": "Só realizados" if self.status == "realized" else "Só previstos",
                          "qs": self.querystring(status=None)})
        if self.include_loans != self.defaults.get("loans", True):
            chips.append({"label": "Sem empréstimos" if not self.include_loans else "Com empréstimos",
                          "qs": self.querystring(loans=None)})
        if self.include_investments != self.defaults.get("investments", True):
            chips.append({"label": "Com aportes" if self.include_investments else "Sem aportes",
                          "qs": self.querystring(investments=None)})
        return chips

    @property
    def single_category(self) -> Category | None:
        if len(self.selected_categories) == 1:
            return Category.objects.filter(user=self.user, pk=self.selected_categories[0]).first()
        return None


def filter_ui_context(flt: TxFilter, **extra_qs) -> dict:
    """Contexto que o partial _tx_filters.html precisa."""
    from .models import BankAccount
    extra = {k: v for k, v in extra_qs.items() if v is not None}
    prev_f, next_f = flt.shifted(-1), flt.shifted(1)
    return {
        "filter": flt,
        "presets": PRESETS,
        "category_groups": categories_grouped(flt.user),
        "payment_methods": Transaction.PAYMENT_METHODS,
        "origins": Transaction.ORIGIN_CHOICES,
        "accounts": BankAccount.objects.filter(user=flt.user),
        "nav_prev_qs": prev_f.querystring(month=prev_f.anchor.month, year=prev_f.anchor.year, **extra) if prev_f else "",
        "nav_next_qs": next_f.querystring(month=next_f.anchor.month, year=next_f.anchor.year, **extra) if next_f else "",
        "advanced_open": bool(flt.payment_methods or flt.origins or flt.account_id
                              or flt.min_amount is not None or flt.max_amount is not None
                              or flt.status != "all"),
    }


# ── KPIs ──────────────────────────────────────────────────────────────────

def kpis(qs) -> dict:
    """Todos os KPIs de um queryset filtrado numa única ida ao banco."""
    t = today()
    is_inc = Q(type="RECEITA")
    is_exp = Q(type="DESPESA")
    agg = qs.aggregate(
        income=Sum("amount", filter=is_inc),
        expense=Sum("amount", filter=is_exp),
        income_realized=Sum("amount", filter=is_inc & Q(date__lte=t)),
        expense_realized=Sum("amount", filter=is_exp & Q(date__lte=t)),
        income_loans=Sum("amount", filter=is_inc & Q(origin=Transaction.ORIGIN_EMPRESTIMO)),
        expense_loans=Sum("amount", filter=is_exp & Q(origin=Transaction.ORIGIN_EMPRESTIMO)),
        expense_card=Sum("amount", filter=is_exp & Q(payment_method="CREDITO")),
        expense_recurring=Sum("amount", filter=is_exp & Q(origin=Transaction.ORIGIN_RECORRENTE)),
        count=Count("id"),
        count_income=Count("id", filter=is_inc),
        count_expense=Count("id", filter=is_exp),
        avg_expense=Avg("amount", filter=is_exp),
        max_expense=Max("amount", filter=is_exp),
        first_date=Min("date"),
        last_date=Max("date"),
    )
    out = {k: (v if v is not None else ZERO) for k, v in agg.items()
           if k not in ("count", "count_income", "count_expense", "first_date", "last_date")}
    out.update(count=agg["count"], count_income=agg["count_income"],
               count_expense=agg["count_expense"],
               first_date=agg["first_date"], last_date=agg["last_date"])
    out["net"] = out["income"] - out["expense"]
    out["income_forecast"] = out["income"] - out["income_realized"]
    out["expense_forecast"] = out["expense"] - out["expense_realized"]
    out["income_operational"] = out["income"] - out["income_loans"]
    out["savings_rate"] = (out["net"] / out["income"] * 100) if out["income"] > 0 else None
    return out


def pct_change(current, previous):
    if not previous:
        return None
    return (Decimal(current) - Decimal(previous)) / Decimal(previous) * 100


def kpis_with_comparison(flt: TxFilter) -> dict:
    current = kpis(flt.apply())
    prev_flt = flt.previous_period()
    if prev_flt:
        prev = kpis(prev_flt.apply())
        current["prev"] = prev
        current["income_change"] = pct_change(current["income"], prev["income"])
        current["expense_change"] = pct_change(current["expense"], prev["expense"])
        current["net_change"] = (current["net"] - prev["net"]) if prev["count"] else None
    else:
        current["prev"] = None
        current["income_change"] = current["expense_change"] = current["net_change"] = None
    days = flt.days
    if not days and current["first_date"] and current["last_date"]:
        days = (current["last_date"] - current["first_date"]).days + 1
    current["daily_avg"] = (current["expense"] / days) if days else ZERO
    current["days"] = days
    biggest = flt.apply().filter(type="DESPESA").select_related("category").order_by("-amount", "-id").first()
    current["biggest"] = biggest
    return current


# ── séries para gráficos ──────────────────────────────────────────────────

def by_category(qs, type_="DESPESA", top=8) -> list[dict]:
    """Totais agrupados pela categoria-raiz (subcategorias somam no pai)."""
    rows = (
        qs.filter(type=type_)
        .annotate(root_id=Coalesce("category__parent_id", "category_id"))
        .values("root_id")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
    rows = list(rows)
    cats = {c.id: c for c in Category.objects.filter(id__in=[r["root_id"] for r in rows if r["root_id"]])}
    total_all = sum((r["total"] for r in rows), ZERO)
    out = []
    for r in rows:
        cat = cats.get(r["root_id"])
        out.append({
            "id": r["root_id"],
            "name": cat.name if cat else "Sem categoria",
            "color": color_for(r["root_id"], cat.color if cat else ""),
            "total": r["total"],
            "count": r["count"],
            "pct": (r["total"] / total_all * 100) if total_all else ZERO,
        })
    if top and len(out) > top:
        rest = out[top:]
        out = out[:top]
        rest_total = sum((r["total"] for r in rest), ZERO)
        out.append({
            "id": None, "name": f"Outras ({len(rest)})", "color": OTHERS_COLOR,
            "total": rest_total, "count": sum(r["count"] for r in rest),
            "pct": (rest_total / total_all * 100) if total_all else ZERO,
        })
    return out


def by_subcategory(qs, parent: Category) -> list[dict]:
    rows = (
        qs.filter(Q(category=parent) | Q(category__parent=parent))
        .values("category_id", "category__name")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
    rows = list(rows)
    total_all = sum((r["total"] for r in rows), ZERO)
    return [{
        "id": r["category_id"],
        "name": r["category__name"] + (" (direto)" if r["category_id"] == parent.id else ""),
        "total": r["total"], "count": r["count"],
        "pct": (r["total"] / total_all * 100) if total_all else ZERO,
    } for r in rows]


def by_payment_method(qs, type_="DESPESA") -> list[dict]:
    rows = qs.filter(type=type_).values("payment_method").annotate(total=Sum("amount")).order_by("-total")
    return [{"key": r["payment_method"], "name": PAYMENT_METHODS.get(r["payment_method"], r["payment_method"]),
             "total": r["total"]} for r in rows]


def monthly_series(qs, first_month: datetime.date, last_month: datetime.date) -> dict:
    """Receita/despesa/resultado por mês cheio, incluindo meses sem movimento."""
    first_month = first_month.replace(day=1)
    end = month_bounds(last_month.year, last_month.month)[1]
    rows = (
        qs.filter(date__gte=first_month, date__lte=end)
        .annotate(m=TruncMonth("date"))
        .values("m")
        .annotate(income=Sum("amount", filter=Q(type="RECEITA")),
                  expense=Sum("amount", filter=Q(type="DESPESA")))
    )
    by_month = {}
    for r in rows:
        key = r["m"].date() if isinstance(r["m"], datetime.datetime) else r["m"]
        by_month[key] = r
    this_month = today().replace(day=1)
    labels, income, expense, net, forecast = [], [], [], [], []
    for m in iter_months(first_month, end):
        r = by_month.get(m, {})
        inc = float(r.get("income") or 0)
        exp = float(r.get("expense") or 0)
        labels.append(month_label(m))
        income.append(inc)
        expense.append(exp)
        net.append(round(inc - exp, 2))
        forecast.append(m > this_month)
    return {"labels": labels, "income": income, "expense": expense, "net": net, "forecast": forecast}


def daily_cumulative(qs, start: datetime.date, end: datetime.date, type_="DESPESA") -> list[float]:
    rows = (
        qs.filter(type=type_, date__gte=start, date__lte=end)
        .annotate(d=TruncDay("date"))
        .values("d")
        .annotate(total=Sum("amount"))
    )
    by_day = {}
    for r in rows:
        key = r["d"].date() if isinstance(r["d"], datetime.datetime) else r["d"]
        by_day[key] = float(r["total"] or 0)
    out, running = [], 0.0
    day = start
    while day <= end:
        running += by_day.get(day, 0.0)
        out.append(round(running, 2))
        day += datetime.timedelta(days=1)
    return out


def committed_by_origin(user, months=12, include_loans=True) -> dict:
    """Despesas já lançadas nos próximos `months` meses, empilhadas por origem."""
    t = today()
    first = add_months(t.replace(day=1), 1, day=1)
    last = add_months(first, months - 1, day=1)
    qs = Transaction.objects.filter(user=user, type="DESPESA",
                                    date__gte=first, date__lte=month_bounds(last.year, last.month)[1])
    if not include_loans:
        qs = qs.exclude(origin=Transaction.ORIGIN_EMPRESTIMO)
    rows = qs.annotate(m=TruncMonth("date")).values("m", "origin").annotate(total=Sum("amount"))
    groups = OrderedDict([
        (Transaction.ORIGIN_PARCELA, "Cartão (parcelas)"),
        (Transaction.ORIGIN_RECORRENTE, "Fixas (recorrentes)"),
        (Transaction.ORIGIN_EMPRESTIMO, "Empréstimos"),
        ("OUTROS", "Outras já lançadas"),
    ])
    months_list = list(iter_months(first, last))
    data = {g: [0.0] * len(months_list) for g in groups}
    idx = {m: i for i, m in enumerate(months_list)}
    for r in rows:
        key = r["m"].date() if isinstance(r["m"], datetime.datetime) else r["m"]
        g = r["origin"] if r["origin"] in groups else "OUTROS"
        if key in idx:
            data[g][idx[key]] += float(r["total"] or 0)
    return {
        "labels": [month_label(m) for m in months_list],
        "datasets": [{"key": g, "label": label, "data": [round(v, 2) for v in data[g]]}
                     for g, label in groups.items()],
    }


# ── feeds ─────────────────────────────────────────────────────────────────

def recent(user, limit=8) -> list[dict]:
    """Últimos lançamentos por data de cadastro, com parcelas de uma mesma
    compra (e linhas de uma mesma importação) agrupadas num item só."""
    qs = (
        Transaction.objects.filter(user=user)
        # Só o que o usuário lançou: fora as ocorrências geradas automaticamente
        # pelas recorrências e as parcelas previstas de empréstimo.
        .exclude(origin=Transaction.ORIGIN_RECORRENTE, description__endswith="(Recorrente)")
        .exclude(origin=Transaction.ORIGIN_EMPRESTIMO, type="DESPESA", loan_payment__isnull=True,
                 loan__isnull=False)
        .select_related("category", "loan")
        .order_by(F("created_at").desc(nulls_last=True), "-id")
    )
    items: list[dict] = []
    index: dict[tuple, dict] = {}
    t = today()
    for tx in qs[: limit * 25]:
        if tx.installment_group:
            key = ("grp", tx.installment_group)
        elif tx.origin == Transaction.ORIGIN_IMPORTACAO and tx.created_at:
            key = ("imp", tx.created_at.replace(second=0, microsecond=0))
        else:
            key = ("tx", tx.pk)
        item = index.get(key)
        if item is None:
            if len(items) >= limit:
                continue
            item = {"key": key, "kind": key[0], "tx": tx, "txs": [], "total": ZERO}
            index[key] = item
            items.append(item)
        item["txs"].append(tx)
        item["total"] += tx.amount
    for item in items:
        txs = item["txs"]
        tx = item["tx"]
        item["type"] = tx.type
        item["created_at"] = tx.created_at
        item["count"] = len(txs)
        if item["kind"] == "grp":
            first = min(txs, key=lambda x: x.date)
            total_n = tx.installment_total or len(txs)
            base = tx.description.rsplit(" (", 1)[0] if tx.description else tx.display_description
            item["title"] = base or tx.display_description
            item["subtitle"] = f"{total_n}x de {first.amount:.2f}".replace(".", ",") + f" · 1ª em {first.date:%d/%m}"
            item["date"] = first.date
            item["total"] = tx.amount * total_n if len(txs) < total_n else item["total"]
            item["forecast"] = first.date > t
        elif item["kind"] == "imp" and len(txs) > 1:
            item["title"] = f"{len(txs)} lançamentos importados"
            item["subtitle"] = "Importação de extrato"
            item["date"] = max(x.date for x in txs)
            item["forecast"] = False
            item["type"] = "DESPESA" if all(x.type == "DESPESA" for x in txs) else "MISTO"
        else:
            item["title"] = tx.display_description
            item["subtitle"] = tx.category.name if tx.category_id else "Sem categoria"
            item["date"] = tx.date
            item["forecast"] = tx.date > t
    return items


def upcoming(flt: TxFilter, days=15, limit=8):
    t = today()
    qs = flt.apply(period=False).filter(date__gt=t, date__lte=t + datetime.timedelta(days=days))
    return list(qs.select_related("category", "loan").order_by("date", "id")[:limit])


def top_expenses(flt: TxFilter, limit=5):
    return list(flt.apply().filter(type="DESPESA").select_related("category").order_by("-amount", "-id")[:limit])


# ── posição patrimonial ───────────────────────────────────────────────────

def position(user) -> dict:
    """Caixa, investido, dívida e patrimônio líquido — sempre global, hoje."""
    t = today()
    agg = Transaction.objects.filter(user=user, date__lte=t).aggregate(
        income=Sum("amount", filter=Q(type="RECEITA")),
        expense=Sum("amount", filter=Q(type="DESPESA")),
    )
    cash = (agg["income"] or ZERO) - (agg["expense"] or ZERO)
    invested = ZERO
    for inv in Investment.objects.filter(user=user).only("quantity", "purchase_price"):
        invested += inv.quantity * inv.purchase_price
    loans = list(Loan.objects.filter(user=user, is_active=True, current_balance__gt=0))
    debt = sum((l.current_balance for l in loans), ZERO)
    return {
        "cash": cash,
        "invested": invested.quantize(Decimal("0.01")),
        "debt": debt,
        "net_worth": cash + invested - debt,
        "loans_count": len(loans),
    }
