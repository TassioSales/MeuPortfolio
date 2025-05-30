"""
Configurações do Gerenciador de Ativos.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Diretório base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Diretório para armazenamento de dados
DATA_DIR = BASE_DIR / 'data'
DATABASE_DIR = DATA_DIR / 'database'
EXPORTS_DIR = DATA_DIR / 'exports'

# Cria os diretórios se não existirem
for directory in [DATA_DIR, DATABASE_DIR, EXPORTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

class Config:
    """Classe de configuração principal."""
    
    # Configurações gerais
    DEBUG: bool = True
    SECRET_KEY: str = 'sua_chave_secreta_aqui_altere_em_ambiente_de_producao'
    
    # Configurações do banco de dados
    DATABASE_URL: str = f"sqlite:///{DATABASE_DIR}/carteira.db"
    
    # Configurações da API do Yahoo Finance
    YFINANCE_CACHE_DIR: str = str(DATABASE_DIR / 'yfinance_cache')
    YFINANCE_MAX_RETRIES: int = 3
    YFINANCE_REQUEST_DELAY: float = 0.5  # segundos entre requisições
    
    # Configurações de cache
    CACHE_DEFAULT_TIMEOUT: int = 3600  # 1 hora em segundos
    
    # Configurações de exportação
    EXPORT_DIR: str = str(EXPORTS_DIR)
    EXPORT_FORMATS: list = ['xlsx', 'csv', 'json']
    
    # Moeda padrão
    MOEDA_PADRAO: str = 'BRL'
    
    # Configurações de log
    LOG_DIR: str = str(BASE_DIR / 'logs')
    LOG_LEVEL: str = 'INFO'
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configurações de segurança
    PASSWORD_SALT_LENGTH: int = 16
    PASSWORD_HASH_ITERATIONS: int = 100000
    
    # Configurações de sessão
    SESSION_COOKIE_NAME: str = 'gerenciador_ativos_session'
    PERMANENT_SESSION_LIFETIME: int = 86400  # 1 dia em segundos
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """
        Retorna as configurações como um dicionário.
        
        Returns:
            Dict[str, Any]: Dicionário com as configurações
        """
        return {
            key: value for key, value in cls.__dict__.items() 
            if not key.startswith('_') and not callable(value)
        }
    
    @classmethod
    def init_app(cls, app):
        """
        Inicializa a aplicação com as configurações.
        
        Args:
            app: Instância da aplicação
        """
        # Garante que os diretórios necessários existam
        os.makedirs(cls.LOG_DIR, exist_ok=True)
        os.makedirs(cls.YFINANCE_CACHE_DIR, exist_ok=True)
        os.makedirs(cls.EXPORT_DIR, exist_ok=True)


class DevelopmentConfig(Config):
    """Configurações para ambiente de desenvolvimento."""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class TestingConfig(Config):
    """Configurações para ambiente de testes."""
    TESTING = True
    DEBUG = True
    DATABASE_URL = f"sqlite:///{DATABASE_DIR}/test_carteira.db"
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Configurações para ambiente de produção."""
    DEBUG = False
    LOG_LEVEL = 'WARNING'
    SECRET_KEY = os.getenv('SECRET_KEY', 'sua_chave_secreta_segura_aqui')


# Mapeamento de ambientes
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config(config_name: Optional[str] = None) -> Config:
    """
    Retorna a configuração para o ambiente especificado.
    
    Args:
        config_name: Nome do ambiente ('development', 'testing', 'production')
        
    Returns:
        Config: Classe de configuração para o ambiente
    """
    if config_name is None:
        from . import settings
        config_name = os.getenv('FLASK_ENV', 'development')
    
    return config.get(config_name, config['default'])
