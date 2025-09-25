from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

from loguru import logger as _logger

# Configurações de ambiente
ENV = os.getenv("ENV", "development").lower()
IS_PRODUCTION = ENV == "production"

# Configurações de diretório
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"

# Cria o diretório de logs se não existir
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"❌ Erro crítico ao criar diretório de logs: {str(e)} - Verifique permissões do diretório.", file=sys.stderr)
    sys.exit(1)

# Configuração de níveis de log
LOG_LEVEL = "DEBUG" if not IS_PRODUCTION else "INFO"
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<yellow>{extra[username]}</yellow> | <magenta>{extra[user_id]}</magenta> - <level>{message}</level>"
)

# Configuração do arquivo de log
LOG_FILE = LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
LOG_ROTATION = "10 MB"
LOG_RETENTION = "30 days" if IS_PRODUCTION else "7 days"

# Remove handlers padrão para evitar duplicação
_logger.remove()

# Configuração do handler para console
_logger.add(
    sink=sys.stderr,
    level=LOG_LEVEL,
    colorize=True,
    format=LOG_FORMAT,
    enqueue=True,
    backtrace=True,
    diagnose=not IS_PRODUCTION,
)

# Configuração do handler para arquivo
_logger.add(
    sink=LOG_FILE,
    level="DEBUG",
    rotation=LOG_ROTATION,
    retention=LOG_RETENTION,
    encoding="utf-8",
    enqueue=True,
    backtrace=True,
    diagnose=not IS_PRODUCTION,
    format=(
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} | {extra[username]} | {extra[user_id]} - {message}"
    ),
)

# Handler para erros críticos (ex: simula envio de email ou notificação)
def critical_handler(record):
    if record["level"].name == "CRITICAL":
        # Aqui pode integrar com email/Slack, etc. Por enquanto, loga extra.
        print(f"🚨 NOTIFICAÇÃO CRÍTICA: {record['message']}", file=sys.stderr)

_logger.add(critical_handler, level="CRITICAL")

# Adiciona um filtro para logs de requisições (opcional) e evita duplicados
def request_filter(record):
    if "request" in record["extra"] and record["extra"].get("duplicated", False):
        return False
    return "request" not in record["extra"]

_logger = _logger.bind(username="system", user_id="none")

class Logger:
    """Logger wrapper com métodos adicionais para facilitar o uso."""
    
    def __init__(self, module_name: str):
        self.logger = _logger.bind(module=module_name)
    
    def debug(self, message: str, **kwargs):
        """Log de depuração (nível DEBUG)."""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log informativo (nível INFO)."""
        self.logger.info(message, **kwargs)
    
    def success(self, message: str, **kwargs):
        """Log de sucesso (nível INFO com tag SUCCESS)."""
        self.logger.info(f"SUCCESS: {message}", **kwargs)
    
    def warning(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log de aviso (nível WARNING)."""
        if exception:
            message = f"{message} | Exception: {str(exception)}"
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log de erro (nível ERROR)."""
        if exception:
            exc_info = (type(exception), exception, exception.__traceback__)
            message = f"{message} | Exception: {str(exception)} | Traceback: {traceback.format_exc()}"
            self.logger.opt(exception=exc_info).error(message, **kwargs)
        else:
            self.logger.error(message, **kwargs)
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log crítico (nível CRITICAL)."""
        if exception:
            exc_info = (type(exception), exception, exception.__traceback__)
            message = f"{message} | Exception: {str(exception)} | Traceback: {traceback.format_exc()}"
            self.logger.opt(exception=exc_info).critical(message, **kwargs)
        else:
            self.logger.critical(message, **kwargs)
    
    def exception(self, message: str, exception: Exception, **kwargs):
        """Log de exceção com stack trace completo."""
        self.error(message, exception=exception, **kwargs)
    
    def log_http_request(self, request_data: Dict[str, Any], **kwargs):
        """Log estruturado para requisições HTTP."""
        log_data = {
            "method": request_data.get("method", "UNKNOWN"),
            "url": request_data.get("url", ""),
            "status_code": request_data.get("status_code"),
            "response_time": request_data.get("response_time"),
            "client_ip": request_data.get("client_ip"),
        }
        self.info("HTTP Request", request=log_data, **kwargs)

def get_logger(module_name: str) -> Logger:
    """Retorna uma instância do logger para o módulo especificado."""
    return Logger(module_name)

def add_user_context(username: str, user_id: Optional[str] = None):
    """Adiciona contexto de usuário ao logger global."""
    _logger.bind(username=username, user_id=user_id or "none")

def log_exceptions():
    """Decorator para capturar e logar exceções não tratadas."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger = get_logger(func.__module__)
                logger.exception(
                    f"Exceção não tratada em {func.__name__} | Args: {args} | Kwargs: {kwargs}",
                    exception=e,
                    function=func.__name__,
                    module=func.__module__,
                )
                raise
        return wrapper
    return decorator

# Logger global para uso direto (módulos antigos)
logger = _logger

# Exemplo de uso:
# from logger import get_logger
# logger = get_logger(__name__)
# logger.info("Mensagem informativa")
# logger.error("Ocorreu um erro", exception=e)