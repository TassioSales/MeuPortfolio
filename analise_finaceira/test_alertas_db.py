import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from alertas_arq.src.database import create_tables, check_tables
from alertas_arq.src.models import Alerta, HistoricoAlerta
from datetime import datetime, timedelta

def test_database():
    print("=== Testando banco de dados de alertas ===")
    
    # Verifica e cria as tabelas se necessário
    print("Verificando/criando tabelas...")
    check_tables()
    
    # Teste de criação de alerta
    print("\nCriando um novo alerta...")
    novo_alerta = Alerta(
        tipo="valor_excedido",
        descricao="Alerta de valor excedido em compras",
        valor_referencia=1000.00,
        categoria="compras",
        data_inicio=datetime.now().date().isoformat(),
        data_fim=(datetime.now() + timedelta(days=30)).date().isoformat(),
        frequencia="mensal",
        notificacao_sistema=True,
        notificacao_email=True,
        prioridade="alta",
        ativo=True,
        usuario_id=1
    )
    
    if novo_alerta.save():
        print(f"Alerta criado com sucesso! ID: {novo_alerta.id}")
    else:
        print("Falha ao criar alerta.")
        return
    
    # Teste de busca por ID
    print("\nBuscando alerta por ID...")
    alerta_recuperado = Alerta.get_by_id(novo_alerta.id)
    if alerta_recuperado:
        print(f"Alerta encontrado: {alerta_recuperado.descricao}")
        print(f"Detalhes: {alerta_recuperado.to_dict()}")
    else:
        print("Alerta não encontrado.")
    
    # Teste de registro de histórico
    print("\nRegistrando histórico de disparo...")
    historico_id = HistoricoAlerta.registrar_disparo(
        alerta_id=novo_alerta.id,
        mensagem="Alerta disparado: valor excedido em compras",
        status="enviado"
    )
    
    if historico_id:
        print(f"Histórico registrado com sucesso! ID: {historico_id}")
    else:
        print("Falha ao registrar histórico.")
    
    # Teste de busca de histórico
    print("\nBuscando histórico do alerta...")
    historico = HistoricoAlerta.get_historico_por_alerta(novo_alerta.id)
    if historico:
        print(f"Histórico encontrado: {len(historico)} registros")
        for registro in historico:
            print(f"- {registro['data_disparo']}: {registro['mensagem']} ({registro['status']})")
    else:
        print("Nenhum histórico encontrado.")
    
    # Teste de listagem de alertas
    print("\nListando todos os alertas ativos...")
    alertas_ativos = Alerta.get_all({"ativo": 1})
    print(f"Total de alertas ativos: {len(alertas_ativos)}")
    for i, alerta in enumerate(alertas_ativos, 1):
        print(f"{i}. {alerta.descricao} (ID: {alerta.id})")
    
    # Teste de remoção
    print("\nRemovendo alerta de teste...")
    if novo_alerta.delete():
        print("Alerta removido com sucesso!")
    else:
        print("Falha ao remover alerta.")

if __name__ == "__main__":
    test_database()
