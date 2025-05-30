"""
Ponto de entrada principal para executar o aplicativo Flask.
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

# Importa e executa o aplicativo
from src.main import create_app, db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Cria as tabelas do banco de dados se não existirem
        db.create_all()
    
    # Inicia o servidor
    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=5000)
