"""
Pacote principal da aplicação Análise de Ações.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Inicializa as extensões
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

# Importa os modelos para garantir que eles sejam registrados com o SQLAlchemy
# Isso deve ser feito após a inicialização do db para evitar importações circulares
from .models import Usuario, Ativo, HistoricoPreco, Carteira, CarteiraAtivo, Alerta, Operacao, TipoOperacao, StatusOperacao

# Exporta os componentes principais para facilitar as importações
__all__ = [
    'db',
    'login_manager',
    'Usuario',
    'Ativo',
    'HistoricoPreco',
    'Carteira',
    'CarteiraAtivo',
    'Alerta',
    'Operacao',
    'TipoOperacao',
    'StatusOperacao'
]
