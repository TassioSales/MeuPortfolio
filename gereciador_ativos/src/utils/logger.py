"""
Módulo de configuração do Loguru para gerenciamento de logs da aplicação.
"""
import os
import sys
from datetime import datetime
from pathlib import Path
from loguru import logger as log

# Cria o diretório de logs se não existir
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Configura o formato do log
log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# Configuração padrão do logger
log.remove()  # Remove o handler padrão

# Adiciona saída para console
log.add(
    sys.stderr,
    format=log_format,
    level="INFO",
    colorize=True,
    backtrace=True,
    diagnose=True
)

# Adiciona saída para arquivo com rotação
log.add(
    LOG_DIR / "app_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    format=log_format,
    level="DEBUG",
    encoding="utf-8",
    backtrace=True,
    diagnose=True
)

# Configuração para arquivo de erros separado
log.add(
    LOG_DIR / "error_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    format=log_format,
    level="ERROR",
    encoding="utf-8",
    backtrace=True,
    diagnose=True
)

def get_logger(name: str = None):
    """
    Retorna uma instância do logger configurado.
    
    Args:
        name (str, optional): Nome do módulo. Se não informado, usará o nome do módulo chamador.
        
    Returns:
        Logger: Instância do logger configurado.
    """
    if name:
        return log.bind(module=name)
    return log

# Exemplo de uso:
# from src.utils.logger import get_logger
# logger = get_logger(__name__)
# logger.info("Mensagem informativa")
# logger.error("Ocorreu um erro", exc_info=True)
