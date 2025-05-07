import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, log_function, RequestContext

# Configura o logger para este módulo
logger = get_logger("alertas")


# Importa o blueprint e inicializa o banco de dados
from flask import Blueprint, g, jsonify, make_response, request
from flask_wtf.csrf import generate_csrf, validate_csrf
from .blueprint import alertas_bp
from . import database  # Garante que o módulo database seja importado

# Cria o blueprint
# alertas_bp = Blueprint('alertas', __name__)  # Comentado pois já foi importado

@alertas_bp.before_request
def check_csrf():
    """Verifica o token CSRF para requisições não-GET"""
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        try:
            # Verifica se o token CSRF está presente no cabeçalho ou no formulário
            csrf_token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
            
            if not csrf_token:
                logger.warning("Token CSRF não encontrado na requisição")
                return jsonify({
                    'success': False,
                    'message': 'Token CSRF não fornecido'
                }), 400
                
            # Verifica se o token é válido
            if not validate_csrf(csrf_token):
                logger.warning("Token CSRF inválido")
                return jsonify({
                    'success': False,
                    'message': 'Token CSRF inválido'
                }), 403
                
        except Exception as e:
            logger.error(f"Erro ao verificar token CSRF: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Erro ao verificar token CSRF',
                'error': str(e)
            }), 500

@alertas_bp.after_request
def add_csrf_to_response(response):
    """Adiciona o token CSRF aos cabeçalhos de resposta"""
    # Gera um novo token CSRF
    csrf_token = generate_csrf()
    
    # Adiciona o token como um cookie HTTP-Only
    response.set_cookie('csrf_token', csrf_token, httponly=True, samesite='Strict')
    
    # Adiciona o token como um header personalizado
    response.headers['X-CSRF-Token'] = csrf_token
    
    return response

# Importa as rotas
from . import routes

# Log de inicialização
logger.info("Módulo de alertas inicializado com sucesso")
