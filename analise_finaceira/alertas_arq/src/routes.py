import os
import sys
from pathlib import Path
from flask import render_template, request, jsonify, redirect, url_for, flash, current_app, session
from flask_wtf.csrf import generate_csrf, validate_csrf
from . import alertas_bp
from .models import Alerta, HistoricoAlerta
from datetime import datetime
import functools
import json

@alertas_bp.route('/api/csrf-token', methods=['GET'])
def get_csrf_token():
    """Rota para obter o token CSRF"""
    return jsonify({
        'success': True,
        'csrf_token': generate_csrf()
    })

# Adiciona o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, log_function, RequestContext

# Configura o logger para este módulo
logger = get_logger("alertas.routes")

def log_route(route_name):
    """Decorator para logar informações das rotas"""
    def decorator(f):
        @functools.wraps(f)
        @log_function(logger_instance=logger, level="INFO")
        def wrapper(*args, **kwargs):
            RequestContext.update_context(endpoint=route_name)
            logger.info(f"Acessando rota: {route_name}")
            return f(*args, **kwargs)
        return wrapper
    return decorator

@alertas_bp.route('/')
@alertas_bp.route('/alertas')
@log_route('listar_alertas')
def alertas():
    """Rota principal para a página de alertas"""
    try:
        # Busca todos os alertas ativos para exibir na lista
        alertas = Alerta.get_all({"ativo": 1})
        # Converte os objetos Alerta para dicionários
        alertas_list = [alerta.to_dict() for alerta in alertas]
        return render_template('alertas.html', alertas=alertas_list)
    except Exception as e:
        logger.error(f"Erro ao carregar página de alertas: {e}")
        flash("Ocorreu um erro ao carregar os alertas.", "danger")
        return render_template('alertas.html', alertas=[])

@alertas_bp.route('/api/alertas', methods=['GET'])
@log_route('api_get_alertas')
def get_alertas():
    """API para buscar alertas com filtros"""
    try:
        # Parâmetros de filtro
        ativo = request.args.get('ativo', type=int)
        tipo = request.args.get('tipo')
        prioridade = request.args.get('prioridade')
        
        # Log dos parâmetros recebidos
        logger.info(f"Buscando alertas com filtros - ativo: {ativo}, tipo: {tipo}, prioridade: {prioridade}")
        
        filtros = {}
        if ativo is not None:
            filtros['ativo'] = ativo
        if tipo:
            filtros['tipo'] = tipo
        if prioridade:
            filtros['prioridade'] = prioridade
            
        alertas = Alerta.get_all(filtros)
        
        # Log do resultado
        logger.info(f"Encontrados {len(alertas)} alertas com os filtros fornecidos")
        
        return jsonify({
            'success': True,
            'data': [alerta.to_dict() for alerta in alertas]
        })
    except Exception as e:
        logger.error(f"Erro ao buscar alertas: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Erro ao buscar alertas'
        }), 500

@alertas_bp.route('/api/alertas/<int:alerta_id>', methods=['GET'])
@log_route('api_get_alerta')
def get_alerta(alerta_id):
    """API para buscar um alerta específico"""
    try:
        alerta = Alerta.get_by_id(alerta_id)
        if alerta:
            return jsonify({
                'success': True,
                'data': alerta.to_dict()
            })
        return jsonify({
            'success': False,
            'message': 'Alerta não encontrado'
        }), 404
    except Exception as e:
        logger.error(f"Erro ao buscar alerta {alerta_id}: {e}")
        return jsonify({
            'success': False,
            'message': 'Erro ao buscar alerta'
        }), 500

@alertas_bp.route('/api/alertas', methods=['POST'])
@log_route('api_criar_alerta')
def criar_alerta():
    """API para criar um novo alerta"""
    try:
        # Log dos headers da requisição
        logger.info(f"Iniciando criação de novo alerta")
        logger.debug(f"Headers recebidos: {dict(request.headers)}")
        logger.debug(f"Content-Type: {request.content_type}")
        
        # Tenta obter os dados JSON
        try:
            data = request.get_json(force=True)
            logger.debug(f"Dados recebidos: {data}")
        except Exception as e:
            error_msg = f"Erro ao processar JSON: {str(e)}"
            logger.error(error_msg)
            return jsonify({
                'success': False,
                'message': 'Erro ao processar os dados da requisição',
                'error': error_msg
            }), 400
        
        # Verifica se há dados na requisição
        if not data:
            error_msg = "Nenhum dado recebido na requisição"
            logger.error(error_msg)
            return jsonify({
                'success': False,
                'message': error_msg
            }), 400
        
        # Verifica se os dados necessários estão presentes
        required_fields = ['tipo', 'descricao']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            error_msg = f'Campos obrigatórios não fornecidos: {', '.join(missing_fields)}'
            logger.warning(error_msg)
            return jsonify({
                'success': False,
                'message': error_msg,
                'missing_fields': missing_fields
            }), 400
            
        logger.debug(f"Dados validados com sucesso")
        
        # Cria o alerta
        try:
            logger.debug("Iniciando criação do registro no banco de dados")
            
            # Cria um dicionário com os dados do alerta
            alerta_data = {
                'tipo': data.get('tipo'),
                'descricao': data.get('descricao'),
                'status': data.get('status', 'pendente'),
                'prioridade': data.get('prioridade', 'media'),
                'valor_referencia': data.get('valor_referencia'),
                'data_limite': data.get('data_limite'),
                'usuario_id': data.get('usuario_id', 1),  # TODO: Obter do usuário autenticado
                'ativo_id': data.get('ativo_id'),
                'criado_por': data.get('criado_por', 'sistema')
            }
            
            logger.debug(f"Dados do alerta a serem salvos: {alerta_data}")
            
            # Cria o alerta no banco de dados
            alerta = Alerta(**alerta_data)
            db.session.add(alerta)
            db.session.commit()
            
            logger.info(f"Alerta criado com sucesso. ID: {alerta.id}")
            
            return jsonify({
                'success': True,
                'message': 'Alerta criado com sucesso',
                'alerta_id': alerta.id
            }), 201
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Erro ao criar alerta: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return jsonify({
                'success': False,
                'message': 'Erro ao criar alerta',
                'error': str(e)
            }), 500
            
    except Exception as e:
        error_msg = f"Erro inesperado ao processar a requisição: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor',
            'error': error_msg
        }), 500

@alertas_bp.route('/api/alertas/<int:alerta_id>', methods=['PUT'])
@log_route('api_atualizar_alerta')
def atualizar_alerta(alerta_id):
    """API para atualizar um alerta existente"""
    try:
        logger.info(f"Iniciando atualização do alerta ID: {alerta_id}")
        
        alerta = Alerta.get_by_id(alerta_id)
        if not alerta:
            logger.warning(f"Tentativa de atualização de alerta não encontrado. ID: {alerta_id}")
            return jsonify({
                'success': False,
                'message': 'Alerta não encontrado'
            }), 404
        
        # Faz uma cópia dos dados atuais para log
        dados_atuais = alerta.to_dict()
        
        data = request.get_json()
        
        # Log dos dados recebidos para atualização (sem dados sensíveis)
        log_data = data.copy()
        if 'valor_referencia' in log_data:
            log_data['valor_referencia'] = '***' if log_data['valor_referencia'] else None
        logger.info(f"Dados recebidos para atualização: {json.dumps(log_data, default=str)}")
        
        # Identifica e loga os campos que serão alterados
        campos_alterados = {}
        for key, value in data.items():
            if hasattr(alerta, key) and getattr(alerta, key) != value:
                campos_alterados[key] = {
                    'de': getattr(alerta, key),
                    'para': value
                }
        
        if not campos_alterados:
            logger.warning("Nenhum campo alterado na requisição de atualização")
        else:
            logger.info(f"Campos a serem atualizados: {json.dumps(campos_alterados, default=str)}")
        
        # Atualiza os campos fornecidos
        for key, value in data.items():
            if hasattr(alerta, key):
                setattr(alerta, key, value)
        
        if alerta.save():
            logger.info(f"Alerta ID {alerta_id} atualizado com sucesso")
            return jsonify({
                'success': True,
                'message': 'Alerta atualizado com sucesso',
                'data': alerta.to_dict()
            })
        
        error_msg = 'Falha ao salvar as alterações do alerta no banco de dados'
        logger.error(error_msg)
        return jsonify({
            'success': False,
            'message': error_msg
        }), 500
        
    except Exception as e:
        logger.error(f"Erro ao atualizar alerta {alerta_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Erro ao processar a requisição de atualização'
        }), 500

@alertas_bp.route('/api/alertas/<int:alerta_id>', methods=['DELETE'])
@log_route('api_deletar_alerta')
def deletar_alerta(alerta_id):
    """API para remover um alerta"""
    try:
        logger.info(f"Iniciando exclusão do alerta ID: {alerta_id}")
        
        alerta = Alerta.get_by_id(alerta_id)
        if not alerta:
            logger.warning(f"Tentativa de exclusão de alerta não encontrado. ID: {alerta_id}")
            return jsonify({
                'success': False,
                'message': 'Alerta não encontrado'
            }), 404
        
        # Faz uma cópia dos dados atuais para log
        dados_alerta = alerta.to_dict()
        if 'valor_referencia' in dados_alerta:
            dados_alerta['valor_referencia'] = '***' if dados_alerta['valor_referencia'] else None
        logger.info(f"Dados do alerta a ser excluído: {json.dumps(dados_alerta, default=str)}")
        
        if alerta.delete():
            logger.info(f"Alerta ID {alerta_id} excluído com sucesso")
            return jsonify({
                'success': True,
                'message': 'Alerta removido com sucesso'
            })
        
        error_msg = f'Falha ao excluir o alerta ID {alerta_id} do banco de dados'
        logger.error(error_msg)
        return jsonify({
            'success': False,
            'message': error_msg
        }), 500
        
    except Exception as e:
        logger.error(f"Erro ao excluir alerta {alerta_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Erro ao processar a requisição de exclusão'
        }), 500

@alertas_bp.route('/api/alertas/<int:alerta_id>/historico', methods=['GET'])
@log_route('api_get_historico_alerta')
def get_historico_alerta(alerta_id):
    """API para buscar o histórico de um alerta"""
    try:
        logger.info(f"Buscando histórico para o alerta ID: {alerta_id}")
        
        # Verifica se o alerta existe antes de buscar o histórico
        alerta = Alerta.get_by_id(alerta_id)
        if not alerta:
            logger.warning(f"Tentativa de buscar histórico para alerta não encontrado. ID: {alerta_id}")
            return jsonify({
                'success': False,
                'message': 'Alerta não encontrado'
            }), 404
        
        # Obtém o parâmetro de limite da query string (padrão: 10)
        limit = request.args.get('limit', default=10, type=int)
        logger.debug(f"Buscando até {limit} registros de histórico para o alerta ID: {alerta_id}")
        
        historico = HistoricoAlerta.get_historico_por_alerta(alerta_id, limit)
        
        logger.info(f"Encontrados {len(historico)} registros de histórico para o alerta ID: {alerta_id}")
        
        return jsonify({
            'success': True,
            'data': historico
        })
    except Exception as e:
        logger.error(f"Erro ao buscar histórico do alerta {alerta_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Erro ao processar a requisição de histórico'
        }), 500
