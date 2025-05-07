"""
Ponto de entrada principal para a aplicação.
Este arquivo inicia o servidor Flask usando a configuração do main.py.
"""
from main import app

if __name__ == '__main__':
    # Inicia o servidor Flask
    app.run(debug=True)
