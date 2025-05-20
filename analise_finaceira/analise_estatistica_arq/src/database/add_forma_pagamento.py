import sqlite3

def add_forma_pagamento():
    # Conectar ao banco de dados
    conn = sqlite3.connect(r'D:\Github\MeuPortfolio\analise_finaceira\banco\financas.db')
    cursor = conn.cursor()
    
    try:
        # Verificar se a coluna já existe
        cursor.execute("PRAGMA table_info(transacoes)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'forma_pagamento' not in columns:
            # Adicionar a coluna forma_pagamento
            cursor.execute("ALTER TABLE transacoes ADD COLUMN forma_pagamento TEXT")
            print("Coluna forma_pagamento adicionada com sucesso.")
        else:
            print("Coluna forma_pagamento já existe.")
        
        conn.commit()
        
    except Exception as e:
        print(f"Erro ao adicionar coluna: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    add_forma_pagamento()
