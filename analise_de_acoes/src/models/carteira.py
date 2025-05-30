from datetime import datetime
from . import db  # Importa db do pacote models

class Carteira(db.Model):
    """Model for user's investment portfolio."""
    __tablename__ = 'carteiras'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    ativo_id = db.Column(db.Integer, db.ForeignKey('ativos.id'))
    symbol = db.Column(db.String(20), nullable=False)  # Store symbol directly for easier access
    quantidade = db.Column(db.Float, nullable=False, default=0.0)
    preco_medio = db.Column(db.Float, nullable=False)
    custo_total = db.Column(db.Float, nullable=False)  # quantidade * preco_medio
    valor_atual = db.Column(db.Float, default=0.0)  # quantidade * preco_atual
    lucro_prejuizo = db.Column(db.Float, default=0.0)  # valor_atual - custo_total
    lucro_prejuizo_percentual = db.Column(db.Float, default=0.0)  # (lucro_prejuizo / custo_total) * 100
    data_compra = db.Column(db.DateTime, default=datetime.utcnow)
    ultima_atualizacao = db.Column(db.DateTime, onupdate=datetime.utcnow)
    notas = db.Column(db.Text)
    
    def __init__(self, usuario_id, symbol, quantidade, preco_medio, ativo_id=None, data_compra=None, notas=None):
        self.usuario_id = usuario_id
        self.ativo_id = ativo_id
        self.symbol = symbol
        self.quantidade = quantidade
        self.preco_medio = preco_medio
        self.custo_total = quantidade * preco_medio
        self.data_compra = data_compra or datetime.utcnow()
        self.notas = notas
    
    def update_valor_atual(self, preco_atual):
        """Update current value and calculate P&L."""
        if preco_atual is not None:
            self.valor_atual = self.quantidade * preco_atual
            self.lucro_prejuizo = self.valor_atual - self.custo_total
            if self.custo_total > 0:
                self.lucro_prejuizo_percentual = (self.lucro_prejuizo / self.custo_total) * 100
            else:
                self.lucro_prejuizo_percentual = 0.0
            self.ultima_atualizacao = datetime.utcnow()
    
    def to_dict(self):
        """Return portfolio data as dictionary."""
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'ativo_id': self.ativo_id,
            'symbol': self.symbol,
            'quantidade': self.quantidade,
            'preco_medio': self.preco_medio,
            'custo_total': self.custo_total,
            'valor_atual': self.valor_atual,
            'lucro_prejuizo': self.lucro_prejuizo,
            'lucro_prejuizo_percentual': self.lucro_prejuizo_percentual,
            'data_compra': self.data_compra.isoformat() if self.data_compra else None,
            'ultima_atualizacao': self.ultima_atualizacao.isoformat() if self.ultima_atualizacao else None,
            'notas': self.notas
        }
    
    def __repr__(self):
        return f'<Carteira {self.usuario_id} - {self.symbol} x{self.quantidade} @ {self.preco_medio}>'
