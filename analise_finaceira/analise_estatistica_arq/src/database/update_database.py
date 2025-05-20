import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import random

def update_database():
    # Conectar ao banco de dados
    conn = sqlite3.connect(r'D:\Github\MeuPortfolio\analise_finaceira\banco\financas.db')
    cursor = conn.cursor()
    
    try:
        # Verificar se a tabela existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transacoes'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("Tabela 'transacoes' não existe no banco de dados.")
            return
        
        # Adicionar novas colunas se não existirem
        cursor.execute("PRAGMA table_info(transacoes)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Lista de novas colunas necessárias
        new_columns = {
            'preco': 'REAL',
            'quantidade': 'REAL',
            'tipo_operacao': 'TEXT',
            'taxa': 'REAL',
            'ativo': 'TEXT',
            'indicador1': 'REAL',
            'indicador2': 'REAL'
        }
        
        # Adicionar colunas que não existem
        for col_name, col_type in new_columns.items():
            if col_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE transacoes ADD COLUMN {col_name} {col_type}")
                    print(f"Coluna {col_name} adicionada com sucesso.")
                except sqlite3.OperationalError as e:
                    print(f"Erro ao adicionar coluna {col_name}: {str(e)}")
        
        # Obter dados existentes
        df = pd.read_sql_query("SELECT * FROM transacoes", conn)
        print(f"\nRegistros existentes: {len(df)}")
        
        # Gerar novos dados para atualização
        new_data = []
        for _, row in df.iterrows():
            # Para investimentos
            if row['categoria'] == 'Investimentos':
                preco = abs(row['valor'])
                quantidade = 1
                tipo_operacao = random.choice(['Compra', 'Venda'])
                taxa = round(random.uniform(0, 50), 2)
                ativo = random.choice(['PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'B3SA3',
                                     'BOVA11', 'IVVB11', 'SMAL11', 'IMAB11', 'SPXI11',
                                     'Tesouro Selic', 'CDB', 'LCI', 'LCA'])
                indicador1 = round(random.uniform(-1, 1), 4)
                indicador2 = round(random.uniform(-1, 1), 4)
            else:
                preco = abs(row['valor'])
                quantidade = 1
                tipo_operacao = ''
                taxa = 0
                ativo = ''
                indicador1 = None
                indicador2 = None
            
            new_data.append({
                'id': row['id'],
                'preco': preco,
                'quantidade': quantidade,
                'tipo_operacao': tipo_operacao,
                'taxa': taxa,
                'ativo': ativo,
                'indicador1': indicador1,
                'indicador2': indicador2
            })
        
        # Atualizar os dados no banco
        if new_data:
            df_new = pd.DataFrame(new_data)
            for _, row in df_new.iterrows():
                cursor.execute(f"""
                    UPDATE transacoes 
                    SET preco = ?, 
                        quantidade = ?,
                        tipo_operacao = ?,
                        taxa = ?,
                        ativo = ?,
                        indicador1 = ?,
                        indicador2 = ?
                    WHERE id = ?
                """, (row['preco'], row['quantidade'], row['tipo_operacao'],
                       row['taxa'], row['ativo'], row['indicador1'],
                       row['indicador2'], row['id']))
            conn.commit()
            print(f"\n{len(new_data)} registros atualizados com sucesso.")
        
    except Exception as e:
        print(f"Erro ao atualizar banco de dados: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    update_database()
