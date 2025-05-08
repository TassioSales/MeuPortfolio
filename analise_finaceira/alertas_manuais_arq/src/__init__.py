"""
Módulo para gerenciamento de alertas manuais do sistema financeiro.

Este pacote contém as rotas, modelos e lógica de negócios para o gerenciamento
de alertas manuais no sistema de análise financeira.
"""

import os
import sys

# Adiciona o diretório raiz ao path para importar o logger
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from logger import get_logger

# Configura o logger para este módulo
logger = get_logger('alertas_manuais')
logger.info("Módulo de alertas manuais inicializado")
