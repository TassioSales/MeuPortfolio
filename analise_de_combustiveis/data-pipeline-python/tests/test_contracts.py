from __future__ import annotations

import polars as pl

from fuel_analytics.market import build_market_signals
from fuel_analytics.processing import normalize_frame


def test_price_contract_columns() -> None:
    frame = pl.DataFrame(
        {
            "Data da Coleta": ["2026-04-01"],
            "Estado - Sigla": ["SP"],
            "Municipio": ["Sao Paulo"],
            "Produto": ["GASOLINA C"],
            "Valor de Venda": ["6.19"],
            "Valor de Compra": ["5.52"],
            "Unidade de Medida": ["R$/l"],
            "Bandeira": ["Bandeira X"],
            "Regiao - Sigla": ["SE"],
        }
    )
    normalized = normalize_frame(frame)
    assert {"date", "state", "city", "product", "price", "price_buy"}.issubset(normalized.columns)
    assert normalized["product"][0] == "gasolina"


def test_market_contract_columns() -> None:
    sales = pl.DataFrame(
        {
            "date": ["2026-04-01"],
            "state": ["SP"],
            "product": ["gasolina"],
            "sales_volume_m3": [1000.0],
            "segment": ["distribuicao"],
        }
    ).with_columns(pl.col("date").str.to_date())
    processing = pl.DataFrame(
        {
            "date": ["2026-04-01"],
            "refinery": ["REPLAN"],
            "product": ["gasolina"],
            "processed_m3": [2000.0],
            "produced_m3": [1500.0],
        }
    ).with_columns(pl.col("date").str.to_date())
    signals = build_market_signals(sales, processing)
    assert {"month", "state", "product", "sales_volume_m3", "produced_m3", "market_regime"}.issubset(
        signals.columns
    )
    assert signals["market_regime"][0] == "balanced"
