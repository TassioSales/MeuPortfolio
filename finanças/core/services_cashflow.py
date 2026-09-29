"""Previsão de fluxo de caixa — sem ML, só regras explicáveis.

Para cada mês do horizonte:

    saldo inicial
  + entradas certas   (receitas já lançadas com data no mês)
  + entradas estimadas(mediana das receitas "variáveis" dos últimos meses)
  − saídas certas     (cartão, fixas/recorrentes, empréstimos, outras já lançadas)
  − saídas estimadas  (mediana do gasto variável dos últimos meses)
  = saldo final

"Certo" = já existe uma Transaction com data futura (parcelas do cartão,
recorrências e parcelas de empréstimo são materializadas antes do cálculo).
"Variável" = lançamentos manuais/importados de natureza operacional — o gasto
do dia a dia que ainda não foi lançado. Nunca se usa mês futuro no histórico
e nunca se soma uma recorrência "projetada" que já esteja materializada.
"""
from __future__ import annotations

import datetime
import statistics
from collections import OrderedDict, defaultdict
from decimal import Decimal

from django.db.models import Q, Sum

from .dates import add_months, iter_months, month_bounds, month_label, today
from .models import Category, Transaction
from .money import q2

ZERO = Decimal("0")

GROUPS = OrderedDict([
    ("card", "Cartão (parcelas)"),
    ("fixed", "Fixas (recorrentes)"),
    ("loans", "Empréstimos"),
    ("other", "Outras já lançadas"),
    ("variable", "Variável (estimado)"),
])
ORIGIN_TO_GROUP = {
    Transaction.ORIGIN_PARCELA: "card",
    Transaction.ORIGIN_RECORRENTE: "fixed",
    Transaction.ORIGIN_EMPRESTIMO: "loans",
}
VARIABLE_ORIGINS = (Transaction.ORIGIN_MANUAL, Transaction.ORIGIN_IMPORTACAO)

SCENARIOS = OrderedDict([
    ("pessimista", "Pessimista"),
    ("base", "Base"),
    ("otimista", "Otimista"),
])
HISTORY_MONTHS = 6


def _percentile(values: list[Decimal], pct: float) -> Decimal:
    if not values:
        return ZERO
    vals = sorted(values)
    k = (len(vals) - 1) * pct
    lo, hi = int(k), min(int(k) + 1, len(vals) - 1)
    return vals[lo] + (vals[hi] - vals[lo]) * Decimal(str(k - lo))


def _variable_filter():
    return Q(origin__in=VARIABLE_ORIGINS) & (
        Q(category__isnull=True) | Q(category__nature=Category.NATURE_OPERACIONAL)
    )


def variable_history(user, t=None):
    """Totais mensais de receita/despesa variável dos últimos meses cheios."""
    t = t or today()
    cur = t.replace(day=1)
    first_tx = Transaction.objects.filter(user=user).order_by("date").values_list("date", flat=True).first()
    start = add_months(cur, -HISTORY_MONTHS, day=1)
    if first_tx and first_tx.replace(day=1) > start:
        start = first_tx.replace(day=1)
    months = [m for m in iter_months(start, add_months(cur, -1, day=1))] if start < cur else []
    rows = (
        Transaction.objects.filter(user=user, date__gte=start, date__lt=cur)
        .filter(_variable_filter())
        .values("date__year", "date__month", "type").annotate(total=Sum("amount"))
    )
    by = defaultdict(lambda: {"RECEITA": ZERO, "DESPESA": ZERO})
    for r in rows:
        by[datetime.date(r["date__year"], r["date__month"], 1)][r["type"]] += r["total"]
    return [{"month": m, "label": month_label(m), "income": by[m]["RECEITA"], "expense": by[m]["DESPESA"]}
            for m in months]


def estimates(history, scenario="base"):
    incomes = [h["income"] for h in history]
    expenses = [h["expense"] for h in history]
    if not history:
        return {"income": ZERO, "expense": ZERO}
    med_inc = Decimal(str(statistics.median(incomes)))
    if scenario == "pessimista":
        return {"income": q2(med_inc * Decimal("0.9")), "expense": q2(_percentile(expenses, 0.75))}
    if scenario == "otimista":
        return {"income": q2(med_inc), "expense": q2(_percentile(expenses, 0.25))}
    return {"income": q2(med_inc), "expense": q2(Decimal(str(statistics.median(expenses))))}


def build_forecast(user, horizon: int = 3, scenario: str = "base", include_loans: bool = True) -> dict:
    t = today()
    horizon = max(1, min(int(horizon), 12))
    scenario = scenario if scenario in SCENARIOS else "base"
    cur = t.replace(day=1)
    last_month = add_months(cur, horizon, day=1)
    horizon_end = month_bounds(last_month.year, last_month.month)[1]

    base_qs = Transaction.objects.filter(user=user)
    if not include_loans:
        base_qs = base_qs.exclude(Q(origin=Transaction.ORIGIN_EMPRESTIMO) & Q(date__gt=t))

    agg = base_qs.filter(date__lte=t).aggregate(
        inc=Sum("amount", filter=Q(type="RECEITA")), exp=Sum("amount", filter=Q(type="DESPESA")))
    cash_today = (agg["inc"] or ZERO) - (agg["exp"] or ZERO)
    agg = base_qs.filter(date__lt=cur).aggregate(
        inc=Sum("amount", filter=Q(type="RECEITA")), exp=Sum("amount", filter=Q(type="DESPESA")))
    opening_current = (agg["inc"] or ZERO) - (agg["exp"] or ZERO)

    history = variable_history(user, t)
    est = {s: estimates(history, s) for s in SCENARIOS}
    sel = est[scenario]

    # Lançamentos certos (já existentes) de hoje+1 até o fim do horizonte.
    future_txs = list(
        base_qs.filter(date__gt=t, date__lte=horizon_end)
        .select_related("category").order_by("date", "id")
    )
    # Realizado do mês corrente (até hoje), por grupo.
    realized_rows = (
        base_qs.filter(date__gte=cur, date__lte=t)
        .values("type", "origin").annotate(total=Sum("amount"))
    )

    def group_of(tx_origin):
        return ORIGIN_TO_GROUP.get(tx_origin, "other")

    months = []
    daily_certain = defaultdict(lambda: ZERO)
    for tx in future_txs:
        daily_certain[tx.date] += tx.amount if tx.type == "RECEITA" else -tx.amount

    for idx, m in enumerate(iter_months(cur, last_month)):
        m_start, m_end = month_bounds(m.year, m.month)
        days_in_month = (m_end - m_start).days + 1
        row = {
            "month": m, "label": month_label(m, short=False), "is_current": idx == 0,
            "income_certain": ZERO, "income_realized": ZERO, "income_est": ZERO,
            "out": {g: ZERO for g in GROUPS}, "out_realized": ZERO,
            "items": [],
        }
        if idx == 0:
            for r in realized_rows:
                if r["type"] == "RECEITA":
                    row["income_realized"] += r["total"]
                else:
                    g = group_of(r["origin"])
                    row["out"][g] += r["total"]
                    row["out_realized"] += r["total"]
            remaining_ratio = Decimal((m_end - t).days) / Decimal(days_in_month)
        else:
            remaining_ratio = Decimal("1")
        for tx in future_txs:
            if m_start <= tx.date <= m_end:
                if tx.type == "RECEITA":
                    row["income_certain"] += tx.amount
                else:
                    row["out"][group_of(tx.origin)] += tx.amount
                if len(row["items"]) < 60:
                    row["items"].append(tx)
        row["income_est"] = q2(sel["income"] * remaining_ratio)
        row["out"]["variable"] = q2(sel["expense"] * remaining_ratio)
        row["opening"] = opening_current if idx == 0 else months[-1]["closing"]
        row["income_total"] = row["income_realized"] + row["income_certain"] + row["income_est"]
        row["out_total"] = sum(row["out"].values(), ZERO)
        row["closing"] = row["opening"] + row["income_total"] - row["out_total"]
        row["net"] = row["income_total"] - row["out_total"]
        row["remaining_ratio"] = remaining_ratio
        months.append(row)

    # Série diária: 30 dias realizados + horizonte previsto (3 cenários).
    past_start = t - datetime.timedelta(days=30)
    past_rows = (
        base_qs.filter(date__gt=past_start, date__lte=t)
        .values("date", "type").annotate(total=Sum("amount"))
    )
    past_by_day = defaultdict(lambda: ZERO)
    for r in past_rows:
        past_by_day[r["date"]] += r["total"] if r["type"] == "RECEITA" else -r["total"]
    running = cash_today - sum(past_by_day.values(), ZERO)
    daily_labels, daily_real = [], []
    d = past_start + datetime.timedelta(days=1)
    while d <= t:
        running += past_by_day.get(d, ZERO)
        daily_labels.append(d)
        daily_real.append(running)
        d += datetime.timedelta(days=1)

    scen_series = {}
    lowest = {}
    for s in SCENARIOS:
        bal = cash_today
        series = []
        low = {"date": t, "balance": cash_today}
        d = t + datetime.timedelta(days=1)
        while d <= horizon_end:
            dim = month_bounds(d.year, d.month)[1].day
            bal += daily_certain.get(d, ZERO) + (est[s]["income"] - est[s]["expense"]) / dim
            series.append(bal)
            if bal < low["balance"]:
                low = {"date": d, "balance": bal}
            d += datetime.timedelta(days=1)
        scen_series[s] = series
        lowest[s] = {"date": low["date"], "balance": q2(low["balance"])}
    future_days = [t + datetime.timedelta(days=i + 1) for i in range((horizon_end - t).days)]

    # Comprometimento: saídas certas ÷ entradas previstas, próximos 3 meses.
    next3 = months[1:4] or months[:1]
    certain_out = sum((sum((r["out"][g] for g in ("card", "fixed", "loans", "other")), ZERO) for r in next3), ZERO)
    expected_in = sum((r["income_certain"] + r["income_est"] for r in next3), ZERO)
    committed_pct = (certain_out / expected_in * 100) if expected_in else None

    future_rows = months[1:] or months
    avg_net = sum((r["net"] for r in future_rows), ZERO) / len(future_rows)

    # Histórico realizado (mesmas colunas), últimos meses cheios.
    hist_start = add_months(cur, -HISTORY_MONTHS, day=1)
    hist_rows_q = (
        base_qs.filter(date__gte=hist_start, date__lt=cur)
        .values("date__year", "date__month", "type", "origin").annotate(total=Sum("amount"))
    )
    hist = OrderedDict((m, {"month": m, "label": month_label(m, short=False), "income": ZERO,
                            "out": {g: ZERO for g in GROUPS if g != "variable"}, "variable": ZERO})
                       for m in iter_months(hist_start, add_months(cur, -1, day=1)))
    for r in hist_rows_q:
        row = hist.get(datetime.date(r["date__year"], r["date__month"], 1))
        if row is None:
            continue
        if r["type"] == "RECEITA":
            row["income"] += r["total"]
        elif r["origin"] in VARIABLE_ORIGINS:
            row["variable"] += r["total"]
        else:
            row["out"][group_of(r["origin"])] += r["total"]
    running_hist = opening_current - sum(
        (h["income"] - sum(h["out"].values(), ZERO) - h["variable"] for h in hist.values()), ZERO)
    history_rows = []
    for h in hist.values():
        h["opening"] = running_hist
        h["out_total"] = sum(h["out"].values(), ZERO) + h["variable"]
        running_hist += h["income"] - h["out_total"]
        h["closing"] = running_hist
        history_rows.append(h)

    counts = defaultdict(int)
    for tx in future_txs:
        counts[group_of(tx.origin) if tx.type == "DESPESA" else "income"] += 1

    return {
        "today": t,
        "horizon": horizon,
        "scenario": scenario,
        "scenarios": SCENARIOS,
        "include_loans": include_loans,
        "cash_today": cash_today,
        "opening_current": opening_current,
        "months": months,
        "groups": GROUPS,
        "history": history,
        "history_rows": [h for h in history_rows if h["income"] or h["out_total"]],
        "history_is_short": len(history) < 3,
        "estimates": est,
        "estimate": sel,
        "end_balance": months[-1]["closing"],
        "end_change": months[-1]["closing"] - cash_today,
        "lowest": lowest[scenario],
        "lowest_all": lowest,
        "avg_net": q2(avg_net),
        "committed_pct": committed_pct,
        "counts": dict(counts),
        "future_count": len(future_txs),
        "chart": {
            "daily_labels": [x.strftime("%d/%m/%y") for x in daily_labels + future_days],
            "real": [float(v) for v in daily_real] + [None] * len(future_days),
            "scenarios": {s: [None] * (len(daily_real) - 1) + [float(daily_real[-1]) if daily_real else float(cash_today)]
                          + [float(v) for v in series] for s, series in scen_series.items()},
            "month_labels": [month_label(r["month"]) for r in months],
            "composition": {g: [float(r["out"][g]) for r in months] for g in GROUPS},
            "income": [float(r["income_total"]) for r in months],
            "closing": [float(r["closing"]) for r in months],
        },
    }
