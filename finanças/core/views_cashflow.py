"""Cash flow forecast view — cálculo em services_cashflow (explicável, sem ML)."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .dates import add_months, month_bounds, today
from .services import process_recurring_transactions
from .services_cashflow import build_forecast
from .services_loans import refresh_user_loans

HORIZONS = (1, 3, 6, 12)


@login_required
def cash_flow_forecast(request):
    try:
        horizon = int(request.GET.get("months", 3))
    except (TypeError, ValueError):
        horizon = 3
    horizon = max(1, min(horizon, 12))
    scenario = request.GET.get("scenario", "base")
    include_loans = request.GET.get("loans", "1") != "0"

    # Garante que tudo o que é "certo" no horizonte já existe como lançamento.
    t = today()
    last = add_months(t.replace(day=1), horizon, day=1)
    process_recurring_transactions(request.user, up_to_date=month_bounds(last.year, last.month)[1])
    refresh_user_loans(request.user)

    forecast = build_forecast(request.user, horizon=horizon, scenario=scenario, include_loans=include_loans)
    return render(request, "core/cash_flow.html", {
        "f": forecast,
        "horizons": HORIZONS,
        "horizon_months": horizon,
    })
