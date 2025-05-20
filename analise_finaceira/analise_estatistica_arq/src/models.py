from sqlalchemy import Column, Integer, Float, String, DateTime
from .database import Base

class Transacao(Base):
    __tablename__ = 'transacoes'

    id = Column(Integer, primary_key=True)
    data = Column(DateTime)
    valor = Column(Float)  # Preço da operação
    quantidade = Column(Float)  # Quantidade de ativos negociados
    tipo_operacao = Column(String)  # 'compra' ou 'venda'
    taxa = Column(Float)  # Taxas/custos da operação
    preco = Column(Float)  # Preço unitário
    ativo = Column(String)  # Nome do ativo
    tipo = Column(String)  # Tipo de ativo (ação, ETF, etc)
    categoria = Column(String)  # Categoria da operação
    descricao = Column(String)  # Descrição detalhada
    indicador1 = Column(Float)  # Indicador técnico 1 (opcional)
    indicador2 = Column(Float)  # Indicador técnico 2 (opcional)

    def __repr__(self):
        return f"<Transacao(id={self.id}, data={self.data}, ativo={self.ativo}, tipo_operacao={self.tipo_operacao}, preco={self.preco}, quantidade={self.quantidade})>"