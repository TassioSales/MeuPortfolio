"""
Módulo de logging para o sistema PDV.
Utiliza Loguru para gerenciar logs em arquivo e console.
"""
import os
import sys
from pathlib import Path
from loguru import logger as log
from datetime import datetime

def configure_logger():
    """Configura o sistema de logging."""
    # Cria o diretório de logs se não existir
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Remove o handler padrão do stderr
    log.remove()
    
    # Configura o formato do log
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    
    # Adiciona handler para arquivo com rotação diária
    log.add(
        log_dir / "app.log",
        rotation="1 day",
        retention="30 days",
        level="INFO",
        format=log_format,
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=True
    )
    
    # Adiciona handler para console
    log.add(
        sys.stderr,
        level="INFO",
        format=log_format,
        colorize=True,
        enqueue=True,
        backtrace=True,
        diagnose=True
    )
    
    log.info("Logger configurado com sucesso")
    return log

# Configura o logger ao importar o módulo
logger = configure_logger()

if __name__ == "__main__":
    # Teste do logger
    logger.debug("Mensagem de debug")
    logger.info("Mensagem informativa")
    logger.warning("Aviso importante")
    logger.error("Erro crítico")
