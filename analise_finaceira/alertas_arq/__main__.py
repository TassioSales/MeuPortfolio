"""
Ponto de entrada principal para o módulo de alertas.
Pode ser usado para testes ou execução direta do módulo.
"""
import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path para importar os módulos
root_dir = str(Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Importa o módulo principal
from alertas_arq.src import logger

if __name__ == "__main__":
    logger.info("Módulo de alertas executado diretamente")
    print("Módulo de alertas inicializado com sucesso.")
    print("Este módulo deve ser executado como parte da aplicação principal.")
