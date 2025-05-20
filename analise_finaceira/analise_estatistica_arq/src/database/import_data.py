import sqlite3
import pandas as pd

def import_data():
    # Conectar ao banco de dados
    conn = sqlite3.connect(r'D:\Github\MeuPortfolio\analise_finaceira\banco\financas.db')
    cursor = conn.cursor()
    
    try:
        # Caminho correto do arquivo CSV
        csv_path = r'D:\Github\MeuPortfolio\analise_finaceira\analise_estatistica_arq\src\database\transacoes_teste.csv'
        
        # Ler o CSV gerado
        df = pd.read_csv(csv_path)
        
        # Converter a coluna data para o formato DATE
        df['data'] = pd.to_datetime(df['data']).dt.date
        
        # Converter todas as colunas para o tipo correto
        df['valor'] = df['valor'].astype(float)
        df['preco'] = df['preco'].astype(float)
        df['quantidade'] = df['quantidade'].astype(float)
        df['taxa'] = df['taxa'].astype(float)
        df['indicador1'] = df['indicador1'].astype(float)
        df['indicador2'] = df['indicador2'].astype(float)
        
        # Inserir os dados no banco
        for _, row in df.iterrows():
            cursor.execute('''
                INSERT INTO transacoes (
                    data, descricao, valor, tipo, categoria, 
                    preco, quantidade, tipo_operacao, taxa, ativo,
                    indicador1, indicador2, forma_pagamento
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['data'],
                row['descricao'],
                row['valor'],
                row['tipo'],
                row['categoria'],
                row['preco'],
                row['quantidade'],
                row['tipo_operacao'],
                row['taxa'],
                row['ativo'],
                row['indicador1'],
                row['indicador2'],
                row['forma_pagamento']
            ))
        
        conn.commit()
        print(f"\nDados importados com sucesso!")
        print(f"Total de registros importados: {len(df)}")
        
    except Exception as e:
        print(f"Erro ao importar dados: {str(e)}")
        conn.rollback()
        
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    import_data()
