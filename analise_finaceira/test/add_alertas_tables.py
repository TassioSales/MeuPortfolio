import os
import sqlite3
from datetime import datetime

def add_alertas_tables():
    """
    Adiciona as tabelas de alertas financeiros ao banco de dados.
    """
    # Caminho para o banco de dados
    db_path = os.path.join(os.path.dirname(__file__), 'banco', 'financas.db')
    
    print(f"Conectando ao banco de dados em: {db_path}")
    
    try:
        # Conecta ao banco de dados
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Cria a tabela alertas_financas
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS alertas_financas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            tipo_alerta VARCHAR(50) NOT NULL,
            descricao TEXT NOT NULL,
            valor_referencia DECIMAL(10, 2) NOT NULL,
            categoria VARCHAR(50),
            data_inicio DATE,
            data_fim DATE,
            frequencia VARCHAR(20),
            prioridade VARCHAR(10) NOT NULL,
            ativo BOOLEAN DEFAULT 1,
            notificar_email BOOLEAN DEFAULT 0,
            notificar_app BOOLEAN DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Cria a tabela historico_disparos_alerta
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_disparos_alerta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alerta_id INTEGER NOT NULL,
            disparado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            valor_observado DECIMAL(10, 2) NOT NULL,
            mensagem_disparo TEXT NOT NULL,
            FOREIGN KEY (alerta_id) REFERENCES alertas_financas(id) ON DELETE CASCADE
        )
        ''')
        
        # Cria índices para melhorar o desempenho
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_alertas_usuario 
        ON alertas_financas(usuario_id, ativo)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_alertas_tipo 
        ON alertas_financas(tipo_alerta, ativo)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_alertas_categoria 
        ON alertas_financas(categoria, ativo)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_historico_alerta 
        ON historico_disparos_alerta(alerta_id, disparado_em)
        ''')
        
        # Salva as alterações
        conn.commit()
        print("Tabelas de alertas criadas com sucesso!")
        print("- alertas_financas")
        print("- historico_disparos_alerta")
        
    except Exception as e:
        print(f"Erro ao criar as tabelas de alertas: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    add_alertas_tables()
