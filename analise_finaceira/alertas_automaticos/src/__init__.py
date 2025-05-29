"""
Pacote para análise e geração de alertas automáticos de transações financeiras.
"""

from .analyse import AnalisadorFinanceiro
from .alert_service import AlertService, alert_service
from .alertasAutomaticos import GerenciadorAlertas

__all__ = [
    'AnalisadorFinanceiro',
    'AlertService',
    'alert_service',
    'GerenciadorAlertas'
]
