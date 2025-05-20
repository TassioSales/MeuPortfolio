from flask import Blueprint

# Criar o blueprint
analise_bp = Blueprint('analise_estatistica', __name__,
                       template_folder='../templates',
                       static_folder='static')

# Registrar as rotas
from .routes import analise, analisar

# Registrar as rotas no blueprint
analise_bp.add_url_rule('/analise', view_func=analise, methods=['GET'])
analise_bp.add_url_rule('/analisar', view_func=analisar, methods=['POST'])
analise_bp.add_url_rule('/analise', view_func=analise, methods=['GET', 'POST'])