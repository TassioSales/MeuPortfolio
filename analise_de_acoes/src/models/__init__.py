from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para permitir importações absolutas
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# Initialize SQLAlchemy
db = SQLAlchemy()

# Import settings after db is defined
from src.config.settings import SQLALCHEMY_DATABASE_URI

# Import models after db is defined to avoid circular imports
# These imports must be after db is created

def init_db(app):
    """Initialize the database with the Flask app."""
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Create default admin user if not exists
        if not Usuario.query.filter_by(username='admin').first():
            from werkzeug.security import generate_password_hash
            admin = Usuario(
                username='admin',
                email='admin@example.com',
                senha_hash=generate_password_hash('admin123'),
                nivel_acesso='admin'
            )
            db.session.add(admin)
            db.session.commit()
    
    return db
