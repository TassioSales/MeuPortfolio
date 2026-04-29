from __future__ import annotations

import json
from pathlib import Path

import duckdb
import polars as pl


def build_warehouse(parquet_paths: list[Path], warehouse_path: Path) -> Path:
    warehouse_path.parent.mkdir(parents=True, exist_ok=True)
    build_path = warehouse_path.with_suffix(".build.duckdb")
    build_path.unlink(missing_ok=True)
    con = duckdb.connect(str(build_path))
    try:
        con.execute(
            """
            CREATE OR REPLACE TABLE raw_prices AS
            SELECT *
            FROM read_parquet(?)
            """,
            [list(map(str, parquet_paths))],
        )
        con.execute(
            """
            CREATE OR REPLACE TABLE staging_prices AS
            SELECT
              week,
              state,
              city,
              product,
              avg_price,
              volatility,
              avg_buy_price,
              dollar,
              brent,
              ipca,
              brand_count
            FROM raw_prices
            WHERE avg_price IS NOT NULL
              AND product IS NOT NULL
              AND state IS NOT NULL
            """
        )
        con.execute(
            """
            CREATE OR REPLACE TABLE curated_weekly_prices AS
            SELECT *
            FROM staging_prices
            """
        )
        con.execute(
            """
            CREATE OR REPLACE TABLE state_summary AS
            SELECT
              week,
              state,
              product,
              AVG(avg_price) AS avg_price,
              AVG(volatility) AS volatility,
              AVG(avg_buy_price) AS avg_buy_price,
              AVG(dollar) AS dollar,
              AVG(brent) AS brent,
              AVG(ipca) AS ipca
            FROM curated_weekly_prices
            GROUP BY 1, 2, 3
            """
        )
        con.execute(
            """
            CREATE OR REPLACE TABLE latest_overview AS
            WITH latest AS (
              SELECT
                state,
                product,
                MAX(week) AS week
              FROM state_summary
              GROUP BY 1, 2
            )
            SELECT
              s.state,
              s.product,
              s.avg_price,
              s.volatility,
              s.dollar,
              s.brent,
              s.ipca,
              CASE
                WHEN s.avg_price > s.avg_buy_price THEN 'up'
                WHEN s.avg_price < s.avg_buy_price THEN 'down'
                ELSE 'flat'
              END AS price_direction
            FROM state_summary s
            INNER JOIN latest l
              ON s.state = l.state
             AND s.product = l.product
             AND s.week = l.week
            """
        )
    finally:
        con.close()
    try:
        build_path.replace(warehouse_path)
        return warehouse_path
    except OSError:
        return build_path


def persist_forecasts(forecasts: dict[str, list[dict]], models_dir: Path) -> Path:
    models_dir.mkdir(parents=True, exist_ok=True)
    destination = models_dir / "forecasts.json"
    destination.write_text(json.dumps(forecasts, indent=2), encoding="utf-8")
    return destination


def persist_api_snapshots(warehouse_path: Path, models_dir: Path) -> dict[str, Path]:
    models_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(warehouse_path), read_only=True)
    try:
        latest_overview = pl.from_arrow(con.execute("SELECT * FROM latest_overview").arrow())
        latest_overview = latest_overview.rename({"avg_price": "average_price"})
        history = pl.from_arrow(
            con.execute(
                """
                SELECT week, state, city, product, avg_price AS average_price, volatility, avg_buy_price AS average_buy_price
                FROM curated_weekly_prices
                ORDER BY week, state, city, product
                """
            ).arrow()
        )
        fuels = pl.from_arrow(con.execute("SELECT DISTINCT product FROM curated_weekly_prices ORDER BY product").arrow())
    finally:
        con.close()

    overview_path = models_dir / "overview.json"
    history_path = models_dir / "history.json"
    fuels_path = models_dir / "fuels.json"

    overview_path.write_text(latest_overview.write_json(), encoding="utf-8")
    history_path.write_text(history.write_json(), encoding="utf-8")
    fuels_path.write_text(json.dumps(fuels.get_column("product").to_list(), indent=2), encoding="utf-8")

    return {
        "overview": overview_path,
        "history": history_path,
        "fuels": fuels_path,
    }


def persist_explorer_snapshot(warehouse_path: Path, models_dir: Path) -> Path:
    models_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(warehouse_path), read_only=True)
    try:
        tables = pl.from_arrow(
            con.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'main'
                ORDER BY table_name
                """
            ).arrow()
        ).get_column("table_name").to_list()
        table_stats: list[dict[str, object]] = []
        for table in tables:
            row_count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            sample_rows = pl.from_arrow(con.execute(f"SELECT * FROM {table} LIMIT 5").arrow()).to_dicts()
            table_stats.append(
                {
                    "table": table,
                    "row_count": row_count,
                    "sample_rows": sample_rows,
                }
            )
        payload = {
            "warehouse_path": str(warehouse_path),
            "tables": table_stats,
        }
    finally:
        con.close()

    destination = models_dir / "explorer.json"
    destination.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return destination


def query_duckdb(warehouse_path: Path, sql: str) -> pl.DataFrame:
    con = duckdb.connect(str(warehouse_path), read_only=True)
    try:
        return pl.from_arrow(con.execute(sql).arrow())
    finally:
        con.close()
