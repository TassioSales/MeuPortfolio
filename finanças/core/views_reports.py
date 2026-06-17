"""Reports, CSV export, and PDF export views."""
import csv
import json
import logging
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.db.models.functions import TruncDay, TruncMonth
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.utils import timezone
from xhtml2pdf import pisa

from .models import Budget, Category, Transaction

logger = logging.getLogger("core")


def _filter_transactions(request, start_date, end_date, category_id):
    qs = Transaction.objects.filter(user=request.user).order_by("-date")
    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)
    if category_id:
        qs = qs.filter(category_id=category_id)
    return qs


@login_required
def reports(request):
    logger.info(f"Generating reports for user {request.user.username}")

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    category_id = request.GET.get("category")

    transactions = _filter_transactions(request, start_date, end_date, category_id)

    total_income = (
        transactions.filter(type="RECEITA").aggregate(Sum("amount"))["amount__sum"] or 0
    )
    total_expense = (
        transactions.filter(type="DESPESA").aggregate(Sum("amount"))["amount__sum"] or 0
    )
    net_balance = total_income - total_expense
    savings_rate = (
        ((total_income - total_expense) / total_income) * 100 if total_income > 0 else 0
    )

    categories = Category.objects.filter(user=request.user)

    expense_by_category = (
        transactions.filter(type="DESPESA")
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    evolution_qs = Transaction.objects.filter(user=request.user)
    if start_date:
        evolution_qs = evolution_qs.filter(date__gte=start_date)
    if end_date:
        evolution_qs = evolution_qs.filter(date__lte=end_date)
    if not start_date and not end_date:
        last_year = timezone.now().date() - timedelta(days=365)
        evolution_qs = evolution_qs.filter(date__gte=last_year)

    monthly_data = (
        evolution_qs.annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(
            income=Sum("amount", filter=Q(type="RECEITA")),
            expense=Sum("amount", filter=Q(type="DESPESA")),
        )
        .order_by("month")
    )

    evolution_labels = []
    evolution_income = []
    evolution_expense = []
    for entry in monthly_data:
        if entry["month"]:
            evolution_labels.append(entry["month"].strftime("%b/%Y"))
            evolution_income.append(float(entry["income"] or 0))
            evolution_expense.append(float(entry["expense"] or 0))

    daily_data = (
        transactions.filter(type="DESPESA")
        .annotate(day=TruncDay("date"))
        .values("day")
        .annotate(total=Sum("amount"))
        .order_by("day")
    )
    daily_labels = []
    daily_expenses = []
    for entry in daily_data:
        if entry["day"]:
            daily_labels.append(entry["day"].strftime("%d/%m"))
            daily_expenses.append(float(entry["total"] or 0))

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

    context = {
        "categories": categories,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": net_balance,
        "savings_rate": savings_rate,
        "expense_by_category": expense_by_category,
        "top_expenses": transactions.filter(type="DESPESA").order_by("-amount")[:5],
        "evolution_labels": json.dumps(evolution_labels),
        "evolution_income": json.dumps(evolution_income),
        "evolution_expense": json.dumps(evolution_expense),
        "daily_labels": json.dumps(daily_labels),
        "daily_expenses": json.dumps(daily_expenses),
        "budget_labels": json.dumps(budget_labels),
        "budget_limits": json.dumps(budget_limits),
        "budget_actuals": json.dumps(budget_actuals),
        "recent_transactions": transactions.order_by("-date", "-id")[:20],
    }
    return render(request, "core/reports.html", context)


@login_required
def export_csv(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    category_id = request.GET.get("category")

    transactions = _filter_transactions(request, start_date, end_date, category_id)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="transactions.csv"'

    writer = csv.writer(response)
    writer.writerow(["Date", "Type", "Category", "Amount", "Description"])
    for t in transactions:
        writer.writerow([
            t.date,
            t.get_type_display(),
            t.category.name if t.category else "-",
            t.amount,
            t.description,
        ])
    return response


@login_required
def export_pdf(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    category_id = request.GET.get("category")

    transactions = _filter_transactions(request, start_date, end_date, category_id)

    total_income = (
        transactions.filter(type="RECEITA").aggregate(Sum("amount"))["amount__sum"] or 0
    )
    total_expense = (
        transactions.filter(type="DESPESA").aggregate(Sum("amount"))["amount__sum"] or 0
    )

    context = {
        "transactions": transactions,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": total_income - total_expense,
        "start_date": start_date,
        "end_date": end_date,
    }

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="relatorio_financeiro.pdf"'

    template = get_template("core/reports_pdf.html")
    html = template.render(context)
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse("We had some errors <pre>" + html + "</pre>")
    return response
