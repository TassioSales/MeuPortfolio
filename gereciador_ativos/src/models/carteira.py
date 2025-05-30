"""
Modelo de Carteira de Investimentos.
"""
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal

from .ativo import Ativo

# Obtém o diretório base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Define o diretório de banco de dados
DATABASE_DIR = os.path.join(BASE_DIR, 'data', 'database')

# Garante que o diretório existe
os.makedirs(DATABASE_DIR, exist_ok=True)

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
        """
        Calcula o valor total do item na carteira.
        
        Returns:
            Decimal: Valor total calculado como quantidade * preço médio
        """
        # Garante que ambos os valores sejam Decimal
        quantidade = Decimal(str(self.quantidade))
        preco_medio = Decimal(str(self.preco_medio))
        return quantidade * preco_medio
    
    @property
    def valor_atual(self) -> Optional[Decimal]:
        """
        Calcula o valor atual do item na carteira.
        
        Returns:
            Optional[Decimal]: Valor atual ou None se o preço não estiver disponível
        """
        if self.ativo.preco_atual is not None:
            # Converte ambos os valores para Decimal para evitar problemas de tipo
            preco_atual_decimal = Decimal(str(self.ativo.preco_atual))
            quantidade_decimal = Decimal(str(self.quantidade))
            return quantidade_decimal * preco_atual_decimal
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
            # Ambos os valores já são Decimal
            return valor_atual - self.valor_total
        return None
    
    @property
    def resultado_percentual(self) -> Optional[float]:
        """
        Calcula o resultado percentual do item.
        
        Returns:
            Optional[float]: Resultado em percentual ou None se não for possível calcular
        """
        if self.valor_total == Decimal('0'):
            return None
            
        resultado = self.resultado
        if resultado is not None:
            # Converte o valor total para Decimal para garantir a precisão
            valor_total_decimal = Decimal(str(self.valor_total))
            if valor_total_decimal != Decimal('0'):
                # Faz a divisão com precisão e converte para float no final
                percentual = (resultado / valor_total_decimal) * Decimal('100')
                return float(percentual)
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
        # Garante que todos os valores são Decimal para evitar problemas de tipo
        quantidade_decimal = Decimal(str(quantidade))
        preco_medio_decimal = Decimal(str(preco_medio))
        
        if ativo.ticker in self.itens:
            # Atualiza item existente
            item = self.itens[ativo.ticker]
            
            # Calcula o novo preço médio usando Decimal para todos os cálculos
            soma_valores = (item.quantidade * item.preco_medio) + (quantidade_decimal * preco_medio_decimal)
            nova_quantidade = item.quantidade + quantidade_decimal
            
            # Atualiza o item existente
            item.quantidade = nova_quantidade
            item.preco_medio = soma_valores / nova_quantidade if nova_quantidade > Decimal('0') else Decimal('0')
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
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte a carteira para um dicionário.
        
        Returns:
            Dict[str, Any]: Dicionário com os dados da carteira
        """
        return {
            'nome': self.nome,
            'descricao': self.descricao,
            'data_criacao': self.data_criacao.isoformat(),
            'itens': {
                ticker: {
                    'ativo': {
                        'ticker': item.ativo.ticker,
                        'nome': item.ativo.nome,
                        'tipo': item.ativo.tipo,
                        'setor': item.ativo.setor,
                        'preco_atual': item.ativo.preco_atual,
                        'moeda': item.ativo.moeda,
                        'dados_mercado': item.ativo.dados_mercado,
                        'ultima_atualizacao': item.ativo.ultima_atualizacao.isoformat() if item.ativo.ultima_atualizacao else None
                    },
                    'quantidade': str(item.quantidade),
                    'preco_medio': str(item.preco_medio),
                    'data_compra': item.data_compra.isoformat()
                }
                for ticker, item in self.itens.items()
            }
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Carteira':
        """
        Cria uma instância de Carteira a partir de um dicionário.
        
        Args:
            data: Dicionário com os dados da carteira
            
        Returns:
            Carteira: Nova instância de Carteira
        """
        from .ativo import Ativo  # Importação local para evitar importação circular
        
        carteira = cls(
            nome=data['nome'],
            descricao=data.get('descricao', '')
        )
        carteira.data_criacao = datetime.fromisoformat(data['data_criacao'])
        
        for ticker, item_data in data.get('itens', {}).items():
            ativo_data = item_data['ativo']
            ativo = Ativo(
                ticker=ativo_data['ticker'],
                nome=ativo_data['nome'],
                tipo=ativo_data['tipo'],
                setor=ativo_data.get('setor'),
                preco_atual=ativo_data.get('preco_atual'),
                moeda=ativo_data.get('moeda', 'BRL'),
                dados_mercado=ativo_data.get('dados_mercado', {})
            )
            
            if ativo_data.get('ultima_atualizacao'):
                ativo.ultima_atualizacao = datetime.fromisoformat(ativo_data['ultima_atualizacao'])
            
            carteira.itens[ticker] = ItemCarteira(
                ativo=ativo,
                quantidade=Decimal(str(item_data['quantidade'])),
                preco_medio=Decimal(str(item_data['preco_medio'])),
                data_compra=datetime.fromisoformat(item_data['data_compra'])
            )
        
        return carteira
        
    def salvar_para_arquivo(self, caminho_arquivo: Optional[str] = None) -> str:
        """
        Salva a carteira em um arquivo JSON.
        
        Args:
            caminho_arquivo: Caminho completo do arquivo (opcional).
                            Se não informado, será usado o caminho padrão.
                            
        Returns:
            str: Caminho do arquivo salvo
        """
        if caminho_arquivo is None:
            # Usa o diretório de banco de dados definido nas configurações
            nome_arquivo = f"carteira_{self.nome.lower().replace(' ', '_')}.json"
            caminho_arquivo = os.path.join(DATABASE_DIR, nome_arquivo)
        
        # Garante que o diretório existe
        os.makedirs(os.path.dirname(caminho_arquivo), exist_ok=True)
        
        # Converte a carteira para dicionário e salva em JSON
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            
        return caminho_arquivo
        
    @classmethod
    def carregar_de_arquivo(cls, caminho_arquivo: str) -> 'Carteira':
        """
        Carrega uma carteira a partir de um arquivo JSON.
        
        Args:
            caminho_arquivo: Caminho completo do arquivo JSON
            
        Returns:
            Carteira: Instância de Carteira carregada do arquivo
            
        Raises:
            FileNotFoundError: Se o arquivo não existir
            json.JSONDecodeError: Se o arquivo não for um JSON válido
        """
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            
        return cls.from_dict(dados)
