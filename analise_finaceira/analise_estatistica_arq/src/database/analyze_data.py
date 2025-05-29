import pandas as pd
import sqlite3
from prettytable import PrettyTable
import os

def analyze_database():
    # Conectar ao banco de dados
    print("\n=== Verificando estrutura do banco de dados ===")
    conn = sqlite3.connect(r'D:\Github\MeuPortfolio\analise_finaceira\banco\financas.db')
    
    try:
        # Verificar se a tabela existe
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transacoes'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("\nTabela 'transacoes' não existe no banco de dados.")
            return
        
        # Obter informações das colunas
        cursor.execute("PRAGMA table_info(transacoes)")
        columns = cursor.fetchall()
        
        print("\n\n=== Estrutura da Tabela ===")
        table = PrettyTable()
        table.field_names = ["ID", "Nome", "tipo", "Não Nulo", "Padrão", "PK"]
        for col in columns:
            table.add_row(col)
        print(table)
        
        # Obter dados da tabela
        df = pd.read_sql_query("SELECT * FROM transacoes LIMIT 10", conn)
        
        print("\n\n=== Primeiros 10 registros ===")
        print(df)
        
        # Verificar quantidade total de registros
        cursor.execute("SELECT COUNT(*) FROM transacoes")
        total_registros = cursor.fetchone()[0]
        print(f"\nTotal de registros na tabela: {total_registros}")
        
        if total_registros > 0:
            # Estatísticas básicas
            print("\n\n=== Estatísticas ===")
            print("\nQuantidade de registros:", len(df))
            print("\ntipos de operações:")
            print(df['tipo'].value_counts())
            print("\ncategorias:")
            print(df['categoria'].value_counts())
            
            # Analisar valores
            print("\n\n=== Análise de Valores ===")
            print("\nValores por tipo de operação:")
            print(df.groupby('tipo')['valor'].agg(['count', 'mean', 'std', 'min', 'max']))
            
            # Analisar quantidade
            print("\nQuantidades por tipo de operação:")
            print(df.groupby('tipo')['quantidade'].agg(['count', 'mean', 'std', 'min', 'max']))
            
            # Analisar por data
            print("\n\n=== Análise Temporal ===")
            print("\nNúmero de transações por mês:")
            df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y')
            print(df.groupby(df['data'].dt.to_period('M')).size())
            
            # Analisar por forma de pagamento
            print("\n\n=== Análise de Formas de Pagamento ===")
            print("\nFormas de pagamento por tipo:")
            print(df.groupby(['tipo', 'forma_pagamento']).size())
            
            # Analisar por tipo de operação
            print("\n\n=== Análise de tipos de Operação ===")
            print("\ntipos de operação por categoria:")
            print(df.groupby(['categoria', 'tipo_operacao']).size())
        else:
            print("\nNenhum registro encontrado na tabela.")
            
    except Exception as e:
        print(f"Erro ao analisar dados: {str(e)}")
        conn.close()
        return

    # Obter dados da tabela
    df = pd.read_sql_query("SELECT * FROM transacoes LIMIT 10", conn)
    
    print("\n\n=== Primeiros 10 registros ===")
    print(df)
    
    # Verificar se todas as colunas do CSV existem na tabela
    print("\n\n=== Verificação de Conformidade ===")
    print("\nColunas do CSV que não existem na tabela:")
    missing_cols = [col for col in df_csv.columns if col not in df.columns]
    if missing_cols:
        print(missing_cols)
    else:
        print("Todas as colunas do CSV existem na tabela")
    
    print("\nColunas da tabela que não existem no CSV:")
    extra_cols = [col for col in df.columns if col not in df_csv.columns]
    if extra_cols:
        print(extra_cols)
    else:
        print("Todas as colunas da tabela existem no CSV")
    
    # Encontrar colunas comuns
    common_cols = list(set(df_csv.columns) & set(df.columns))
    print("\n\n=== Colunas Comuns ===")
    print("\nColunas comuns entre CSV e banco:")
    print(common_cols)
    
    # Analisar apenas as colunas comuns
    if common_cols:
        print("\n\n=== Análise das Colunas Comuns ===")
        df_common = df_csv[common_cols]
        print("\ntipos de dados das colunas comuns:")
        print(df_common.dtypes)
        print("\nQuantidade de valores nulos nas colunas comuns:")
        print(df_common.isnull().sum())
        
        # Estatísticas básicas para colunas numéricas
        numeric_cols = df_common.select_dtypes(include=['float64']).columns
        if len(numeric_cols) > 0:
            print("\n\n=== Estatísticas para Colunas Numéricas ===")
            print(df_common[numeric_cols].describe())
        
        # Contagem de valores únicos para colunas categóricas
        categorical_cols = df_common.select_dtypes(include=['object']).columns
        if len(categorical_cols) > 0:
            print("\n\n=== Valores Únicos por Coluna Categórica ===")
            for col in categorical_cols:
                print(f"\n{col}:")
                print(df_common[col].value_counts())

    conn.close()

if __name__ == '__main__':
    analyze_database()
