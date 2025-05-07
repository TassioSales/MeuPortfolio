from flask import Blueprint
import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger

# Configura o logger para o módulo de upload
log = get_logger("upload")
log.info("Iniciando módulo de upload")

# Configuração do blueprint
upload_bp = Blueprint(
    'upload',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static/upload'
)

# Importa as rotas após a criação do blueprint para evitar importação circular
from . import routes