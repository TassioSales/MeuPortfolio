from __future__ import annotations

from pathlib import Path

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


settings = Settings()
