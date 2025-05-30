"""
Carteira routes for the application.
Handles portfolio-related operations.
"""
from flask import Blueprint, jsonify, request, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
import logging

from src.models import db, Ativo, HistoricoPreco
from src.models.carteira import Carteira, CarteiraAtivo
from src.utils.logger import setup_logger

# Setup logger
carteira_logger = setup_logger('carteira_routes', 'carteira.log')

# Create blueprint
carteira_bp = Blueprint('carteira', __name__, url_prefix='/carteira')

@carteira_bp.route('', methods=['GET'])
@login_required
def get_carteira():
    """Get user's portfolio."""
    try:
        # Get user's portfolio with assets
        portfolio = Carteira.query.filter_by(usuario_id=current_user.id).first()
        
        if not portfolio:
            return jsonify({
                'success': True,
                'data': {
                    'total_investido': 0,
                    'valor_atual': 0,
                    'lucro_prejuizo': 0,
                    'lucro_prejuizo_percentual': 0,
                    'ativos': []
                }
            })
        
        # Get portfolio assets with current prices
        portfolio_ativos = []
        total_investido = 0
        valor_atual_total = 0
        
        for ativo in portfolio.ativos:
            # Get current price
            preco_atual = ativo.ativo.preco_atual if ativo.ativo else 0
            
            # Calculate values
            valor_investido = ativo.quantidade * ativo.preco_medio
            valor_atual = ativo.quantidade * preco_atual
            lucro_prejuizo = valor_atual - valor_investido
            lucro_prejuizo_percentual = (lucro_prejuizo / valor_investido * 100) if valor_investido > 0 else 0
            
            total_investido += valor_investido
            valor_atual_total += valor_atual
            
            portfolio_ativos.append({
                'id': ativo.id,
                'ticker': ativo.ativo.ticker if ativo.ativo else 'N/A',
                'nome': ativo.ativo.nome if ativo.ativo else 'Ativo não encontrado',
                'quantidade': ativo.quantidade,
                'preco_medio': ativo.preco_medio,
                'valor_investido': valor_investido,
                'preco_atual': preco_atual,
                'valor_atual': valor_atual,
                'lucro_prejuizo': lucro_prejuizo,
                'lucro_prejuizo_percentual': lucro_prejuizo_percentual,
                'data_compra': ativo.data_compra.isoformat() if ativo.data_compra else None,
                'notas': ativo.notas or ''
            })
        
        # Calculate totals
        lucro_prejuizo_total = valor_atual_total - total_investido
        lucro_prejuizo_total_percent = (lucro_prejuizo_total / total_investido * 100) if total_investido > 0 else 0
        
        return jsonify({
            'success': True,
            'data': {
                'total_investido': total_investido,
                'valor_atual': valor_atual_total,
                'lucro_prejuizo': lucro_prejuizo_total,
                'lucro_prejuizo_percentual': lucro_prejuizo_total_percent,
                'ativos': portfolio_ativos
            }
        })
        
    except Exception as e:
        carteira_logger.error(f'Error getting portfolio: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Erro ao buscar carteira'
        }), 500

@carteira_bp.route('/adicionar', methods=['POST'])
@login_required
def adicionar_ativo():
    """Add an asset to the user's portfolio."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['ticker', 'quantidade', 'preco_medio']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Campo obrigatório não informado: {field}'
                }), 400
        
        ticker = data['ticker'].upper()
        quantidade = float(data['quantidade'])
        preco_medio = float(data['preco_medio'])
        data_compra = data.get('data_compra', datetime.utcnow().date().isoformat())
        notas = data.get('notas', '')
        
        # Get or create the asset
        ativo = Ativo.query.filter_by(ticker=ticker).first()
        if not ativo:
            # If asset doesn't exist, create a new one
            ativo = Ativo(
                ticker=ticker,
                nome=ticker,  # Will be updated with real data later
                tipo='ACAO',  # Default type, can be updated later
                preco_atual=preco_medio,
                ultima_atualizacao=datetime.utcnow()
            )
            db.session.add(ativo)
            db.session.flush()  # Get the ID without committing
        
        # Get or create the user's portfolio
        portfolio = Carteira.query.filter_by(usuario_id=current_user.id).first()
        if not portfolio:
            portfolio = Carteira(usuario_id=current_user.id)
            db.session.add(portfolio)
            db.session.flush()
        
        # Check if asset already exists in portfolio
        carteira_ativo = CarteiraAtivo.query.filter_by(
            carteira_id=portfolio.id,
            ativo_id=ativo.id
        ).first()
        
        if carteira_ativo:
            # Update existing position
            novo_total = (carteira_ativo.quantidade * carteira_ativo.preco_medio + 
                         quantidade * preco_medio)
            nova_quantidade = carteira_ativo.quantidade + quantidade
            
            carteira_ativo.preco_medio = novo_total / nova_quantidade if nova_quantidade > 0 else 0
            carteira_ativo.quantidade = nova_quantidade
            carteira_ativo.data_compra = data_compra
            carteira_ativo.notas = notas
            
            message = 'Posição atualizada com sucesso!'
        else:
            # Add new position
            carteira_ativo = CarteiraAtivo(
                carteira_id=portfolio.id,
                ativo_id=ativo.id,
                quantidade=quantidade,
                preco_medio=preco_medio,
                data_compra=data_compra,
                notas=notas
            )
            db.session.add(carteira_ativo)
            message = 'Ativo adicionado à carteira com sucesso!'
        
        # Commit changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message,
            'data': {
                'id': carteira_ativo.id,
                'ticker': ativo.ticker,
                'nome': ativo.nome,
                'quantidade': carteira_ativo.quantidade,
                'preco_medio': carteira_ativo.preco_medio,
                'data_compra': carteira_ativo.data_compra.isoformat() if carteira_ativo.data_compra else None,
                'notas': carteira_ativo.notas
            }
        })
        
    except Exception as e:
        db.session.rollback()
        carteira_logger.error(f'Error adding asset to portfolio: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Erro ao adicionar ativo à carteira'
        }), 500

@carteira_bp.route('/remover/<int:posicao_id>', methods=['DELETE'])
@login_required
def remover_posicao(posicao_id):
    """Remove a position from the user's portfolio."""
    try:
        # Find the position
        posicao = CarteiraAtivo.query.get_or_404(posicao_id)
        
        # Verify ownership
        portfolio = Carteira.query.filter_by(
            id=posicao.carteira_id,
            usuario_id=current_user.id
        ).first()
        
        if not portfolio:
            return jsonify({
                'success': False,
                'error': 'Posição não encontrada ou sem permissão'
            }), 404
        
        # Delete the position
        db.session.delete(posicao)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Posição removida com sucesso!'
        })
        
    except Exception as e:
        db.session.rollback()
        carteira_logger.error(f'Error removing position {posicao_id}: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Erro ao remover posição'
        }), 500
