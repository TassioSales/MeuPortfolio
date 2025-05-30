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

# Create main blueprint for all routes
routes_bp = Blueprint('routes', __name__)

def init_app(app):
    """Initialize routes with the Flask app."""
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(errors_bp)
    
    # Register error handlers
    from . import errors  # noqa: F401
    
    return app
