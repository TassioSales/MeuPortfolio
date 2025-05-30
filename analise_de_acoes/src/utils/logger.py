import os
import sys
from loguru import logger
from pathlib import Path
from ..config.settings import LOG_LEVEL, LOG_FILE

# Ensure log directory exists
log_path = Path(LOG_FILE)
log_path.parent.mkdir(parents=True, exist_ok=True)

# Remove default logger
logger.remove()

# Add console logger
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Add file logger
logger.add(
    LOG_FILE,
    rotation="500 MB",
    retention="10 days",
    level=LOG_LEVEL.upper(),
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    enqueue=True,
    backtrace=True,
    diagnose=True
)

# Example usage:
# from ..utils.logger import logger
# logger.debug("Debug message")
# logger.info("Info message")
# logger.warning("Warning message")
# logger.error("Error message")
# logger.critical("Critical message")
