from flask import Flask, render_template, redirect, url_for, session, jsonify, send_from_directory, request
from flask_wtf.csrf import CSRFProtect
import secrets
from upload_arq.src import upload_bp
from dashboard_arq.src import dashboard_bp, inserir_bp
from alertas_manuais_arq.src.blueprint import alertas_manuais_bp
import os
from logger import get_logger

logger = get_logger("main")

# Criar diretório para uploads se não existir
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
logger.info(f"Diretório de uploads configurado: {UPLOAD_FOLDER}")

# Criar diretório para o banco de dados se não existir
DB_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'banco')
os.makedirs(DB_FOLDER, exist_ok=True)
logger.info(f"Diretório do banco de dados configurado: {DB_FOLDER}")

# Configurar o aplicativo Flask
app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')
logger.info("Aplicativo Flask inicializado")

# Configurar os diretórios de templates adicionais
template_dirs = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard_arq', 'templates'),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'upload_arq', 'templates'),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'alertas_manuais_arq', 'templates')
]
app.jinja_loader.searchpath = template_dirs

# Configurações do aplicativo
app.config['SECRET_KEY'] = 'sua_chave_secreta_muito_segura_aqui'  # Use uma chave fixa para desenvolvimento
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = 'outra_chave_secreta_para_csrf'
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hora de validade para o token CSRF
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DATABASE'] = os.path.join(DB_FOLDER, 'financas.db')

# Habilitar proteção CSRF
csrf = CSRFProtect()
csrf.init_app(app)

# Desabilitar CSRF para a rota de exclusão de alertas (apenas para teste)
@alertas_manuais_bp.before_request
def check_csrf_for_excluir():
    if request.endpoint == 'alertas_manuais.excluir_alerta':
        return None
    return None

# Aplicar isenção CSRF para a rota de exclusão
alertas_manuais_bp.before_request(csrf.exempt(check_csrf_for_excluir))

# Registrar blueprints
app.register_blueprint(upload_bp, url_prefix='/upload')
logger.info("Blueprint de upload registrado")
app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
logger.info("Blueprint de dashboard registrado")
app.register_blueprint(inserir_bp, url_prefix='/inserir')
logger.info("Blueprint de inserir registrado")
app.register_blueprint(alertas_manuais_bp, url_prefix='/alertas-manuais')
logger.info("Blueprint de alertas manuais registrado")




# Configurar o template global para o token CSRF
@app.context_processor
def inject_csrf_token():
    from flask_wtf.csrf import generate_csrf
    token = generate_csrf()
    return dict(csrf_token=token)  # Retorna o token diretamente, não a função

# Rota para arquivos estáticos do dashboard
@app.route('/dashboard/static/<path:filename>')
def dashboard_static(filename):
    return send_from_directory('dashboard_arq/static', filename)

# Rota principal
from utils import get_dashboard_highlights
from datetime import datetime

@app.route('/')
def index():
    total_transacoes, total_alertas_ativos, total_categorias = get_dashboard_highlights()
    hora = datetime.now().hour
    if 5 <= hora < 12:
        saudacao = 'Bom dia'
    elif 12 <= hora < 18:
        saudacao = 'Boa tarde'
    else:
        saudacao = 'Boa noite'
    return render_template(
        'index.html',
        active_page='home',
        ano_atual=datetime.now().year,
        total_transacoes=total_transacoes,
        total_alertas_ativos=total_alertas_ativos,
        total_categorias=total_categorias,
        saudacao=saudacao
    )

# Rota para redirecionar /upload para /upload/ para evitar problemas com URLs relativas
@app.route('/upload')
def redirect_upload():
    return redirect(url_for('upload.upload_file'))

# Rota para redirecionar /dashboard para /dashboard/
@app.route('/dashboard')
def redirect_dashboard():
    return redirect(url_for('dashboard.dashboard'))

# Rota para verificar o token CSRF
@app.route('/api/check_csrf', methods=['GET'])
def check_csrf():
    from flask_wtf.csrf import generate_csrf
    token = generate_csrf()
    return jsonify({
        'status': 'success',
        'csrf_token': token,
        'token_length': len(token) if token else 0,
        'token_type': type(token).__name__
    })

if __name__ == '__main__':
    logger.info("Iniciando aplicação Flask...")
    try:
        # Criar diretório para templates se não existir
        os.makedirs('templates', exist_ok=True)
        # Criar diretório para arquivos estáticos se não existir
        os.makedirs('static', exist_ok=True)
        app.run(debug=True)
    except Exception as e:
        logger.error(f"Erro ao iniciar a aplicação: {e}", exc_info=True)
