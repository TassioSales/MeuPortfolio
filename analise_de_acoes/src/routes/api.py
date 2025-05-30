"""
API routes for AJAX requests and data fetching.
"""
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np
import logging

from src.models import db, Ativo, HistoricoPreco
from src.models.alerta import Alerta
from src.models.carteira import CarteiraAtivo
from src.services.analise_pred import predict_prices
from src.utils.formatacao import format_currency, format_percentage
from src.utils.logger import setup_logger

# Setup logger
api_logger = setup_logger('api_routes', 'api.log')

# Create blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/cotacao/<string:ticker>', methods=['GET'])
@login_required
def get_quote(ticker):
    """Get current quote for a ticker."""
    try:
        # Check if we have recent data in the database
        asset = Ativo.query.filter_by(ticker=ticker).first()
        
        if not asset:
            return jsonify({'error': 'Ativo não encontrado'}), 404
        
        # Get the latest price from history
        latest_price = HistoricoPreco.query.filter_by(ativo_id=asset.id).order_by(
            HistoricoPreco.data.desc()
        ).first()
        
        if not latest_price or (datetime.utcnow() - latest_price.data).seconds > 300:  # 5 minutes
            # Fetch fresh data if data is stale or doesn't exist
            if asset.tipo == 'CRYPTO':
                data = get_binance_data(f"{ticker}USDT")
            elif asset.tipo in ['ACAO', 'FII', 'ETF'] and '.' not in ticker and len(ticker) <= 6:
                data = get_brapi_data(ticker)
            else:
                data = get_yfinance_data(ticker)
            
            if not data or 'price' not in data:
                return jsonify({'error': 'Não foi possível obter a cotação'}), 500
            
            # Update the asset with new price
            asset.preco_atual = data['price']
            asset.ultima_atualizacao = datetime.utcnow()
            asset.fonte_preco = data.get('source', 'unknown')
            
            # Add to price history
            new_price = HistoricoPreco(
                ativo_id=asset.id,
                preco_abertura=data.get('open', data['price']),
                preco_fechamento=data['price'],
                preco_maximo=data.get('high', data['price']),
                preco_minimo=data.get('low', data['price']),
                volume=data.get('volume', 0),
                data_hora=datetime.utcnow()
            )
            
            db.session.add(new_price)
            db.session.commit()
            
            price_data = {
                'preco': data['price'],
                'variacao': data.get('change', 0),
                'variacao_percentual': data.get('change_percent', 0),
                'volume': data.get('volume', 0),
                'atualizado_em': datetime.utcnow().isoformat(),
                'fonte': data.get('source', 'unknown')
            }
        else:
            # Use cached data
            price_data = {
                'preco': float(latest_price.preco_fechamento),
                'variacao': 0,  # Would need to calculate from previous close
                'variacao_percentual': 0,  # Would need to calculate from previous close
                'volume': float(latest_price.volume) if latest_price.volume else 0,
                'atualizado_em': latest_price.data.isoformat(),
                'fonte': asset.fonte_preco or 'cache'
            }
        
        return jsonify(price_data)
    except Exception as e:
        api_logger.error(f'Error getting quote for {ticker}: {str(e)}')
        return jsonify({'error': 'Erro ao obter cotação'}), 500

@api_bp.route('/historico/<string:ticker>', methods=['GET'])
@login_required
def get_historical_data(ticker):
    """Get historical price data for a ticker."""
    try:
        period = request.args.get('period', '1mo')  # Default to 1 month
        interval = request.args.get('interval', '1d')  # Default to daily
        
        # Convert period to start/end dates
        end_date = datetime.utcnow()
        
        if period == '1d':
            start_date = end_date - timedelta(days=1)
            interval = '5m'  # 5-minute intervals for intraday
        elif period == '5d':
            start_date = end_date - timedelta(days=5)
            interval = '15m'  # 15-minute intervals for 5 days
        elif period == '1mo':
            start_date = end_date - timedelta(days=30)
        elif period == '3mo':
            start_date = end_date - timedelta(days=90)
        elif period == '6mo':
            start_date = end_date - timedelta(days=180)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        elif period == '5y':
            start_date = end_date - timedelta(days=5*365)
        else:
            start_date = end_date - timedelta(days=30)  # Default to 1 month
        
        # Get asset from database
        asset = Ativo.query.filter_by(ticker=ticker).first()
        
        if not asset:
            return jsonify({'error': 'Ativo não encontrado'}), 404
        
        # Get historical data from database
        history = HistoricoPreco.query.filter(
            HistoricoPreco.ativo_id == asset.id,
            HistoricoPreco.data_hora >= start_date
        ).order_by(HistoricoPreco.data_hora.asc()).all()
        
        if not history:
            return jsonify({'error': 'Dados históricos não disponíveis'}), 404
        
        # Format data for chart
        data = [{
            'date': h.data_hora.isoformat(),
            'open': float(h.preco_abertura),
            'high': float(h.preco_maximo),
            'low': float(h.preco_minimo),
            'close': float(h.preco_fechamento),
            'volume': float(h.volume) if h.volume else 0
        } for h in history]
        
        return jsonify(data)
    except Exception as e:
        api_logger.error(f'Error getting historical data for {ticker}: {str(e)}')
        return jsonify({'error': 'Erro ao obter dados históricos'}), 500

@api_bp.route('/previsao/<string:ticker>', methods=['GET'])
@login_required
def get_forecast(ticker):
    """Get price forecast for a ticker."""
    try:
        days = int(request.args.get('days', 7))  # Default to 7 days forecast
        
        # Get forecast from prediction service
        forecast = predict_prices(ticker, days=days)
        
        if not forecast:
            return jsonify({'error': 'Não foi possível gerar previsão'}), 500
        
        return jsonify(forecast)
    except Exception as e:
        api_logger.error(f'Error getting forecast for {ticker}: {str(e)}')
        return jsonify({'error': 'Erro ao gerar previsão'}), 500

@api_bp.route('/carteira/atualizar', methods=['POST'])
@login_required
def update_portfolio():
    """Update user's portfolio with current prices."""
    try:
        portfolio = Carteira.query.filter_by(usuario_id=current_user.id).first()
        
        if not portfolio:
            portfolio = Carteira(usuario_id=current_user.id, saldo=0.0, valor_total=0.0)
            db.session.add(portfolio)
        
        # Get all assets in the portfolio
        portfolio_items = CarteiraAtivo.query.filter_by(carteira_id=portfolio.id).all()
        
        total_value = 0.0
        total_invested = 0.0
        
        for item in portfolio_items:
            # Get current price
            asset = Ativo.query.get(item.ativo_id)
            if not asset or not asset.preco_atual:
                continue
                
            current_price = float(asset.preco_atual)
            item_total = current_price * item.quantidade
            
            total_value += item_total
            total_invested += float(item.preco_medio) * item.quantidade
            
            # Update item values
            item.valor_atual = item_total
            item.lucro_prejuizo = item_total - (float(item.preco_medio) * item.quantidade)
            item.variacao_percentual = (item.lucro_prejuizo / (float(item.preco_medio) * item.quantidade)) * 100 \
                if item.preco_medio and item.quantidad > 0 else 0
        
        # Update portfolio totals
        portfolio.valor_total = total_value
        portfolio.lucro_prejuizo = total_value - total_invested
        portfolio.variacao_percentual = (portfolio.lucro_prejuizo / total_invested * 100) if total_invested > 0 else 0
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'valor_total': float(portfolio.valor_total),
            'lucro_prejuizo': float(portfolio.lucro_prejuizo),
            'variacao_percentual': float(portfolio.variacao_percentual)
        })
    except Exception as e:
        db.session.rollback()
        api_logger.error(f'Error updating portfolio: {str(e)}')
        return jsonify({'error': 'Erro ao atualizar carteira'}), 500

@api_bp.route('/alerta/novo', methods=['POST'])
@login_required
def create_alert():
    """Create a new price alert."""
    try:
        data = request.get_json()
        
        ticker = data.get('ticker')
        tipo = data.get('tipo')  # 'acima' or 'abaixo'
        valor = float(data.get('valor', 0))
        
        if not ticker or not tipo or not valor:
            return jsonify({'error': 'Dados incompletos'}), 400
        
        # Get asset
        asset = Ativo.query.filter_by(ticker=ticker).first()
        if not asset:
            return jsonify({'error': 'Ativo não encontrado'}), 404
        
        # Create alert
        alerta = Alerta(
            usuario_id=current_user.id,
            ativo_id=asset.id,
            tipo=tipo,
            valor=valor,
            ativo=True,
            data_criacao=datetime.utcnow()
        )
        
        db.session.add(alerta)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Alerta criado com sucesso!',
            'alerta_id': alerta.id
        })
    except Exception as e:
        db.session.rollback()
        api_logger.error(f'Error creating alert: {str(e)}')
        return jsonify({'error': 'Erro ao criar alerta'}), 500

@api_bp.route('/alerta/<int:alert_id>', methods=['DELETE'])
@login_required
def delete_alert(alert_id):
    """Delete a price alert."""
    try:
        alerta = Alerta.query.filter_by(id=alert_id, usuario_id=current_user.id).first()
        
        if not alerta:
            return jsonify({'error': 'Alerta não encontrado'}), 404
        
        db.session.delete(alerta)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Alerta removido com sucesso!'})
    except Exception as e:
        db.session.rollback()
        api_logger.error(f'Error deleting alert {alert_id}: {str(e)}')
        return jsonify({'error': 'Erro ao remover alerta'}), 500

@api_bp.route('/notificacoes', methods=['GET'])
@login_required
def get_notifications():
    """Get user notifications."""
    try:
        # Get unread alerts
        alerts = Alerta.query.filter_by(
            usuario_id=current_user.id,
            lido=False
        ).order_by(Alerta.data_criacao.desc()).limit(10).all()
        
        # Format notifications
        notifications = [{
            'id': a.id,
            'tipo': 'alerta',
            'titulo': f'Alerta de Preço - {a.ativo.ticker}',
            'mensagem': f'O preço de {a.ativo.ticker} está {a.tipo} de {format_currency(a.valor)}',
            'data': a.data_criacao.isoformat(),
            'lido': a.lido
        } for a in alerts]
        
        # Mark notifications as read
        for alert in alerts:
            alert.lido = True
        
        db.session.commit()
        
        return jsonify(notifications)
    except Exception as e:
        db.session.rollback()
        api_logger.error(f'Error getting notifications: {str(e)}')
        return jsonify({'error': 'Erro ao buscar notificações'}), 500
