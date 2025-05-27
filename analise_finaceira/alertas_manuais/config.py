import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, LogLevel

# Configurar logger
logger = get_logger('alertas_manuais.config')

class Config:
    """Configurações do módulo de alertas manuais."""
    
    # Configurações do banco de dados
    DATABASE_PATH = os.path.join(Path(__file__).parent.parent, 'banco', 'financas.db')
    
    # Configurações de paginação
    ITENS_POR_PAGINA = 10
    
    # Chave secreta para formulários (será sobrescrita pela aplicação principal)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chave-secreta-padrao-alterar-em-producao'
    
    # Configurações de upload
    UPLOAD_FOLDER = os.path.join(Path(__file__).parent, 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    
    # Configurações de template
    TEMPLATES_AUTO_RELOAD = True
    
    @classmethod
    def init_app(cls, app):
        """Inicialização de configurações específicas da aplicação."""
        try:
            logger.info('Inicializando configurações do módulo de alertas manuais')
            
            # Criar pastas necessárias
            os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
            os.makedirs(os.path.dirname(cls.DATABASE_PATH), exist_ok=True)
            
            # Configurar pasta de upload
            app.config['UPLOAD_FOLDER'] = cls.UPLOAD_FOLDER
            
            logger.info(f'Pasta de uploads configurada: {cls.UPLOAD_FOLDER}')
            logger.info(f'Banco de dados: {cls.DATABASE_PATH}')
            
        except Exception as e:
            logger.error(f'Erro ao inicializar configurações: {e}')
            raise
