from __future__ import annotations

from pathlib import Path

import polars as pl

from fuel_analytics.clients.anp import ANPClient
from fuel_analytics.logging import logger

MONTH_MAP = {
    "JAN": 1,
    "FEV": 2,
    "MAR": 3,
    "ABR": 4,
    "MAI": 5,
    "JUN": 6,
    "JUL": 7,
    "AGO": 8,
    "SET": 9,
    "OUT": 10,
    "NOV": 11,
    "DEZ": 12,
}

PRODUCT_ALIASES = {
    "ETANOL HIDRATADO": "etanol",
    "GASOLINA C": "gasolina",
    "GASOLINA AUTOMOTIVA": "gasolina",
    "GLP": "glp",
    "ÓLEO DIESEL": "diesel",
    "OLEO DIESEL": "diesel",
    "ÓLEO DIESEL B": "diesel",
    "GNV": "gnv",
    "GÁS NATURAL VEICULAR": "gnv",
    "GAS NATURAL VEICULAR": "gnv",
}

STATE_ALIASES = {
    "ACRE": "AC",
    "ALAGOAS": "AL",
    "AMAPA": "AP",
    "AMAPÁ": "AP",
    "AMAZONAS": "AM",
    "BAHIA": "BA",
    "CEARA": "CE",
    "CEARÁ": "CE",
    "DISTRITO FEDERAL": "DF",
    "ESPIRITO SANTO": "ES",
    "ESPÍRITO SANTO": "ES",
    "GOIAS": "GO",
    "GOIÁS": "GO",
    "MARANHAO": "MA",
    "MARANHÃO": "MA",
    "MATO GROSSO": "MT",
    "MATO GROSSO DO SUL": "MS",
    "MINAS GERAIS": "MG",
    "PARA": "PA",
    "PARÁ": "PA",
    "PARAIBA": "PB",
    "PARAÍBA": "PB",
    "PARANA": "PR",
    "PARANÁ": "PR",
    "PERNAMBUCO": "PE",
    "PIAUI": "PI",
    "PIAUÍ": "PI",
    "RIO DE JANEIRO": "RJ",
    "RIO GRANDE DO NORTE": "RN",
    "RIO GRANDE DO SUL": "RS",
    "RONDONIA": "RO",
    "RONDÔNIA": "RO",
    "RORAIMA": "RR",
    "SANTA CATARINA": "SC",
    "SAO PAULO": "SP",
    "SÃO PAULO": "SP",
    "SERGIPE": "SE",
    "TOCANTINS": "TO",
}


def load_market_datasets(raw_dir: Path) -> tuple[pl.DataFrame, pl.DataFrame]:
    client = ANPClient()
    sales = load_sales_dataset(client, raw_dir / "sales")
    processing = load_processing_dataset(client, raw_dir / "processing")
    if sales.height == 0 or processing.height == 0:
        raise RuntimeError("Official market sources returned empty frames")
    logger.info(
        "Loaded official market datasets: sales_rows={} processing_rows={}",
        sales.height,
        processing.height,
    )
    return sales, processing


def load_sales_dataset(client: ANPClient, raw_dir: Path) -> pl.DataFrame:
    files = client.list_sales_files()
    candidates = [item for item in files if "vendas-combustiveis-m3" in item.label.lower()]
    if not candidates:
        raise RuntimeError("Sales dataset link not found on ANP page")
    paths = client.download_files(candidates[:1], raw_dir)
    logger.info("Reading sales dataset from {}", paths[0])
    raw = _read_any_table(paths[0], separator=";")
    logger.info("Sales raw columns: {}", raw.columns)
    return normalize_sales_frame(raw)


def load_processing_dataset(client: ANPClient, raw_dir: Path) -> pl.DataFrame:
    files = client.list_processing_files()
    processing_candidates = [
        item
        for item in files
        if "processamento-petroleo" in item.label.lower() or "processamento" in item.label.lower()
    ]
    production_candidates = [
        item
        for item in files
        if "producao" in item.label.lower() and "refinaria" in item.label.lower()
    ]
    if not production_candidates:
        production_candidates = [
            item
            for item in files
            if "producao" in item.label.lower() and "derivados" in item.label.lower()
        ]
    if not processing_candidates or not production_candidates:
        raise RuntimeError("Processing dataset links not found on ANP page")

    processing_path = client.download_files(processing_candidates[:1], raw_dir)[0]
    production_path = client.download_files(production_candidates[:1], raw_dir)[0]
    logger.info("Reading processing dataset from {}", processing_path)
    processing_raw = _read_any_table(processing_path, separator=";")
    logger.info("Reading production dataset from {}", production_path)
    production_raw = _read_any_table(production_path, separator=";")
    logger.info("Processing raw columns: {}", processing_raw.columns)
    logger.info("Production raw columns: {}", production_raw.columns)
    return normalize_processing_frame(processing_raw, production_raw)


def _read_any_table(path: Path, separator: str = ",") -> pl.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pl.read_csv(path, separator=separator, infer_schema_length=1000, try_parse_dates=True)
    if suffix in {".xls", ".xlsx"}:
        return pl.read_excel(path)
    raise ValueError(f"Formato nao suportado: {path}")


def normalize_sales_frame(frame: pl.DataFrame) -> pl.DataFrame:
    renamed = frame.rename(
        {
            column: _normalize_column_name(column)
            for column in frame.columns
        }
    )
    month_expr = (
        pl.col("mes")
        .cast(pl.Utf8)
        .str.to_uppercase()
        .map_elements(lambda value: MONTH_MAP.get((value or "").upper(), 1), return_dtype=pl.Int64)
        .cast(pl.Int64)
    )
    sales_expr = _numeric_expr("vendas")
    product_expr = _product_expr(pl.col("produto"))
    state_expr = _state_expr(pl.col("unidade_da_federacao"))
    return (
        renamed.with_columns(
            pl.date(pl.col("ano").cast(pl.Int64), month_expr, pl.lit(1)).alias("date"),
            state_expr.alias("state"),
            product_expr.alias("product"),
            sales_expr.alias("sales_volume_m3"),
            pl.lit("distribuicao").alias("segment"),
        )
        .select(["date", "state", "product", "sales_volume_m3", "segment"])
        .drop_nulls(["date", "state", "product", "sales_volume_m3"])
        .filter(pl.col("product").is_in(["gasolina", "etanol", "diesel", "gnv"]))
    )


def normalize_processing_frame(processing_frame: pl.DataFrame, production_frame: pl.DataFrame) -> pl.DataFrame:
    processing = processing_frame.rename(
        {column: _normalize_column_name(column) for column in processing_frame.columns}
    )
    production = production_frame.rename(
        {column: _normalize_column_name(column) for column in production_frame.columns}
    )

    processing_norm = processing.with_columns(
        _date_from_year_month(processing).alias("date"),
        _refinery_expr(processing).alias("refinery"),
        _numeric_expr(_guess_numeric_column(processing, ("volume", "process", "refinad", "carga"))).alias("processed_m3"),
    ).select(["date", "refinery", "processed_m3"])

    production_norm = production.with_columns(
        _date_from_year_month(production).alias("date"),
        _product_expr(_guess_product_column(production)).alias("product"),
        _refinery_expr(production).alias("refinery"),
        _numeric_expr(_guess_numeric_column(production, ("volume", "produ", "derivad"))).alias("produced_m3"),
    ).select(["date", "refinery", "product", "produced_m3"])

    processing_totals = (
        processing_norm.group_by("date")
        .agg(pl.sum("processed_m3").alias("processed_m3"))
        .sort("date")
    )
    production_totals = (
        production_norm.group_by(["date", "product"])
        .agg(pl.sum("produced_m3").alias("produced_m3"))
        .sort(["date", "product"])
    )
    merged = production_totals.join(processing_totals, on="date", how="left")
    logger.info("Normalized processing dataset rows={}", merged.height)
    return merged.drop_nulls(["date", "product"]).with_columns(
        pl.col("processed_m3").fill_null(0.0),
        pl.col("produced_m3").fill_null(0.0),
    )


def _normalize_column_name(column: str) -> str:
    cleaned = (
        column.strip()
        .lower()
        .replace("ã", "a")
        .replace("á", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace("(", "")
        .replace(")", "")
    )
    return cleaned


def _date_from_year_month(frame: pl.DataFrame) -> pl.Expr:
    columns = set(frame.columns)
    if "date" in columns:
        return pl.col("date").cast(pl.Date)
    if {"ano", "mes"}.issubset(columns):
        month_expr = (
            pl.col("mes")
            .cast(pl.Utf8)
            .str.to_uppercase()
            .map_elements(lambda value: MONTH_MAP.get((value or "").upper(), 1), return_dtype=pl.Int64)
            .cast(pl.Int64)
        )
        return pl.date(pl.col("ano").cast(pl.Int64), month_expr, pl.lit(1))
    if {"ano", "mes_referencia"}.issubset(columns):
        return pl.date(pl.col("ano").cast(pl.Int64), pl.col("mes_referencia").cast(pl.Int64), pl.lit(1))
    raise ValueError("Nao foi possivel inferir colunas de data para dataset mensal")


def _guess_product_column(frame: pl.DataFrame) -> pl.Expr:
    for name in frame.columns:
        if "produto" in name:
            return pl.col(name)
    raise ValueError("Nao foi possivel encontrar coluna de produto")


def _guess_numeric_column(frame: pl.DataFrame, keywords: tuple[str, ...]) -> str:
    prioritized: list[str] = []
    for name in frame.columns:
        if "produto" in name:
            continue
        if any(keyword in name for keyword in keywords):
            prioritized.append(name)
    if prioritized:
        prioritized.sort(key=lambda value: ("produc" not in value and "process" not in value, value))
        return prioritized[0]
    raise ValueError(f"Nao foi possivel encontrar coluna numerica para {keywords}")


def _refinery_expr(frame: pl.DataFrame) -> pl.Expr:
    for name in frame.columns:
        if "refinaria" in name or "unidade" in name:
            return pl.col(name).cast(pl.Utf8)
    return pl.lit("NACIONAL")


def _product_expr(col: pl.Expr) -> pl.Expr:
    return col.cast(pl.Utf8).str.to_uppercase().map_elements(_normalize_product_name, return_dtype=pl.Utf8)


def _state_expr(col: pl.Expr) -> pl.Expr:
    return (
        col.cast(pl.Utf8)
        .str.extract(r"\(([A-Z]{2})\)$", group_index=1)
        .fill_null(col.cast(pl.Utf8).str.to_uppercase().map_elements(_normalize_state_name, return_dtype=pl.Utf8))
    )


def _numeric_expr(column_name: str) -> pl.Expr:
    return (
        pl.col(column_name)
        .cast(pl.Utf8)
        .str.replace_all(r"\.", "")
        .str.replace(",", ".")
        .cast(pl.Float64, strict=False)
    )


def _normalize_product_name(value: str | None) -> str:
    raw = (value or "").strip().upper()
    if raw in PRODUCT_ALIASES:
        return PRODUCT_ALIASES[raw]
    if "GLP" in raw:
        return "glp"
    if "ETANOL" in raw:
        return "etanol"
    if "GASOLINA" in raw and "AVIA" not in raw:
        return "gasolina"
    if "DIESEL" in raw:
        return "diesel"
    if "GNV" in raw or "GAS NATURAL VEICULAR" in raw or "GÁS NATURAL VEICULAR" in raw:
        return "gnv"
    return raw.lower()


def _normalize_state_name(value: str | None) -> str:
    raw = (value or "").strip().upper()
    if raw in STATE_ALIASES:
        return STATE_ALIASES[raw]
    if len(raw) == 2:
        return raw
    return raw[:2]


def build_market_signals(sales: pl.DataFrame, processing: pl.DataFrame) -> pl.DataFrame:
    logger.info("Building market signals with sales_rows={} processing_rows={}", sales.height, processing.height)
    sales_monthly = (
        sales.with_columns(
            pl.col("date").cast(pl.Date).dt.truncate("1mo").alias("month"),
            pl.col("state").cast(pl.Utf8).str.to_uppercase().alias("state"),
            pl.col("product").cast(pl.Utf8).str.to_lowercase().alias("product"),
        )
        .group_by(["month", "state", "product"])
        .agg(pl.sum("sales_volume_m3").alias("sales_volume_m3"))
    )
    processing_monthly = (
        processing.with_columns(
            pl.col("date").cast(pl.Date).dt.truncate("1mo").alias("month"),
            pl.col("product").cast(pl.Utf8).str.to_lowercase().alias("product"),
        )
        .group_by(["month", "product"])
        .agg(
            pl.max("processed_m3").alias("processed_m3"),
            pl.sum("produced_m3").alias("produced_m3"),
        )
    )
    joined = sales_monthly.join(processing_monthly, on=["month", "product"], how="left").with_columns(
        (pl.col("produced_m3") / pl.col("sales_volume_m3")).fill_null(0.0).round(3).alias("supply_demand_ratio"),
        (pl.col("processed_m3") - pl.col("produced_m3")).fill_null(0.0).alias("refinery_gap_m3"),
        pl.when(pl.col("produced_m3") >= pl.col("sales_volume_m3"))
        .then(pl.lit("balanced"))
        .when(pl.col("produced_m3") >= pl.col("sales_volume_m3") * 0.85)
        .then(pl.lit("tight"))
        .otherwise(pl.lit("stressed"))
        .alias("market_regime"),
    )
    logger.info("Market signals built with {} rows", joined.height)
    return joined.sort(["product", "state", "month"])


def persist_market_signals(frame: pl.DataFrame, models_dir: Path) -> Path:
    models_dir.mkdir(parents=True, exist_ok=True)
    destination = models_dir / "market_signals.json"
    destination.write_text(frame.write_json(), encoding="utf-8")
    return destination
