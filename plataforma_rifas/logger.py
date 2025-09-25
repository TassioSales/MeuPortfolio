from __future__ import annotations

from pathlib import Path
from loguru import logger as _logger

# Ensure log directory exists
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "log"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure log file
LOG_FILE = LOG_DIR / "app.log"

# Remove default handler to avoid duplicate logs in some environments
_logger.remove()

# Console handler (info+)
_logger.add(
    sink=lambda msg: print(msg, end=""),
    level="INFO",
    colorize=True,
    enqueue=True,
)

# File handler with rotation and retention
_logger.add(
    LOG_FILE,
    rotation="10 MB",
    retention="14 days",
    encoding="utf-8",
    level="DEBUG",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)

logger = _logger
