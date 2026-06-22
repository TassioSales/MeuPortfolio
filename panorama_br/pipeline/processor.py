from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from loguru import logger

from . import db


def process_and_store(
    bcb_data: dict,
    market_data: dict,
    regional_data: list[dict],
) -> None:
    """Processa os dados coletados e armazena no SQLite."""
    conn = db.get_conn()
    try:
        _store_macro(conn, bcb_data)
        _store_history(conn, bcb_data)
        _store_market(conn, market_data)
        _store_regional(conn, regional_data)
        logger.info("Dados processados e armazenados com sucesso.")
    except Exception as exc:
        logger.error(f"Erro ao processar/armazenar dados: {exc}")
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Macro indicators
# ---------------------------------------------------------------------------

def _store_macro(conn: sqlite3.Connection, bcb: dict) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    _macro_entries = [
        ("selic",      bcb.get("selic_atual", 0.0),    "% a.a.",  today),
        ("ipca_mensal", bcb.get("ipca_mensal", 0.0),   "%",        today),
        ("ipca_12m",   bcb.get("ipca_12m", 0.0),       "% a.a.",  today),
        ("cambio_usd", bcb.get("cambio_usd", 0.0),     "R$/USD",  today),
        ("desemprego", bcb.get("desemprego", 0.0),     "%",        today),
    ]

    for indicator, value, unit, ref_date in _macro_entries:
        db.upsert_macro(conn, indicator, value, unit, ref_date)
        logger.debug(f"Macro salvo: {indicator}={value}{unit}")


# ---------------------------------------------------------------------------
# Historical series
# ---------------------------------------------------------------------------

def _store_history(conn: sqlite3.Connection, bcb: dict) -> None:
    history_keys = [
        "selic_history",
        "ipca_mensal_history",
        "ipca_12m_history",
        "cambio_history",
        "desemprego_history",
    ]
    total = 0
    for key in history_keys:
        series: list[dict] = bcb.get(key, [])
        for item in series:
            try:
                db.insert_history(
                    conn,
                    indicator=item["indicator"],
                    value=float(item["value"]),
                    date=item["date"],
                )
                total += 1
            except (KeyError, ValueError) as exc:
                logger.warning(f"Ponto de histórico inválido em {key}: {exc}")
    logger.info(f"Histórico: {total} pontos inseridos/ignorados.")


# ---------------------------------------------------------------------------
# Market snapshot
# ---------------------------------------------------------------------------

def _store_market(conn: sqlite3.Connection, market: dict) -> None:
    stocks: list[dict] = market.get("stocks", [])
    for s in stocks:
        try:
            db.upsert_market(
                conn,
                symbol=s["symbol"],
                name=s.get("name", ""),
                price=float(s.get("price", 0)),
                change_pct=float(s.get("change_pct", 0)),
                volume=float(s.get("volume", 0)),
                market_cap=float(s.get("market_cap", 0)),
            )
        except (KeyError, ValueError) as exc:
            logger.warning(f"Dado de mercado inválido para {s.get('symbol', '?')}: {exc}")
    logger.info(f"Mercado: {len(stocks)} ativo(s) salvo(s).")


# ---------------------------------------------------------------------------
# Regional indicators
# ---------------------------------------------------------------------------

def _store_regional(conn: sqlite3.Connection, regional: list[dict]) -> None:
    for r in regional:
        try:
            db.upsert_regional(
                conn,
                uf=r["uf"],
                year=int(r["year"]),
                state_name=r.get("state_name", ""),
                region=r.get("region", ""),
                pib=float(r.get("pib", 0)),
                pib_per_capita=float(r.get("pib_per_capita", 0)),
                population=int(r.get("population", 0)),
                desemprego=float(r.get("desemprego", 0)),
            )
        except (KeyError, ValueError) as exc:
            logger.warning(f"Dado regional inválido para {r.get('uf', '?')}: {exc}")
    logger.info(f"Regional: {len(regional)} estado(s) salvo(s).")


# ---------------------------------------------------------------------------
# Health check / summary
# ---------------------------------------------------------------------------

def get_summary_stats(conn: sqlite3.Connection) -> dict:
    """Retorna estatísticas de registros por tabela para health check."""
    tables = [
        "macro_indicators",
        "indicator_history",
        "market_snapshot",
        "regional_indicators",
        "pipeline_log",
    ]
    stats: dict[str, int] = {}
    for table in tables:
        try:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608
            stats[table] = cursor.fetchone()[0]
        except Exception as exc:
            logger.warning(f"Erro ao contar registros em {table}: {exc}")
            stats[table] = -1
    return stats
