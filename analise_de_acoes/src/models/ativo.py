from datetime import datetime
from . import db  # Importa db do pacote models

class Ativo(db.Model):
    """Model for financial assets (stocks, crypto, etc.)."""
    __tablename__ = 'ativos'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100))
    price = db.Column(db.Float, default=0.0)
    change = db.Column(db.Float, default=0.0)  # percentage change
    volume = db.Column(db.Float, default=0.0)
    market_cap = db.Column(db.Float)
    source = db.Column(db.String(20))  # binance, brapi, yfinance
    category = db.Column(db.String(20))  # crypto, stocks, etc.
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    historico = db.relationship('HistoricoPreco', backref='ativo', lazy=True, cascade='all, delete-orphan')
    carteira = db.relationship('Carteira', backref='ativo_rel', lazy=True, cascade='all, delete-orphan')
    alertas = db.relationship('Alerta', backref='ativo_rel', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, symbol, name=None, price=0.0, change=0.0, volume=0.0, 
                 market_cap=None, source=None, category=None):
        self.symbol = symbol
        self.name = name or symbol
        self.price = price
        self.change = change
        self.volume = volume
        self.market_cap = market_cap
        self.source = source
        self.category = category
    
    def update_price(self, new_price, timestamp=None):
        """Update asset price and calculate change."""
        if self.price and new_price:
            self.change = ((new_price - self.price) / self.price) * 100
        self.price = new_price
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self):
        """Return asset data as dictionary."""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'name': self.name,
            'price': self.price,
            'change': self.change,
            'volume': self.volume,
            'market_cap': self.market_cap,
            'source': self.source,
            'category': self.category,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
    
    def __repr__(self):
        return f'<Ativo {self.symbol} - {self.name}>'


class HistoricoPreco(db.Model):
    """Model for storing historical price data for assets."""
    __tablename__ = 'historico_precos'
    
    id = db.Column(db.Integer, primary_key=True)
    ativo_id = db.Column(db.Integer, db.ForeignKey('ativos.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __init__(self, ativo_id, price, volume=None, timestamp=None):
        self.ativo_id = ativo_id
        self.price = price
        self.volume = volume
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self):
        """Return historical price data as dictionary."""
        return {
            'id': self.id,
            'ativo_id': self.ativo_id,
            'price': self.price,
            'volume': self.volume,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    def __repr__(self):
        return f'<HistoricoPreco {self.ativo_id} - {self.price} @ {self.timestamp}>'
