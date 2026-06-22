from __future__ import annotations

from datetime import datetime, timezone

import requests
from loguru import logger

try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False
    logger.warning("yfinance não disponível; dados de mercado serão sintéticos.")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BCB_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs"

_TICKER_NAMES: dict[str, str] = {
    "^BVSP": "IBOVESPA",
    "VALE3.SA": "Vale",
    "PETR4.SA": "Petrobras PN",
    "ITUB4.SA": "Itaú Unibanco",
    "ABEV3.SA": "Ambev",
    "WEGE3.SA": "WEG",
    "B3SA3.SA": "B3",
    "RENT3.SA": "Localiza",
}

_TICKERS = list(_TICKER_NAMES.keys())


def _bcb_date_to_iso(date_str: str) -> str:
    """Converte 'DD/MM/YYYY' para 'YYYY-MM-DD'."""
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return date_str


def _fetch_bcb_series(series_id: int, n: int = 90) -> list[dict]:
    """Busca os últimos n registros de uma série BCB."""
    url = f"{_BCB_BASE}.{series_id}/dados/ultimos/{n}?formato=json"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _series_to_history(raw: list[dict], indicator: str) -> list[dict]:
    """Converte lista BCB em lista de dicts com indicator, value, date."""
    result = []
    for item in raw:
        try:
            result.append(
                {
                    "indicator": indicator,
                    "value": float(item["valor"].replace(",", ".")),
                    "date": _bcb_date_to_iso(item["data"]),
                }
            )
        except (KeyError, ValueError):
            continue
    return result


# ---------------------------------------------------------------------------
# BCB fallback data (valores realistas 2024)
# ---------------------------------------------------------------------------

def _bcb_fallback() -> dict:
    logger.warning("Usando dados sintéticos BCB.")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return {
        "selic_atual": 10.50,
        "selic_history": [{"indicator": "selic", "value": 10.50, "date": today}],
        "ipca_mensal": 0.44,
        "ipca_mensal_history": [{"indicator": "ipca_mensal", "value": 0.44, "date": today}],
        "ipca_12m": 4.83,
        "ipca_12m_history": [{"indicator": "ipca_12m", "value": 4.83, "date": today}],
        "cambio_usd": 4.97,
        "cambio_history": [{"indicator": "cambio_usd", "value": 4.97, "date": today}],
        "desemprego": 7.8,
        "desemprego_history": [{"indicator": "desemprego", "value": 7.8, "date": today}],
    }


# ---------------------------------------------------------------------------
# collect_bcb
# ---------------------------------------------------------------------------

def collect_bcb() -> dict:
    """Retorna dict com chaves: selic_atual, selic_history, ipca_mensal, ipca_mensal_history,
    ipca_12m, ipca_12m_history, cambio_usd, cambio_history, desemprego, desemprego_history."""
    try:
        raw_selic = _fetch_bcb_series(11, 90)
        raw_ipca_m = _fetch_bcb_series(433, 36)
        raw_ipca_12 = _fetch_bcb_series(13522, 36)
        raw_usd = _fetch_bcb_series(1, 365)
        raw_desemp = _fetch_bcb_series(24369, 24)

        def _last_value(raw: list[dict]) -> float:
            return float(raw[-1]["valor"].replace(",", ".")) if raw else 0.0

        selic_h = _series_to_history(raw_selic, "selic")
        ipca_m_h = _series_to_history(raw_ipca_m, "ipca_mensal")
        ipca_12_h = _series_to_history(raw_ipca_12, "ipca_12m")
        cambio_h = _series_to_history(raw_usd, "cambio_usd")
        desemp_h = _series_to_history(raw_desemp, "desemprego")

        return {
            "selic_atual": _last_value(raw_selic),
            "selic_history": selic_h,
            "ipca_mensal": _last_value(raw_ipca_m),
            "ipca_mensal_history": ipca_m_h,
            "ipca_12m": _last_value(raw_ipca_12),
            "ipca_12m_history": ipca_12_h,
            "cambio_usd": _last_value(raw_usd),
            "cambio_history": cambio_h,
            "desemprego": _last_value(raw_desemp),
            "desemprego_history": desemp_h,
        }

    except Exception as exc:
        logger.warning(f"Erro ao coletar dados BCB: {exc}. Usando fallback sintético.")
        return _bcb_fallback()


# ---------------------------------------------------------------------------
# Market fallback
# ---------------------------------------------------------------------------

def _market_fallback() -> dict:
    logger.warning("Usando dados sintéticos de mercado.")
    today = datetime.now(timezone.utc).isoformat()
    ibov_price = 128_000.0
    stocks = [
        {"symbol": "^BVSP",    "name": "IBOVESPA",       "price": 128_000.0, "change_pct":  0.55, "volume": 15_000_000_000.0, "market_cap": 0.0},
        {"symbol": "VALE3.SA", "name": "Vale",            "price": 63.50,    "change_pct": -0.80, "volume": 45_000_000.0,     "market_cap": 280_000_000_000.0},
        {"symbol": "PETR4.SA", "name": "Petrobras PN",   "price": 37.20,    "change_pct":  1.20, "volume": 90_000_000.0,     "market_cap": 480_000_000_000.0},
        {"symbol": "ITUB4.SA", "name": "Itaú Unibanco",  "price": 34.80,    "change_pct":  0.30, "volume": 55_000_000.0,     "market_cap": 350_000_000_000.0},
        {"symbol": "ABEV3.SA", "name": "Ambev",           "price": 12.50,    "change_pct": -0.40, "volume": 30_000_000.0,     "market_cap": 195_000_000_000.0},
        {"symbol": "WEGE3.SA", "name": "WEG",             "price": 47.90,    "change_pct":  0.65, "volume": 12_000_000.0,     "market_cap": 210_000_000_000.0},
        {"symbol": "B3SA3.SA", "name": "B3",              "price": 12.10,    "change_pct": -0.25, "volume": 25_000_000.0,     "market_cap": 72_000_000_000.0},
        {"symbol": "RENT3.SA", "name": "Localiza",        "price": 55.30,    "change_pct":  0.90, "volume": 8_000_000.0,      "market_cap": 58_000_000_000.0},
    ]
    for s in stocks:
        s["updated_at"] = today
    return {
        "ibovespa": {"value": ibov_price, "change_pct": 0.55},
        "stocks": stocks,
    }


# ---------------------------------------------------------------------------
# collect_market
# ---------------------------------------------------------------------------

def collect_market() -> dict:
    """Retorna dict com: ibovespa (valor, change_pct), stocks (lista)."""
    if not _YF_AVAILABLE:
        return _market_fallback()

    try:
        today = datetime.now(timezone.utc).isoformat()
        stocks = []
        ibov_value = 0.0
        ibov_change = 0.0

        for ticker_sym in _TICKERS:
            try:
                ticker = yf.Ticker(ticker_sym)
                info = ticker.fast_info
                last_price = float(info.last_price or 0)
                prev_close = float(info.previous_close or 0)
                change_pct = (
                    (last_price - prev_close) / prev_close * 100
                    if prev_close and prev_close != 0
                    else 0.0
                )
                volume = float(getattr(info, "three_month_average_volume", None) or 0)
                market_cap = float(getattr(info, "market_cap", None) or 0)
                name = _TICKER_NAMES.get(ticker_sym, ticker_sym)

                entry = {
                    "symbol": ticker_sym,
                    "name": name,
                    "price": last_price,
                    "change_pct": round(change_pct, 4),
                    "volume": volume,
                    "market_cap": market_cap,
                    "updated_at": today,
                }
                stocks.append(entry)

                if ticker_sym == "^BVSP":
                    ibov_value = last_price
                    ibov_change = round(change_pct, 4)

            except Exception as ticker_exc:
                logger.warning(f"Erro ao buscar ticker {ticker_sym}: {ticker_exc}")

        if not stocks:
            return _market_fallback()

        return {
            "ibovespa": {"value": ibov_value, "change_pct": ibov_change},
            "stocks": stocks,
        }

    except Exception as exc:
        logger.warning(f"Erro ao coletar dados de mercado: {exc}. Usando fallback sintético.")
        return _market_fallback()


# ---------------------------------------------------------------------------
# collect_regional
# ---------------------------------------------------------------------------

def collect_regional() -> list[dict]:
    """Retorna lista de dicts com dados regionais por estado (IBGE 2022 estimativas)."""
    return [
        {"uf": "SP", "year": 2022, "state_name": "São Paulo",          "region": "Sudeste",       "pib": 2800.0,  "pib_per_capita": 59000.0, "population": 47_000_000, "desemprego": 7.5},
        {"uf": "MG", "year": 2022, "state_name": "Minas Gerais",       "region": "Sudeste",       "pib": 700.0,   "pib_per_capita": 33000.0, "population": 21_000_000, "desemprego": 8.2},
        {"uf": "RJ", "year": 2022, "state_name": "Rio de Janeiro",     "region": "Sudeste",       "pib": 850.0,   "pib_per_capita": 47000.0, "population": 17_000_000, "desemprego": 11.5},
        {"uf": "RS", "year": 2022, "state_name": "Rio Grande do Sul",  "region": "Sul",           "pib": 550.0,   "pib_per_capita": 47000.0, "population": 11_000_000, "desemprego": 6.8},
        {"uf": "PR", "year": 2022, "state_name": "Paraná",             "region": "Sul",           "pib": 500.0,   "pib_per_capita": 42000.0, "population": 11_000_000, "desemprego": 6.2},
        {"uf": "BA", "year": 2022, "state_name": "Bahia",              "region": "Nordeste",      "pib": 300.0,   "pib_per_capita": 19000.0, "population": 15_000_000, "desemprego": 16.5},
        {"uf": "SC", "year": 2022, "state_name": "Santa Catarina",     "region": "Sul",           "pib": 380.0,   "pib_per_capita": 48000.0, "population":  7_600_000, "desemprego": 4.9},
        {"uf": "GO", "year": 2022, "state_name": "Goiás",              "region": "Centro-Oeste",  "pib": 240.0,   "pib_per_capita": 32000.0, "population":  7_200_000, "desemprego": 8.1},
        {"uf": "PE", "year": 2022, "state_name": "Pernambuco",         "region": "Nordeste",      "pib": 200.0,   "pib_per_capita": 20000.0, "population":  9_600_000, "desemprego": 16.8},
        {"uf": "CE", "year": 2022, "state_name": "Ceará",              "region": "Nordeste",      "pib": 180.0,   "pib_per_capita": 18000.0, "population":  9_200_000, "desemprego": 14.2},
        {"uf": "AM", "year": 2022, "state_name": "Amazonas",           "region": "Norte",         "pib": 120.0,   "pib_per_capita": 28000.0, "population":  4_100_000, "desemprego": 10.5},
        {"uf": "DF", "year": 2022, "state_name": "Distrito Federal",   "region": "Centro-Oeste",  "pib": 280.0,   "pib_per_capita": 84000.0, "population":  3_000_000, "desemprego": 11.5},
        {"uf": "PA", "year": 2022, "state_name": "Pará",               "region": "Norte",         "pib": 170.0,   "pib_per_capita": 18000.0, "population":  8_700_000, "desemprego": 11.8},
        {"uf": "MT", "year": 2022, "state_name": "Mato Grosso",        "region": "Centro-Oeste",  "pib": 200.0,   "pib_per_capita": 52000.0, "population":  3_600_000, "desemprego": 5.8},
        {"uf": "MS", "year": 2022, "state_name": "Mato Grosso do Sul", "region": "Centro-Oeste",  "pib": 130.0,   "pib_per_capita": 43000.0, "population":  2_800_000, "desemprego": 6.5},
        {"uf": "ES", "year": 2022, "state_name": "Espírito Santo",     "region": "Sudeste",       "pib": 175.0,   "pib_per_capita": 40000.0, "population":  4_100_000, "desemprego": 9.5},
        {"uf": "MA", "year": 2022, "state_name": "Maranhão",           "region": "Nordeste",      "pib": 105.0,   "pib_per_capita": 14000.0, "population":  7_100_000, "desemprego": 14.5},
        {"uf": "PB", "year": 2022, "state_name": "Paraíba",            "region": "Nordeste",      "pib":  72.0,   "pib_per_capita": 17000.0, "population":  4_000_000, "desemprego": 14.0},
        {"uf": "RN", "year": 2022, "state_name": "Rio Grande do Norte","region": "Nordeste",      "pib":  78.0,   "pib_per_capita": 20000.0, "population":  3_500_000, "desemprego": 14.2},
        {"uf": "AL", "year": 2022, "state_name": "Alagoas",            "region": "Nordeste",      "pib":  60.0,   "pib_per_capita": 17000.0, "population":  3_300_000, "desemprego": 18.5},
        {"uf": "PI", "year": 2022, "state_name": "Piauí",              "region": "Nordeste",      "pib":  60.0,   "pib_per_capita": 16000.0, "population":  3_300_000, "desemprego": 12.5},
        {"uf": "SE", "year": 2022, "state_name": "Sergipe",            "region": "Nordeste",      "pib":  50.0,   "pib_per_capita": 20000.0, "population":  2_300_000, "desemprego": 18.0},
        {"uf": "RO", "year": 2022, "state_name": "Rondônia",           "region": "Norte",         "pib":  52.0,   "pib_per_capita": 27000.0, "population":  1_800_000, "desemprego": 8.5},
        {"uf": "TO", "year": 2022, "state_name": "Tocantins",          "region": "Norte",         "pib":  40.0,   "pib_per_capita": 23000.0, "population":  1_600_000, "desemprego": 9.0},
        {"uf": "AC", "year": 2022, "state_name": "Acre",               "region": "Norte",         "pib":  18.0,   "pib_per_capita": 18000.0, "population":    900_000, "desemprego": 13.0},
        {"uf": "AP", "year": 2022, "state_name": "Amapá",              "region": "Norte",         "pib":  18.0,   "pib_per_capita": 20000.0, "population":    800_000, "desemprego": 14.5},
        {"uf": "RR", "year": 2022, "state_name": "Roraima",            "region": "Norte",         "pib":  14.0,   "pib_per_capita": 20000.0, "population":    600_000, "desemprego": 15.0},
    ]
