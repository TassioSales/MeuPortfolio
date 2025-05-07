from flask import Flask, render_template, redirect, url_for, session, jsonify, send_from_directory
from flask_wtf.csrf import CSRFProtect
import secrets
from upload_arq.src import upload_bp
from dashboard_arq.src import dashboard_bp, inserir_bp
import os

# Criar diretório para uploads se não existir
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Criar diretório para o banco de dados se não existir
DB_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'banco')
os.makedirs(DB_FOLDER, exist_ok=True)

# Configurar o aplicativo Flask
app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')

# Configurar os diretórios de templates adicionais
template_dirs = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard_arq', 'templates'),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'upload_arq', 'templates')
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

# Registrar blueprints
app.register_blueprint(upload_bp, url_prefix='/upload')
app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
app.register_blueprint(inserir_bp, url_prefix='/inserir')




# Configurar o template global para o token CSRF
@app.context_processor
def inject_csrf_token():
    from flask_wtf.csrf import generate_csrf
    token = generate_csrf()
    print(f"\n=== GERANDO TOKEN CSRF ===\n{token}\n")
    print(f"Token CSRF gerado: {token}")
    print(f"Tipo do token: {type(token)}")
    print(f"Tamanho do token: {len(token) if token else 0}")
    return dict(csrf_token=token)  # Retorna o token diretamente, não a função

# Rota para arquivos estáticos do dashboard
@app.route('/dashboard/static/<path:filename>')
def dashboard_static(filename):
    return send_from_directory('dashboard_arq/static', filename)

# Rota principal
@app.route('/')
def index():
    return render_template('index.html', active_page='home')

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
    # Criar diretório para templates se não existir
    os.makedirs('templates', exist_ok=True)
    # Criar diretório para arquivos estáticos se não existir
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Iniciar o servidor
    app.run(debug=True, port=5000)
