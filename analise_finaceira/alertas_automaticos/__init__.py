from flask import Blueprint
from flask import current_app
import os
import sys
from pathlib import Path
from datetime import datetime

# Adicionar o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger

# Configurar logger
logger = get_logger('alertas_automaticos')

# Criar o blueprint
bp = Blueprint(
    'alertas_automaticos',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/alertas_automaticos/static'
)

def format_datetime(value, format='%d/%m/%Y %H:%M'):
    """Filtro para formatar datas no template."""
    if value is None:
        return ""
    if isinstance(value, str):
        # Tenta converter a string para datetime
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            try:
                value = datetime.fromisoformat(value)
            except (ValueError, TypeError):
                return value
    try:
        return value.strftime(format)
    except (AttributeError, ValueError):
        return value

def create_blueprint():
    # Registrar filtro personalizado
    @bp.app_template_filter('strftime')
    def _jinja2_filter_strftime(date, fmt=None):
        """Filtro para formatar datas no template."""
        return format_datetime(date, fmt)
    
    # Importar rotas aqui para evitar importação circular
    try:
        from . import routes
        logger.info("Blueprint de alertas automáticos criado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao importar rotas do blueprint de alertas automáticos: {str(e)}")
        raise
    return bp
