"""
Script para adicionar novas colunas à tabela 'ativos'.
Execute este script após atualizar o modelo Ativo.
"""

import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para permitir importações absolutas
sys.path.append(str(Path(__file__).parent.parent))

from src import create_app
from src.models import db

def upgrade():
    """Adiciona as novas colunas à tabela ativos."""
    # Cria a aplicação e o contexto
    app = create_app()
    app.app_context().push()
    
    # Obtém o engine e a conexão
    engine = db.engine
    connection = engine.connect()
    
    # Inicia uma transação
    trans = connection.begin()
    
    try:
        # Adiciona as novas colunas
        print("Adicionando novas colunas à tabela 'ativos'...")
        
        # Lista de colunas a serem adicionadas
        columns_to_add = [
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS preco_abertura FLOAT",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS preco_max FLOAT",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS preco_min FLOAT",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS preco_fechamento_anterior FLOAT",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS variacao_24h FLOAT DEFAULT 0.0",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS variacao_percentual_24h FLOAT DEFAULT 0.0",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS volume_24h FLOAT DEFAULT 0.0",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS valor_mercado FLOAT",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS max_52s FLOAT",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS min_52s FLOAT",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS pe_ratio FLOAT",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS pb_ratio FLOAT",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS dividend_yield FLOAT",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS roe FLOAT",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS setor VARCHAR(100)",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS subsetor VARCHAR(100)",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS segmento VARCHAR(100)",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS bolsa VARCHAR(50)",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS tipo VARCHAR(20)",
            "ALTER TABLE ativos ADD COLUMN IF NOT EXISTS historico_precos TEXT"
        ]
        
        # Executa cada comando SQL
        for sql in columns_to_add:
            try:
                connection.execute(sql)
                print(f"Executado: {sql}")
            except Exception as e:
                print(f"Erro ao executar {sql}: {str(e)}")
        
        # Confirma a transação
        trans.commit()
        print("Migração concluída com sucesso!")
        
    except Exception as e:
        # Em caso de erro, faz rollback
        trans.rollback()
        print(f"Erro durante a migração: {str(e)}")
        raise
    finally:
        # Fecha a conexão
        connection.close()
        engine.dispose()

if __name__ == "__main__":
    upgrade()
