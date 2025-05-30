"""
Alertas routes for the application.
Handles price alerts for assets.
"""
from flask import Blueprint, jsonify, request, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import logging

from src.models import db, Ativo, HistoricoPreco
from src.models.alerta import Alerta
from src.utils.logger import setup_logger

# Setup logger
alertas_logger = setup_logger('alertas_routes', 'alertas.log')

# Create blueprint
alertas_bp = Blueprint('alertas', __name__, url_prefix='/alertas')

@alertas_bp.route('/compra', methods=['GET'])
@login_required
def get_alertas_compra():
    """Get buy alerts for the current user."""
    try:
        alerts = Alerta.query.filter_by(
            usuario_id=current_user.id,
            tipo='compra',
            ativo=True
        ).order_by(Alerta.data_criacao.desc()).all()
        
        return jsonify({
            'success': True,
            'data': [{
                'id': alerta.id,
                'ticker': alerta.ativo.ticker if alerta.ativo else 'N/A',
                'nome': alerta.ativo.nome if alerta.ativo else 'Ativo não encontrado',
                'preco_alvo': alerta.preco_alvo,
                'preco_atual': alerta.ativo.preco_atual if alerta.ativo else 0,
                'data_criacao': alerta.data_criacao.isoformat(),
                'notas': alerta.notas or ''
            } for alerta in alerts]
        })
        
    except Exception as e:
        alertas_logger.error(f'Error getting buy alerts: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Erro ao buscar alertas de compra'
        }), 500

@alertas_bp.route('/venda', methods=['GET'])
@login_required
def get_alertas_venda():
    """Get sell alerts for the current user."""
    try:
        alerts = Alerta.query.filter_by(
            usuario_id=current_user.id,
            tipo='venda',
            ativo=True
        ).order_by(Alerta.data_criacao.desc()).all()
        
        return jsonify({
            'success': True,
            'data': [{
                'id': alerta.id,
                'ticker': alerta.ativo.ticker if alerta.ativo else 'N/A',
                'nome': alerta.ativo.nome if alerta.ativo else 'Ativo não encontrado',
                'preco_alvo': alerta.preco_alvo,
                'preco_atual': alerta.ativo.preco_atual if alerta.ativo else 0,
                'data_criacao': alerta.data_criacao.isoformat(),
                'notas': alerta.notas or ''
            } for alerta in alerts]
        })
        
    except Exception as e:
        alertas_logger.error(f'Error getting sell alerts: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Erro ao buscar alertas de venda'
        }), 500

@alertas_bp.route('/criar', methods=['POST'])
@login_required
def criar_alerta():
    """Create a new price alert."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['ticker', 'tipo', 'preco_alvo']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Campo obrigatório não informado: {field}'
                }), 400
        
        ticker = data['ticker'].upper()
        tipo = data['tipo'].lower()
        preco_alvo = float(data['preco_alvo'])
        notas = data.get('notas', '')
        
        # Validate alert type
        if tipo not in ['compra', 'venda']:
            return jsonify({
                'success': False,
                'error': 'Tipo de alerta inválido. Use "compra" ou "venda".'
            }), 400
        
        # Get or create the asset
        ativo = Ativo.query.filter_by(ticker=ticker).first()
        if not ativo:
            # If asset doesn't exist, create a new one
            ativo = Ativo(
                ticker=ticker,
                nome=ticker,  # Will be updated with real data later
                tipo='ACAO',  # Default type, can be updated later
                preco_atual=0,  # Will be updated later
                ultima_atualizacao=datetime.utcnow()
            )
            db.session.add(ativo)
            db.session.flush()  # Get the ID without committing
        
        # Create the alert
        alerta = Alerta(
            usuario_id=current_user.id,
            ativo_id=ativo.id,
            tipo=tipo,
            preco_alvo=preco_alvo,
            preco_atual=ativo.preco_atual or 0,
            ativo=True,
            data_criacao=datetime.utcnow(),
            notas=notas
        )
        
        db.session.add(alerta)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Alerta criado com sucesso!',
            'data': {
                'id': alerta.id,
                'ticker': ativo.ticker,
                'nome': ativo.nome,
                'tipo': alerta.tipo,
                'preco_alvo': alerta.preco_alvo,
                'preco_atual': alerta.preco_atual,
                'data_criacao': alerta.data_criacao.isoformat(),
                'notas': alerta.notas
            }
        })
        
    except Exception as e:
        db.session.rollback()
        alertas_logger.error(f'Error creating alert: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Erro ao criar alerta'
        }), 500

@alertas_bp.route('/atualizar/<int:alerta_id>', methods=['POST'])
@login_required
def atualizar_alerta(alerta_id):
    """Update an existing alert."""
    try:
        alerta = Alerta.query.get_or_404(alerta_id)
        
        # Verify ownership
        if alerta.usuario_id != current_user.id:
            return jsonify({
                'success': False,
                'error': 'Acesso não autorizado'
            }), 403
        
        data = request.get_json()
        
        # Update fields if provided
        if 'preco_alvo' in data:
            alerta.preco_alvo = float(data['preco_alvo'])
        
        if 'notas' in data:
            alerta.notas = data['notas']
        
        if 'ativo' in data:
            alerta.ativo = bool(data['ativo'])
        
        alerta.ultima_atualizacao = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Alerta atualizado com sucesso!',
            'data': {
                'id': alerta.id,
                'ticker': alerta.ativo.ticker if alerta.ativo else 'N/A',
                'tipo': alerta.tipo,
                'preco_alvo': alerta.preco_alvo,
                'preco_atual': alerta.preco_atual,
                'ativo': alerta.ativo,
                'ultima_atualizacao': alerta.ultima_atualizacao.isoformat(),
                'notas': alerta.notas
            }
        })
        
    except Exception as e:
        db.session.rollback()
        alertas_logger.error(f'Error updating alert {alerta_id}: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Erro ao atualizar alerta'
        }), 500

@alertas_bp.route('/excluir/<int:alerta_id>', methods=['DELETE'])
@login_required
def excluir_alerta(alerta_id):
    """Delete an alert."""
    try:
        alerta = Alerta.query.get_or_404(alerta_id)
        
        # Verify ownership
        if alerta.usuario_id != current_user.id:
            return jsonify({
                'success': False,
                'error': 'Acesso não autorizado'
            }), 403
        
        db.session.delete(alerta)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Alerta excluído com sucesso!'
        })
        
    except Exception as e:
        db.session.rollback()
        alertas_logger.error(f'Error deleting alert {alerta_id}: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Erro ao excluir alerta'
        }), 500

@alertas_bp.route('/verificar', methods=['POST'])
@login_required
def verificar_alertas():
    """Check all active alerts for the current user and return triggered ones."""
    try:
        # Get all active alerts for the user
        alertas = Alerta.query.filter_by(
            usuario_id=current_user.id,
            ativo=True
        ).all()
        
        triggered = []
        
        for alerta in alertas:
            if not alerta.ativo:
                continue
                
            # Get current price
            if not alerta.ativo or not alerta.ativo.preco_atual:
                continue
                
            preco_atual = alerta.ativo.preco_atual
            
            # Check if alert is triggered
            if (alerta.tipo == 'compra' and preco_atual <= alerta.preco_alvo) or \
               (alerta.tipo == 'venda' and preco_atual >= alerta.preco_alvo):
                
                # Add to triggered list
                triggered.append({
                    'id': alerta.id,
                    'ticker': alerta.ativo.ticker,
                    'nome': alerta.ativo.nome,
                    'tipo': alerta.tipo,
                    'preco_alvo': alerta.preco_alvo,
                    'preco_atual': preco_atual,
                    'data_criacao': alerta.data_criacao.isoformat(),
                    'notas': alerta.notas or ''
                })
                
                # Mark as triggered (optional: could disable the alert)
                # alerta.ativo = False
                # alerta.data_trigger = datetime.utcnow()
        
        # db.session.commit()
        
        return jsonify({
            'success': True,
            'data': triggered
        })
        
    except Exception as e:
        alertas_logger.error(f'Error checking alerts: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Erro ao verificar alertas'
        }), 500
