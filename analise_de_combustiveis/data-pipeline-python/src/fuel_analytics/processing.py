from __future__ import annotations

from pathlib import Path

import polars as pl


PRODUCT_MAP = {
    "GASOLINA": "gasolina",
    "GASOLINA C": "gasolina",
    "GASOLINA ADITIVADA": "gasolina",
    "ETANOL": "etanol",
    "ETANOL HIDRATADO": "etanol",
    "DIESEL": "diesel",
    "DIESEL S10": "diesel",
    "ÓLEO DIESEL": "diesel",
    "OLEO DIESEL": "diesel",
    "ÓLEO DIESEL B S10": "diesel",
    "GNV": "gnv",
    "GAS NATURAL VEICULAR": "gnv",
}


def _normalize_product(col: pl.Expr) -> pl.Expr:
    return (
        col.cast(pl.Utf8)
        .str.to_uppercase()
        .replace(PRODUCT_MAP, default=col.cast(pl.Utf8).str.to_lowercase())
        .alias("product")
    )


def load_sample(sample_csv: Path) -> pl.DataFrame:
    return pl.read_csv(sample_csv, try_parse_dates=True)


def normalize_frame(frame: pl.DataFrame) -> pl.DataFrame:
    aliases = {
        "Data da Coleta": "date",
        "Estado - Sigla": "state",
        "Municipio": "city",
        "Produto": "product",
        "Valor de Venda": "price",
        "Valor de Compra": "price_buy",
        "Unidade de Medida": "unit",
        "Bandeira": "brand",
        "Regiao - Sigla": "region",
    }
    renamed = frame.rename({source: target for source, target in aliases.items() if source in frame.columns})
    required = {"date", "state", "city", "product", "price"}
    if not required.issubset(set(renamed.columns)):
        raise ValueError(f"Colunas obrigatorias ausentes: {sorted(required - set(renamed.columns))}")
    for column, default in {
        "price_buy": None,
        "unit": "R$/l",
        "brand": "Sem Bandeira",
        "region": "NA",
    }.items():
        if column not in renamed.columns:
            renamed = renamed.with_columns(pl.lit(default).alias(column))
    date_dtype = renamed.schema.get("date")
    if date_dtype in {pl.Date, pl.Datetime}:
        date_expr = pl.col("date").cast(pl.Date)
    else:
        date_text = pl.col("date").cast(pl.Utf8).str.strip_chars()
        date_expr = (
            pl.when(date_text.str.contains(r"^\d{2}/\d{2}/\d{4}$"))
            .then(date_text.str.to_date(format="%d/%m/%Y", strict=False))
            .when(date_text.str.contains(r"^\d{4}-\d{2}-\d{2}$"))
            .then(date_text.str.to_date(format="%Y-%m-%d", strict=False))
            .otherwise(date_text.str.to_date(strict=False))
        )

    price_expr = (
        pl.col("price")
        .cast(pl.Utf8)
        .str.replace_all(r"\.", "")
        .str.replace(",", ".")
        .cast(pl.Float64, strict=False)
    )
    price_buy_expr = (
        pl.col("price_buy")
        .cast(pl.Utf8)
        .str.replace_all(r"\.", "")
        .str.replace(",", ".")
        .cast(pl.Float64, strict=False)
    )
    normalized = renamed.with_columns(
        date_expr.alias("date"),
        pl.col("state").cast(pl.Utf8).str.to_uppercase().alias("state"),
        pl.col("city").cast(pl.Utf8).str.to_titlecase().alias("city"),
        _normalize_product(pl.col("product")),
        price_expr.alias("price"),
        price_buy_expr.alias("price_buy"),
        pl.col("unit").cast(pl.Utf8).fill_null("R$/l").alias("unit"),
        pl.col("brand").cast(pl.Utf8).fill_null("Sem Bandeira").alias("brand"),
        pl.col("region").cast(pl.Utf8).fill_null("NA").alias("region"),
    )
    return normalized.drop_nulls(["date", "state", "city", "product", "price"])


def enrich_with_external_features(frame: pl.DataFrame) -> pl.DataFrame:
    if {"dollar", "brent", "ipca"}.issubset(frame.columns) and "price_buy" in frame.columns:
        return frame.with_columns(pl.col("price_buy").fill_null((pl.col("price") * 0.83).round(2)))
    return frame.with_columns(
        pl.when(pl.col("price_buy").is_null())
        .then((pl.col("price") * 0.83).round(2))
        .otherwise(pl.col("price_buy"))
        .alias("price_buy"),
        (pl.col("price") * 0.82).round(2).alias("brent"),
        pl.lit(5.1).alias("ipca"),
        pl.lit(5.0).alias("dollar"),
    )


def aggregate_weekly(frame: pl.DataFrame) -> pl.DataFrame:
    return (
        frame.with_columns(pl.col("date").dt.truncate("1w").alias("week"))
        .group_by(["week", "state", "city", "product"])
        .agg(
            pl.mean("price").alias("avg_price"),
            pl.std("price").fill_null(0.0).alias("volatility"),
            pl.mean("price_buy").alias("avg_buy_price"),
            pl.mean("dollar").alias("dollar"),
            pl.mean("brent").alias("brent"),
            pl.mean("ipca").alias("ipca"),
            pl.n_unique("brand").alias("brand_count"),
        )
        .sort(["product", "state", "city", "week"])
    )


def write_partitioned_parquet(frame: pl.DataFrame, curated_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for (product, state), chunk in frame.partition_by(["product", "state"], as_dict=True).items():
        target_dir = curated_dir / f"product={product}" / f"state={state}"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "weekly.parquet"
        chunk.write_parquet(target, compression="zstd")
        paths.append(target)
    return paths
