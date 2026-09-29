"""Dashboard, registration, and calendar views."""
import calendar
import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import redirect, render
from django.urls import reverse

from . import analytics as an
from .dates import add_months, month_bounds, month_label, today
from .money import fmt_brl
from .models import Budget, Goal, Loan, LoanDisbursement, LoanPayment, RecurringTransaction, Transaction
from .services import budget_spent_map, process_recurring_transactions
from .services_loans import loans_summary, refresh_user_loans

ZERO = Decimal("0")


def _income_expense_totals(queryset):
    """Sum RECEITA/DESPESA amounts for a Transaction queryset in a single query."""
    totals = queryset.aggregate(
        income=Sum("amount", filter=Q(type="RECEITA")),
        expense=Sum("amount", filter=Q(type="DESPESA")),
    )
    return totals["income"] or 0, totals["expense"] or 0


def register(request):
    # Public self-registration is disabled — this app may be exposed on the
    # public internet (e.g. via a Cloudflare tunnel); new accounts must be
    # created by a staff user via /admin/ instead.
    messages.info(request, "O cadastro público está desabilitado. Peça a um administrador para criar sua conta.")
    return redirect("login")


@login_required
def dashboard(request):
    user = request.user
    t = today()
    if request.GET.get("clear"):
        request.session.pop("dashboard_filter", None)
        return redirect("dashboard")
    flt = an.TxFilter.from_request(
        request, default_preset="month", include_investments=False, session_key="dashboard_filter",
    )
    period_end = flt.end or t

    # Materializa recorrências (e parcelas de empréstimo) até o fim do período
    # navegado, para que meses futuros já mostrem o que está comprometido.
    processed_count = process_recurring_transactions(user, up_to_date=max(period_end, t))
    if processed_count > 0:
        messages.info(request, f"{processed_count} transações recorrentes foram geradas automaticamente.")
    refresh_user_loans(user)

    anchor = flt.anchor or t.replace(day=1)
    k = an.kpis_with_comparison(flt)
    position = an.position(user)
    # Saldo projetado no fim do período = saldo hoje + a receber − a pagar até lá.
    ahead = _toggled(user, flt).filter(date__gt=t, date__lte=period_end)         if period_end > t else Transaction.objects.none()
    ahead_in, ahead_out = _income_expense_totals(ahead)
    if period_end > t:
        k["end_balance"] = position["cash"] + ahead_in - ahead_out
    else:
        inc, exp = _income_expense_totals(Transaction.objects.filter(user=user, date__lte=period_end))
        k["end_balance"] = inc - exp
    k["ahead_in"], k["ahead_out"] = ahead_in, ahead_out
    this_month = _month_outlook(user, flt, anchor if flt.preset == "month" else t.replace(day=1))
    loans = loans_summary(user)
    ref_month = (flt.end or t).replace(day=1)

    # ── Gráficos ──────────────────────────────────────────────────────────
    # Meses anteriores ao período + 3 à frente (previstos, barras claras).
    span = 12 if flt.preset in ("12m", "year", "all", "custom") else 6
    first_month = add_months(ref_month, -(span - 1), day=1)
    last_month = add_months(ref_month, 3, day=1)
    if flt.preset == "year":
        first_month, last_month = datetime.date(anchor.year, 1, 1), datetime.date(anchor.year, 12, 1)
    series = an.monthly_series(flt.apply(period=False), first_month, last_month)

    categories = an.by_category(flt.apply(), top=8)

    cumulative = None
    if flt.start and flt.end and flt.days <= 93:
        prev = flt.previous_period()
        cur_vals = an.daily_cumulative(flt.apply(), flt.start, flt.end)
        prev_vals = an.daily_cumulative(prev.apply(), prev.start, prev.end) if prev else []
        labels = [(flt.start + datetime.timedelta(days=i)).strftime("%d/%m") for i in range(len(cur_vals))]
        # Hoje em diante é previsto: a linha "atual" para em hoje se o período o contém.
        cutoff = (t - flt.start).days + 1 if flt.start <= t <= flt.end else None
        cumulative = {
            "labels": labels,
            "current": cur_vals if cutoff is None else cur_vals[:cutoff] + [None] * (len(cur_vals) - cutoff),
            "forecast": None if cutoff is None else [None] * (cutoff - 1) + cur_vals[cutoff - 1:],
            "previous": prev_vals[: len(cur_vals)],
            "previous_label": prev.period_label if prev else "",
        }

    budgets = list(Budget.objects.filter(user=user).select_related("category"))
    spent_map = budget_spent_map(user, budgets, year=anchor.year, month=anchor.month)
    budget_rows = sorted(
        ({"name": b.category.name, "limit": float(b.limit), "spent": float(spent_map.get(b.id) or 0),
          "period": b.get_period_display()} for b in budgets),
        key=lambda r: -(r["spent"] / r["limit"] if r["limit"] else 0),
    )[:8]

    evolution = _balance_and_debt_series(user, months=12)
    payment_split = an.by_payment_method(flt.apply())
    committed = an.committed_by_origin(user, months=12, include_loans=flt.include_loans)

    # ── Alertas ───────────────────────────────────────────────────────────
    alerts = []
    for b in budgets:
        spent = spent_map.get(b.id) or ZERO
        if b.limit and spent / b.limit >= Decimal("0.9"):
            pct = int(spent / b.limit * 100)
            alerts.append({
                "level": "danger" if pct >= 100 else "warning",
                "icon": "bi-exclamation-triangle-fill",
                "text": f"Atenção: você já consumiu {pct}% do orçamento de {b.category.name} "
                        f"({fmt_brl(spent)} de {fmt_brl(b.limit)}).",
            })
    low = _lowest_balance_this_month(user, position["cash"])
    if low and low["balance"] < 0:
        alerts.append({
            "level": "danger", "icon": "bi-graph-down-arrow",
            "text": f"Seu saldo previsto fica negativo em {low['date']:%d/%m} ({fmt_brl(low['balance'])}).",
            "link_url": reverse("cash_flow_forecast"), "link_label": "Ver fluxo de caixa",
        })
    for tx in loans["next"]:
        if t <= tx.date <= t + datetime.timedelta(days=5):
            alerts.append({
                "level": "info", "icon": "bi-bank",
                "text": f"Parcela de {tx.loan.name} vence em {tx.date:%d/%m}: {fmt_brl(tx.amount)}.",
                "link_url": reverse("loan_pay", args=[tx.loan_id]), "link_label": "Pagar",
            })
    month_start, month_end = month_bounds(t.year, t.month)
    for rt in RecurringTransaction.objects.filter(user=user, active=True, end_date__range=[month_start, month_end]):
        alerts.append({
            "level": "light", "icon": "bi-arrow-repeat",
            "text": f"A recorrência “{rt.description or (rt.category.name if rt.category else '')}” termina em {rt.end_date:%d/%m}.",
        })

    # ── Indicadores rápidos ───────────────────────────────────────────────
    quick = {}
    if flt.preset == "month" and anchor == t.replace(day=1):
        days_left = (month_end - t).days + 1
        left = k["income"] - k["expense"]
        quick["per_day"] = (left / days_left) if days_left else None
        quick["days_left"] = days_left
    if k["income_operational"]:
        quick["debt_ratio"] = k["expense_loans"] / k["income_operational"] * 100
    elif k["expense_loans"]:
        quick["debt_ratio"] = None

    context = {
        **an.filter_ui_context(flt),
        "kpis": k,
        "position": position,
        "month_outlook": this_month,
        "loans": loans,
        "quick": quick,
        "alerts": alerts,
        "recent_items": an.recent(user, limit=8),
        "upcoming": an.upcoming(flt, days=15),
        "top_expenses": an.top_expenses(flt, limit=6),
        "goals": Goal.objects.filter(user=user).order_by("deadline")[:6],
        "today": t,
        "period_end": period_end,
        "chart": {
            "monthly": series,
            "categories": {
                "labels": [c["name"] for c in categories],
                "values": [float(c["total"]) for c in categories],
                "colors": [c["color"] for c in categories],
                "ids": [c["id"] for c in categories],
            },
            "cumulative": cumulative,
            "budgets": budget_rows,
            "evolution": evolution,
            "payments": {"labels": [p["name"] for p in payment_split],
                         "values": [float(p["total"]) for p in payment_split]},
            "committed": committed,
        },
        "category_filter_base": flt.querystring(category=None),
    }
    cat = flt.single_category
    if cat:
        from .views_transactions import category_insight
        context["category_insight"] = category_insight(flt, cat)
    # Compatibilidade com o template antigo / testes
    context.update(
        monthly_income=k["income"], monthly_expense=k["expense"], net_balance=k["net"],
        total_balance=position["cash"], current_month_name=flt.period_label,
        active_loans=loans["count"], total_loan_debt=loans["debt"],
    )
    return render(request, "core/dashboard.html", context)


def _toggled(user, flt):
    """Todas as transações do usuário respeitando só as chaves de
    empréstimos/aportes (não o tipo, categoria ou forma de pagamento)."""
    from dataclasses import replace
    return replace(an.TxFilter(user=user), include_loans=flt.include_loans,
                   include_investments=flt.include_investments).apply(period=False)


def _month_outlook(user, flt, month_first):
    """O que ainda falta pagar/receber no mês e a(s) parcela(s) de empréstimo."""
    t = today()
    start, end = month_bounds(month_first.year, month_first.month)
    base = _toggled(user, flt).filter(date__gte=start, date__lte=end)
    pending = base.filter(date__gt=t)
    to_pay_in, to_pay_out = _income_expense_totals(pending)
    next_bill = pending.filter(type="DESPESA").select_related("category").order_by("date", "id").first()
    loan_txs = list(
        Transaction.objects.filter(user=user, origin=Transaction.ORIGIN_EMPRESTIMO, type="DESPESA",
                                   date__gte=start, date__lte=end, loan__isnull=False)
        .select_related("loan", "loan_payment").order_by("date")
    )
    loan_open = [x for x in loan_txs if not hasattr(x, "loan_payment")]
    return {
        "label": month_label(start, short=False),
        "is_current": start <= t <= end,
        "is_past": end < t,
        "to_pay": to_pay_out,
        "to_pay_count": pending.filter(type="DESPESA").count(),
        "to_receive": to_pay_in,
        "next_bill": next_bill,
        "loan_total": sum((x.amount for x in loan_txs), ZERO),
        "loan_open_total": sum((x.amount for x in loan_open), ZERO),
        "loan_txs": loan_txs,
        "loan_next": loan_open[0] if loan_open else None,
        "loan_paid": bool(loan_txs) and not loan_open,
    }


def _balance_and_debt_series(user, months=12):
    """Saldo acumulado (realizado) e dívida de empréstimos no fim de cada mês."""
    t = today()
    last = t.replace(day=1)
    first = add_months(last, -(months - 1), day=1)
    month_ends = [min(month_bounds(m.year, m.month)[1], t) for m in
                  (add_months(first, i, day=1) for i in range(months))]

    before = Transaction.objects.filter(user=user, date__lt=first).aggregate(
        inc=Sum("amount", filter=Q(type="RECEITA")), exp=Sum("amount", filter=Q(type="DESPESA")))
    running = (before["inc"] or ZERO) - (before["exp"] or ZERO)
    rows = (
        Transaction.objects.filter(user=user, date__gte=first, date__lte=t)
        .values("date", "type").annotate(total=Sum("amount"))
    )
    by_month = {}
    for r in rows:
        key = r["date"].replace(day=1)
        sign = 1 if r["type"] == "RECEITA" else -1
        by_month[key] = by_month.get(key, ZERO) + sign * r["total"]

    loans = list(Loan.objects.filter(user=user))
    payments = list(LoanPayment.objects.filter(loan__user=user).values("loan_id", "payment_date", "principal_paid",
                                                                       "balance_after", "balance_before"))
    disb = list(LoanDisbursement.objects.filter(loan__user=user).values("loan_id", "date", "amount"))

    labels, balance, debt, net = [], [], [], []
    for i, end in enumerate(month_ends):
        m = add_months(first, i, day=1)
        running += by_month.get(m, ZERO)
        d = ZERO
        for loan in loans:
            if loan.start_date > end:
                continue
            # Saldo na data = saldo atual desfeito dos movimentos posteriores a `end`.
            bal = loan.current_balance
            for p in payments:
                if p["loan_id"] == loan.pk and p["payment_date"] > end:
                    before_bal = p["balance_before"] if p["balance_before"] is not None else p["balance_after"] + p["principal_paid"]
                    bal += before_bal - p["balance_after"]
            for x in disb:
                if x["loan_id"] == loan.pk and x["date"] > end:
                    bal -= x["amount"]
            d += max(bal, ZERO)
        labels.append(month_label(m))
        balance.append(float(running))
        debt.append(float(d))
        net.append(float(running - d))
    return {"labels": labels, "balance": balance, "debt": debt, "net": net}


def _lowest_balance_this_month(user, cash_today):
    """Menor saldo previsto do dia seguinte até o fim do mês corrente."""
    t = today()
    _, month_end = month_bounds(t.year, t.month)
    rows = (
        Transaction.objects.filter(user=user, date__gt=t, date__lte=month_end)
        .values("date", "type").annotate(total=Sum("amount")).order_by("date")
    )
    running = cash_today
    lowest = None
    for r in rows:
        running += r["total"] if r["type"] == "RECEITA" else -r["total"]
        if lowest is None or running < lowest["balance"]:
            lowest = {"date": r["date"], "balance": running}
    return lowest


@login_required
def calendar_view(request):
    t = today()
    try:
        month = int(request.GET.get("month", t.month))
        year = int(request.GET.get("year", t.year))
        if not 1 <= month <= 12:
            raise ValueError
    except ValueError:
        month = t.month
        year = t.year

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    _, last_day = calendar.monthrange(year, month)
    start_date = datetime.date(year, month, 1)
    end_date = datetime.date(year, month, last_day)

    # Same forward-projection as the dashboard: browsing the calendar ahead
    # must also materialize recurring transactions up through the viewed
    # month, not just up to today.
    process_recurring_transactions(request.user, up_to_date=max(end_date, t))

    transactions = Transaction.objects.filter(
        user=request.user, date__range=[start_date, end_date]
    ).select_related("category")

    transactions_by_day = {}
    for tx in transactions:
        transactions_by_day.setdefault(tx.date.day, []).append(tx)

    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdayscalendar(year, month)

    context = {
        "month_days": month_days,
        "transactions_by_day": transactions_by_day,
        "current_month": month,
        "current_year": year,
        "prev_month": prev_month,
        "prev_year": prev_year,
        "next_month": next_month,
        "next_year": next_year,
        "month_name": month_label(start_date, short=False).split("/")[0],
    }
    return render(request, "core/calendar.html", context)
