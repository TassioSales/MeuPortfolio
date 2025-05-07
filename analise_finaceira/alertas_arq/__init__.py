"""
Pacote do módulo de alertas.

Este pacote fornece funcionalidades para gerenciar alertas financeiros,
incluindo criação, atualização, exclusão e consulta de alertas.
"""

# Importações principais
try:
    from .src import alertas_bp
    from .src.database import create_tables, check_tables
    
    # Verifica e cria as tabelas necessárias
    check_tables()
    
except ImportError as e:
    import sys
    import os
    from pathlib import Path
    
    # Adiciona o diretório raiz ao path para importar os módulos
    root_dir = str(Path(__file__).parent.parent)
    if root_dir not in sys.path:
        sys.path.append(root_dir)
    
    # Tenta importar novamente
    try:
        from .src import alertas_bp
        from .src.database import create_tables, check_tables
        check_tables()
    except ImportError as e:
        print(f"Erro ao importar módulos: {e}")
        raise

# Versão do pacote
__version__ = '1.0.0'
