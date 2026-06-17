import logging
import os
import requests
import yfinance as yf
from datetime import datetime, timedelta
from functools import lru_cache

logger = logging.getLogger('core')

_BRAPI_TOKEN = os.environ.get("BRAPI_TOKEN", "")

# BCB Series Codes
SERIES_CDI_MENSAL = 4391  # % a.m.
SERIES_IPCA_MENSAL = 433  # % a.m.
SERIES_IGPM_MENSAL = 189  # % a.m.
SERIES_SELIC_META = 432   # % a.a.


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


def get_latest_indicator(code):
    """Get the most recent value from a BCB series."""
    start_date = (datetime.now() - timedelta(days=60)).strftime('%d/%m/%Y')
    series = get_bcb_series(code, start_date)
    if series:
        return float(series[-1]['valor'])
    return 0.0


def calculate_cdi_correction(principal, start_date, percentage_of_cdi=100.0, due_date=None):
    """Calculate compound correction by CDI monthly rates."""
    if not principal or principal <= 0:
        return 0
    if not start_date:
        return principal
    start_str = start_date.strftime('%d/%m/%Y')
    series = get_bcb_series(SERIES_CDI_MENSAL, start_str)
    accumulated_factor = 1.0
    pct_factor = float(percentage_of_cdi) / 100.0
    for item in series:
        val = float(item['valor'])
        effective_rate = val * pct_factor
        accumulated_factor *= (1 + (effective_rate / 100.0))
    return float(principal) * accumulated_factor


def calculate_pre_fixado(principal, start_date, rate_yearly):
    """Calculate constant-rate appreciation. rate_yearly in % a.a."""
    if not principal or not rate_yearly:
        return principal
    days_elapsed = max((datetime.now().date() - start_date).days, 0)
    rate_decimal = float(rate_yearly) / 100.0
    factor = (1 + rate_decimal) ** (days_elapsed / 365.0)
    return float(principal) * factor


def get_real_time_currency(symbol_pair="USD"):
    """Return conversion rate of 1 unit of the given currency in BRL."""
    symbol_pair = symbol_pair.upper().strip()

    # AwesomeAPI is primary for USD/EUR (fast, no rate limits)
    if symbol_pair in ['USD', 'EUR']:
        try:
            url = f"https://economia.awesomeapi.com.br/json/last/{symbol_pair}-BRL"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                pair_key = f"{symbol_pair}BRL"
                if pair_key in data:
                    return float(data[pair_key]['bid'])
        except Exception as e:
            logger.warning(f"AwesomeAPI failed for {symbol_pair}: {e}")

    # yfinance fallback
    try:
        ticker_name = 'BRL=X' if symbol_pair == 'USD' else 'EURBRL=X' if symbol_pair == 'EUR' else symbol_pair
        ticker = yf.Ticker(ticker_name)
        price = getattr(ticker.fast_info, 'last_price', None)
        if price:
            return price
        hist = ticker.history(period='1d')
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except Exception as e:
        logger.warning(f"yfinance failed for {symbol_pair}: {e}")

    # AwesomeAPI fallback for other pairs
    if symbol_pair not in ['USD', 'EUR']:
        try:
            url = f"https://economia.awesomeapi.com.br/json/last/{symbol_pair}-BRL"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                pair_key = f"{symbol_pair}BRL"
                if pair_key in data:
                    return float(data[pair_key]['bid'])
        except Exception:
            pass

    return None


def _parse_yahoo_chart(data: dict) -> dict:
    """Extract quote fields from a Yahoo Finance v8 chart API response dict."""
    results = data.get("chart", {}).get("result", [])
    if not results:
        return {}
    r = results[0]
    meta = r.get("meta", {})
    timestamps = r.get("timestamp", [])
    quotes = r.get("indicators", {}).get("quote", [{}])
    closes = quotes[0].get("close", []) if quotes else []

    chart_dates, chart_prices = [], []
    for ts, close_price in zip(timestamps, closes):
        if close_price is not None:
            chart_dates.append(datetime.fromtimestamp(ts).strftime("%d/%m/%Y"))
            chart_prices.append(round(float(close_price), 4))

    return {
        "price": meta.get("regularMarketPrice"),
        "previous_close": meta.get("previousClose") or meta.get("chartPreviousClose"),
        "day_high": meta.get("regularMarketDayHigh"),
        "day_low": meta.get("regularMarketDayLow"),
        "year_high": meta.get("fiftyTwoWeekHigh"),
        "year_low": meta.get("fiftyTwoWeekLow"),
        "currency": meta.get("currency", "BRL"),
        "long_name": meta.get("longName") or meta.get("shortName"),
        "chart_dates": chart_dates,
        "chart_prices": chart_prices,
    }


def get_brapi_quote(symbol: str) -> dict:
    """
    Fetch quote + 6-month history for a ticker.

    Priority:
    1. brapi.dev (if BRAPI_TOKEN is set) — best data for Brazilian stocks
    2. Yahoo Finance v8 chart API (no token needed, same source as get_price_manual)
    """
    # ── 1. brapi.dev with token ───────────────────────────────────────────────
    if _BRAPI_TOKEN and symbol.endswith(".SA"):
        try:
            ticker = symbol[:-3]
            url = f"https://brapi.dev/api/quote/{ticker}?range=6mo&interval=1d&token={_BRAPI_TOKEN}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    r = results[0]
                    chart_dates, chart_prices = [], []
                    for h in r.get("historicalDataPrice", []):
                        try:
                            chart_dates.append(datetime.fromtimestamp(h["date"]).strftime("%d/%m/%Y"))
                            chart_prices.append(round(float(h["close"]), 4))
                        except Exception:
                            pass
                    return {
                        "price": r.get("regularMarketPrice"),
                        "previous_close": r.get("regularMarketPreviousClose"),
                        "day_high": r.get("regularMarketDayHigh"),
                        "day_low": r.get("regularMarketDayLow"),
                        "year_high": r.get("fiftyTwoWeekHigh"),
                        "year_low": r.get("fiftyTwoWeekLow"),
                        "currency": "BRL",
                        "long_name": r.get("longName") or r.get("shortName"),
                        "chart_dates": chart_dates,
                        "chart_prices": chart_prices,
                    }
            else:
                logger.warning(f"BRAPI returned {resp.status_code} for {symbol}")
        except Exception as e:
            logger.warning(f"BRAPI failed for {symbol}: {e}")

    # ── 2. Yahoo Finance v8 chart API (no auth needed) ────────────────────────
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        for host in ("query2", "query1"):
            url = f"https://{host}.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=6mo"
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                result = _parse_yahoo_chart(resp.json())
                if result.get("price"):
                    return result
    except Exception as e:
        logger.warning(f"Yahoo chart API failed for {symbol}: {e}")

    return {}
