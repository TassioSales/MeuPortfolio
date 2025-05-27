from flask import Flask, render_template, redirect, url_for, jsonify, send_from_directory, request
from flask_wtf.csrf import CSRFProtect
import secrets
import os
from pathlib import Path
import sys
import logging
from datetime import datetime

# Adiciona o diretório raiz ao path para importar módulos locais
root_dir = str(Path(__file__).parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Configurar logger
try:
    from logger import get_logger, log_function, LogLevel
except ImportError:
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

# Configurar o aplicativo Flask
app = Flask(__name__, template_folder='templates', static_folder='static')

# Adicionar caminho para arquivos estáticos do módulo analise_estatistica_arq
analise_static_path = os.path.join(os.path.dirname(__file__), 'analise_estatistica_arq', 'static')
app.static_folder = analise_static_path
logger.info("Aplicativo Flask inicializado")

# Configurações do aplicativo
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_CHECK_DEFAULT'] = False

# Criar diretórios para uploads e banco de dados
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
logger.info(f"Diretório de uploads configurado: {UPLOAD_FOLDER}")

DB_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'banco')
os.makedirs(DB_FOLDER, exist_ok=True)
app.config['DATABASE'] = os.path.join(DB_FOLDER, 'financas.db')
logger.info(f"Diretório do banco de dados configurado: {app.config['DATABASE']}")

# Importar blueprints
try:
    from upload_arq.src import upload_bp
    from dashboard_arq.src import dashboard_bp, inserir_bp
    from dashboard_arq.src.acoes import acoes_bp
    from dashboard_arq.src.transacoes import obter_saldo_atual
    from analise_estatistica_arq.src.__init__ import analise_bp as analise_estatistica_bp
    from alertas_manuais import init_app as init_alertas_manuais
    
    # Habilitar proteção CSRF
    csrf = CSRFProtect()
    csrf.init_app(app)
    logger.info("Proteção CSRF habilitada")
    
    # Desabilitar CSRF para rotas de API
    csrf.exempt(acoes_bp)  # Desabilita CSRF para todas as rotas no blueprint de ações

    # Registrar blueprints com prefixos únicos
    app.register_blueprint(upload_bp, url_prefix='/upload')
    logger.info("Blueprint de upload registrado")
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    logger.info("Blueprint de dashboard registrado")
    app.register_blueprint(inserir_bp, url_prefix='/inserir')
    logger.info("Blueprint de inserir registrado")
    app.register_blueprint(acoes_bp, url_prefix='/acoes')
    logger.info("Blueprint de ações registrado")
    
    app.register_blueprint(analise_estatistica_bp, url_prefix='/analise_estatistica')
    logger.info("Blueprint de análise estatística registrado")
    
    # Inicializar o módulo de alertas manuais
    print("Iniciando inicialização do módulo de alertas manuais...")
    init_alertas_manuais(app)
    logger.info("Módulo de alertas manuais inicializado")
    print("Módulo de alertas manuais inicializado com sucesso")
except ImportError as e:
    logger.error(f"Erro ao importar blueprints: {e}")
    raise

# Configurar o template global para o token CSRF
@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=app.jinja_env.globals.get('csrf_token'))

# Rota para arquivos estáticos do dashboard
@app.route('/dashboard/static/<path:filename>')
def dashboard_static(filename):
    try:
        return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard_arq', 'static'), filename)
    except Exception as e:
        logger.error(f"Erro ao servir arquivo estático do dashboard: {e}")
        return jsonify({'status': 'error', 'message': 'Arquivo não encontrado'}), 404

# Rota principal
from datetime import datetime
from dashboard_arq.src.dashboard_utils import get_dashboard_highlights, get_recent_activities, calcular_saldo_atual

@app.route('/')
def index():
    try:
        # Inicializar variáveis com valores padrão
        dados_transacoes = {
            'total': 0,
            'este_mes': 0,
            'variacao': 0,
            'variacao_percentual': 0
        }
        dados_categorias = {
            'total': 0,
            'novas_este_mes': 0
        }
        total_alertas_ativos = 0
        saldo_atual = 0.0
        atividades_recentes = []
        
        try:
            # Obter dados do dashboard
            # Obter dados do dashboard
            dados_transacoes, total_alertas_ativos, dados_categorias = get_dashboard_highlights()
            
            # Calcular saldo atual usando a nova função
            saldo_info = calcular_saldo_atual()
            saldo_atual = saldo_info.get('saldo_atual', 0.0)
            total_receitas = saldo_info.get('total_receitas', 0.0)
            total_despesas = saldo_info.get('total_despesas', 0.0)
            
            # Obter as 10 atividades mais recentes do banco de dados
            atividades_recentes = get_recent_activities(limit=10)
            
            # Adicionar saldo atual como primeira atividade
            if saldo_atual is not None:
                saldo_formatado = f'R$ {saldo_atual:,.2f}'.replace('.', 'X').replace(',', '.').replace('X', ',')
                receitas_formatado = f'R$ {total_receitas:,.2f}'.replace('.', 'X').replace(',', '.').replace('X', ',')
                despesas_formatado = f'R$ {total_despesas:,.2f}'.replace('.', 'X').replace(',', '.').replace('X', ',')
                
                atividades_recentes.insert(0, {
                    'titulo': 'Saldo Atual',
                    'descricao': f'Seu saldo atual é de {saldo_formatado}',
                    'tempo': 'Agora',
                    'icone': 'wallet2',
                    'cor': 'success' if saldo_atual >= 0 else 'danger',
                    'detalhes': {
                        'receitas': receitas_formatado,
                        'despesas': despesas_formatado
                    }
                })
        except Exception as e:
            logger.error(f"Erro ao obter dados do dashboard: {str(e)}")
        
        # Obter data atual para exibição
        hoje = datetime.now()
        
        # Obter saudação com base no horário
        hora = hoje.hour
        saudacao = 'Bom dia' if 5 <= hora < 12 else 'Boa tarde' if 12 <= hora < 18 else 'Boa noite'
        
        # Nome do mês em português
        meses = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        mes_atual = meses[hoje.month - 1]
        
        # Garantir que os dicionários tenham todas as chaves necessárias
        dados_transacoes = {
            'total': dados_transacoes.get('total', 0),
            'este_mes': dados_transacoes.get('este_mes', 0),
            'variacao': dados_transacoes.get('variacao', 0),
            'variacao_percentual': dados_transacoes.get('variacao_percentual', 0)
        }
        
        dados_categorias = {
            'total': dados_categorias.get('total', 0),
            'novas_este_mes': dados_categorias.get('novas_este_mes', 0)
        }
        
        return render_template(
            'index.html',
            active_page='home',
            ano_atual=hoje.year,
            mes_atual=mes_atual,
            hoje=hoje,
            dados_transacoes=dados_transacoes,
            total_alertas_ativos=total_alertas_ativos,
            dados_categorias=dados_categorias,
            saudacao=saudacao,
            atividades_recentes=atividades_recentes,
            saldo_atual=saldo_atual or 0.0,
            total_receitas=total_receitas or 0.0,
            total_despesas=total_despesas or 0.0
        )
        
    except Exception as e:
        logger.error(f"Erro na rota index: {str(e)}")
        # Em caso de erro, tenta retornar a página com valores padrão
        return render_template(
            'index.html',
            active_page='home',
            ano_atual=datetime.now().year,
            mes_atual='Maio',
            hoje=datetime.now(),
            dados_transacoes={'total': 0, 'este_mes': 0, 'variacao': 0, 'variacao_percentual': 0},
            total_alertas_ativos=0,
            dados_categorias={'total': 0, 'novas_este_mes': 0},
            saudacao='Olá',
            atividades_recentes=[],
            saldo_atual=0.0,
            total_receitas=0.0,
            total_despesas=0.0
        )
        
    except Exception as e:
        logger.error(f"Erro na rota index: {str(e)}")
        # Em caso de erro, tenta retornar a página com valores padrão
        return render_template(
            'index.html',
            active_page='home',
            ano_atual=datetime.now().year,
            total_transacoes=0,
            total_alertas_ativos=0,
            total_categorias=0,
            saudacao='Olá',
            saldo_atual=0.0,
            total_receitas=0.0,
            total_despesas=0.0
        )

# Rotas de redirecionamento
@app.route('/upload')
def redirect_upload():
    return redirect(url_for('upload.upload_file'))

@app.route('/dashboard')
def redirect_dashboard():
    return redirect(url_for('dashboard.dashboard'))

@app.route('/alertas-manuais')
def redirect_alertas_manuais():
    return redirect(url_for('alertas_manuais.index'))

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