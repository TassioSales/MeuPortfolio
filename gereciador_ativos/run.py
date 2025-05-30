"""
Script para executar a aplicação localmente em modo de desenvolvimento.
"""
import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(str(Path(__file__).parent))

from src.main import app
from src.utils.logger import get_logger

# Configura o logger
logger = get_logger(__name__)

if __name__ == "__main__":
    try:
        # Configurações de desenvolvimento
        os.environ["FLASK_ENV"] = "development"
        os.environ["FLASK_DEBUG"] = "True"
        
        logger.info("Iniciando aplicação em modo de desenvolvimento...")
        logger.info(f"FLASK_ENV: {os.getenv('FLASK_ENV')}")
        logger.info(f"FLASK_DEBUG: {os.getenv('FLASK_DEBUG')}")
        
        # Executa a aplicação
        app.run(debug=True, host='0.0.0.0', port=5000)
        
    except Exception as e:
        logger.critical("Erro ao iniciar a aplicação", exc_info=True)
        sys.exit(1)
