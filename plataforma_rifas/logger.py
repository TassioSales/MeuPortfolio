from __future__ import annotations

from pathlib import Path
from loguru import logger as _logger

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "log"

try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"Erro ao criar diretório de logs: {e}")

LOG_FILE = LOG_DIR / "app.log"

_logger.remove()

_logger.add(
    sink="stderr",
    level="INFO",
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <yellow>{extra[username]}</yellow> - <level>{message}</level>",
    enqueue=True,
)

_logger.add(
    LOG_FILE,
    rotation="10 MB",
    retention="14 days",
    encoding="utf-8",
    level="DEBUG",
    enqueue=True,
    backtrace=True,
    diagnose=True,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {extra[username]} - {message}",
)

logger = _logger.bind(username="unknown")

def add_user_context(username: str):
    """Adiciona contexto de usuário ao logger."""
    global logger
    logger = _logger.bind(username=username)
