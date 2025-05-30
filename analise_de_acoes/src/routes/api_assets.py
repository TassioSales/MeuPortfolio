"""
API routes for asset-related operations.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import logging

from src.models import db, Ativo, HistoricoPreco
from src.services.binance_service import get_binance_data
from src.services.brapi_service import get_brapi_data
from src.services.yfinance_service import get_yfinance_data
from src.utils.logger import setup_logger

# Setup logger
assets_logger = setup_logger('assets_routes', 'assets.log')

# Create blueprint
assets_bp = Blueprint('assets', __name__, url_prefix='/api/assets')

@assets_bp.route('', methods=['GET'])
@login_required
def list_assets():
    """List all available assets."""
    try:
        # Get query parameters for filtering and pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '').upper()
        tipo = request.args.get('tipo', '').upper()
        
        # Build query
        query = Ativo.query
        
        # Apply filters
        if search:
            query = query.filter(Ativo.ticker.like(f'%{search}%') | 
                              Ativo.nome.like(f'%{search}%'))
        
        if tipo:
            query = query.filter_by(tipo=tipo)
        
        # Paginate results
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Format response
        assets = []
        for asset in pagination.items:
            assets.append({
                'id': asset.id,
                'ticker': asset.ticker,
                'nome': asset.nome,
                'tipo': asset.tipo,
                'preco_atual': asset.preco_atual,
                'variacao_diaria': asset.variacao_diaria,
                'volume_24h': asset.volume_24h,
                'valor_mercado': asset.valor_mercado,
                'ultima_atualizacao': asset.ultima_atualizacao.isoformat() if asset.ultima_atualizacao else None,
                'fonte_preco': asset.fonte_preco
            })
        
        return jsonify({
            'success': True,
            'data': assets,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total_pages': pagination.pages,
                'total_items': pagination.total
            }
        })
        
    except Exception as e:
        assets_logger.error(f'Error listing assets: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Erro ao listar ativos'
        }), 500

@assets_bp.route('/<string:symbol>', methods=['GET'])
@login_required
def get_asset(symbol):
    """Get real-time or latest data for an asset."""
    try:
        symbol = symbol.upper()
        
        # Find the asset in the database
        asset = Ativo.query.filter_by(ticker=symbol).first()
        
        if not asset:
            return jsonify({
                'success': False,
                'error': 'Ativo não encontrado'
            }), 404
        
        # Check if data is stale (older than 5 minutes)
        is_stale = not asset.ultima_atualizacao or \
                  (datetime.utcnow() - asset.ultima_atualizacao).total_seconds() > 300
        
        if is_stale:
            # Fetch fresh data based on asset type
            if asset.tipo == 'CRYPTO':
                data = get_binance_data(f"{symbol}USDT")
            elif asset.tipo in ['ACAO', 'FII', 'ETF'] and '.' not in symbol and len(symbol) <= 6:
                data = get_brapi_data(symbol)
            else:
                data = get_yfinance_data(symbol)
            
            if not data or 'price' not in data:
                assets_logger.warning(f'Failed to fetch data for {symbol} from external APIs')
                # Return cached data if available
                if asset.preco_atual is None:
                    return jsonify({
                        'success': False,
                        'error': 'Não foi possível obter os dados do ativo'
                    }), 500
            else:
                # Update the asset with new data
                asset.preco_atual = data['price']
                asset.variacao_diaria = data.get('change_percent', 0)
                asset.volume_24h = data.get('volume', 0)
                asset.valor_mercado = data.get('market_cap')
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
        
        # Format response
        response_data = {
            'id': asset.id,
            'ticker': asset.ticker,
            'nome': asset.nome,
            'tipo': asset.tipo,
            'preco_atual': asset.preco_atual,
            'variacao_diaria': asset.variacao_diaria,
            'volume_24h': asset.volume_24h,
            'valor_mercado': asset.valor_mercado,
            'ultima_atualizacao': asset.ultima_atualizacao.isoformat() if asset.ultima_atualizacao else None,
            'fonte_preco': asset.fonte_preco,
            'is_stale': is_stale
        }
        
        return jsonify({
            'success': True,
            'data': response_data
        })
        
    except Exception as e:
        db.session.rollback()
        assets_logger.error(f'Error getting asset {symbol}: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Erro ao obter dados do ativo'
        }), 500

@assets_bp.route('/<string:symbol>/history', methods=['GET'])
@login_required
def get_asset_history(symbol):
    """Get historical data for an asset."""
    try:
        symbol = symbol.upper()
        period = request.args.get('period', '7d')  # Default to 7 days
        interval = request.args.get('interval', '1h')  # Default to 1 hour
        
        # Find the asset in the database
        asset = Ativo.query.filter_by(ticker=symbol).first()
        
        if not asset:
            return jsonify({
                'success': False,
                'error': 'Ativo não encontrado'
            }), 404
        
        # Calculate start and end dates based on period
        end_date = datetime.utcnow()
        
        if period == '1h':
            start_date = end_date - timedelta(hours=1)
        elif period == '1d':
            start_date = end_date - timedelta(days=1)
        elif period == '7d':
            start_date = end_date - timedelta(days=7)
        elif period == '1m':
            start_date = end_date - timedelta(days=30)
        elif period == '3m':
            start_date = end_date - timedelta(days=90)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=7)  # Default to 7 days
        
        # Get historical data from database
        history = HistoricoPreco.query.filter(
            HistoricoPreco.ativo_id == asset.id,
            HistoricoPreco.data_hora >= start_date
        ).order_by(HistoricoPreco.data_hora).all()
        
        # If not enough data, fetch from API
        if not history or len(history) < 2:
            if asset.tipo == 'CRYPTO':
                data = get_binance_data(f"{symbol}USDT", interval=interval, limit=100)
            elif asset.tipo in ['ACAO', 'FII', 'ETF'] and '.' not in symbol and len(symbol) <= 6:
                data = get_brapi_data(symbol, interval=interval, days=7)
            else:
                data = get_yfinance_data(symbol, period=period, interval=interval)
            
            if not data or 'history' not in data:
                assets_logger.warning(f'Failed to fetch historical data for {symbol} from external APIs')
                return jsonify({
                    'success': False,
                    'error': 'Não foi possível obter os dados históricos',
                    'data': []
                }), 200
            
            # Format response from API data
            history_data = []
            for item in data['history']:
                history_data.append({
                    'timestamp': item['timestamp'].isoformat() if hasattr(item['timestamp'], 'isoformat') else item['timestamp'],
                    'open': item['open'],
                    'high': item['high'],
                    'low': item['low'],
                    'close': item['close'],
                    'volume': item.get('volume', 0)
                })
            
            return jsonify({
                'success': True,
                'data': history_data,
                'source': data.get('source', 'external')
            })
        
        # Format response from database
        history_data = []
        for h in history:
            history_data.append({
                'timestamp': h.data_hora.isoformat(),
                'open': float(h.preco_abertura),
                'high': float(h.preco_maximo),
                'low': float(h.preco_minimo),
                'close': float(h.preco_fechamento),
                'volume': float(h.volume) if h.volume else 0
            })
        
        return jsonify({
            'success': True,
            'data': history_data,
            'source': 'database'
        })
        
    except Exception as e:
        assets_logger.error(f'Error getting history for {symbol}: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Erro ao obter dados históricos',
            'data': []
        }), 200  # Return 200 with empty data to avoid breaking the frontend

# Add this blueprint to the app in routes/__init__.py
