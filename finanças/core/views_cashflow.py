"""Cash flow forecast view — statistical projection, no AI/ML required."""
import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone

from .models import RecurringTransaction, Transaction


def _monthly_averages(user, months: int = 6) -> tuple[float, float]:
    """Return (avg_income, avg_expense) for the last `months` months."""
    cutoff = timezone.now().date().replace(day=1) - timedelta(days=months * 30)
    qs = (
        Transaction.objects.filter(user=user, date__gte=cutoff)
        .annotate(month=TruncMonth("date"))
        .values("month", "type")
        .annotate(total=Sum("amount"))
    )
    monthly: dict[str, dict] = {}
    for row in qs:
        key = row["month"].strftime("%Y-%m")
        if key not in monthly:
            monthly[key] = {"RECEITA": 0.0, "DESPESA": 0.0}
        monthly[key][row["type"]] = float(row["total"])

    if not monthly:
        return 0.0, 0.0

    avg_income = sum(m["RECEITA"] for m in monthly.values()) / len(monthly)
    avg_expense = sum(m["DESPESA"] for m in monthly.values()) / len(monthly)
    return avg_income, avg_expense


def _recurring_monthly_total(user, tx_type: str) -> float:
    """Sum of active recurring transactions of a given type (monthly equivalent)."""
    total = 0.0
    for rt in RecurringTransaction.objects.filter(user=user, active=True, type=tx_type):
        amount = float(rt.amount)
        if rt.frequency == "DIARIO":
            total += amount * 30
        elif rt.frequency == "SEMANAL":
            total += amount * 4
        elif rt.frequency == "QUINZENAL":
            total += amount * 2
        elif rt.frequency == "MENSAL":
            total += amount
        elif rt.frequency == "ANUAL":
            total += amount / 12
    return total


@login_required
def cash_flow_forecast(request):
    horizon_months = int(request.GET.get("months", 3))
    horizon_months = max(1, min(horizon_months, 12))

    avg_income, avg_expense = _monthly_averages(request.user, months=6)

    # Recurring transactions are certainties — give them priority over historical avg
    recurring_income = _recurring_monthly_total(request.user, "RECEITA")
    recurring_expense = _recurring_monthly_total(request.user, "DESPESA")

    # Projected monthly: recurring + historical non-recurring residual
    proj_income = max(avg_income, recurring_income)
    proj_expense = max(avg_expense, recurring_expense)

    # Current accumulated balance
    total_income_so_far = float(
        Transaction.objects.filter(user=request.user, type="RECEITA")
        .aggregate(Sum("amount"))["amount__sum"] or 0
    )
    total_expense_so_far = float(
        Transaction.objects.filter(user=request.user, type="DESPESA")
        .aggregate(Sum("amount"))["amount__sum"] or 0
    )
    current_balance = total_income_so_far - total_expense_so_far

    # Build projection
    today = timezone.now().date()
    months_list = []
    balance = current_balance

    month_names_pt = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
        5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
        9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
    }

    for i in range(1, horizon_months + 1):
        proj_date = (today.replace(day=1) + timedelta(days=32 * i)).replace(day=1)
        balance += proj_income - proj_expense
        months_list.append({
            "label": f"{month_names_pt[proj_date.month]}/{proj_date.year}",
            "income": round(proj_income, 2),
            "expense": round(proj_expense, 2),
            "balance": round(balance, 2),
        })

    # Historical balance for context (last 6 months actual)
    hist_labels = []
    hist_balances = []
    running = current_balance - sum(
        (m["income"] - m["expense"]) for m in months_list
    )  # rewind to 6 months ago start
    hist_qs = (
        Transaction.objects.filter(user=request.user)
        .annotate(month=TruncMonth("date"))
        .values("month", "type")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )
    hist_monthly: dict = {}
    for row in hist_qs:
        key = row["month"].strftime("%Y-%m")
        if key not in hist_monthly:
            hist_monthly[key] = {"RECEITA": 0.0, "DESPESA": 0.0}
        hist_monthly[key][row["type"]] = float(row["total"])

    running_bal = 0.0
    for key in sorted(hist_monthly.keys()):
        running_bal += hist_monthly[key]["RECEITA"] - hist_monthly[key]["DESPESA"]
        dt = date.fromisoformat(key + "-01")
        hist_labels.append(f"{month_names_pt[dt.month]}/{dt.year}")
        hist_balances.append(round(running_bal, 2))

    all_labels = hist_labels + [m["label"] for m in months_list]
    all_balances = hist_balances + [m["balance"] for m in months_list]
    split_index = len(hist_labels)

    context = {
        "months": months_list,
        "horizon_months": horizon_months,
        "current_balance": round(current_balance, 2),
        "proj_income": round(proj_income, 2),
        "proj_expense": round(proj_expense, 2),
        "avg_income": round(avg_income, 2),
        "avg_expense": round(avg_expense, 2),
        "recurring_income": round(recurring_income, 2),
        "recurring_expense": round(recurring_expense, 2),
        "chart_labels": json.dumps(all_labels),
        "chart_balances": json.dumps(all_balances),
        "chart_split": split_index,
        "proj_income_list": json.dumps([m["income"] for m in months_list]),
        "proj_expense_list": json.dumps([m["expense"] for m in months_list]),
        "proj_labels": json.dumps([m["label"] for m in months_list]),
    }
    return render(request, "core/cash_flow.html", context)
