import os
import sys
from pathlib import Path
from datetime import datetime
from flask import (
    render_template, request, redirect, url_for, flash, jsonify, current_app, g
)
from werkzeug.security import generate_password_hash, check_password_hash

# Adicionar o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, LogLevel, RequestContext, log_function

# Importar o blueprint do pacote
from . import bp

# Configurar logger
logger = get_logger('alertas_manuais.routes')

# Importações locais
from .models import Alerta, get_db_connection, init_db
from .forms import AlertaForm

def get_alertas_paginados(pagina=1, itens_por_pagina=10, prioridade=None):
    """Função auxiliar para obter alertas com paginação"""
    # Calcular o deslocamento
    offset = (pagina - 1) * itens_por_pagina
    
    # Construir a consulta
    query = """
        SELECT * FROM alertas_financas
        WHERE ativo = 1
    """
    params = []
    
    # Adicionar filtros
    if prioridade:
        query += " AND prioridade = ?"
        params.append(prioridade.lower())  # Garantir que a prioridade esteja em minúsculas
    
    # Ordenação
    query += " ORDER BY criado_em DESC"
    
    # Paginação
    query += " LIMIT ? OFFSET ?"
    params.extend([itens_por_pagina, offset])
    
    # Executar a consulta
    logger.debug(f'Executando consulta: {query} com parâmetros {params}')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    alertas = []
    
    # Converter os resultados para objetos Alerta
    for row in cursor.fetchall():
        alerta_dict = dict(row)
        # Converter valores booleanos de volta para Python
        for key in ['notificar_email', 'notificar_app', 'ativo']:
            if key in alerta_dict:
                alerta_dict[key] = bool(alerta_dict[key])
        alertas.append(Alerta(**alerta_dict))
    
    # Contar o total de registros para paginação
    count_query = "SELECT COUNT(*) as total FROM alertas_financas WHERE ativo = 1"
    count_params = []
    
    if prioridade:
        count_query += " AND prioridade = ?"
        count_params.append(prioridade.lower())
    
    total_registros = conn.execute(count_query, count_params).fetchone()['total']
    total_paginas = (total_registros + itens_por_pagina - 1) // itens_por_pagina if itens_por_pagina > 0 else 1
    
    # Fechar a conexão
    conn.close()
    
    return alertas, total_registros, total_paginas

@bp.route('/')
@log_function(level=LogLevel.INFO, log_args=True, log_result=False, track_performance=True)
def index():
    """Rota principal que exibe a lista de alertas."""
    print("Acessando a rota / do blueprint alertas_manuais")
    
    # Valores padrão
    contexto = {
        'alertas': [],
        'pagina_atual': 1,
        'total_paginas': 1,
        'prioridade': None,
        'erro': None
    }
    
    try:
        # Inicializar o contexto da requisição
        print("Iniciando processamento da rota /alertas-manuais/")
        request_id = RequestContext.set_request_context()
        logger.info(f'Iniciando requisição {request_id} para listar alertas')
        
        # Inicializar o banco de dados se necessário
        logger.debug('Inicializando banco de dados')
        init_db()
        print("Banco de dados inicializado com sucesso")
        
        # Obter parâmetros da requisição
        pagina = request.args.get('pagina', 1, type=int)
        itens_por_pagina = current_app.config.get('ITENS_POR_PAGINA', 10)
        prioridade = request.args.get('prioridade')
        
        logger.debug(f'Parâmetros - Página: {pagina}, Itens por página: {itens_por_pagina}, Prioridade: {prioridade}')
        
        # Obter alertas paginados
        alertas, total_registros, total_paginas = get_alertas_paginados(
            pagina=pagina,
            itens_por_pagina=itens_por_pagina,
            prioridade=prioridade
        )
        
        logger.info(f'Consulta retornou {len(alertas)} alertas de um total de {total_registros}')
        
        # Atualizar contexto
        contexto.update({
            'alertas': alertas,
            'pagina_atual': pagina,
            'total_paginas': total_paginas,
            'prioridade': prioridade
        })
        
    except Exception as e:
        logger.error(f'Erro ao carregar alertas: {e}', exc_info=True)
        contexto['erro'] = str(e)
        flash('Ocorreu um erro ao carregar os alertas.', 'danger')
    finally:
        if 'request_id' in locals():
            logger.info(f'Finalizando requisição {request_id}')
    
    # Renderizar o template com o contexto
    return render_template('AlertaManuaisIndex.html', **contexto)

@bp.route('/api/alertas', methods=['GET'])
@log_function(level=LogLevel.INFO, log_args=True, log_result=False)
def api_alertas():
    """API para obter a lista de alertas em formato JSON."""
    try:
        # Inicializar o contexto da requisição
        request_id = RequestContext.set_request_context()
        logger.info(f'Iniciando requisição API {request_id} para listar alertas')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obter parâmetros de consulta
        status = request.args.get('status', '').lower()  # Padroniza para minúsculas
        prioridade = request.args.get('prioridade')
        tipo = request.args.get('tipo')
        busca = request.args.get('busca', '').strip()
        
        logger.debug(f'Parâmetros brutos - status: {request.args.get("status")}, status processado: {status}')
        
        # Parâmetros de paginação
        pagina = int(request.args.get('pagina', 1))
        itens_por_pagina = int(request.args.get('itens_por_pagina', 10))
        
        # Calcular o offset
        offset = (pagina - 1) * itens_por_pagina
        
        logger.debug(f'Parâmetros API - Status: {status}, Prioridade: {prioridade}, Tipo: {tipo}, Busca: {busca}, Página: {pagina}, Itens por página: {itens_por_pagina}')
        
        # Construir a consulta base
        query = """
            SELECT * 
            FROM alertas_financas 
            WHERE 1=1
        """
        count_query = "SELECT COUNT(*) as total FROM alertas_financas WHERE 1=1"
        params = []
        
        # Filtrar por status (ativo/inativo)
        if status == 'ativo':
            query += " AND ativo = 1"
            count_query += " AND ativo = 1"
            logger.debug('Aplicando filtro: status = ativo')
        elif status == 'inativo':
            query += " AND ativo = 0"
            count_query += " AND ativo = 0"
            logger.debug('Aplicando filtro: status = inativo')
        # Se for vazio ou qualquer outro valor, não aplica filtro de ativo
        
        # Adicionar filtros
        if prioridade and prioridade.lower() in ['alta', 'media', 'baixa']:
            query += " AND prioridade = ?"
            count_query += " AND prioridade = ?"
            params.append(prioridade.lower())
            
        if tipo and tipo in ['acima_media', 'abaixo_media', 'meta_atingida', 'limite_gasto']:
            query += " AND tipo_alerta = ?"
            count_query += " AND tipo_alerta = ?"
            params.append(tipo)
            
        if busca:
            search_term = f"%{busca}%"
            query += " AND (descricao LIKE ? OR tipo_alerta LIKE ?)"
            count_query += " AND (descricao LIKE ? OR tipo_alerta LIKE ?)"
            params.extend([search_term, search_term])
        
        # Ordenação
        query += " ORDER BY criado_em DESC"
        
        # Adicionar paginação
        query += " LIMIT ? OFFSET ?"
        
        # Executar a consulta de contagem total
        logger.debug(f'Executando contagem: {count_query} com parâmetros {params}')
        cursor.execute(count_query, params)
        total_registros = cursor.fetchone()['total']
        
        # Contar apenas os alertas ativos para a estatística
        cursor.execute("SELECT COUNT(*) as total_ativos FROM alertas_financas WHERE ativo = 1")
        total_ativos = cursor.fetchone()['total_ativos']
        
        # Adicionar parâmetros de paginação para a consulta principal
        params.extend([itens_por_pagina, offset])
        
        # Executar a consulta principal
        logger.debug(f'Executando consulta API: {query} com parâmetros {params}')
        cursor.execute(query, params)
        
        # Processar resultados
        alertas = []
        valor_total = 0
        
        for row in cursor.fetchall():
            alerta_dict = dict(row)
            # Converter valores booleanos
            for key in ['notificar_email', 'notificar_app', 'ativo']:
                if key in alerta_dict:
                    alerta_dict[key] = bool(alerta_dict[key])
            
            # Calcular valor total (soma dos valores de referência)
            if alerta_dict.get('valor_referencia'):
                valor_total += float(alerta_dict['valor_referencia'])
                
            alertas.append(alerta_dict)
        
        # Fechar a conexão
        conn.close()
        
        logger.info(f'Consulta API retornou {len(alertas)} de {total_registros} alertas totais (ativos: {total_ativos})')
        
        return jsonify({
            'success': True,
            'data': alertas,
            'total': total_registros,
            'ativos': total_ativos,  # Retorna a contagem real de alertas ativos
            'valor_total': valor_total,
            'pagina_atual': pagina,
            'total_paginas': (total_registros + itens_por_pagina - 1) // itens_por_pagina if itens_por_pagina > 0 else 1,
            'request_id': request_id
        })
        
    except Exception as e:
        logger.error(f'Erro na API de alertas: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor',
            'error': str(e),
            'request_id': request_id if 'request_id' in locals() else None
        }), 500
    finally:
        if 'request_id' in locals():
            logger.info(f'Finalizando requisição API {request_id}')

@bp.route('/api/alertas', methods=['POST', 'OPTIONS'], endpoint='api_novo_alerta')
@bp.route('/novo', methods=['POST', 'OPTIONS'], endpoint='novo_alerta')
@log_function(level=LogLevel.INFO, log_args=True, log_result=True, track_performance=True)
def novo_alerta():
    """Cria um novo alerta no sistema."""
    # Configurar cabeçalhos CORS
    if request.method == 'OPTIONS':
        response = current_app.make_default_options_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-Requested-With')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
        
    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type, X-Requested-With',
        'Content-Type': 'application/json'
    }
    
    try:
        # Verificar se é uma requisição JSON
        if not request.is_json:
            logger.warning('Requisição sem cabeçalho Content-Type: application/json')
            return jsonify({
                'sucesso': False,
                'mensagem': 'Content-Type deve ser application/json'
            }), 400, response_headers
            
        # Obter dados do formulário
        dados = request.get_json()
        
        # Log dos dados recebidos
        logger.info(f'Dados recebidos: {dados}')
        logger.info(f'Headers: {dict(request.headers)}')
        logger.info(f'Content-Type: {request.content_type}')
        logger.info(f'Request method: {request.method}')
        logger.info(f'Request URL: {request.url}')
        
        # Validar dados obrigatórios
        campos_obrigatorios = ['titulo', 'prioridade', 'status', 'valor_referencia', 'tipo_alerta']
        campos_faltantes = [campo for campo in campos_obrigatorios if campo not in dados or not dados[campo]]
        
        # Validar tipo de alerta
        if 'tipo_alerta' in dados and dados['tipo_alerta'] not in ['receita', 'despesa']:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Tipo de alerta inválido. Use "receita" ou "despesa"'
            }), 400, response_headers
        
        if campos_faltantes:
            logger.warning(f'Dados obrigatórios faltando: {campos_faltantes}', extra={'dados': dados})
            mensagem_erro = f'Campos obrigatórios faltando: {", ".join(campos_faltantes)}'
            logger.warning(mensagem_erro)
            return jsonify({
                'sucesso': False,
                'mensagem': mensagem_erro
            }), 400, response_headers
            
        # Processar valores numéricos
        try:
            valor_referencia = float(dados.get('valor_referencia', 0)) if dados.get('valor_referencia') else 0
        except (ValueError, TypeError):
            return jsonify({
                'sucesso': False,
                'mensagem': 'Valor de referência inválido. Use números decimais com ponto (ex: 100.50)'
            }), 400, response_headers
            
        # Processar datas
        data_inicio = dados.get('data_inicio')
        data_fim = dados.get('data_fim')
        
        # Validar datas
        if data_inicio and data_fim and data_inicio > data_fim:
            return jsonify({
                'sucesso': False,
                'mensagem': 'A data de início não pode ser posterior à data de término.'
            }), 400, response_headers
        
        # Conectar ao banco de dados
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Inserir novo alerta
        cursor.execute("""
            INSERT INTO alertas_financas 
            (usuario_id, tipo_alerta, descricao, valor_referencia, categoria, 
             data_inicio, data_fim, prioridade, notificar_email, notificar_app, ativo, criado_em, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (
            1,  # TODO: Obter ID do usuário logado
            dados.get('tipo_alerta', 'despesa'),  # Tipo de alerta (receita/despesa)
            dados.get('titulo', 'Sem título').strip(),  # Título do alerta (vai para a coluna descricao)
            valor_referencia,  # Valor de referência
            dados.get('categoria', 'outros').strip().lower() if dados.get('categoria') else 'outros',  # Categoria
            data_inicio if data_inicio else None,  # Data de início (opcional)
            data_fim if data_fim else None,  # Data de término (opcional)
            dados.get('prioridade', 'média').lower(),  # Prioridade (padrão: média)
            bool(dados.get('notificar_email', True)),  # Notificar por email
            bool(dados.get('notificar_app', True)),  # Notificar no app
            dados.get('status', 'ativo') == 'ativo'  # Ativo baseado no status
        ))
        
        # Obter o ID do alerta inserido
        alerta_id = cursor.lastrowid
        
        # Commit e fechar conexão
        conn.commit()
        conn.close()
        
        logger.info(f'Alerta criado com sucesso. ID: {alerta_id}')
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Alerta criado com sucesso!',
            'alerta_id': alerta_id
        }), 201, response_headers
        
    except Exception as e:
        logger.error(f'Erro ao criar alerta: {str(e)}', exc_info=True)
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({
            'sucesso': False,
            'mensagem': f'Erro ao criar alerta: {str(e)}'
        }), 500, response_headers

@bp.route('/api/alertas/<int:alerta_id>', methods=['GET'])
@log_function(level=LogLevel.INFO, log_args=True, log_result=True)
def obter_alerta(alerta_id):
    """Obtém os dados de um alerta específico."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar o alerta pelo ID
        cursor.execute("""
            SELECT id, usuario_id, tipo_alerta, descricao, valor_referencia, categoria, 
                   data_inicio, data_fim, prioridade, notificar_email, notificar_app, ativo
            FROM alertas_financas 
            WHERE id = ?
        """, (alerta_id,))
        
        alerta = cursor.fetchone()
        conn.close()
        
        if not alerta:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Alerta não encontrado.'
            }), 404
        
        # Converter para dicionário
        alerta_dict = dict(alerta)
        
        # Converter valores booleanos para 0/1
        for key in ['notificar_email', 'notificar_app', 'ativo']:
            if key in alerta_dict:
                alerta_dict[key] = 1 if alerta_dict[key] else 0
        
        return jsonify({
            'sucesso': True,
            'alerta': alerta_dict
        })
        
    except Exception as e:
        logger.error(f'Erro ao buscar alerta: {str(e)}', exc_info=True)
        return jsonify({
            'sucesso': False,
            'mensagem': f'Erro ao buscar alerta: {str(e)}'
        }), 500

@bp.route('/api/alertas/<int:alerta_id>', methods=['PUT'])
@log_function(level=LogLevel.INFO, log_args=True, log_result=True)
def atualizar_alerta(alerta_id):
    """Atualiza um alerta existente."""
    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type, X-Requested-With',
        'Content-Type': 'application/json'
    }
    
    try:
        # Verificar se é uma requisição JSON
        if not request.is_json:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Content-Type deve ser application/json'
            }), 400, response_headers
            
        # Obter dados do formulário
        dados = request.get_json()
        
        # Validar dados obrigatórios
        campos_obrigatorios = ['descricao', 'prioridade', 'valor_referencia', 'tipo_alerta']
        campos_faltantes = [campo for campo in campos_obrigatorios if campo not in dados or dados[campo] is None]
        
        if campos_faltantes:
            return jsonify({
                'sucesso': False,
                'mensagem': f'Campos obrigatórios faltando: {", ".join(campos_faltantes)}'
            }), 400, response_headers
            
        # Validar tipo de alerta
        if 'tipo_alerta' in dados and dados['tipo_alerta'] not in ['receita', 'despesa']:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Tipo de alerta inválido. Use "receita" ou "despesa"'
            }), 400, response_headers
            
        # Processar valores numéricos
        try:
            valor_referencia = float(dados.get('valor_referencia', 0)) if dados.get('valor_referencia') is not None else 0
        except (ValueError, TypeError):
            return jsonify({
                'sucesso': False,
                'mensagem': 'Valor de referência inválido. Use números decimais com ponto (ex: 100.50)'
            }), 400, response_headers
            
        # Processar datas
        data_inicio = dados.get('data_inicio')
        data_fim = dados.get('data_fim')
        
        # Validar datas
        if data_inicio and data_fim and data_inicio > data_fim:
            return jsonify({
                'sucesso': False,
                'mensagem': 'A data de início não pode ser posterior à data de término.'
            }), 400, response_headers
        
        # Conectar ao banco de dados
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se o alerta existe
        cursor.execute("SELECT id FROM alertas_financas WHERE id = ?", (alerta_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({
                'sucesso': False,
                'mensagem': 'Alerta não encontrado.'
            }), 404, response_headers
        
        # Atualizar alerta
        cursor.execute("""
            UPDATE alertas_financas 
            SET descricao = ?,
                tipo_alerta = ?,
                valor_referencia = ?,
                categoria = ?,
                data_inicio = ?,
                data_fim = ?,
                prioridade = ?,
                notificar_email = ?,
                notificar_app = ?,
                ativo = ?,
                atualizado_em = datetime('now')
            WHERE id = ?
        """, (
            dados.get('descricao', '').strip(),
            dados.get('tipo_alerta', 'despesa'),
            valor_referencia,
            dados.get('categoria', 'outros').strip().lower() if dados.get('categoria') else 'outros',
            data_inicio if data_inicio else None,
            data_fim if data_fim else None,
            dados.get('prioridade', 'média').lower(),
            bool(dados.get('notificar_email', True)),
            bool(dados.get('notificar_app', True)),
            bool(dados.get('ativo', True)),
            alerta_id
        ))
        
        # Commit e fechar conexão
        conn.commit()
        conn.close()
        
        logger.info(f'Alerta {alerta_id} atualizado com sucesso')
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Alerta atualizado com sucesso!',
            'alerta_id': alerta_id
        }), 200, response_headers
        
    except Exception as e:
        logger.error(f'Erro ao atualizar alerta: {str(e)}', exc_info=True)
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({
            'sucesso': False,
            'mensagem': f'Erro ao atualizar alerta: {str(e)}'
        }), 500, response_headers

@bp.route('/api/alertas/<int:alerta_id>', methods=['DELETE'])
@log_function(level=LogLevel.INFO, log_args=True, log_result=True)
def excluir_alerta(alerta_id):
    """Exclui permanentemente um alerta pelo ID."""
    request_id = None
    conn = None
    
    try:
        # Configura o contexto da requisição
        request_id = RequestContext.set_request_context()
        logger.info(f'[{request_id}] Iniciando exclusão do alerta ID: {alerta_id}')
        
        # Obter informações do usuário autenticado, se disponível
        usuario_info = 'Não autenticado'
        if hasattr(g, 'usuario') and hasattr(g.usuario, 'id'):
            usuario_info = f'ID: {g.usuario.id}'
        logger.info(f'[{request_id}] Usuário: {usuario_info}')
        
        # Obter informações do alerta antes da exclusão para registro
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar detalhes do alerta para log
        cursor.execute(
            """
            SELECT id, tipo_alerta, descricao, prioridade, usuario_id, criado_em 
            FROM alertas_financas 
            WHERE id = ?
            """, 
            (alerta_id,)
        )
        alerta = cursor.fetchone()
        
        if not alerta:
            logger.warning(f'[{request_id}] Tentativa de excluir alerta inexistente: ID {alerta_id}')
            return jsonify({
                'success': False,
                'message': 'Alerta não encontrado',
                'request_id': request_id
            }), 404
        
        # Registrar detalhes do alerta que será excluído
        logger.info(
            f'[{request_id}] Dados do alerta a ser excluído - '
            f'ID: {alerta[0]}, Tipo: {alerta[1]}, '
            f'Prioridade: {alerta[3]}, Criado em: {alerta[5]}'
        )
        
        # Verificar se o usuário tem permissão para excluir (opcional)
        if hasattr(g, 'usuario') and hasattr(g.usuario, 'id') and g.usuario.id != alerta[4]:
            logger.warning(
                f'[{request_id}] Tentativa de exclusão não autorizada. '
                f'Usuário {g.usuario.id} tentou excluir alerta do usuário {alerta[4]}'
            )
            return jsonify({
                'success': False,
                'message': 'Não autorizado',
                'request_id': request_id
            }), 403
        
        # Registrar contagem de alertas antes da exclusão
        cursor.execute("SELECT COUNT(*) FROM alertas_financas WHERE usuario_id = ?", (alerta[4],))
        total_alertas_antes = cursor.fetchone()[0]
        logger.info(f'[{request_id}] Total de alertas do usuário antes da exclusão: {total_alertas_antes}')
        
        # Excluir o alerta permanentemente
        logger.info(f'[{request_id}] Executando exclusão do alerta ID: {alerta_id}')
        cursor.execute("DELETE FROM alertas_financas WHERE id = ?", (alerta_id,))
        
        # Verificar se a exclusão foi bem-sucedida
        if cursor.rowcount == 0:
            logger.error(f'[{request_id}] Nenhum registro foi excluído. ID: {alerta_id}')
            return jsonify({
                'success': False,
                'message': 'Nenhum registro foi excluído',
                'request_id': request_id
            }), 500
        
        conn.commit()
        
        # Registrar contagem de alertas após a exclusão
        cursor.execute("SELECT COUNT(*) FROM alertas_financas WHERE usuario_id = ?", (alerta[4],))
        total_alertas_depois = cursor.fetchone()[0]
        logger.info(f'[{request_id}] Total de alertas do usuário após a exclusão: {total_alertas_depois}')
        
        logger.info(f'[{request_id}] Alerta ID {alerta_id} excluído com sucesso')
        
        return jsonify({
            'success': True,
            'message': 'Alerta excluído com sucesso',
            'request_id': request_id,
            'alerta_id': alerta_id
        })
        
    except Exception as e:
        if conn is not None:
            conn.rollback()
        error_msg = f'Erro ao excluir o alerta ID {alerta_id}: {str(e)}'
        logger.error(f'[{request_id if request_id else "NO_REQUEST"}] {error_msg}', exc_info=True)
        
        return jsonify({
            'success': False,
            'message': 'Ocorreu um erro ao excluir o alerta',
            'error': str(e),
            'request_id': request_id,
            'alerta_id': alerta_id
        }), 500
        
    finally:
        if conn is not None:
            try:
                conn.close()
                logger.debug(f'[{request_id if request_id else "NO_REQUEST"}] Conexão com o banco de dados fechada')
            except Exception as e:
                logger.error(f'[{request_id if request_id else "NO_REQUEST"}] Erro ao fechar conexão com o banco: {str(e)}')
        
        if request_id is not None:
            logger.info(f'[{request_id}] Finalizada requisição de exclusão do alerta ID: {alerta_id}')
