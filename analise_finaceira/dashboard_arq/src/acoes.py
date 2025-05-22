from flask import Blueprint, request, jsonify, redirect, url_for, flash, make_response
from flask_cors import cross_origin
from sqlalchemy import text
import os
import sqlite3
from datetime import datetime
import sys

# Adiciona o diretório raiz ao path para importar o logger
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from logger import get_logger, LogLevel, RequestContext

# Configura o logger para o módulo acoes
logger = get_logger("acoes")

# Configuração do logger já foi feita na importação

# Cria o blueprint para as rotas de ações
acoes_bp = Blueprint('acoes', __name__)
logger.info("Blueprint 'acoes' criado")

def get_db_connection():
    """Conecta ao banco de dados SQLite."""
    try:
        # Obtém o diretório base do projeto
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # Define o caminho para o banco de dados
        db_path = os.path.join(base_dir, 'banco', 'financas.db')
        
        # Verifica se o diretório do banco existe, se não existir, cria
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            logger.info(f"Criando diretório do banco de dados: {db_dir}")
            os.makedirs(db_dir, exist_ok=True)
        
        # Conecta ao banco de dados
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        logger.debug(f"Conexão com o banco de dados estabelecida: {db_path}")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}", exc_info=True)
        return None

@acoes_bp.route('/excluir_transacao/<int:transacao_id>', methods=['DELETE'])
def excluir_transacao(transacao_id):
    """Exclui uma transação do banco de dados."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verifica se a transação existe
        cursor.execute(
            'SELECT id FROM transacoes WHERE id = ?',
            (transacao_id,)
        )
        transacao = cursor.fetchone()
        
        if not transacao:
            return jsonify({'success': False, 'message': 'Transação não encontrada'}), 404
        
        # Exclui a transação
        cursor.execute(
            'DELETE FROM transacoes WHERE id = ?',
            (transacao_id,)
        )
        conn.commit()
        
        logger.info(f"Transação {transacao_id} excluída com sucesso")
        return jsonify({'success': True, 'message': 'Transação excluída com sucesso'})
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao excluir transação {transacao_id}: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro ao excluir transação: {str(e)}'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@acoes_bp.route('/editar_transacao/<int:transacao_id>', methods=['GET', 'POST', 'OPTIONS'])
@cross_origin()
def editar_transacao(transacao_id):
    """Edita uma transação existente."""
    logger.info("\n" + "="*50)
    logger.info(f"=== NOVA REQUISIÇÃO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    # Função para criar uma resposta com CORS
    def make_cors_response(data, status_code=200):
        response = jsonify(data)
        response.status_code = status_code
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-CSRFToken')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response
    
    # Define o contexto da requisição
    request_id = RequestContext.set_request_context()
    
    # Responde a requisições OPTIONS para CORS
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-CSRFToken')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response
    
    # Se for uma requisição OPTIONS, já retornamos acima
    if request.method == 'OPTIONS':
        return '', 204
        
    # Log da requisição
    logger.info("Iniciando processamento da requisição", extra={
        'method': request.method,
        'url': request.url,
        'view_args': request.view_args,
        'content_type': request.headers.get('Content-Type', '')
    })
    
    # Processa os dados recebidos
    data = None
    if request.method == 'POST':
        content_type = request.headers.get('Content-Type', '').lower()
        if 'application/json' in content_type:
            data = request.get_json(silent=True)
            logger.debug("Dados JSON recebidos", extra={'data': data})
        else:
            data = request.form.to_dict()
            logger.debug("Dados de formulário recebidos", extra={'data': data})

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'GET':
            logger.info(f"Buscando transação com ID: {transacao_id}")
            # Busca os dados da transação
            cursor.execute('SELECT * FROM transacoes WHERE id = ?', (transacao_id,))
            columns = [column[0] for column in cursor.description]
            transacao = cursor.fetchone()
            
            if not transacao:
                logger.warning(f"Transação não encontrada", extra={'transacao_id': transacao_id})
                return make_cors_response(
                    {'success': False, 'message': 'Transação não encontrada'},
                    404
                )
            
            # Converte a tupla para dicionário
            transacao_dict = dict(zip(columns, transacao))
            logger.debug("Dados da transação encontrados", extra={
                'transacao_id': transacao_id,
                'dados': {k: v for k, v in transacao_dict.items() if k != 'senha'}  # Exclui campos sensíveis
            })
            
            # Formata a data para exibição
            if 'data' in transacao_dict and transacao_dict['data']:
                if isinstance(transacao_dict['data'], str):
                    transacao_dict['data'] = transacao_dict['data'].split(' ')[0]
                elif hasattr(transacao_dict['data'], 'strftime'):
                    transacao_dict['data'] = transacao_dict['data'].strftime('%Y-%m-%d')
                else:
                    transacao_dict['data'] = str(transacao_dict['data'])
            
            logger.info("Dados da transação formatados com sucesso", extra={'transacao_id': transacao_id})
            return make_cors_response({'success': True, 'data': transacao_dict})
            
        elif request.method == 'POST':
            logger.info("Iniciando atualização de transação", extra={'transacao_id': transacao_id})
            
            if not data:
                logger.error("Nenhum dado recebido para atualização", extra={'transacao_id': transacao_id})
                return make_cors_response(
                    {'success': False, 'message': 'Nenhum dado recebido'},
                    400
                )
            
            # Validação dos dados obrigatórios
            required_fields = ['descricao', 'valor', 'tipo', 'categoria']
            missing_fields = [field for field in required_fields if field not in data or not data[field]]
            
            if missing_fields:
                logger.error("Campos obrigatórios ausentes", extra={
                    'transacao_id': transacao_id,
                    'missing_fields': missing_fields,
                    'dados_recebidos': list(data.keys())
                })
                return make_cors_response({
                    'success': False, 
                    'message': f'Campos obrigatórios ausentes: {", ".join(missing_fields)}'
                }, 400)
            
            # Verifica se a transação ainda existe antes de tentar atualizar
            cursor.execute('SELECT id FROM transacoes WHERE id = ?', (transacao_id,))
            if not cursor.fetchone():
                logger.warning(f"Transação {transacao_id} não encontrada antes da atualização")
                return make_cors_response(
                    {'success': False, 'message': 'Transação não encontrada'},
                    404
                )
            
            # Converte os valores para os tipos corretos
            try:
                valor = float(data.get('valor', 0)) if data.get('valor') else 0.0
                quantidade = float(data.get('quantidade', 0)) if data.get('quantidade') else 0.0
                preco = float(data.get('preco', 0)) if data.get('preco') else 0.0
                taxa = float(data.get('taxa', 0)) if data.get('taxa') else 0.0
                
                # Se for despesa, garante que o valor seja negativo
                tipo = data.get('tipo', '').lower()
                if tipo == 'despesa' and valor > 0:
                    valor = -valor
                    logger.debug("Valor convertido para negativo para despesa", 
                               extra={'valor_original': abs(valor), 'valor_convertido': valor})
                
            except (ValueError, TypeError) as e:
                logger.error(f"Erro ao converter valores numéricos: {str(e)}")
                return make_cors_response(
                    {'success': False, 'message': 'Valores numéricos inválidos'},
                    400
                )
            
            # Mapeia os campos para o banco de dados com tipos corretos
            update_fields = {
                'data': data.get('data', ''),
                'descricao': data.get('descricao', '').strip(),
                'valor': valor,
                'tipo': data.get('tipo', '').lower(),
                'categoria': data.get('categoria', '').lower(),
                'ativo': data.get('ativo', '').upper() if data.get('ativo') else '',
                'quantidade': quantidade,
                'preco': preco,
                'taxa': taxa,
                'forma_pagamento': data.get('forma_pagamento', '').lower()
            }
            
            logger.info("Campos preparados para atualização", extra={
                'transacao_id': transacao_id,
                'campos': {k: v for k, v in update_fields.items() if k != 'senha'}
            })
            
            # Verifica se a transação existe antes de tentar atualizar
            cursor.execute('SELECT id FROM transacoes WHERE id = ?', (transacao_id,))
            if not cursor.fetchone():
                logger.warning("Transação não encontrada para atualização", 
                              extra={'transacao_id': transacao_id})
                return make_cors_response(
                    {'success': False, 'message': 'Transação não encontrada'},
                    404
                )
            
            # Inicia uma transação
            conn.execute('BEGIN')
            
            # Verifica novamente se a transação ainda existe dentro da transação
            cursor.execute('SELECT id FROM transacoes WHERE id = ?', (transacao_id,))
            if not cursor.fetchone():
                conn.rollback()
                logger.warning("Transação não encontrada durante a verificação de concorrência",
                              extra={'transacao_id': transacao_id})
                return make_cors_response(
                    {'success': False, 'message': 'Transação não encontrada'},
                    404
                )
            
            # Primeiro, vamos verificar os dados atuais da transação
            cursor.execute('SELECT * FROM transacoes WHERE id = ?', (transacao_id,))
            transacao_atual = cursor.fetchone()
            
            if not transacao_atual:
                conn.rollback()
                logger.warning("Transação não encontrada durante a verificação final",
                              extra={'transacao_id': transacao_id})
                return make_cors_response(
                    {'success': False, 'message': 'Transação não encontrada'},
                    404
                )
            
            # Log dos dados atuais para comparação
            logger.debug("Dados atuais da transação", extra={
                'transacao_id': transacao_id,
                'dados_atuais': dict(zip([column[0] for column in cursor.description], transacao_atual))
            })
            
            # Constrói a consulta SQL dinamicamente
            set_clause = ", ".join([f"{field} = ?" for field in update_fields.keys()])
            params = list(update_fields.values()) + [transacao_id]
            
            query = f"""
                UPDATE transacoes 
                SET {set_clause}, data_importacao = datetime('now')
                WHERE id = ?
            """
            
            logger.debug("Query de atualização preparada", extra={
                'transacao_id': transacao_id,
                'query': query,
                'params': params
            })
            
            # Executa a atualização
            cursor.execute(query, params)
            
            # Verifica se alguma linha foi afetada
            if cursor.rowcount == 0:
                conn.rollback()
                logger.warning("Nenhuma linha afetada ao atualizar transação",
                              extra={'transacao_id': transacao_id})
                
                # Verifica novamente se a transação existe
                cursor.execute('SELECT id FROM transacoes WHERE id = ?', (transacao_id,))
                if not cursor.fetchone():
                    logger.error("Confirmação: Transação não encontrada na tabela",
                                extra={'transacao_id': transacao_id})
                    return make_cors_response(
                        {'success': False, 'message': 'Transação não encontrada'},
                        404
                    )
                else:
                    logger.error("A transação existe, mas não foi possível atualizá-la",
                                extra={'transacao_id': transacao_id})
                    return make_cors_response(
                        {'success': False, 'message': 'Falha ao atualizar a transação (possível problema de concorrência)'},
                        409  # Conflict
                    )
            
            # Confirma a transação
            conn.commit()
            
            logger.info("Transação atualizada com sucesso",
                       extra={'transacao_id': transacao_id, 'linhas_afetadas': cursor.rowcount})
            
            # Retorna sucesso (o commit já foi feito)
            return make_cors_response({
                'success': True, 
                'message': 'Transação atualizada com sucesso',
                'transacao_id': transacao_id
            })
            
    except Exception as e:
        logger.error("Erro ao processar a transação", 
                    extra={'transacao_id': transacao_id, 'error': str(e)}, 
                    exc_info=True)
        if conn:
            try:
                conn.rollback()
            except Exception as rollback_error:
                logger.error("Erro ao fazer rollback da transação", 
                            extra={'transacao_id': transacao_id, 'error': str(rollback_error)})
        
        return make_cors_response(
            {'success': False, 'message': f'Erro ao editar transação: {str(e)}'},
            500
        )
    finally:
        if conn:
            try:
                conn.close()
            except Exception as close_error:
                logger.error("Erro ao fechar conexão com o banco de dados",
                            extra={'transacao_id': transacao_id, 'error': str(close_error)})
    
    # Se chegou até aqui, é um método não suportado
    return make_cors_response(
        {'success': False, 'message': 'Método não suportado'},
        405
    )

def init_app(app):
    """Registra o blueprint na aplicação."""
    app.register_blueprint(acoes_bp, url_prefix='/acoes')
