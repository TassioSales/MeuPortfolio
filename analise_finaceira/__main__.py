"""
Ponto de entrada principal para a aplicação de Análise Financeira.

Este módulo inicia o servidor Flask e configura todos os blueprints necessários.
"""
import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para importar os módulos
root_dir = str(Path(__file__).parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Importa o aplicativo Flask
from main import app

if __name__ == "__main__":
    # Configuração para desenvolvimento
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    
    # Inicia o servidor Flask
    app.run(host=host, port=port, debug=debug)
