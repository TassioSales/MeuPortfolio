"""
Modelo de Ativo Financeiro.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class Ativo:
    """
    Classe que representa um ativo financeiro.
    
    Atributos:
        ticker (str): Código do ativo (ex: PETR4.SA, AAPL)
        nome (str): Nome completo do ativo
        tipo (str): Tipo do ativo (Ação, FII, ETF, etc.)
        setor (str, optional): Setor do ativo
        preco_atual (float, optional): Preço atual do ativo
        moeda (str, optional): Moeda do ativo (BRL, USD, etc.)
        dados_mercado (dict, optional): Dados adicionais de mercado
        ultima_atualizacao (datetime, optional): Data/hora da última atualização
    """
    ticker: str
    nome: str
    tipo: str
    setor: Optional[str] = None
    preco_atual: Optional[float] = None
    moeda: Optional[str] = 'BRL'
    dados_mercado: Dict[str, Any] = field(default_factory=dict)
    ultima_atualizacao: Optional[datetime] = None
    
    def __post_init__(self):
        """Validação pós-inicialização."""
        self.ticker = self.ticker.upper().strip()
        
        if not self.ultima_atualizacao:
            self.ultima_atualizacao = datetime.now()
    
    def atualizar_preco(self, novo_preco: float, data: Optional[datetime] = None):
        """
        Atualiza o preço do ativo.
        
        Args:
            novo_preco: Novo preço do ativo
            data: Data/hora da atualização (opcional, usa o horário atual se não informado)
        """
        self.preco_atual = novo_preco
        self.ultima_atualizacao = data or datetime.now()
    
    def adicionar_dado_mercado(self, chave: str, valor: Any):
        """
        Adiciona ou atualiza um dado de mercado.
        
        Args:
            chave: Nome do dado
            valor: Valor do dado
        """
        self.dados_mercado[chave] = valor
    
    def to_dict(self) -> dict:
        """
        Converte o ativo para um dicionário.
        
        Returns:
            dict: Dicionário com os dados do ativo
        """
        return {
            'ticker': self.ticker,
            'nome': self.nome,
            'tipo': self.tipo,
            'setor': self.setor,
            'preco_atual': self.preco_atual,
            'moeda': self.moeda,
            'ultima_atualizacao': self.ultima_atualizacao.isoformat() if self.ultima_atualizacao else None,
            'dados_mercado': self.dados_mercado
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Ativo':
        """
        Cria uma instância de Ativo a partir de um dicionário.
        
        Args:
            data: Dicionário com os dados do ativo
            
        Returns:
            Ativo: Nova instância de Ativo
        """
        return cls(
            ticker=data['ticker'],
            nome=data['nome'],
            tipo=data['tipo'],
            setor=data.get('setor'),
            preco_atual=data.get('preco_atual'),
            moeda=data.get('moeda', 'BRL'),
            dados_mercado=data.get('dados_mercado', {}),
            ultima_atualizacao=datetime.fromisoformat(data['ultima_atualizacao']) if data.get('ultima_atualizacao') else None
        )
