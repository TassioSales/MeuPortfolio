"""
Routes package initialization.
Imports and registers all route blueprints.
"""
from flask import Blueprint

# Import route blueprints
from .auth import auth_bp
from .main import main_bp
from .api import api_bp
from .errors import errors_bp
from .carteira import carteira_bp
from .alertas import alertas_bp
from .api_assets import assets_bp

# Create main blueprint for all routes
routes_bp = Blueprint('routes', __name__)

def init_app(app):
    """Initialize routes with the Flask app."""
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(assets_bp, url_prefix='/api/assets')
    app.register_blueprint(carteira_bp, url_prefix='/carteira')
    app.register_blueprint(alertas_bp, url_prefix='/alertas')
    app.register_blueprint(errors_bp)
    
    # Register error handlers
    from .errors import page_not_found, internal_server_error
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_server_error)
    
    return app
