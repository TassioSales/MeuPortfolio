"""Logger setup for L'Aquila AI Backend."""

import sys
import os
from loguru import logger as _logger

from app.config import settings


def configure_logger():
    """Configure loguru logger with file and console outputs."""
    # Remove default handler
    _logger.remove()

    # Console handler
    _logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True,
    )

    # File handler
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    _logger.add(
        f"{log_dir}/app.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.log_level,
        rotation="500 MB",
        retention="7 days",
        encoding="utf-8",
    )

    # Error file handler
    _logger.add(
        f"{log_dir}/error.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="500 MB",
        retention="7 days",
        encoding="utf-8",
    )

    return _logger


logger = configure_logger()
