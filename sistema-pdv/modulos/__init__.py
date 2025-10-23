"""
Módulo de modelos de dados do sistema PDV.
"""

# Importa todos os modelos para facilitar o acesso
from .produto import Produto
from .cliente import Cliente
from .usuario import Usuario
from .venda import Venda, ItemVenda

__all__ = ['Produto', 'Cliente', 'Usuario', 'Venda', 'ItemVenda']
