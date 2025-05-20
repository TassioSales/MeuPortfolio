import sqlite3

def clear_data():
    # Conectar ao banco de dados
    conn = sqlite3.connect(r'D:\Github\MeuPortfolio\analise_finaceira\banco\financas.db')
    cursor = conn.cursor()
    
    try:
        # Deletar todos os dados da tabela transacoes
        cursor.execute("DELETE FROM transacoes")
        conn.commit()
        print("Dados limpos com sucesso!")
        
        # Verificar se a tabela está vazia
        cursor.execute("SELECT COUNT(*) FROM transacoes")
        count = cursor.fetchone()[0]
        print(f"\nNúmero de registros na tabela: {count}")
        
    except Exception as e:
        print(f"Erro ao limpar dados: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    clear_data()
