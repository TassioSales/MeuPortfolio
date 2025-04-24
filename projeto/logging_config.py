import logging
import sys

# Formato customizado para logs mais informativos e organizados
LOG_FORMAT = (
    "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
)

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt="%d/%m/%Y %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)

def get_logger(name):
    return logging.getLogger(name)
