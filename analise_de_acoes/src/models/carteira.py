from datetime import datetime
from . import db  # Importa db do pacote models


# Tabela de associação para relacionamento muitos-para-muitos entre Carteira e Ativo
carteira_ativos = db.Table('carteira_ativos',
    db.Column('carteira_id', db.Integer, db.ForeignKey('carteiras.id'), primary_key=True),
    db.Column('ativo_id', db.Integer, db.ForeignKey('ativos.id'), primary_key=True),
    db.Column('quantidade', db.Float, nullable=False, default=0.0),
    db.Column('preco_medio', db.Float, nullable=False),
    db.Column('data_entrada', db.DateTime, default=datetime.utcnow),
    db.Column('notas', db.Text),
    db.Column('criado_em', db.DateTime, default=datetime.utcnow),
    db.Column('atualizado_em', db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
)


class CarteiraAtivo(db.Model):
    """Model para representar o relacionamento entre Carteira e Ativo com atributos adicionais."""
    __tablename__ = 'carteira_ativos_metadados'
    
    carteira_id = db.Column(db.Integer, db.ForeignKey('carteiras.id'), primary_key=True)
    ativo_id = db.Column(db.Integer, db.ForeignKey('ativos.id'), primary_key=True)
    quantidade = db.Column(db.Float, nullable=False, default=0.0)
    preco_medio = db.Column(db.Float, nullable=False)
    custo_total = db.Column(db.Float, nullable=False)  # quantidade * preco_medio
    data_entrada = db.Column(db.DateTime, default=datetime.utcnow)
    notas = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    carteira = db.relationship('Carteira', back_populates='carteira_ativos')
    ativo = db.relationship('Ativo', back_populates='carteira_ativos')
    
    def __init__(self, carteira_id, ativo_id, quantidade, preco_medio, data_entrada=None, notas=None):
        self.carteira_id = carteira_id
        self.ativo_id = ativo_id
        self.quantidade = quantidade
        self.preco_medio = preco_medio
        self.custo_total = quantidade * preco_medio
        self.data_entrada = data_entrada or datetime.utcnow()
        self.notas = notas
    
    def atualizar_quantidade(self, nova_quantidade, novo_preco_medio=None):
        """Atualiza a quantidade e recalcula o preço médio."""
        if nova_quantidade < 0:
            raise ValueError("A quantidade não pode ser negativa.")
            
        if novo_preco_medio is not None and novo_preco_medio > 0:
            self.preco_medio = novo_preco_medio
        
        self.quantidade = nova_quantidade
        self.custo_total = self.quantidade * self.preco_medio
        self.atualizado_em = datetime.utcnow()
    
    def to_dict(self):
        """Retorna os dados do ativo na carteira como dicionário."""
        return {
            'carteira_id': self.carteira_id,
            'ativo_id': self.ativo_id,
            'quantidade': self.quantidade,
            'preco_medio': self.preco_medio,
            'custo_total': self.custo_total,
            'data_entrada': self.data_entrada.isoformat() if self.data_entrada else None,
            'notas': self.notas,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None
        }
    
    def __repr__(self):
        return f'<CarteiraAtivo carteira_id={self.carteira_id}, ativo_id={self.ativo_id}, quantidade={self.quantidade}>'


# Modelo original de Carteira (mantido para compatibilidade)

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
    
    # Relationships
    # Relacionamento com Usuario
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    usuario_rel = db.relationship('Usuario', back_populates='carteiras')
    
    # Relacionamento com CarteiraAtivo
    carteira_ativos = db.relationship('CarteiraAtivo', back_populates='carteira', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Carteira {self.usuario_id} - {self.symbol} x{self.quantidade} @ {self.preco_medio}>'
