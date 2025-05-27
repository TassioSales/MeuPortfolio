import sqlite3
from datetime import datetime
from flask import current_app
import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, LogLevel, RequestContext, log_function

# Configurar logger
logger = get_logger('alertas_manuais.models')

class Alerta:
    """Classe que representa um alerta no sistema"""
    
    @staticmethod
    def _parse_datetime(dt_str):
        """Converte uma string de data/hora para objeto datetime"""
        if dt_str is None:
            return None
        if isinstance(dt_str, datetime):
            return dt_str
        try:
            # Tenta converter de string ISO format
            if 'T' in dt_str:
                return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            # Tenta converter de formato SQLite (YYYY-MM-DD HH:MM:SS)
            try:
                return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return datetime.strptime(dt_str, '%Y-%m-%d')
        except (ValueError, TypeError) as e:
            logger.warning(f'Não foi possível converter a data: {dt_str}. Erro: {e}')
            return None

    def __init__(self, id=None, usuario_id=None, tipo_alerta=None, descricao=None, 
                 valor_referencia=None, categoria=None, data_inicio=None, data_fim=None, 
                 prioridade='media', notificar_email=False, notificar_app=True, ativo=True,
                 criado_em=None, atualizado_em=None):
        self.id = id
        self.usuario_id = usuario_id
        self.tipo_alerta = tipo_alerta
        self.descricao = descricao
        self.valor_referencia = float(valor_referencia) if valor_referencia is not None else None
        self.categoria = categoria
        self.data_inicio = self._parse_datetime(data_inicio)
        self.data_fim = self._parse_datetime(data_fim)
        self.prioridade = prioridade.lower() if prioridade else 'media'
        self.notificar_email = bool(notificar_email) if notificar_email is not None else False
        self.notificar_app = bool(notificar_app) if notificar_app is not None else True
        self.ativo = bool(ativo) if ativo is not None else True
        self.criado_em = self._parse_datetime(criado_em) or datetime.now()
        self.atualizado_em = self._parse_datetime(atualizado_em) or datetime.now()
    
    def to_dict(self, format_dates=True):
        """Converte o objeto para dicionário
        
        Args:
            format_dates (bool): Se True, converte as datas para string ISO format
            
        Returns:
            dict: Dicionário com os dados do alerta
        """
        def format_date(dt):
            if dt is None:
                return None
            if not format_dates:
                return dt
            if hasattr(dt, 'isoformat'):
                return dt.isoformat()
            return str(dt)
            
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'tipo_alerta': self.tipo_alerta,
            'descricao': self.descricao,
            'valor_referencia': float(self.valor_referencia) if self.valor_referencia is not None else None,
            'categoria': self.categoria,
            'data_inicio': format_date(self.data_inicio),
            'data_fim': format_date(self.data_fim),
            'prioridade': self.prioridade,
            'notificar_email': 1 if self.notificar_email else 0,
            'notificar_app': 1 if self.notificar_app else 0,
            'ativo': 1 if self.ativo else 0,
            'criado_em': format_date(self.criado_em),
            'atualizado_em': format_date(self.atualizado_em)
        }
    
    @classmethod
    def from_dict(cls, data):
        """Cria um objeto Alerta a partir de um dicionário"""
        return cls(
            id=data.get('id'),
            usuario_id=data.get('usuario_id', 1),  # Default para admin
            tipo_alerta=data.get('tipo_alerta'),
            descricao=data.get('descricao'),
            valor_referencia=data.get('valor_referencia'),
            categoria=data.get('categoria'),
            data_inicio=data.get('data_inicio'),
            data_fim=data.get('data_fim'),
            prioridade=data.get('prioridade', 'media'),
            data_atualizacao=datetime.fromisoformat(data['data_atualizacao']) if data.get('data_atualizacao') else None,
            status=data.get('status', 'ativo')
        )


def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    from .config import Config
    
    try:
        logger.debug(f'Conectando ao banco de dados: {Config.DATABASE_PATH}')
        print(f'[DEBUG] Tentando conectar ao banco de dados em: {Config.DATABASE_PATH}')
        
        # Verificar se o diretório existe
        db_dir = os.path.dirname(Config.DATABASE_PATH)
        print(f'[DEBUG] Diretório do banco de dados: {db_dir}')
        print(f'[DEBUG] Diretório existe? {os.path.exists(db_dir)}')
        
        # Verificar se o arquivo do banco de dados existe
        print(f'[DEBUG] Arquivo do banco de dados existe? {os.path.exists(Config.DATABASE_PATH)}')
        
        conn = sqlite3.connect(Config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        print('[DEBUG] Conexão com o banco de dados estabelecida com sucesso')
        return conn
    except sqlite3.Error as e:
        error_msg = f'Erro ao conectar ao banco de dados: {e}'
        logger.error(error_msg)
        print(f'[ERROR] {error_msg}')
        raise


def init_db():
    """Inicializa o banco de dados.
    
    Nota: A tabela alertas_financas já deve existir com a estrutura correta.
    Esta função agora apenas verifica a conexão com o banco de dados.
    """
    from .config import Config
    
    try:
        logger.info('Verificando conexão com o banco de dados de alertas')
        
        # Verificar se o diretório do banco de dados existe
        db_dir = os.path.dirname(Config.DATABASE_PATH)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f'Diretório do banco de dados criado: {db_dir}')
        
        # Verificar se o banco de dados existe e está acessível
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se a tabela alertas_financas existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alertas_financas'")
        if not cursor.fetchone():
            logger.error('A tabela alertas_financas não foi encontrada no banco de dados')
            raise Exception('A tabela alertas_financas não foi encontrada no banco de dados')
        
        logger.info('Conexão com o banco de dados de alertas verificada com sucesso')
        
    except sqlite3.Error as e:
        logger.error(f'Erro ao conectar ao banco de dados: {e}')
        raise
    except Exception as e:
        logger.error(f'Erro inesperado ao verificar o banco de dados: {e}')
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()
