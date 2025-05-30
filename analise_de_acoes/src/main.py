import os
import sys
from pathlib import Path
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, json
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import threading
import time

# Adiciona o diretório raiz ao path para permitir importações absolutas
sys.path.append(str(Path(__file__).parent.parent))

# Import configurations and models
from src.config import settings
from src.models import db, init_db
# Import models after db is initialized to avoid circular imports
from src.models.usuario import Usuario
from src.models.ativo import Ativo, HistoricoPreco
from src.models.carteira import Carteira
from src.models.alerta import Alerta
from src.utils.logger import logger

# Import blueprints
from src.routes.carteira import carteira_bp
from src.routes.alertas import alertas_bp
from flask_cors import CORS  # Import para lidar com CORS

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, 
               template_folder='frontend/templates',
               static_folder='frontend/static')
    
    # Load configurations
    app.config.from_object(settings)
    
    # Initialize extensions
    db.init_app(app)
    
    # Initialize CSRF protection
    csrf = CSRFProtect(app)
    
    # Initialize login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login."""
        return Usuario.query.get(int(user_id))
    
    # Configura CORS para permitir requisições do frontend
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:5000", "http://127.0.0.1:5000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Register blueprints
    app.register_blueprint(carteira_bp, url_prefix='/api/carteira')
    app.register_blueprint(alertas_bp, url_prefix='/api/alertas')
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Create default admin user if not exists
        if not Usuario.query.filter_by(username='admin').first():
            admin = Usuario(
                username='admin',
                email='admin@example.com',
                senha_hash=generate_password_hash('admin123'),
                nivel_acesso='admin'
            )
            db.session.add(admin)
            db.session.commit()
            logger.info("Created default admin user")
    
    # Routes
    @app.route('/')
    @login_required
    def index():
        """Main dashboard route."""
        return render_template('index.html', active_page='dashboard')
        
    @app.route('/pesquisa')
    @login_required
    def pesquisa():
        """Pesquisa de ativos."""
        return render_template('pesquisa.html', active_page='pesquisa')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Login route."""
        if current_user.is_authenticated:
            return redirect(url_for('index'))
            
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            user = Usuario.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user)
                next_page = request.args.get('next')
                logger.info(f"User {username} logged in successfully")
                return redirect(next_page or url_for('index'))
            
            flash('Usuário ou senha inválidos', 'error')
            logger.warning(f"Failed login attempt for user: {username}")
        
        return render_template('auth/login.html')
    
    @app.route('/logout')
    @login_required
    def logout():
        """Logout route."""
        logout_user()
        return redirect(url_for('login'))
    
    # API Routes
    @app.route('/api/assets')
    @login_required
    def get_assets():
        """Get all available assets."""
        assets = Ativo.query.all()
        return jsonify([asset.to_dict() for asset in assets])
    
    @app.route('/api/price/<symbol>')
    @login_required
    def get_price(symbol):
        """Get current price for a symbol."""
        asset = Ativo.query.filter_by(symbol=symbol).first()
        if not asset:
            return jsonify({'error': 'Asset not found'}), 404
        return jsonify(asset.to_dict())
        
    @app.route('/api/assets/search', methods=['GET'])
    @login_required
    def search_assets():
        """Search assets with filters."""
        try:
            # Get query parameters
            query = request.args.get('q', '').strip().lower()
            market = request.args.get('market', 'all')
            exchange = request.args.get('exchange', 'all')
            sector = request.args.get('sector', 'all')
            sort_by = request.args.get('sort_by', 'volume')
            
            # Start with base query
            assets_query = Ativo.query
            
            # Apply filters
            if query:
                assets_query = assets_query.filter(
                    (Ativo.symbol.ilike(f'%{query}%')) | 
                    (Ativo.nome.ilike(f'%{query}%'))
                )
                
            if market != 'all':
                assets_query = assets_query.filter(Ativo.tipo == market)
                
            if exchange != 'all':
                assets_query = assets_query.filter(Ativo.bolsa == exchange)
                
            if sector != 'all':
                assets_query = assets_query.filter(Ativo.setor == sector)
            
            # Apply sorting
            if sort_by == 'volume':
                assets_query = assets_query.order_by(Ativo.volume_24h.desc())
            elif sort_by == 'liquidity':
                assets_query = assets_query.order_by((Ativo.volume_24h * Ativo.preco_atual).desc())
            elif sort_by == 'performance':
                assets_query = assets_query.order_by(Ativo.variacao_24h.desc())
            elif sort_by == 'dividend':
                assets_query = assets_query.order_by(Ativo.dividend_yield.desc())
            elif sort_by == 'alphabetical':
                assets_query = assets_query.order_by(Ativo.symbol.asc())
            
            # Execute query
            assets = assets_query.all()
            
            # Convert to list of dicts
            result = [{
                'id': asset.id,
                'symbol': asset.symbol,
                'name': asset.nome,
                'price': float(asset.preco_atual) if asset.preco_atual else None,
                'change': float(asset.variacao_24h) if asset.variacao_24h else None,
                'changePercent': float(asset.variacao_percentual_24h) if asset.variacao_percentual_24h else None,
                'volume': float(asset.volume_24h) if asset.volume_24h else None,
                'marketCap': float(asset.valor_mercado) if asset.valor_mercado else None,
                'peRatio': float(asset.pe_ratio) if asset.pe_ratio else None,
                'pbRatio': float(asset.pb_ratio) if asset.pb_ratio else None,
                'dividendYield': float(asset.dividend_yield) if asset.dividend_yield else None,
                'roe': float(asset.roe) if asset.roe else None,
                'sector': asset.setor,
                'exchange': asset.bolsa,
                'type': asset.tipo,
                'high52w': float(asset.max_52s) if asset.max_52s else None,
                'low52w': float(asset.min_52s) if asset.min_52s else None,
                'chartData': json.loads(asset.historico_precos) if asset.historico_precos else []
            } for asset in assets]
            
            return jsonify(result)
            
        except Exception as e:
            app.logger.error(f'Error in search_assets: {str(e)}')
            return jsonify({'error': 'Internal server error'}), 500
    
    # Background tasks
    def price_updater():
        """Background task to update asset prices."""
        with app.app_context():
            while True:
                try:
                    # TODO: Implement price updates from different sources
                    logger.info("Updating asset prices...")
                    # Update prices here
                    time.sleep(settings.PRICE_UPDATE_INTERVAL)
                except Exception as e:
                    logger.error(f"Error in price_updater: {str(e)}")
                    time.sleep(60)  # Wait a minute before retrying
    
    # Start background tasks
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        # Only start the background task once, not in each reloader process
        price_thread = threading.Thread(target=price_updater, daemon=True)
        price_thread.start()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=settings.DEBUG, host='0.0.0.0', port=5001)
