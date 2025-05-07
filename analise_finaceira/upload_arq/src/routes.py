import os
from flask import render_template, request, flash, redirect, url_for, current_app, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path
import sys

# Adiciona o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, log_function, LogLevel
from . import upload_bp
from .processamento import process_csv, process_pdf, get_all_transactions, get_upload_history
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
    return os.path.join(current_app.root_path, '..', '..', 'uploads')

@upload_bp.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """Rota para upload de arquivos"""
    if request.method == 'POST':
        logger.info("Iniciando processamento de upload de arquivo")
        
        # Verifica se o arquivo foi enviado
        if 'file' not in request.files:
            error_msg = 'Nenhum arquivo enviado'
            logger.warning(error_msg)
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': False, 'message': error_msg}, 400
            flash(error_msg, 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        # Verifica se o arquivo tem um nome
        if file.filename == '':
            error_msg = 'Nenhum arquivo selecionado'
            logger.warning(error_msg)
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': False, 'message': error_msg}, 400
            flash(error_msg, 'error')
            return redirect(request.url)
        
        # Verifica a extensão do arquivo
        if not allowed_file(file.filename):
            error_msg = f'Tipo de arquivo não permitido: {file.filename}. Use apenas arquivos CSV ou PDF.'
            logger.warning(error_msg)
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': False, 'message': error_msg}, 400
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
                
                if success:
                    logger.success(f"Arquivo processado com sucesso: {message}")
                    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return {'success': True, 'message': message}
                    flash(message, 'success')
                    return redirect(url_for('upload.upload_file'))
                else:
                    error_msg = f'Erro ao processar o arquivo: {message}'
                    logger.error(error_msg)
                    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return {'success': False, 'message': error_msg}, 400
                    flash(error_msg, 'error')
                    return redirect(request.url)
                    
            except Exception as e:
                logger.error(f"Erro durante o processamento do arquivo: {str(e)}", exc_info=True)
                raise
            
        except Exception as e:
            error_msg = f'Erro ao processar o arquivo: {str(e)}'
            logger.error(error_msg)
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': False, 'message': error_msg}, 500
            flash(error_msg, 'error')
            return redirect(request.url)
    
    # Se for GET, mostra o formulário de upload e o histórico
    upload_history = get_upload_history()
    return render_template('upload.html', upload_history=upload_history)

@upload_bp.route('/transactions')
def list_transactions():
    """Rota para listar as transações"""
    try:
        transactions = get_all_transactions()
        return render_template('transactions.html', transactions=transactions)
    except Exception as e:
        logger.error(f"Erro ao buscar transações: {str(e)}")
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
        # Conecta ao banco de dados usando o caminho correto
        db_path = os.path.join(root_dir, 'banco', 'financas.db')
        logger.info(f"Conectando ao banco de dados em: {db_path}")
        
        # Verifica se o arquivo do banco de dados existe
        if not os.path.exists(db_path):
            error_msg = f"Arquivo do banco de dados não encontrado em: {db_path}"
            logger.error(error_msg)
            return jsonify({'success': False, 'message': error_msg}), 404
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verifica se a tabela existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='uploads_historico'")
        if not cursor.fetchone():
            error_msg = "Tabela 'uploads_historico' não encontrada no banco de dados"
            logger.error(error_msg)
            return jsonify({'success': False, 'message': error_msg}), 404
        
        # Remove todas as entradas do histórico
        cursor.execute('DELETE FROM uploads_historico')
        conn.commit()
        
        logger.info("Histórico de uploads limpo com sucesso")
        
        # Retorna uma lista vazia para atualizar a tabela no frontend
        return jsonify({
            'success': True, 
            'message': 'Histórico de uploads limpo com sucesso',
            'data': []
        })
        
    except Exception as e:
        error_msg = f"Erro ao limpar histórico de uploads: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': error_msg}), 500
    finally:
        if conn:
            conn.close()