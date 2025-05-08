"""
Módulo para gerenciamento de alertas manuais do sistema financeiro.

Este pacote contém as rotas, modelos e lógica de negócios para o gerenciamento
de alertas manuais no sistema de análise financeira.
"""
from .src.blueprint import alertas_manuais_bp

# Exporta o blueprint para ser importado pelo aplicativo principal
__all__ = ['alertas_manuais_bp']

__version__ = '0.1.0'
