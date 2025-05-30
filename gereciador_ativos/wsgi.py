"""
Arquivo WSGI para execução da aplicação em produção.
"""
import os
from src.main import app

if __name__ == "__main__":
    # Obtém a porta do ambiente ou usa 5000 como padrão
    port = int(os.environ.get("PORT", 5000))
    
    # Executa a aplicação
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'False') == 'True')
