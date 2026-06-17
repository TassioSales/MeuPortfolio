"""Investment views: dashboard, safe haven, ticker search, and CRUD."""
import json

import yfinance as yf
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from .forms import InvestmentForm
from .market_data import (
    SERIES_CDI_MENSAL,
    SERIES_SELIC_META,
    calculate_cdi_correction,
    calculate_pre_fixado,
    get_latest_indicator,
    get_real_time_currency,
)
from .models import Investment
from .views_shared import get_price_manual


def _cached_ticker_fetch(symbol: str) -> dict:
    """Fetch yfinance data with 5-minute in-memory cache to avoid rate limiting."""
    key = f"yf_{symbol}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    result = {"price": None, "currency": "BRL", "info": {}, "history": None}
    try:
        ticker = yf.Ticker(symbol)
        try:
            result["price"] = ticker.fast_info.last_price
            result["currency"] = ticker.fast_info.currency
        except Exception:
            pass

        if result["price"] is None:
            hist = ticker.history(period="1d")
            if not hist.empty:
                result["price"] = hist["Close"].iloc[-1]

        try:
            result["info"] = ticker.info
        except Exception:
            pass

        try:
            result["history"] = ticker.history(period="6mo")
        except Exception:
            pass
    except Exception:
        pass

    cache.set(key, result, timeout=300)
    return result


@login_required
def search_ticker(request):
    ticker_symbol = request.GET.get("ticker", "").upper().strip()
    if not ticker_symbol:
        return JsonResponse({"error": "Ticker is required"}, status=400)

    if (
        any(char.isdigit() for char in ticker_symbol)
        and "." not in ticker_symbol
        and "-" not in ticker_symbol
    ):
        ticker_symbol += ".SA"

    aliases = {"EURO": "EUR", "DOLAR": "USD", "BITCOIN": "BTC"}
    ticker_symbol = aliases.get(ticker_symbol, ticker_symbol)

    price = None
    currency = "BRL"
    name = ticker_symbol
    previous_close = None
    day_high = None
    day_low = None
    year_high = None
    year_low = None
    chart_labels = []
    chart_data = []

    if ticker_symbol in ["USD", "EUR"]:
        price = get_real_time_currency(ticker_symbol)
        if price:
            return JsonResponse({
                "symbol": ticker_symbol,
                "name": "Dólar Americano" if ticker_symbol == "USD" else "Euro",
                "price": price,
                "currency": "BRL",
                "change_percent": 0,
                "day_high": price,
                "day_low": price,
                "year_high": price,
                "year_low": price,
                "chart_labels": [],
                "chart_data": [],
            })

    fetched = _cached_ticker_fetch(ticker_symbol)
    price = fetched["price"]
    currency = fetched["currency"] or "BRL"
    info = fetched["info"]
    history_chart = fetched["history"]

    name = info.get("longName") or info.get("shortName") or ticker_symbol
    previous_close = info.get("previousClose")
    day_high = info.get("dayHigh")
    day_low = info.get("dayLow")
    year_high = info.get("fiftyTwoWeekHigh")
    year_low = info.get("fiftyTwoWeekLow")

    if price is None and not info:
        info_fallback = {}
        try:
            info_fallback = yf.Ticker(ticker_symbol).info
        except Exception:
            pass
        price = info_fallback.get("currentPrice") or info_fallback.get("regularMarketPrice")
        currency = info_fallback.get("currency", "BRL")

    if history_chart is not None and not history_chart.empty:
        for date, row in history_chart.iterrows():
            chart_labels.append(date.strftime("%d/%m/%Y"))
            chart_data.append(row["Close"])

    if price is None:
        price, currency_manual = get_price_manual(ticker_symbol)
        if price is not None and currency_manual:
            currency = currency_manual

    usd_brl_rate = 1.0
    if currency == "USD":
        try:
            usd_brl_rate = get_real_time_currency("USD")
            price = price * usd_brl_rate
            currency = "BRL"
        except Exception:
            pass

    if currency == "BRL" and usd_brl_rate != 1.0:
        if previous_close:
            previous_close *= usd_brl_rate
        if day_high:
            day_high *= usd_brl_rate
        if day_low:
            day_low *= usd_brl_rate
        if year_high:
            year_high *= usd_brl_rate
        if year_low:
            year_low *= usd_brl_rate

    change_percent = 0
    if previous_close and price:
        change_percent = ((price - previous_close) / previous_close) * 100

    return JsonResponse({
        "symbol": ticker_symbol,
        "name": name,
        "price": price,
        "currency": currency,
        "change_percent": change_percent,
        "day_high": day_high,
        "day_low": day_low,
        "year_high": year_high,
        "year_low": year_low,
        "chart_labels": chart_labels,
        "chart_data": chart_data,
    })


@login_required
def investment_dashboard(request):
    investments = Investment.objects.filter(user=request.user)

    try:
        usd_brl_rate = get_real_time_currency("USD")
    except Exception:
        usd_brl_rate = 5.0

    aggregated_portfolio = {}
    for inv in investments:
        key = (inv.symbol, inv.category_type)
        if key not in aggregated_portfolio:
            aggregated_portfolio[key] = {
                "symbol": inv.symbol,
                "category": inv.category_type,
                "name": inv.name,
                "quantity": 0.0,
                "total_cost": 0.0,
            }
        aggregated_portfolio[key]["quantity"] += float(inv.quantity)
        aggregated_portfolio[key]["total_cost"] += float(inv.total_cost)
        if not aggregated_portfolio[key]["name"] and inv.name:
            aggregated_portfolio[key]["name"] = inv.name

    portfolio_data = []
    total_invested = 0
    total_current_value = 0
    labels = []
    data_values = []

    for key, data in aggregated_portfolio.items():
        symbol = data["symbol"]
        category = data["category"]
        quantity = data["quantity"]
        invested_value = data["total_cost"]
        avg_price = invested_value / quantity if quantity > 0 else 0

        total_invested += invested_value
        current_price = None

        if category == "CURRENCY":
            current_price = get_real_time_currency(symbol) or avg_price
        elif category == "FIXED":
            current_price = avg_price
        else:
            try:
                ticker = yf.Ticker(symbol)
                try:
                    current_price = ticker.fast_info.last_price
                except Exception:
                    pass

                if current_price is None:
                    history = ticker.history(period="1d")
                    if not history.empty:
                        current_price = history["Close"].iloc[-1]

                if current_price is None:
                    current_price, _ = get_price_manual(symbol)

                if current_price is not None:
                    try:
                        if ticker.fast_info.currency == "USD":
                            current_price *= usd_brl_rate
                    except Exception:
                        if not symbol.endswith(".SA"):
                            current_price *= usd_brl_rate
                else:
                    current_price = avg_price
            except Exception:
                current_price = avg_price

        current_value = quantity * float(current_price)
        total_current_value += current_value
        profit_loss = current_value - invested_value
        profit_loss_pct = (profit_loss / invested_value) * 100 if invested_value > 0 else 0

        portfolio_data.append({
            "investment": {
                "symbol": symbol,
                "name": data["name"],
                "quantity": quantity,
                "purchase_price": avg_price,
            },
            "current_price": current_price,
            "current_value": current_value,
            "invested_value": invested_value,
            "profit_loss": profit_loss,
            "profit_loss_pct": profit_loss_pct,
        })

        labels.append(symbol)
        data_values.append(current_value)

    roi = total_current_value - float(total_invested)
    roi_pct = (roi / float(total_invested)) * 100 if total_invested > 0 else 0

    context = {
        "portfolio": portfolio_data,
        "total_invested": total_invested,
        "total_current_value": total_current_value,
        "roi": roi,
        "roi_pct": roi_pct,
        "chart_labels": json.dumps(labels),
        "chart_data": json.dumps(data_values),
    }
    return render(request, "core/investment_dashboard.html", context)


@login_required
def safe_haven_dashboard(request):
    usd_rate = get_real_time_currency("USD") or 0.0
    eur_rate = get_real_time_currency("EUR") or 0.0
    selic_rate = get_latest_indicator(SERIES_SELIC_META)
    cdi_rate = selic_rate - 0.10

    safe_investments = Investment.objects.filter(
        user=request.user,
        category_type__in=["FIXED", "CURRENCY", "POUPANCA"],
    )

    fixed_assets = []
    my_currencies = []
    total_fixed_invested = 0
    total_fixed_current = 0

    for inv in safe_investments:
        current_val = float(inv.total_cost)

        if inv.category_type in ["FIXED", "POUPANCA"]:
            if inv.index_type == "CDI":
                current_val = calculate_cdi_correction(
                    inv.total_cost, inv.date, percentage_of_cdi=inv.fixed_rate or 100
                )
            elif inv.index_type == "PRE":
                current_val = calculate_pre_fixado(
                    inv.total_cost, inv.date, rate_yearly=inv.fixed_rate
                )
            elif inv.index_type == "IPCA":
                rate = 4.0 + float(inv.fixed_rate or 0)
                current_val = calculate_pre_fixado(
                    inv.total_cost, inv.date, rate_yearly=rate
                )

            gain = current_val - float(inv.total_cost)
            fixed_assets.append({
                "investment": inv,
                "rate_display": f"{inv.fixed_rate or 100}% {inv.get_index_type_display()}",
                "current_value": current_val,
                "gain": gain,
            })
            total_fixed_invested += float(inv.total_cost)
            total_fixed_current += current_val

        elif inv.category_type == "CURRENCY":
            rate = 1.0
            if "USD" in inv.symbol.upper():
                rate = usd_rate
            elif "EUR" in inv.symbol.upper():
                rate = eur_rate

            current_val = float(inv.quantity) * rate
            my_currencies.append({
                "investment": inv,
                "current_price": rate,
                "current_value": current_val,
            })

    context = {
        "usd_rate": usd_rate,
        "eur_rate": eur_rate,
        "selic_rate": selic_rate,
        "cdi_rate": cdi_rate,
        "fixed_assets": fixed_assets,
        "currencies": my_currencies,
        "total_fixed_invested": total_fixed_invested,
        "total_fixed_current": total_fixed_current,
    }
    return render(request, "core/safe_haven_dashboard.html", context)


class InvestmentListView(LoginRequiredMixin, ListView):
    model = Investment
    template_name = "core/investment_list.html"
    context_object_name = "investments"

    def get_queryset(self):
        return Investment.objects.filter(user=self.request.user)


class InvestmentDetailView(LoginRequiredMixin, TemplateView):
    template_name = "core/investment_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        symbol = self.kwargs["symbol"]

        investments = Investment.objects.filter(user=self.request.user, symbol=symbol)
        if not investments.exists():
            raise Http404("Investimento não encontrado")

        total_quantity = sum(inv.quantity for inv in investments)
        total_invested = sum(inv.total_cost for inv in investments)
        avg_price = total_invested / total_quantity if total_quantity > 0 else 0

        context["investment"] = {
            "symbol": symbol,
            "name": investments.first().name,
            "quantity": total_quantity,
            "total_cost": total_invested,
            "purchase_price": avg_price,
            "pk": investments.first().pk,
        }

        try:
            ticker = yf.Ticker(symbol)
            history = ticker.history(period="6mo")

            dates = [d.strftime("%d/%m/%Y") for d, _ in history.iterrows()]
            prices = [row["Close"] for _, row in history.iterrows()]

            context["chart_labels"] = json.dumps(dates)
            context["chart_data"] = json.dumps(prices)

            try:
                current_price = ticker.fast_info.last_price
                previous_close = ticker.fast_info.previous_close
                day_change = ((current_price - previous_close) / previous_close) * 100
            except Exception:
                current_price = history["Close"].iloc[-1] if not history.empty else 0
                day_change = 0

            context["current_price"] = current_price
            context["day_change"] = day_change

            current_value = float(total_quantity) * float(current_price)
            invested_value = float(total_invested)
            context["current_value"] = current_value
            context["profit_loss"] = current_value - invested_value
            context["profit_loss_pct"] = (
                (context["profit_loss"] / invested_value) * 100 if invested_value > 0 else 0
            )
        except Exception as e:
            context["error"] = str(e)

        return context


class InvestmentCreateView(LoginRequiredMixin, CreateView):
    model = Investment
    form_class = InvestmentForm
    template_name = "core/investment_form.html"
    success_url = reverse_lazy("investment_dashboard")

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class InvestmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Investment
    form_class = InvestmentForm
    template_name = "core/investment_form.html"
    success_url = reverse_lazy("investment_dashboard")

    def form_valid(self, form):
        if not form.cleaned_data.get("create_transaction"):
            form.instance._skip_transaction = True
        return super().form_valid(form)

    def get_queryset(self):
        return Investment.objects.filter(user=self.request.user)


class InvestmentDeleteView(LoginRequiredMixin, DeleteView):
    model = Investment
    template_name = "core/confirm_delete.html"
    success_url = reverse_lazy("investment_dashboard")

    def get_queryset(self):
        return Investment.objects.filter(user=self.request.user)
