import os
import sqlite3
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from logger import get_logger

# Configura o logger
logger = get_logger("dashboard.verificar_tabela")

def conectar_banco():
    """Conecta ao banco de dados SQLite."""
    try:
        base_dir = str(Path(__file__).parent.parent.parent)
        db_path = os.path.join(base_dir, 'banco', 'financas.db')
        logger.debug(f"Conectando ao banco em: {db_path}")
        return sqlite3.connect(db_path)
    except sqlite3.Error as e:
        logger.error(f"Erro ao conectar ao banco: {e}", exc_info=True)
        raise

def verificar_tabela_transacoes():
    """Verifica e mostra todos os dados da tabela transacoes, incluindo todas as colunas."""
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        
        # Mostrar estrutura da tabela
        logger.info("\n=== Estrutura da Tabela transacoes ===")
        cursor.execute("PRAGMA table_info(transacoes)")
        colunas = cursor.fetchall()
        for col in colunas:
            logger.info(f"Coluna: {col[1]} - tipo: {col[2]} - Não Nulo: {col[3]} - PK: {col[5]}")
        
        # Mostrar dados da tabela
        logger.info("\n=== Dados da Tabela transacoes ===")
        query = """
        SELECT 
            id,
            data,
            descricao,
            valor,
            tipo,
            categoria,
            preco,
            quantidade,
            tipo_operacao,
            taxa,
            ativo,
            forma_pagamento,
            indicador1,
            indicador2,
            data_importacao,
            upload_id
        FROM transacoes
        ORDER BY data DESC, id DESC
        LIMIT 10
        """
        
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            logger.info(f"\nTotal de registros encontrados: {len(df)}")
            logger.info("\nPrimeiros 10 registros:")
            logger.info(df.to_string())
        else:
            logger.info("Nenhum registro encontrado na tabela transacoes")
        
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Erro ao verificar tabela: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Erro inesperado: {e}", exc_info=True)
        conn = conectar_banco()
        cursor = conn.cursor()
        
        # Verificar estrutura da tabela
        logger.info("=== ESTRUTURA DA TABELA ===")
        cursor.execute("PRAGMA table_info(transacoes)")
        columns = cursor.fetchall()
        print("{:<15} {:<15} {:<15} {:<15} {:<15} {:<15}".format('Nome', 'tipo', 'Não Nulo', 'PK', 'Default', 'ID'))
        print("-" * 90)
        for col in columns:
            print("{:<15} {:<15} {:<15} {:<15} {:<15} {:<15}".format(
                col[1], col[2], str(bool(col[3])), str(bool(col[5])), str(col[4]), str(col[0])
            ))
        
        # Verificar total de registros
        cursor.execute("SELECT COUNT(*) FROM transacoes")
        total_registros = cursor.fetchone()[0]
        print(f"\nTotal de registros na tabela: {total_registros}")
        
        # Verificar dados detalhados
        print("\n=== DADOS DETALHADOS ===")
        cursor.execute("SELECT * FROM transacoes ORDER BY data DESC LIMIT 100")
        
        # Obter nomes das colunas
        col_names = [desc[0] for desc in cursor.description]
        print("\nColunas:", ", ".join(col_names))
        
        # Mostrar dados
        print("\nDados:")
        for row in cursor.fetchall():
            print("\nRegistro:")
            for col_name, value in zip(col_names, row):
                print(f"{col_name}: {value}")
        
        # Verificar tipos de dados
        print("\n=== tipoS DE DADOS ===")
        df = pd.read_sql_query("SELECT * FROM transacoes LIMIT 100", conn)
        print("\ntipos de dados:")
        print(df.dtypes)
        
        # Verificar valores nulos
        print("\n=== VALORES NULOS ===")
        null_counts = df.isnull().sum()
        print("\nValores nulos por coluna:")
        for col, count in null_counts.items():
            print(f"{col}: {count} valores nulos")
        
        # Verificar valores únicos importantes
        print("\n=== VALORES ÚNICOS ===")
        unique_values = {
            'tipo': df['tipo'].unique(),
            'categoria': df['categoria'].unique(),
            'forma_pagamento': df['forma_pagamento'].unique()
        }
        print("\ntipos únicos:")
        for field, values in unique_values.items():
            print(f"\n{field}: {len(values)} valores únicos")
            print(values)
        
    except Exception as e:
        logger.error(f"Erro ao verificar tabela: {str(e)}", exc_info=True)
    finally:
        if 'conn' in locals():
            try:
                conn.close()
                logger.info("Conexão com o banco de dados fechada")
            except Exception as e:
                logger.error(f"Erro ao fechar conexão: {str(e)}", exc_info=True)

if __name__ == "__main__":
    verificar_tabela_transacoes()
