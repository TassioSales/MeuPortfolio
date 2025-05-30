"""
Main application routes for the stock analysis dashboard.
"""
from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import logging

from src.models import db, Ativo, Carteira, Alerta, HistoricoPreco
from src.services.binance_service import get_binance_data
from src.services.brapi_service import get_brapi_data
from src.services.yfinance_service import get_yfinance_data
from src.services.analise_pred import predict_prices
from src.utils.formatacao import format_currency, format_percentage, format_number
from src.utils.logger import setup_logger

# Setup logger
main_logger = setup_logger('main_routes', 'app.log')

# Create blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def dashboard():
    """Render the main dashboard."""
    try:
        # Get user's portfolio
        portfolio = Carteira.query.filter_by(usuario_id=current_user.id).first()
        
        # Get user's alerts
        alerts = Alerta.query.filter_by(usuario_id=current_user.id, ativo=True).order_by(
            Alerta.data_criacao.desc()
        ).limit(5).all()
        
        # Get recent transactions
        recent_transactions = []  # This would come from a transaction model
        
        # Get market data for dashboard cards
        market_data = get_dashboard_market_data()
        
        # Get portfolio performance data
        performance_data = get_portfolio_performance(current_user.id)
        
        return render_template(
            'dashboard.html',
            portfolio=portfolio,
            alerts=alerts,
            recent_transactions=recent_transactions,
            market_data=market_data,
            performance_data=performance_data
        )
    except Exception as e:
        main_logger.error(f'Error loading dashboard: {str(e)}')
        flash('Ocorreu um erro ao carregar o dashboard. Por favor, tente novamente.', 'error')
        return redirect(url_for('auth.logout'))

@main_bp.route('/ativos')
@login_required
def ativos():
    """List all available assets."""
    try:
        assets = Ativo.query.filter_by(ativo=True).order_by(Ativo.ticker.asc()).all()
        return render_template('ativos/lista.html', assets=assets)
    except Exception as e:
        main_logger.error(f'Error loading assets: {str(e)}')
        flash('Ocorreu um erro ao carregar a lista de ativos.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/ativo/<string:ticker>')
@login_required
def ativo_detalhes(ticker):
    """Show details for a specific asset."""
    try:
        asset = Ativo.query.filter_by(ticker=ticker).first_or_404()
        
        # Get price history (last 30 days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        history = HistoricoPreco.query.filter(
            HistoricoPreco.ativo_id == asset.id,
            HistoricoPreco.data >= start_date
        ).order_by(HistoricoPreco.data.asc()).all()
        
        # Prepare chart data
        dates = [h.data.strftime('%Y-%m-%d') for h in history]
        prices = [float(h.preco) for h in history]
        
        # Get predictions
        predictions = predict_prices(ticker, days=7)
        
        # Get related news (placeholder)
        news = []
        
        return render_template(
            'ativos/detalhes.html',
            asset=asset,
            dates=dates,
            prices=prices,
            predictions=predictions,
            news=news
        )
    except Exception as e:
        main_logger.error(f'Error loading asset details for {ticker}: {str(e)}')
        flash('Ocorreu um erro ao carregar os detalhes do ativo.', 'error')
        return redirect(url_for('main.ativos'))

@main_bp.route('/carteira')
@login_required
def carteira():
    """Show user's portfolio."""
    try:
        portfolio = Carteira.query.filter_by(usuario_id=current_user.id).first()
        
        if not portfolio:
            # Create a new portfolio if it doesn't exist
            portfolio = Carteira(
                usuario_id=current_user.id,
                saldo=0.0,
                valor_total=0.0,
                lucro_prejuizo=0.0,
                variacao_percentual=0.0,
                ativos=[]
            )
            db.session.add(portfolio)
            db.session.commit()
        
        # Get portfolio assets with current prices
        portfolio_assets = []
        total_value = 0.0
        
        for asset in portfolio.ativos:
            # Get current price from the most recent history
            latest_price = HistoricoPreco.query.filter_by(
                ativo_id=asset.ativo_id
            ).order_by(HistoricoPreco.data.desc()).first()
            
            if latest_price:
                current_price = float(latest_price.preco)
                asset_value = current_price * asset.quantidade
                total_value += asset_value
                
                # Calculate profit/loss
                cost_basis = float(asset.preco_medio) * asset.quantidade
                pnl = asset_value - cost_basis
                pnl_pct = (pnl / cost_basis) * 100 if cost_basis > 0 else 0
                
                portfolio_assets.append({
                    'id': asset.id,
                    'ticker': asset.ativo.ticker,
                    'nome': asset.ativo.nome,
                    'quantidade': asset.quantidade,
                    'preco_medio': asset.preco_medio,
                    'preco_atual': current_price,
                    'valor_total': asset_value,
                    'lucro_prejuizo': pnl,
                    'variacao_percentual': pnl_pct
                })
        
        # Update portfolio total value
        portfolio.valor_total = total_value
        db.session.commit()
        
        return render_template(
            'carteira/index.html',
            portfolio=portfolio,
            assets=portfolio_assets,
            format_currency=format_currency,
            format_percentage=format_percentage
        )
    except Exception as e:
        main_logger.error(f'Error loading portfolio: {str(e)}')
        flash('Ocorreu um erro ao carregar sua carteira.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/alertas')
@login_required
def alertas():
    """Show user's price alerts."""
    try:
        alerts = Alerta.query.filter_by(usuario_id=current_user.id).order_by(
            Alerta.data_criacao.desc()
        ).all()
        
        return render_template('alertas/lista.html', alerts=alerts)
    except Exception as e:
        main_logger.error(f'Error loading alerts: {str(e)}')
        flash('Ocorreu um erro ao carregar seus alertas.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/configuracoes', methods=['GET', 'POST'])
@login_required
def configuracoes():
    """User settings page."""
    if request.method == 'POST':
        try:
            # Update user preferences
            current_user.receber_alertas_email = 'receber_alertas_email' in request.form
            current_user.receber_newsletter = 'receber_newsletter' in request.form
            current_user.tema = request.form.get('tema', 'claro')
            
            db.session.commit()
            flash('Configurações salvas com sucesso!', 'success')
            return redirect(url_for('main.configuracoes'))
            
        except Exception as e:
            db.session.rollback()
            main_logger.error(f'Error saving settings: {str(e)}')
            flash('Ocorreu um erro ao salvar suas configurações.', 'error')
    
    return render_template('configuracoes/index.html')

# API Endpoints
@main_bp.route('/api/ativos')
@login_required
def api_ativos():
    """API endpoint to get all assets."""
    try:
        assets = Ativo.query.filter_by(ativo=True).all()
        return jsonify([{
            'id': a.id,
            'ticker': a.ticker,
            'nome': a.nome,
            'tipo': a.tipo,
            'setor': a.setor,
            'preco_atual': float(a.preco_atual) if a.preco_atual else None,
            'variacao_dia': float(a.variacao_dia) if a.variacao_dia else None,
            'volume': float(a.volume) if a.volume else None,
            'market_cap': float(a.market_cap) if a.market_cap else None
        } for a in assets])
    except Exception as e:
        main_logger.error(f'API Error (ativos): {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

@main_bp.route('/api/grafico/<string:ticker>')
@login_required
def api_grafico(ticker):
    """API endpoint to get chart data for an asset."""
    try:
        asset = Ativo.query.filter_by(ticker=ticker).first_or_404()
        
        # Get price history (last 30 days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        history = HistoricoPreco.query.filter(
            HistoricoPreco.ativo_id == asset.id,
            HistoricoPreco.data >= start_date
        ).order_by(HistoricoPreco.data.asc()).all()
        
        # Prepare chart data
        data = [{
            'date': h.data.strftime('%Y-%m-%d'),
            'price': float(h.preco)
        } for h in history]
        
        return jsonify(data)
    except Exception as e:
        main_logger.error(f'API Error (grafico/{ticker}): {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

# Helper functions
def get_dashboard_market_data():
    """Get market data for the dashboard."""
    try:
        # Get major indices (example with B3 and some stocks)
        ibovespa = yf.Ticker('^BVSP').history(period='1d')
        if not ibovespa.empty:
            ibov_close = round(ibovespa['Close'].iloc[-1], 2)
            ibov_prev_close = round(ibovespa['Close'].iloc[-2] if len(ibovespa) > 1 else ibov_close, 2)
            ibov_change = round(((ibov_close - ibov_prev_close) / ibov_prev_close) * 100, 2)
        else:
            ibov_close = 0
            ibov_change = 0
        
        # Get USD/BRL rate
        usd_brl = yf.Ticker('BRL=X').history(period='1d')
        if not usd_brl.empty:
            usd_rate = round(usd_brl['Close'].iloc[-1], 2)
            usd_prev = round(usd_brl['Close'].iloc[-2] if len(usd_brl) > 1 else usd_rate, 2)
            usd_change = round(((usd_rate - usd_prev) / usd_prev) * 100, 2)
        else:
            usd_rate = 0
            usd_change = 0
        
        # Get some popular stocks
        stocks = ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA']
        stock_data = []
        
        for stock in stocks:
            try:
                data = yf.Ticker(stock).history(period='1d')
                if not data.empty:
                    close = round(data['Close'].iloc[-1], 2)
                    prev_close = round(data['Close'].iloc[-2] if len(data) > 1 else close, 2)
                    change = round(((close - prev_close) / prev_close) * 100, 2)
                    
                    stock_data.append({
                        'ticker': stock.split('.')[0],
                        'price': close,
                        'change': change
                    })
            except Exception as e:
                main_logger.warning(f'Error fetching data for {stock}: {str(e)}')
                continue
        
        return {
            'ibovespa': {
                'value': ibov_close,
                'change': ibov_change
            },
            'usd_brl': {
                'value': usd_rate,
                'change': usd_change
            },
            'stocks': stock_data
        }
    except Exception as e:
        main_logger.error(f'Error getting market data: {str(e)}')
        return {}

def get_portfolio_performance(user_id):
    """Get portfolio performance data."""
    try:
        # This would be more complex in a real app
        portfolio = Carteira.query.filter_by(usuario_id=user_id).first()
        
        if not portfolio:
            return {
                'total_value': 0,
                'total_invested': 0,
                'profit_loss': 0,
                'profit_loss_pct': 0,
                'daily_change': 0,
                'monthly_change': 0,
                'yearly_change': 0
            }
        
        # Placeholder values - in a real app, calculate these from transactions and price history
        return {
            'total_value': float(portfolio.valor_total) if portfolio.valor_total else 0,
            'total_invested': 10000,  # Placeholder
            'profit_loss': float(portfolio.lucro_prejuizo) if portfolio.lucro_prejuizo else 0,
            'profit_loss_pct': float(portfolio.variacao_percentual) if portfolio.variacao_percentual else 0,
            'daily_change': 0.5,  # Placeholder
            'monthly_change': 2.3,  # Placeholder
            'yearly_change': 15.7  # Placeholder
        }
    except Exception as e:
        main_logger.error(f'Error getting portfolio performance: {str(e)}')
        return {}
