"""
Módulo de configuração do blueprint de alertas.
"""
import os
import sys
from pathlib import Path
from flask import Blueprint, send_from_directory, current_app, send_file, abort
from logger import get_logger, log_function, setup_logger

# Configura o logger para este módulo
logger = setup_logger("alertas.blueprint") if 'setup_logger' in globals() else get_logger("alertas.blueprint")

@log_function()
def get_base_directories() -> tuple[str, str, str]:
    """
    Obtém os diretórios base do módulo de alertas.
    
    Returns:
        tuple: (base_dir, template_dir, static_dir)
    """
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        template_dir = os.path.join(base_dir, 'alertas_arq', 'templates')
        static_dir = os.path.join(base_dir, 'alertas_arq', 'static')
        
        logger.debug(f"[Alertas] Diretório base: {base_dir}")
        logger.debug(f"[Alertas] Diretório de templates: {template_dir}")
        logger.debug(f"[Alertas] Diretório estático: {static_dir}")
        
        # Verificar se os diretórios existem
        if not os.path.exists(template_dir):
            logger.warning(f"[Alertas] Diretório de templates não encontrado: {template_dir}")
        if not os.path.exists(static_dir):
            logger.warning(f"[Alertas] Diretório estático não encontrado: {static_dir}")
            
        return base_dir, template_dir, static_dir
    except Exception as e:
        logger.error(f"[Alertas] Erro ao obter diretórios base: {str(e)}")
        raise

@log_function()
def serve_static_file(filename: str):
    """
    Rota para servir arquivos estáticos com tratamento de erros.
    
    Args:
        filename (str): Nome do arquivo estático a ser servido
    """
    try:
        static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')
        logger.debug(f"[Alertas] Servindo arquivo estático: {filename} de {static_dir}")
        return send_from_directory(static_dir, filename)
    except FileNotFoundError:
        logger.warning(f"[Alertas] Arquivo estático não encontrado: {filename}")
        abort(404)
    except Exception as e:
        logger.error(f"[Alertas] Erro ao servir arquivo estático {filename}: {str(e)}")
        abort(500)

# Obter os diretórios base
base_dir, template_dir, static_dir = get_base_directories()

# Criar o blueprint
alertas_bp = Blueprint('alertas', __name__,
                    template_folder=template_dir,
                    static_folder=static_dir,
                    static_url_path='/static/alertas')

# Registrar a rota para arquivos estáticos
alertas_bp.route('/static/alertas/<path:filename>')(serve_static_file)

# Log de inicialização
logger.info("Blueprint de alertas inicializado com sucesso")
logger.info(f"[Alertas] Servindo arquivos estáticos de: {static_dir}")
logger.info(f"[Alertas] Usando templates de: {template_dir}")
