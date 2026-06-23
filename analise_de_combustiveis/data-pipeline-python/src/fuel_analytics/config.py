from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class Settings(BaseModel):
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3])
    data_lake_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3] / "data-lake")
    raw_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3] / "data-lake" / "raw")
    curated_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[3] / "data-lake" / "curated"
    )
    warehouse_path: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[3] / "data-lake" / "warehouse" / "fuel_analytics.duckdb"
    )
    models_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3] / "models")
    forecast_horizon_days: int = 15
    chunk_rows: int = 100_000

    # ── BasedosDados / BigQuery (opcional) ─────────────────────────────────
    # Defina GCP_BILLING_PROJECT no .env ou variavel de ambiente para ativar
    # microdados por posto (muito mais ricos que os CSVs agregados da ANP)
    gcp_billing_project: Optional[str] = Field(
        default_factory=lambda: (
            os.environ.get("GCP_BILLING_PROJECT")
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
        )
    )
    # Anos a consultar no BigQuery (reduz custo filtrando por periodo)
    gcp_years: list[int] = Field(
        default_factory=lambda: [
            int(y) for y in os.environ.get("GCP_YEARS", "2023,2024,2025").split(",")
            if y.strip().isdigit()
        ]
    )
    # Limite de linhas por query (seguranca de custo)
    gcp_limit: int = Field(
        default_factory=lambda: int(os.environ.get("GCP_LIMIT", "5000000"))
    )


settings = Settings()
