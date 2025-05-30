from datetime import datetime
from . import db  # Importa db do pacote models

class Alerta(db.Model):
    """Model for price alerts."""
    __tablename__ = 'alertas'
    
    TIPO_COMPRA = 'compra'
    TIPO_VENDA = 'venda'
    
    STATUS_ATIVO = 'ativo'
    STATUS_DISPARADO = 'disparado'
    STATUS_CANCELADO = 'cancelado'
    
    CONDICAO_ACIMA = 'acima'
    CONDICAO_ABAIXO = 'abaixo'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    ativo_id = db.Column(db.Integer, db.ForeignKey('ativos.id'))
    symbol = db.Column(db.String(20), nullable=False)  # Store symbol directly for easier access
    
    # Relationships
    ativo = db.relationship('Ativo', back_populates='alertas')
    usuario = db.relationship('Usuario', back_populates='alertas')
    tipo = db.Column(db.String(10), nullable=False)  # compra, venda
    preco_alvo = db.Column(db.Float, nullable=False)
    condicao = db.Column(db.String(10), nullable=False)  # acima, abaixo
    status = db.Column(db.String(15), default=STATUS_ATIVO)  # ativo, disparado, cancelado
    mensagem = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_disparo = db.Column(db.DateTime)
    preco_disparo = db.Column(db.Float)
    
    def __init__(self, usuario_id, symbol, tipo, preco_alvo, condicao, ativo_id=None, mensagem=None):
        self.usuario_id = usuario_id
        self.ativo_id = ativo_id
        self.symbol = symbol
        self.tipo = tipo
        self.preco_alvo = preco_alvo
        self.condicao = condicao
        self.mensagem = mensagem
    
    def check_condition(self, current_price):
        """Check if the alert condition is met."""
        if self.status != self.STATUS_ATIVO:
            return False
            
        if self.condicao == self.CONDICAO_ACIMA:
            return current_price >= self.preco_alvo
        else:  # CONDICAO_ABAIXO
            return current_price <= self.preco_alvo
    
    def trigger(self, current_price):
        """Trigger the alert."""
        self.status = self.STATUS_DISPARADO
        self.data_disparo = datetime.utcnow()
        self.preco_disparo = current_price
        
        # Generate a default message if none provided
        if not self.mensagem:
            self.mensagem = (
                f"Alerta de {self.tipo} para {self.symbol} "
                f"{self.condicao} de {self.preco_alvo:.2f} "
                f"foi disparado em {self.data_disparo}. "
                f"Preço atual: {current_price:.2f}"
            )
    
    def to_dict(self):
        """Return alert data as dictionary."""
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'ativo_id': self.ativo_id,
            'symbol': self.symbol,
            'tipo': self.tipo,
            'preco_alvo': self.preco_alvo,
            'condicao': self.condicao,
            'status': self.status,
            'mensagem': self.mensagem,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'data_disparo': self.data_disparo.isoformat() if self.data_disparo else None,
            'preco_disparo': self.preco_disparo
        }
    
    def __repr__(self):
        return f'<Alerta {self.symbol} {self.tipo} {self.condicao} {self.preco_alvo} ({self.status})>'
