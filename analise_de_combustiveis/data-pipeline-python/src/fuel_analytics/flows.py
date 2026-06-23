from __future__ import annotations

from pathlib import Path

import polars as pl
from dotenv import load_dotenv
from prefect import flow, task

load_dotenv()  # carrega .env antes de ler settings

from fuel_analytics.clients.anp import ANPClient
from fuel_analytics.config import settings
from fuel_analytics.forecasting import forecast_series
from fuel_analytics.logging import logger
from fuel_analytics.market import build_market_signals, load_market_datasets, persist_market_signals
from fuel_analytics.processing import (
    aggregate_weekly,
    enrich_with_external_features,
    normalize_frame,
    write_partitioned_parquet,
)
from fuel_analytics.storage import (
    build_warehouse,
    persist_api_snapshots,
    persist_explorer_snapshot,
    persist_forecasts,
)


def _read_price_csv(path: Path) -> pl.DataFrame:
    return pl.read_csv(
        path,
        separator=";",
        encoding="utf8-lossy",
        infer_schema_length=5000,
        ignore_errors=True,
        truncate_ragged_lines=True,
        try_parse_dates=False,
    )


@task
def ingest_anp(per_series_limit: int = 2) -> pl.DataFrame:
    logger.info("Starting ANP ingestion with per-series file limit={}", per_series_limit)
    client = ANPClient()
    files = client.select_price_files(client.list_csv_files(), per_series=per_series_limit)
    paths = client.download_files(files, settings.raw_dir)
    frames: list[pl.DataFrame] = []
    for target, path in zip(files, paths, strict=False):
        try:
            frame = _read_price_csv(path)
            if frame.height == 0:
                raise RuntimeError("empty frame after CSV parse")
            logger.info("Loaded raw file {} with {} rows", path.name, frame.height)
            frames.append(frame)
        except Exception as exc:
            logger.warning("Cached ANP file {} failed validation, retrying download: {}", path, exc)
            try:
                refreshed = client.redownload_file(target, settings.raw_dir)
                frame = _read_price_csv(refreshed)
                if frame.height == 0:
                    raise RuntimeError("empty frame after retry")
                logger.info("Loaded refreshed raw file {} with {} rows", refreshed.name, frame.height)
                frames.append(frame)
            except Exception as retry_exc:
                logger.exception("Failed to load raw ANP file {} after retry: {}", path, retry_exc)
                continue
    if not frames:
        logger.error("ANP ingestion produced zero readable files")
        raise RuntimeError("Nenhum arquivo da ANP pode ser lido no momento.")
    merged = pl.concat(frames, how="diagonal_relaxed")
    logger.info("ANP ingestion completed with {} consolidated rows", merged.height)
    return merged


@task
def curate(frame: pl.DataFrame) -> tuple[list[Path], pl.DataFrame]:
    logger.info("Starting curation step with {} input rows", frame.height)
    normalized = normalize_frame(frame)
    logger.info("Normalization completed with {} rows", normalized.height)
    enriched = enrich_with_external_features(normalized)
    weekly = aggregate_weekly(enriched)
    paths = write_partitioned_parquet(weekly, settings.curated_dir)
    logger.info("Curation completed with {} weekly rows and {} parquet partitions", weekly.height, len(paths))
    return paths, weekly


@task
def train_forecasts(weekly: pl.DataFrame) -> Path:
    logger.info("Starting forecast training for {} weekly rows", weekly.height)
    forecasts: dict[str, list[dict]] = {}
    for keys, chunk in weekly.partition_by(["product", "state"], as_dict=True).items():
        product, state = keys
        logger.debug("Training forecast for product={} state={} with {} rows", product, state, chunk.height)
        forecasts[f"{product}:{state}"] = forecast_series(chunk, settings.forecast_horizon_days)
    destination = persist_forecasts(forecasts, settings.models_dir)
    logger.info("Forecast artifacts persisted to {}", destination)
    return destination


@task
def materialize_market_signals() -> Path:
    logger.info("Loading supplemental demand and processing datasets")
    sales, processing = load_market_datasets(settings.raw_dir)
    signals = build_market_signals(sales, processing)
    destination = persist_market_signals(signals, settings.models_dir)
    logger.info("Market signals persisted to {}", destination)
    return destination


@flow(name="fuel-bootstrap")
def bootstrap_flow() -> int:
    logger.info("Bootstrapping pipeline with official ANP sources")
    frame = ingest_anp()
    logger.info("Bootstrap finished with {} rows", frame.height)
    return frame.height


@task
def ingest_basedosdados_task() -> pl.DataFrame:
    from fuel_analytics.clients.basedosdados_client import ingest_basedosdados
    logger.info(
        "Ingest via BasedosDados microdados (billing={})", settings.gcp_billing_project
    )
    return ingest_basedosdados(
        settings.gcp_billing_project,  # type: ignore[arg-type]
        years=settings.gcp_years,
        limit=settings.gcp_limit,
    )


@flow(name="fuel-analytics-pipeline")
def pipeline_flow() -> dict[str, str]:
    if settings.gcp_billing_project:
        logger.info(
            "GCP billing project detectado — usando BasedosDados microdados (mais ricos)"
        )
        frame = ingest_basedosdados_task()
    else:
        logger.info("Sem GCP billing project — usando download direto ANP CSV")
        frame = ingest_anp()
    parquet_paths, weekly = curate(frame)
    logger.info("Building DuckDB warehouse at {}", settings.warehouse_path)
    actual_warehouse_path = build_warehouse(parquet_paths, settings.warehouse_path)
    logger.info("Warehouse materialized at {}", actual_warehouse_path)
    snapshot_paths = persist_api_snapshots(actual_warehouse_path, settings.models_dir)
    explorer_path = persist_explorer_snapshot(actual_warehouse_path, settings.models_dir)
    forecast_path = train_forecasts(weekly)
    market_path = materialize_market_signals()
    result = {
        "warehouse": str(actual_warehouse_path),
        "overview": str(snapshot_paths["overview"]),
        "history": str(snapshot_paths["history"]),
        "fuels": str(snapshot_paths["fuels"]),
        "explorer": str(explorer_path),
        "forecast": str(forecast_path),
        "market": str(market_path),
        "rows": str(weekly.height),
    }
    logger.info("Pipeline finished successfully: {}", result)
    return result


if __name__ == "__main__":
    from fuel_analytics.logging import configure_logging
    configure_logging()
    try:
        result = pipeline_flow()
        logger.info("Resultado final: {}", result)
    except Exception as exc:
        logger.exception("Pipeline falhou: {}", exc)
        raise
