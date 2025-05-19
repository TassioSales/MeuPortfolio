import os
import sys
from pathlib import Path
from typing import Optional, Any
from flask import Blueprint, send_from_directory, current_app, send_file, abort

# Adiciona o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Importa o módulo logger e configura o logger
from logger import get_logger, log_function, setup_logger

# Configura o logger para este módulo
logger = setup_logger("dashboard.blueprint") if 'setup_logger' in globals() else get_logger("dashboard.blueprint")

dashboard_bp = Blueprint('dashboard', __name__,
    template_folder=os.path.join(root_dir, 'dashboard_arq', 'templates'),
    static_folder=os.path.join(root_dir, 'dashboard_arq', 'static'))

@log_function()
def get_base_directories() -> tuple[str, str, str]:
    """
    Obtém os diretórios base do projeto.
    
    Returns:
        tuple: (base_dir, template_dir, static_dir)
    """
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        template_dir = os.path.join(base_dir, 'dashboard_arq', 'templates')
        static_dir = os.path.join(base_dir, 'dashboard_arq', 'static')
        
        logger.debug(f"Diretório base: {base_dir}")
        logger.debug(f"Diretório de templates: {template_dir}")
        logger.debug(f"Diretório estático: {static_dir}")
        
        # Verificar se os diretórios existem
        if not os.path.exists(template_dir):
            logger.warning(f"Diretório de templates não encontrado: {template_dir}")
        if not os.path.exists(static_dir):
            logger.warning(f"Diretório estático não encontrado: {static_dir}")
            
        return base_dir, template_dir, static_dir
    except Exception as e:
        logger.error(f"Erro ao obter diretórios base: {str(e)}")
        raise

@log_function()
def serve_static_file(filename: str):
    """
    Rota para servir arquivos estáticos com tratamento de erros.
    
    Args:
        filename: Nome do arquivo estático a ser servido
        
    Returns:
        Response: Arquivo estático ou 404 se não encontrado
    """
    try:
        logger.debug(f"Solicitando arquivo estático: {filename}")
        
        # Verificar se o arquivo existe
        file_path = os.path.join(dashboard_bp.static_folder, filename)
        if not os.path.exists(file_path):
            logger.warning(f"Arquivo estático não encontrado: {filename}")
            abort(404)
            
        # Registrar o tipo de arquivo sendo servido
        file_ext = os.path.splitext(filename)[1].lower()
        logger.debug(f"Servindo arquivo {file_ext.upper().lstrip('.')}: {filename}")
        
        return send_from_directory(dashboard_bp.static_folder, filename)
    except Exception as e:
        logger.error(f"Erro ao servir arquivo estático {filename}: {str(e)}")
        abort(500)

# Obter os diretórios base
base_dir, template_dir, static_dir = get_base_directories()

# Criar o blueprint
dashboard_bp = Blueprint('dashboard', __name__,
                      template_folder=template_dir,
                      static_folder=static_dir,
                      static_url_path='/static/dashboard')

# Registrar a rota para arquivos estáticos
dashboard_bp.route('/static/dashboard/<path:filename>')(serve_static_file)

# Log de inicialização
logger.info("Blueprint do dashboard inicializado com sucesso")
logger.info(f"Serving static files from: {static_dir}")
logger.info(f"Using templates from: {template_dir}")
