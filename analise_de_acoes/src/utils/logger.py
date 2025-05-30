import os
import sys
from loguru import logger
from pathlib import Path
from ..config.settings import LOG_LEVEL, LOG_FILE

def setup_logger(name, log_file=None, level=LOG_LEVEL.upper()):
    """Configura e retorna um logger personalizado.
    
    Args:
        name (str): Nome do logger
        log_file (str, optional): Caminho para o arquivo de log. Se None, usa o padrão.
        level (str, optional): Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        logger: Instância do logger configurado
    """
    # Cria um novo logger com o nome fornecido
    logger_instance = logger.bind(name=name)
    
    # Remove handlers existentes
    logger_instance.remove()
    
    # Configura o formato do log para incluir o nome do módulo
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    
    # Adiciona handler para console
    logger_instance.add(
        sys.stderr,
        format=log_format,
        level=level,
        colorize=True
    )
    
    # Se um arquivo de log for especificado, adiciona handler para arquivo
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger_instance.add(
            str(log_path),
            rotation="500 MB",
            retention="10 days",
            level=level,
            format=(
                "{time:YYYY-MM-DD HH:mm:ss} | "
                "{level: <8} | "
                "{name}:{function}:{line} - {message}"
            ),
            enqueue=True,
            backtrace=True,
            diagnose=True
        )
    
    return logger_instance

# Configuração do logger padrão
log_path = Path(LOG_FILE)
log_path.parent.mkdir(parents=True, exist_ok=True)

# Remove default logger
logger.remove()

# Formato do log
console_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

file_format = (
    "{time:YYYY-MM-DD HH:mm:ss} | "
    "{level: <8} | "
    "{name}:{function}:{line} - {message}"
)

# Add console logger
logger.add(
    sys.stderr,
    format=console_format,
    level=LOG_LEVEL.upper(),
    colorize=True
)

# Add file logger
logger.add(
    str(log_path),
    rotation="500 MB",
    retention="10 days",
    level=LOG_LEVEL.upper(),
    format=file_format,
    enqueue=True,
    backtrace=True,
    diagnose=True,
    encoding='utf-8'
)

# Exemplo de uso:
# from ..utils.logger import setup_logger
# logger = setup_logger('meu_modulo', 'meu_arquivo.log')
# logger.info("Mensagem de informação")
