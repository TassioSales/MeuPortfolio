import sqlite3
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Adicionar o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, log_function, LogLevel

# Configurar logger
logger = get_logger('alertas_automaticos.criar_tabela')

def get_db_path():
    """Retorna o caminho absoluto para o banco de dados financas.db"""
    try:
        # Sobe três níveis a partir do diretório do script para chegar na raiz do projeto
        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / 'banco' / 'financas.db'
        
        logger.debug(f"Caminho do banco de dados: {db_path}")
        return str(db_path)
    except Exception as e:
        logger.error(f"Erro ao obter caminho do banco de dados: {str(e)}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise

@log_function(level=LogLevel.INFO, log_args=False, log_result=True)
def criar_tabela_alertas_automaticos():
    """
    Cria a tabela de alertas automáticos no banco de dados.
    
    Returns:
        bool: True se a tabela foi criada com sucesso, False caso contrário
    """
    conn = None
    try:
        # Obtém o caminho do banco de dados
        db_path = get_db_path()
        
        logger.info(f"Iniciando criação da tabela 'alertas_automaticos' em: {db_path}")
        
        # Conecta ao banco de dados
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verifica se a tabela já existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alertas_automaticos';")
        if cursor.fetchone():
            logger.warning("A tabela 'alertas_automaticos' já existe.")
            print("\nA tabela 'alertas_automaticos' já existe. Deseja recriá-la? (s/n)")
            resposta = input("> ").strip().lower()
            
            if resposta != 's':
                logger.info("Operação cancelada pelo usuário.")
                print("\nOperação cancelada.")
                return False
            
            # Remove a tabela existente
            logger.info("Removendo tabela existente...")
            cursor.execute("DROP TABLE IF EXISTS alertas_automaticos;")
            logger.info("Tabela existente removida com sucesso.")
        
        # Cria a tabela com as colunas especificadas
        logger.info("Criando nova tabela 'alertas_automaticos'...")
        cursor.execute('''
        CREATE TABLE alertas_automaticos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            tipo VARCHAR(50) NOT NULL,
            prioridade VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pendente',
            data_criacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            data_atualizacao TIMESTAMP,
            data_ocorrencia DATETIME NOT NULL,
            categoria VARCHAR(100),
            valor DECIMAL(15,2),
            origem VARCHAR(100) NOT NULL,
            dados_adicionais TEXT
        )
        ''')
        logger.info("Tabela criada com sucesso.")
        
        # Insere alguns dados de exemplo
        dados_exemplo = [
            ('Alerta de Despesa Alta', 'Despesa com Supermercado acima da média', 'despesa', 'alta', 'pendente', 
             '2023-01-15 10:30:00', 'alimentacao', 450.75, 'sistema', None),
            ('Alerta de Receita', 'Recebimento de Cliente', 'receita', 'media', 'lido', 
             '2023-01-10 14:15:00', 'vendas', 1200.00, 'sistema', None),
            ('Alerta de Conta a Pagar', 'Conta de Energia vencendo em 3 dias', 'conta', 'alta', 'pendente', 
             '2023-01-20 08:45:00', 'despesas_fixas', 250.00, 'sistema', None),
        ]
        
        logger.info("Inserindo dados de exemplo...")
        cursor.executemany('''
        INSERT INTO alertas_automaticos 
        (titulo, descricao, tipo, prioridade, status, data_ocorrencia, categoria, valor, origem, dados_adicionais)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', dados_exemplo)
        
        # Salva as alterações
        conn.commit()
        
        logger.success(f"Foram inseridos {len(dados_exemplo)} registros de exemplo.")
        print("\nTabela 'alertas_automaticos' criada e populada com sucesso!")
        
        return True
        
    except sqlite3.Error as e:
        error_msg = f"Erro ao criar a tabela: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Traceback: {traceback.format_exc()}")
        print(f"\nErro: {error_msg}")
        return False
        
    except Exception as e:
        error_msg = f"Erro inesperado: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Traceback: {traceback.format_exc()}")
        print(f"\nErro inesperado: {error_msg}")
        return False
        
    finally:
        if conn:
            conn.close()
            logger.debug("Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    try:
        print("\n" + "="*60)
        print("=== CRIADOR DE TABELA DE ALERTAS AUTOMÁTICOS".center(60))
        print("="*60 + "\n")
        
        logger.info("Iniciando script de criação da tabela de alertas automáticos")
        
        if criar_tabela_alertas_automaticos():
            logger.info("Processo concluído com sucesso")
            print("\n" + "="*60)
            print("=== PROCESSO CONCLUÍDO COM SUCESSO ===".center(60))
            print("="*60)
        else:
            logger.error("Falha ao criar a tabela de alertas automáticos")
            print("\n" + "="*60)
            print("=== OCORREU UM ERRO DURANTE O PROCESSO ===".center(60))
            print("="*60)
        
    except Exception as e:
        error_msg = f"Erro inesperado: {str(e)}"
        logger.critical(error_msg)
        logger.debug(f"Traceback: {traceback.format_exc()}")
        print(f"\n{'-'*60}")
        print("ERRO CRÍTICO:".center(60))
        print(f"{error_msg}".center(60))
        print(f"Verifique os logs para mais detalhes.".center(60))
        print(f"{'-'*60}")
    
    finally:
        input("\nPressione Enter para sair...")
        logger.info("Script finalizado")
