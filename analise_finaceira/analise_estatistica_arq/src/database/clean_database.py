import sqlite3
import os

def clean_database():
    # Verificar e criar diretório do banco de dados se necessário
    banco_dir = r'D:\Github\MeuPortfolio\analise_finaceira\banco'
    if not os.path.exists(banco_dir):
        os.makedirs(banco_dir)
        print(f"Diretório {banco_dir} criado")
    
    # Verificar se o arquivo do banco existe
    banco_path = os.path.join(banco_dir, 'financas.db')
    print(f"\nVerificando arquivo do banco: {banco_path}")
    if os.path.exists(banco_path):
        print("Arquivo do banco encontrado!")
    else:
        print("Arquivo do banco não encontrado. Criando novo arquivo...")
    
    # Conectar ao banco de dados
    conn = sqlite3.connect(banco_path)
    cursor = conn.cursor()
    
    try:
        print("\nIniciando limpeza do banco de dados...")
        
        # Remover todos os dados de todas as tabelas relacionadas
        print("\nLimpando todas as tabelas relacionadas...")
        cursor.execute("PRAGMA foreign_keys = OFF")  # Desativar chaves estrangeiras temporariamente
        
        # Lista de tabelas para limpar
        tabelas = ['transacoes', 'uploads_historico', 'alertas_financas', 'historico_disparos_alerta']
        
        for tabela in tabelas:
            try:
                print(f"\nLimpando tabela {tabela}...")
                cursor.execute(f"DELETE FROM {tabela}")
                print(f"Tabela {tabela} limpa com sucesso!")
            except Exception as e:
                print(f"Erro ao limpar tabela {tabela}: {str(e)}")
        
        cursor.execute("PRAGMA foreign_keys = ON")  # Reativar chaves estrangeiras
        
        # Dropar e recriar a tabela transacoes
        print("\nRecriando tabela transacoes...")
        cursor.execute("DROP TABLE IF EXISTS transacoes")
        cursor.execute('''
            CREATE TABLE transacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                valor REAL NOT NULL,
                preco REAL,
                quantidade REAL,
                tipo_operacao TEXT,
                taxa REAL,
                ativo TEXT,
                tipo TEXT NOT NULL,
                categoria TEXT,
                descricao TEXT NOT NULL,
                forma_pagamento TEXT,
                indicador1 REAL,
                indicador2 REAL,
                data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                upload_id INTEGER
            )
        ''')
        
        print("\nTabela transacoes recriada com sucesso!")
        
        # Verificar se a tabela está vazia
        cursor.execute("SELECT COUNT(*) FROM transacoes")
        count = cursor.fetchone()[0]
        print(f"\nRegistros na tabela transacoes: {count}")
        
        conn.commit()
        print("\nBanco de dados limpo e atualizado com sucesso!")
        
    except Exception as e:
        print(f"\nErro ao limpar banco de dados: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    clean_database()
