"""
Modelo de Carteira de Investimentos.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

from .ativo import Ativo

@dataclass
class ItemCarteira:
    """
    Item da carteira, representando um ativo e sua quantidade.
    """
    ativo: Ativo
    quantidade: Decimal
    preco_medio: Decimal
    data_compra: datetime = field(default_factory=datetime.now)
    
    @property
    def valor_total(self) -> Decimal:
        """Calcula o valor total do item na carteira."""
        return self.quantidade * self.preco_medio
    
    @property
    def valor_atual(self) -> Optional[Decimal]:
        """
        Calcula o valor atual do item na carteira.
        
        Returns:
            Optional[Decimal]: Valor atual ou None se o preço não estiver disponível
        """
        if self.ativo.preco_atual is not None:
            return self.quantidade * Decimal(str(self.ativo.preco_atual))
        return None
    
    @property
    def resultado(self) -> Optional[Decimal]:
        """
        Calcula o resultado (lucro/prejuízo) do item.
        
        Returns:
            Optional[Decimal]: Resultado em valor ou None se não for possível calcular
        """
        valor_atual = self.valor_atual
        if valor_atual is not None:
            return valor_atual - self.valor_total
        return None
    
    @property
    def resultado_percentual(self) -> Optional[float]:
        """
        Calcula o resultado percentual do item.
        
        Returns:
            Optional[float]: Resultado em percentual ou None se não for possível calcular
        """
        if self.valor_total == 0:
            return None
            
        resultado = self.resultado
        if resultado is not None:
            return float((resultado / self.valor_total) * 100)
        return None

@dataclass
class Carteira:
    """
    Classe que representa uma carteira de investimentos.
    """
    nome: str
    descricao: str = ""
    itens: Dict[str, ItemCarteira] = field(default_factory=dict)
    data_criacao: datetime = field(default_factory=datetime.now)
    
    def adicionar_ativo(self, ativo: Ativo, quantidade: float, preco_medio: float) -> None:
        """
        Adiciona um ativo à carteira.
        
        Args:
            ativo: Instância de Ativo a ser adicionado
            quantidade: Quantidade do ativo
            preco_medio: Preço médio de compra
        """
        quantidade_decimal = Decimal(str(quantidade))
        preco_medio_decimal = Decimal(str(preco_medio))
        
        if ativo.ticker in self.itens:
            # Atualiza item existente
            item = self.itens[ativo.ticker]
            novo_total = item.quantidade + quantidade_decimal
            novo_preco_medio = (
                (item.quantidade * item.preco_medio) + 
                (quantidade_decimal * preco_medio_decimal)
            ) / (item.quantidade + quantidade_decimal)
            
            item.quantidade += quantidade_decimal
            item.preco_medio = novo_preco_medio
        else:
            # Adiciona novo item
            self.itens[ativo.ticker] = ItemCarteira(
                ativo=ativo,
                quantidade=quantidade_decimal,
                preco_medio=preco_medio_decimal
            )
    
    def remover_ativo(self, ticker: str, quantidade: Optional[float] = None) -> bool:
        """
        Remove um ativo da carteira.
        
        Args:
            ticker: Ticker do ativo a ser removido
            quantidade: Quantidade a ser removida (None para remover todo o ativo)
            
        Returns:
            bool: True se o ativo foi removido, False caso contrário
        """
        ticker = ticker.upper()
        if ticker not in self.itens:
            return False
            
        if quantidade is None:
            # Remove todo o ativo
            del self.itens[ticker]
            return True
        else:
            # Remove apenas a quantidade especificada
            quantidade_decimal = Decimal(str(quantidade))
            item = self.itens[ticker]
            
            if quantidade_decimal >= item.quantidade:
                # Remove o ativo se a quantidade for maior ou igual à quantidade atual
                del self.itens[ticker]
            else:
                # Apenas reduz a quantidade
                item.quantidade -= quantidade_decimal
            return True
    
    def calcular_valor_total(self) -> Tuple[Decimal, Dict[str, Decimal]]:
        """
        Calcula o valor total da carteira e por tipo de ativo.
        
        Returns:
            Tuple[Decimal, Dict[str, Decimal]]: 
                - Valor total da carteira
                - Dicionário com valores totais por tipo de ativo
        """
        total = Decimal('0')
        por_tipo = {}
        
        for item in self.itens.values():
            valor_atual = item.valor_atual
            if valor_atual is not None:
                total += valor_atual
                tipo = item.ativo.tipo
                if tipo not in por_tipo:
                    por_tipo[tipo] = Decimal('0')
                por_tipo[tipo] += valor_atual
        
        return total, por_tipo
    
    def obter_ativos_por_tipo(self) -> Dict[str, List[ItemCarteira]]:
        """
        Agrupa os itens da carteira por tipo de ativo.
        
        Returns:
            Dict[str, List[ItemCarteira]]: Dicionário com listas de itens agrupados por tipo
        """
        por_tipo = {}
        for item in self.itens.values():
            tipo = item.ativo.tipo
            if tipo not in por_tipo:
                por_tipo[tipo] = []
            por_tipo[tipo].append(item)
        return por_tipo
