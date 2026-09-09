"""Dashboard, registration, and calendar views."""
import calendar
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Budget, Goal, Loan, Transaction
from .services import budget_spent_map, process_recurring_transactions
import datetime


def _income_expense_totals(queryset):
    """Sum RECEITA/DESPESA amounts for a Transaction queryset in a single query."""
    totals = queryset.aggregate(
        income=Sum("amount", filter=Q(type="RECEITA")),
        expense=Sum("amount", filter=Q(type="DESPESA")),
    )
    return totals["income"] or 0, totals["expense"] or 0


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get("username")
            messages.success(request, f"Conta criada para {username}!")
            return redirect("login")
    else:
        form = UserCreationForm()
    return render(request, "registration/register.html", {"form": form})


@login_required
def dashboard(request):
    today = timezone.now().date()
    try:
        month = int(request.GET.get("month", today.month))
        year = int(request.GET.get("year", today.year))
    except ValueError:
        month = today.month
        year = today.year

    _, last_day = calendar.monthrange(year, month)
    start_date = today.replace(year=year, month=month, day=1)
    end_date = today.replace(year=year, month=month, day=last_day)

    # Materialize recurring transactions up through whichever is later: real
    # "today" (normal catch-up) or the end of the month being browsed to
    # (so navigating ahead projects recurring debts forward immediately,
    # the same way credit-card installments are already pre-created).
    processed_count = process_recurring_transactions(request.user, up_to_date=max(end_date, today))
    if processed_count > 0:
        messages.info(
            request,
            f"{processed_count} transações recorrentes foram geradas automaticamente.",
        )

    recent_transactions = Transaction.objects.filter(
        user=request.user, date__range=[start_date, end_date]
    ).order_by("-date")[:5]

    monthly_income, monthly_expense = _income_expense_totals(
        Transaction.objects.filter(user=request.user, date__range=[start_date, end_date])
    )

    prev_month_end = start_date - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    previous_income_for_change, previous_expense_for_change = _income_expense_totals(
        Transaction.objects.filter(user=request.user, date__range=[prev_month_start, prev_month_end])
    )

    monthly_income_change = (
        ((monthly_income - previous_income_for_change) / previous_income_for_change)
        * 100
        if previous_income_for_change
        else 0
    )
    monthly_expense_change = (
        (
            (monthly_expense - previous_expense_for_change)
            / previous_expense_for_change
        )
        * 100
        if previous_expense_for_change
        else 0
    )

    previous_income, previous_expense = _income_expense_totals(
        Transaction.objects.filter(user=request.user, date__lt=start_date)
    )

    accumulated_balance = previous_income - previous_expense
    net_balance = monthly_income - monthly_expense
    total_balance = accumulated_balance + net_balance

    six_months_ago = start_date - timedelta(days=180)
    chart_qs = (
        Transaction.objects.filter(
            user=request.user, date__gte=six_months_ago, date__lte=end_date
        )
        .annotate(month=TruncMonth("date"))
        .values("month", "type")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )

    chart_data = {}
    for entry in chart_qs:
        month_str = entry["month"].strftime("%Y-%m")
        if month_str not in chart_data:
            chart_data[month_str] = {"RECEITA": 0, "DESPESA": 0}
        chart_data[month_str][entry["type"]] = float(entry["total"])

    labels = sorted(chart_data.keys())
    data_income = [chart_data[m].get("RECEITA", 0) for m in labels]
    data_expense = [chart_data[m].get("DESPESA", 0) for m in labels]

    previous_month_date = start_date - timedelta(days=1)
    next_month_date = end_date + timedelta(days=1)
    previous_month = {
        "month": previous_month_date.month,
        "year": previous_month_date.year,
    }
    next_month = {"month": next_month_date.month, "year": next_month_date.year}

    month_names = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
    }
    current_month_name = f"{month_names[month]} {year}"

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

    # Loans summary
    active_loan_qs = Loan.objects.filter(user=request.user, is_active=True, current_balance__gt=0)
    active_loans_count = active_loan_qs.count()
    loan_min_total = round(sum(l.min_next_payment for l in active_loan_qs), 2)
    total_loan_debt = round(sum(float(l.current_balance) for l in active_loan_qs), 2)

    # Goals summary
    goals = Goal.objects.filter(user=request.user).order_by('deadline')[:6]

    context = {
        "recent_transactions": recent_transactions,
        "monthly_income": monthly_income,
        "monthly_expense": monthly_expense,
        "monthly_income_change": monthly_income_change,
        "monthly_expense_change": monthly_expense_change,
        "net_balance": net_balance,
        "accumulated_balance": accumulated_balance,
        "total_balance": total_balance,
        "chart_labels": labels,
        "chart_income": data_income,
        "chart_expense": data_expense,
        "current_month_name": current_month_name,
        "previous_month": previous_month,
        "next_month": next_month,
        "selected_month": month,
        "selected_year": year,
        "alerts": alerts,
        "active_loans": active_loans_count,
        "loan_min_total": loan_min_total,
        "total_loan_debt": total_loan_debt,
        "goals": goals,
    }
    return render(request, "core/dashboard.html", context)


@login_required
def calendar_view(request):
    today = timezone.now().date()
    try:
        month = int(request.GET.get("month", today.month))
        year = int(request.GET.get("year", today.year))
    except ValueError:
        month = today.month
        year = today.year

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    _, last_day = calendar.monthrange(year, month)
    start_date = datetime.date(year, month, 1)
    end_date = datetime.date(year, month, last_day)

    transactions = Transaction.objects.filter(
        user=request.user, date__range=[start_date, end_date]
    )

    transactions_by_day = {}
    for tx in transactions:
        day = tx.date.day
        if day not in transactions_by_day:
            transactions_by_day[day] = []
        transactions_by_day[day].append(tx)

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
        "month_name": calendar.month_name[month],
    }
    return render(request, "core/calendar.html", context)
