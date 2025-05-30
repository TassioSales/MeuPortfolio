"""
WSGI config for the application.

It exposes the WSGI callable as a module-level variable named ``application``.
"""
import os
import sys
from pathlib import Path

# Adiciona o diretório src ao path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Cria os diretórios necessários
os.makedirs(os.path.join(BASE_DIR, 'data', 'database'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# Importa o aplicativo
from src.main import create_app, db

# Cria o aplicativo
app = create_app()

# Cria as tabelas do banco de dados se não existirem
with app.app_context():
    db.create_all()

# Define a aplicação para o WSGI
application = app

if __name__ == "__main__":
    # Inicia o servidor de desenvolvimento
    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])
