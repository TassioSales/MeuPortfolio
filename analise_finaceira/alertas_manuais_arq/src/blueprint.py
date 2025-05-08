import os
import logging
from flask import Blueprint

# Importa o logger diretamente do módulo raiz
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from logger import get_logger

# Cria o blueprint para os alertas manuais
alertas_manuais_bp = Blueprint(
    'alertas_manuais',
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
    static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'),
    url_prefix='/alertas-manuais'
)

# Configura o logger para o blueprint
logger = get_logger('alertas_manuais.blueprint')

# Importa as rotas após a criação do blueprint para evitar importação circular
from . import routes  # noqa
