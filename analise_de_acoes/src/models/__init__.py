"""
Módulo de modelos do banco de dados.
"""

# Importa o db do pacote principal para evitar importações circulares
from src import db
from .usuario import Usuario
from .ativo import Ativo, HistoricoPreco
from .carteira import Carteira, CarteiraAtivo
from .alerta import Alerta
from .operacao import Operacao, TipoOperacao, StatusOperacao

# Create a dictionary of all models for easy access
models = {
    'Usuario': Usuario,
    'Ativo': Ativo,
    'HistoricoPreco': HistoricoPreco,
    'Carteira': Carteira,
    'CarteiraAtivo': CarteiraAtivo,
    'Alerta': Alerta,
    'Operacao': Operacao,
    'TipoOperacao': TipoOperacao,
    'StatusOperacao': StatusOperacao
}

def init_db(app):
    """Initialize the database with the Flask app."""
    from src.config.settings import SQLALCHEMY_DATABASE_URI
    
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
                nivel_acesso='admin',
                ativo=True
            )
            db.session.add(admin)
            db.session.commit()
    
    return db
