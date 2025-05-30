from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db  # Importa db do pacote models

class Usuario(UserMixin, db.Model):
    """User model for authentication and authorization."""
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)
    nivel_acesso = db.Column(db.String(20), default='user')  # admin, user, viewer
    data_criacao = db.Column(db.DateTime, default=db.func.current_timestamp())
    ultimo_acesso = db.Column(db.DateTime, onupdate=db.func.current_timestamp())
    ativo = db.Column(db.Boolean, default=True)
    
    # Relationships
    # Relacionamento com Carteira
    carteiras = db.relationship('Carteira', back_populates='usuario_rel', lazy=True, cascade='all, delete-orphan')
    
    # Relacionamento com Alerta
    alertas = db.relationship('Alerta', back_populates='usuario', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, username, email, senha_hash, nivel_acesso='user'):
        self.username = username
        self.email = email
        self.senha_hash = senha_hash
        self.nivel_acesso = nivel_acesso
    
    def set_password(self, password):
        """Create hashed password."""
        self.senha_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.senha_hash, password)
    
    def is_admin(self):
        """Check if user has admin privileges."""
        return self.nivel_acesso == 'admin'
    
    def to_dict(self):
        """Return user data as dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'nivel_acesso': self.nivel_acesso,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'ultimo_acesso': self.ultimo_acesso.isoformat() if self.ultimo_acesso else None,
            'ativo': self.ativo
        }
    
    def __repr__(self):
        return f'<Usuario {self.username}>'
