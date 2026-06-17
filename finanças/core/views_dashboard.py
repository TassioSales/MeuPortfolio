"""Dashboard, registration, and calendar views."""
import calendar
import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Budget, Transaction
from .services import process_recurring_transactions
import datetime


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
    processed_count = process_recurring_transactions(request.user)
    if processed_count > 0:
        messages.info(
            request,
            f"{processed_count} transações recorrentes foram geradas automaticamente.",
        )

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

    recent_transactions = Transaction.objects.filter(
        user=request.user, date__range=[start_date, end_date]
    ).order_by("-date")[:5]

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

    context = {
        "recent_transactions": recent_transactions,
        "monthly_income": monthly_income,
        "monthly_expense": monthly_expense,
        "monthly_income_change": monthly_income_change,
        "monthly_expense_change": monthly_expense_change,
        "net_balance": net_balance,
        "accumulated_balance": accumulated_balance,
        "total_balance": total_balance,
        "chart_labels": json.dumps(labels),
        "chart_income": json.dumps(data_income),
        "chart_expense": json.dumps(data_expense),
        "current_month_name": current_month_name,
        "previous_month": previous_month,
        "next_month": next_month,
        "selected_month": month,
        "selected_year": year,
        "alerts": alerts,
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
