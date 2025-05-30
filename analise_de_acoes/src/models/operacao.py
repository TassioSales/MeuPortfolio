"""
Modelo para operações na carteira de investimentos.
"""
from datetime import datetime
from enum import Enum
from . import db

class TipoOperacao(Enum):
    """Enum para os tipos de operações na carteira."""
    COMPRA = 'compra'
    VENDA = 'venda'
    DIVIDENDO = 'dividendo'
    JCP = 'jcp'
    RENDIMENTO = 'rendimento'
    AGRUPAMENTO = 'agrupamento'
    DESDOBRAMENTO = 'desdobramento'
    BONIFICACAO = 'bonificacao'
    TRANSFERENCIA_ENTRADA = 'transferencia_entrada'
    TRANSFERENCIA_SAIDA = 'transferencia_saida'

class StatusOperacao(Enum):
    """Enum para os status das operações na carteira."""
    PENDENTE = 'pendente'
    CONCLUIDA = 'concluida'
    CANCELADA = 'cancelada'
    FALHA = 'falha'

class Operacao(db.Model):
    """Modelo para registrar operações na carteira de investimentos."""
    __tablename__ = 'operacoes'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    ativo_id = db.Column(db.Integer, db.ForeignKey('ativos.id'), nullable=False)
    tipo = db.Column(db.Enum(TipoOperacao), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    valor_total = db.Column(db.Float, nullable=False)
    custos = db.Column(db.Float, default=0.0)
    data_operacao = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    data_liquidacao = db.Column(db.DateTime)
    status = db.Column(db.Enum(StatusOperacao), default=StatusOperacao.CONCLUIDA)
    notas = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    usuario = db.relationship('Usuario', backref='operacoes')
    ativo = db.relationship('Ativo')
    
    def __init__(self, usuario_id, ativo_id, tipo, quantidade, preco_unitario, 
                 valor_total, custos=0.0, data_operacao=None, data_liquidacao=None, 
                 status=StatusOperacao.CONCLUIDA, notas=None):
        self.usuario_id = usuario_id
        self.ativo_id = ativo_id
        self.tipo = tipo if isinstance(tipo, TipoOperacao) else TipoOperacao(tipo)
        self.quantidade = quantidade
        self.preco_unitario = preco_unitario
        self.valor_total = valor_total
        self.custos = custos
        self.data_operacao = data_operacao or datetime.utcnow()
        self.data_liquidacao = data_liquidacao
        self.status = status if isinstance(status, StatusOperacao) else StatusOperacao(status)
        self.notas = notas
    
    def to_dict(self):
        """Converte o objeto para dicionário."""
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'ativo_id': self.ativo_id,
            'tipo': self.tipo.value,
            'quantidade': self.quantidade,
            'preco_unitario': self.preco_unitario,
            'valor_total': self.valor_total,
            'custos': self.custos,
            'data_operacao': self.data_operacao.isoformat() if self.data_operacao else None,
            'data_liquidacao': self.data_liquidacao.isoformat() if self.data_liquidacao else None,
            'status': self.status.value,
            'notas': self.notas,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.isoformat() if self.data_atualizacao else None
        }
    
    def __repr__(self):
        return f'<Operacao {self.id} - {self.tipo.value} {self.quantidade} {self.ativo.symbol}>'
