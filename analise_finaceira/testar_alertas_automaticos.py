"""
Script para testar o módulo de alertas automáticos.
"""
import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import sqlite3

# Adiciona o diretório raiz ao path para importar os módulos
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)

from alertas_automaticos.src.alertasAutomaticos import GerenciadorAlertas

def criar_dados_teste():
    """Cria dados de teste no banco de dados."""
    db_path = os.path.join(root_dir, 'banco', 'financas.db')
    
    # Conecta ao banco de dados
    conn = sqlite3.connect(db_path)
    
    try:
        # Cria a tabela de transações se não existir
        conn.execute('''
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATETIME,
            tipo_Operacao TEXT,
            tipo TEXT,
            categoria TEXT,
            Descricao TEXT,
            valor REAL,
            Preco_Unitario REAL,
            Quantidade REAL,
            Taxa REAL,
            Forma_Pagamento TEXT,
            ativo TEXT,
            Indicador_1 REAL,
            Indicador_2 REAL
        )
        ''')
        
        # Limpa a tabela de transações
        conn.execute('DELETE FROM transacoes')
        
        # Gera dados de teste
        hoje = datetime.now().date()
        dados = []
        
        # Transações normais para Moradia/despesa
        for i in range(5):
            dados.append({
                'data': (hoje - timedelta(days=i)).strftime('%Y-%m-%d %H:%M:%S'),
                'tipo_Operacao': 'Pagamento',
                'tipo': 'despesa',
                'categoria': 'Moradia',
                'Descricao': 'Aluguel',
                'valor': 1500.00 + (i * 10),
                'Preco_Unitario': None,
                'Quantidade': None,
                'Taxa': 0,
                'Forma_Pagamento': 'Transferência',
                'ativo': None,
                'Indicador_1': 0,
                'Indicador_2': 0
            })
        
        # Adiciona um valor atípico
        dados.append({
            'data': hoje.strftime('%Y-%m-%d %H:%M:%S'),
            'tipo_Operacao': 'Pagamento',
            'tipo': 'despesa',
            'categoria': 'Moradia',
            'Descricao': 'Aluguel',
            'valor': 5000.00,  # Valor atípico
            'Preco_Unitario': None,
            'Quantidade': None,
            'Taxa': 0,
            'Forma_Pagamento': 'Transferência',
            'ativo': None,
            'Indicador_1': 0,
            'Indicador_2': 0
        })
        
        # Insere os dados na tabela
        cursor = conn.cursor()
        cursor.executemany('''
        INSERT INTO transacoes (
            data, tipo_Operacao, tipo, categoria, Descricao, valor,
            Preco_Unitario, Quantidade, Taxa, Forma_Pagamento, ativo, Indicador_1, Indicador_2
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [tuple(d.values()) for d in dados])
        
        conn.commit()
        print(f"Dados de teste inseridos com sucesso. Total: {len(dados)} registros.")
        
    except Exception as e:
        print(f"Erro ao criar dados de teste: {e}")
        raise
    finally:
        conn.close()

def main():
    """Função principal para testar o módulo de alertas automáticos."""
    try:
        print("=== TESTE DO MÓDULO DE ALERTAS AUTOMÁTICOS ===\n")
        
        # Cria dados de teste
        print("Criando dados de teste...")
        criar_dados_teste()
        
        # Executa o gerenciador de alertas
        print("\nExecutando análise de alertas...")
        gerenciador = GerenciadorAlertas()
        total_alertas = gerenciador.executar_analise()
        
        print(f"\nProcesso concluído. {total_alertas} alertas foram gerados.")
        
        # Exibe os alertas gerados
        if total_alertas > 0:
            print("\nAlertas gerados:")
            alertas = gerenciador.alert_service.obter_alertas()
            for i, alerta in enumerate(alertas['alertas'], 1):
                print(f"\nAlerta {i}:")
                print(f"  Título: {alerta['titulo']}")
                print(f"  Descrição: {alerta['descricao']}")
                print(f"  tipo: {alerta['tipo']}")
                print(f"  Prioridade: {alerta['prioridade']}")
                print(f"  Status: {alerta['status']}")
                print(f"  Data de Ocorrência: {alerta['data_ocorrencia']}")
        
        print("\n=== FIM DO TESTE ===")
        
    except Exception as e:
        print(f"\nERRO: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
