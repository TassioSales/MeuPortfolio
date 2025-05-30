from datetime import datetime
from . import db  # Importa db do pacote models

class Ativo(db.Model):
    """Model for financial assets (stocks, crypto, etc.)."""
    __tablename__ = 'ativos'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100))
    price = db.Column(db.Float, default=0.0)  # preço atual
    preco_abertura = db.Column(db.Float)  # preço de abertura do dia
    preco_max = db.Column(db.Float)  # preço máximo do dia
    preco_min = db.Column(db.Float)  # preço mínimo do dia
    preco_fechamento_anterior = db.Column(db.Float)  # preço de fechamento anterior
    variacao_24h = db.Column(db.Float, default=0.0)  # variação em valor absoluto
    variacao_percentual_24h = db.Column(db.Float, default=0.0)  # variação percentual
    volume_24h = db.Column(db.Float, default=0.0)  # volume em 24h
    valor_mercado = db.Column(db.Float)  # valor de mercado (market cap)
    max_52s = db.Column(db.Float)  # máxima em 52 semanas
    min_52s = db.Column(db.Float)  # mínima em 52 semanas
    pe_ratio = db.Column(db.Float)  # P/L
    pb_ratio = db.Column(db.Float)  # P/VP
    dividend_yield = db.Column(db.Float)  # Dividend Yield
    roe = db.Column(db.Float)  # Return on Equity
    setor = db.Column(db.String(100))  # setor do ativo
    subsetor = db.Column(db.String(100))  # subsetor do ativo
    segmento = db.Column(db.String(100))  # segmento do ativo
    bolsa = db.Column(db.String(50))  # bolsa de valores (B3, NASDAQ, etc.)
    tipo = db.Column(db.String(20))  # tipo do ativo (stocks, crypto, fii, etf, etc.)
    historico_precos = db.Column(db.Text)  # JSON com histórico de preços
    source = db.Column(db.String(20))  # binance, brapi, yfinance
    category = db.Column(db.String(20))  # crypto, stocks, etc.
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    historico = db.relationship('HistoricoPreco', backref='ativo', lazy=True, cascade='all, delete-orphan')
    # Removido o relacionamento direto com Carteira para evitar conflito
    # carteira = db.relationship('Carteira', backref='ativo_rel', lazy=True, cascade='all, delete-orphan')
    
    # Relacionamento através da tabela de associação CarteiraAtivo
    carteira_ativos = db.relationship('CarteiraAtivo', back_populates='ativo', lazy=True, cascade='all, delete-orphan')
    
    # Relacionamento com alertas
    alertas = db.relationship('Alerta', back_populates='ativo', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, symbol, name=None, price=0.0, preco_abertura=None, preco_max=None, 
                 preco_min=None, preco_fechamento_anterior=None, variacao_24h=0.0, 
                 variacao_percentual_24h=0.0, volume_24h=0.0, valor_mercado=None, 
                 max_52s=None, min_52s=None, pe_ratio=None, pb_ratio=None, 
                 dividend_yield=None, roe=None, setor=None, subsetor=None, 
                 segmento=None, bolsa=None, tipo=None, historico_precos=None, 
                 source=None, category=None):
        self.symbol = symbol
        self.name = name or symbol
        self.price = price
        self.preco_abertura = preco_abertura
        self.preco_max = preco_max
        self.preco_min = preco_min
        self.preco_fechamento_anterior = preco_fechamento_anterior
        self.variacao_24h = variacao_24h
        self.variacao_percentual_24h = variacao_percentual_24h
        self.volume_24h = volume_24h
        self.valor_mercado = valor_mercado
        self.max_52s = max_52s
        self.min_52s = min_52s
        self.pe_ratio = pe_ratio
        self.pb_ratio = pb_ratio
        self.dividend_yield = dividend_yield
        self.roe = roe
        self.setor = setor
        self.subsetor = subsetor
        self.segmento = segmento
        self.bolsa = bolsa
        self.tipo = tipo
        self.historico_precos = historico_precos
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
            'preco_abertura': self.preco_abertura,
            'preco_max': self.preco_max,
            'preco_min': self.preco_min,
            'preco_fechamento_anterior': self.preco_fechamento_anterior,
            'variacao_24h': self.variacao_24h,
            'variacao_percentual_24h': self.variacao_percentual_24h,
            'volume_24h': self.volume_24h,
            'valor_mercado': self.valor_mercado,
            'max_52s': self.max_52s,
            'min_52s': self.min_52s,
            'pe_ratio': self.pe_ratio,
            'pb_ratio': self.pb_ratio,
            'dividend_yield': self.dividend_yield,
            'roe': self.roe,
            'setor': self.setor,
            'subsetor': self.subsetor,
            'segmento': self.segmento,
            'bolsa': self.bolsa,
            'tipo': self.tipo,
            'historico_precos': self.historico_precos,
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
