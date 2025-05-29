import os
from flask import render_template, request, flash, redirect, url_for, current_app, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path
import sys
from .processamento import process_csv, process_pdf, get_all_transactions, get_upload_history

from logger import get_logger, log_function, LogLevel
from . import upload_bp
from . import processamento, utils

# Adiciona o utils ao contexto global do template
@upload_bp.context_processor
def inject_utils():
    return dict(utils=utils)

# Adiciona o filtro de formatação de moeda ao Jinja
upload_bp.app_template_filter('format_currency')(utils.format_currency)

import sqlite3



# Configura o logger para este módulo
logger = get_logger("upload.routes")

# Extensões permitidas
ALLOWED_EXTENSIONS = {'csv', 'pdf'}

def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_upload_folder():
    """Retorna o caminho para a pasta de uploads"""
    return os.path.join(current_app.root_path, '..', '..', 'Uploads')

@upload_bp.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """Rota para upload de arquivos"""
    if request.method == 'POST':
        logger.info("Iniciando processamento de upload de arquivo")
        
        # Verifica o token CSRF
        csrf_token = request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
        if not csrf_token:
            error_msg = 'Token CSRF ausente na solicitação'
            logger.error(error_msg)
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(request.url)

        # Verifica se o arquivo foi enviado
        if 'file' not in request.files:
            error_msg = 'Nenhum arquivo enviado'
            logger.warning(error_msg)
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        # Verifica se o arquivo tem um nome
        if file.filename == '':
            error_msg = 'Nenhum arquivo selecionado'
            logger.warning(error_msg)
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(request.url)
        
        # Verifica a extensão do arquivo
        if not allowed_file(file.filename):
            error_msg = f'tipo de arquivo não permitido: {file.filename}. Use apenas arquivos CSV ou PDF.'
            logger.warning(error_msg)
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(request.url)
        
        try:
            logger.info(f"Processando arquivo: {file.filename}")
            
            # Cria o diretório de uploads se não existir
            upload_folder = get_upload_folder()
            os.makedirs(upload_folder, exist_ok=True)
            logger.debug(f"Diretório de upload: {upload_folder}")
            
            # Salva o arquivo temporariamente
            filename = secure_filename(file.filename)
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            logger.info(f"Arquivo salvo temporariamente em: {file_path}")
            
            try:
                # Processa o arquivo de acordo com a extensão
                if filename.lower().endswith('.csv'):
                    logger.debug("Iniciando processamento de arquivo CSV")
                    success, message = process_csv(file_path)
                elif filename.lower().endswith('.pdf'):
                    logger.debug("Iniciando processamento de arquivo PDF")
                    success, message = process_pdf(file_path)
                else:
                    error_msg = f"tipo de arquivo não suportado: {filename}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                if success:
                    logger.info(f"Arquivo processado com sucesso: {message}")
                    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': True, 'message': message})
                    flash(message, 'success')
                    return redirect(url_for('upload.upload_file'))
                else:
                    error_msg = f'Erro ao processar o arquivo: {message}'
                    logger.error(error_msg)
                    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'message': error_msg}), 400
                    flash(error_msg, 'error')
                    return redirect(request.url)
            
            except Exception as e:
                error_msg = f"Erro durante o processamento do arquivo: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise
            
        except Exception as e:
            error_msg = f'Erro ao processar o arquivo: {str(e)}'
            logger.error(error_msg)
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 500
            flash(error_msg, 'error')
            return redirect(request.url)
    
    # Se for GET, mostra o formulário de upload e o histórico
    upload_history = get_upload_history()
    return render_template('upload.html', upload_history=upload_history)

@upload_bp.route('/transactions')
def list_transactions():
    """Rota para listar as transações com informações sobre colunas faltantes"""
    try:
        transactions = get_all_transactions()
        
        # Verificar se há transações
        if transactions.empty:
            flash('Nenhuma transação encontrada no banco de dados', 'info')
            return redirect(url_for('upload.upload_file'))
        
        # Extrair colunas faltantes do DataFrame
        missing_columns = []
        if 'missing_columns' in transactions.columns:
            missing_columns = eval(transactions['missing_columns'].iloc[0]) if transactions['missing_columns'].iloc[0] else []
            # Remover a coluna missing_columns do DataFrame antes de passar para o template
            transactions = transactions.drop(columns=['missing_columns'])
        
        # Se houver colunas faltantes, mostrar mensagem de aviso
        if missing_columns:
            flash(f'Atenção: As seguintes colunas obrigatórias estão faltando no banco de dados: {", ".join(missing_columns)}', 'warning')
        
        # Adicionar informações estatísticas usando o DataFrame
        stats = {
            'total_transacoes': len(transactions),
            'total_receitas': transactions[transactions['valor'] > 0]['valor'].sum(),
            'total_despesas': abs(transactions[transactions['valor'] < 0]['valor'].sum()),
            'periodo': {
                'inicio': transactions['data'].min(),
                'fim': transactions['data'].max()
            }
        }
        
        return render_template(
            'transactions.html', 
            transactions=transactions,
            stats=stats,
            missing_columns=missing_columns
        )
    except Exception as e:
        logger.error(f"Erro ao buscar transações: {str(e)}", exc_info=True)
        flash('Erro ao buscar transações', 'danger')
        return redirect(url_for('upload.upload_file'))

@upload_bp.route('/upload_history')
def upload_history():
    """Rota para buscar o histórico de uploads via AJAX"""
    try:
        upload_history = get_upload_history()
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'data': upload_history.to_dict('records') if not upload_history.empty else []
            })
        return render_template('upload_history.html', upload_history=upload_history)
    except Exception as e:
        error_msg = f"Erro ao buscar histórico de uploads: {str(e)}"
        logger.error(error_msg)
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        return 'Erro ao buscar histórico de uploads', 500

@upload_bp.route('/clear_upload_history', methods=['POST'])
def clear_upload_history():
    """Rota para limpar o histórico de uploads"""
    conn = None
    try:
        # Conecta ao banco de dados usando o caminho absoluto correto
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'banco', 'financas.db')
        logger.info(f"Conectando ao banco de dados em: {db_path}")
        
        # Conecta ao banco de dados
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Verifica se a tabela existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='uploads_historico'
        """)
        
        if not cursor.fetchone():
            return jsonify({
                'success': True,
                'message': 'Nenhum histórico para limpar',
                'data': []  # Retorna uma lista vazia para a tabela
            })
        
        # Limpa a tabela de histórico
        cursor.execute("DELETE FROM uploads_historico")
        conn.commit()
        
        # Retorna sucesso com lista vazia para a tabela
        return jsonify({
            'success': True,
            'message': 'Histórico de uploads limpo com sucesso!',
            'data': []  # Retorna uma lista vazia para a tabela
        })
        
    except Exception as e:
        error_msg = f'Erro ao limpar histórico: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return jsonify({
            'success': False,
            'message': error_msg,
            'data': []  # Retorna uma lista vazia mesmo em caso de erro
        }), 500
    finally:
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.error(f"Erro ao fechar conexão: {str(e)}")

# Cria um logger para este módulo
logger_categorias = get_logger("categorias")

@upload_bp.route('/get-categorias', methods=['GET'])
@log_function(logger_categorias, LogLevel.INFO)
def get_categorias():
    """
    Rota para obter categorias, opcionalmente filtradas por tipo (Receita/Despesa)
    
    Query Parameters:
        tipo (str, optional): 'Receita' ou 'Despesa' para filtrar as categorias
    """
    try:
        tipo = request.args.get('tipo')
        logger_categorias.info(f"Obtendo categorias para o tipo: {tipo}")
        
        categorias = processamento.get_categorias_por_tipo(tipo)
        
        return jsonify({
            'success': True,
            'categorias': categorias
        })
        
    except Exception as e:
        logger_categorias.error(f"Erro ao obter categorias: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Erro ao obter categorias: {str(e)}'
        }), 500