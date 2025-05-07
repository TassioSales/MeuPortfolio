import sqlite3
import os
from datetime import datetime, timedelta
import random

def popular_banco_exemplo():
    # Caminhos
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(base_dir, 'banco', 'financas.db')
    
    # Dados de exemplo
    categorias = ['Alimentação', 'Moradia', 'Transporte', 'Lazer', 'Saúde', 'Educação']
    
    try:
        # Conectar ao banco de dados
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar se já existem transações
        cursor.execute("SELECT COUNT(*) FROM transacoes")
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"O banco de dados já contém {count} transações. Nenhum dado será adicionado.")
            return
        
        print("Adicionando dados de exemplo ao banco de dados...")
        
        # Adicionar transações de exemplo
        hoje = datetime.now()
        for i in range(30):
            data = (hoje - timedelta(days=i)).strftime('%Y-%m-%d')
            categoria = random.choice(categorias)
            valor = round(random.uniform(50, 500), 2)
            
            cursor.execute(
                """
                INSERT INTO transacoes (data, descricao, valor, tipo, categoria, data_importacao)
                VALUES (?, ?, -?, 'Depesa', ?, ?)
                """,
                (data, f"Despesa em {categoria}", valor, categoria, data)
            )
        
        # Adicionar algumas receitas também
        for i in range(5):
            data = (hoje - timedelta(days=i*7)).strftime('%Y-%m-%d')
            cursor.execute(
                """
                INSERT INTO transacoes (data, descricao, valor, tipo, categoria, data_importacao)
                VALUES (?, 'Salário', 3000.00, 'Receita', 'Salário', ?)
                """,
                (data, data)
            )
        
        # Salvar as alterações
        conn.commit()
        print("Dados de exemplo adicionados com sucesso!")
        
    except sqlite3.Error as e:
        print(f"Erro ao acessar o banco de dados: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    popular_banco_exemplo()
