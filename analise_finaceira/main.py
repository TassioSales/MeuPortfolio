from flask import Flask, render_template, redirect, url_for, jsonify, send_from_directory, request
from flask_wtf.csrf import CSRFProtect
import secrets
import os
from pathlib import Path
import sys
import logging

# Adiciona o diretório raiz ao path para importar módulos locais
root_dir = str(Path(__file__).parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    from logger import get_logger, log_function, LogLevel
except ImportError:
    # Fallback logger if custom logger is not available
    def get_logger(name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

logger = get_logger("main")

# Importar blueprints
try:
    from upload_arq.src import upload_bp
    from dashboard_arq.src import dashboard_bp, inserir_bp
    from alertas_manuais_arq.src.blueprint import alertas_manuais_bp
    from alertas_automaticos.blueprint import alertas_automaticos_bp
except ImportError as e:
    logger.error(f"Erro ao importar blueprints: {e}")
    raise

# Criar diretórios para uploads e banco de dados
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
logger.info(f"Diretório de uploads configurado: {UPLOAD_FOLDER}")

DB_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'banco')
os.makedirs(DB_FOLDER, exist_ok=True)
logger.info(f"Diretório do banco de dados configurado: {DB_FOLDER}")

# Configurar o aplicativo Flask
app = Flask(__name__, template_folder='templates', static_folder='static')
logger.info("Aplicativo Flask inicializado")

# Configurações do aplicativo
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))
app.config['WTF_CSRF_ENABLED'] = True
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DATABASE'] = os.path.join(DB_FOLDER, 'financas.db')
logger.info(f"Configurações do Flask: {app.config}")
logger.info(f"Banco de dados configurado: {app.config['DATABASE']}")

# Habilitar proteção CSRF
csrf = CSRFProtect()
csrf.init_app(app)
logger.info("Proteção CSRF habilitada")

# Registrar blueprints com tratamento de erros
try:
    app.register_blueprint(upload_bp, url_prefix='/upload')
    logger.info("Blueprint de upload registrado")
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    logger.info("Blueprint de dashboard registrado")
    app.register_blueprint(inserir_bp, url_prefix='/inserir')
    logger.info("Blueprint de inserir registrado")
    app.register_blueprint(alertas_manuais_bp, url_prefix='/alertas-manuais')
    logger.info("Blueprint de alertas manuais registrado")
    app.register_blueprint(alertas_automaticos_bp, url_prefix='/alertas-automaticos')
    logger.info("Blueprint de alertas automáticos registrado")
except Exception as e:
    logger.error(f"Erro ao registrar blueprints: {e}")
    raise

# Configurar o template global para o token CSRF
@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=app.jinja_env.globals.get('csrf_token'))

# Rota para arquivos estáticos do dashboard (se necessário)
@app.route('/dashboard/static/<path:filename>')
def dashboard_static(filename):
    try:
        return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard_arq', 'static'), filename)
    except Exception as e:
        logger.error(f"Erro ao servir arquivo estático do dashboard: {e}")
        return jsonify({'status': 'error', 'message': 'Arquivo não encontrado'}), 404

# Rota principal
try:
    from utils import get_dashboard_highlights
except ImportError:
    logger.warning("Módulo utils não encontrado. Definindo get_dashboard_highlights como fallback.")
    def get_dashboard_highlights():
        return 0, 0, 0  # Valores padrão para evitar erros

from datetime import datetime

@app.route('/')
def index():
    try:
        total_transacoes, total_alertas_ativos, total_categorias = get_dashboard_highlights()
        hora = datetime.now().hour
        saudacao = 'Bom dia' if 5 <= hora < 12 else 'Boa tarde' if 12 <= hora < 18 else 'Boa noite'
        return render_template(
            'index.html',
            active_page='home',
            ano_atual=datetime.now().year,
            total_transacoes=total_transacoes,
            total_alertas_ativos=total_alertas_ativos,
            total_categorias=total_categorias,
            saudacao=saudacao
        )
    except Exception as e:
        logger.error(f"Erro na rota index: {e}")
        return render_template('error.html', error_message=str(e)), 500

# Rotas de redirecionamento
@app.route('/upload')
def redirect_upload():
    return redirect(url_for('upload.upload_file'))

@app.route('/dashboard')
def redirect_dashboard():
    return redirect(url_for('dashboard.dashboard'))

# Rota para verificar o token CSRF
@app.route('/api/check_csrf', methods=['GET'])
def check_csrf():
    try:
        from flask_wtf.csrf import generate_csrf
        token = generate_csrf()
        return jsonify({
            'status': 'success',
            'csrf_token': token,
            'token_length': len(token) if token else 0,
            'token_type': type(token).__name__
        })
    except Exception as e:
        logger.error(f"Erro ao verificar token CSRF: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Rota de depuração para upload
@app.route('/debug/upload', methods=['POST'])
def debug_upload():
    logger.info("Depuração de upload iniciada")
    logger.info(f"Form data: {request.form}")
    logger.info(f"Files: {request.files}")
    logger.info(f"Headers: {request.headers}")
    logger.info(f"CSRF Token (form): {request.form.get('csrf_token')}")
    logger.info(f"CSRF Token (header): {request.headers.get('X-CSRFToken')}")
    return jsonify({
        'form_data': dict(request.form),
        'files': list(request.files.keys()),
        'headers': dict(request.headers),
        'csrf_token_form': request.form.get('csrf_token'),
        'csrf_token_header': request.headers.get('X-CSRFToken')
    })

if __name__ == '__main__':
    logger.info("Iniciando aplicação Flask...")
    try:
        os.makedirs('templates', exist_ok=True)
        os.makedirs('static', exist_ok=True)
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Erro ao iniciar a aplicação: {e}", exc_info=True)
        raise