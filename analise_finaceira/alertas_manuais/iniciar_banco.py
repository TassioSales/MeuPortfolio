import os
import sqlite3
from pathlib import Path

# Importar a configuração do módulo
from .config import Config

# Usar o mesmo caminho do banco de dados do config.py
CAMINHO_BANCO = Config.DATABASE_PATH

def criar_tabela_alertas():
    """Cria a tabela alertas_financas se não existir."""
    try:
        # Garantir que o diretório existe
        os.makedirs(os.path.dirname(CAMINHO_BANCO), exist_ok=True)
        
        # Conectar ao banco de dados (será criado se não existir)
        conexao = sqlite3.connect(str(CAMINHO_BANCO))
        cursor = conexao.cursor()
        
        # Verificar se a tabela já existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='alertas_financas'
        """)
        
        if not cursor.fetchone():
            # Criar a tabela se não existir
            cursor.execute("""
                CREATE TABLE alertas_financas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    tipo_alerta TEXT NOT NULL,
                    descricao TEXT NOT NULL,
                    valor_referencia REAL,
                    categoria TEXT,
                    data_inicio TEXT,
                    data_fim TEXT,
                    prioridade TEXT CHECK(prioridade IN ('baixa', 'media', 'alta')) NOT NULL DEFAULT 'media',
                    notificar_email BOOLEAN NOT NULL DEFAULT 0,
                    notificar_app BOOLEAN NOT NULL DEFAULT 1,
                    ativo BOOLEAN NOT NULL DEFAULT 1,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Criar um índice para melhorar consultas por usuário
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alertas_usuario 
                ON alertas_financas(usuario_id)
            """)
            
            conexao.commit()
            print("✅ Tabela 'alertas_financas' criada com sucesso!")
        else:
            print("ℹ️ A tabela 'alertas_financas' já existe.")
            
    except sqlite3.Error as erro:
        print(f"❌ Erro ao criar a tabela: {erro}")
        raise
    finally:
        if 'conexao' in locals():
            conexao.close()

if __name__ == "__main__":
    print("Iniciando configuração do banco de dados...")
    print(f"Local do banco de dados: {CAMINHO_BANCO}")
    criar_tabela_alertas()
    print("Configuração concluída.")
