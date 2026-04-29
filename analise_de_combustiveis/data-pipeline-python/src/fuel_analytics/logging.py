from __future__ import annotations

import os
import sys
from pathlib import Path

from loguru import logger

from fuel_analytics.config import settings


def configure_logging() -> None:
    log_level = os.getenv("FUEL_LOG_LEVEL", "INFO").upper()
    logs_dir = settings.project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        colorize=True,
        backtrace=False,
        diagnose=False,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )
    logger.add(
        Path(logs_dir) / "pipeline.log",
        level=log_level,
        rotation="10 MB",
        retention="10 days",
        compression="zip",
        enqueue=True,
        backtrace=False,
        diagnose=False,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )


__all__ = ["configure_logging", "logger"]

