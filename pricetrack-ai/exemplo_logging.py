"""
Exemplo de Uso do Sistema de Logging - PriceTrack AI
Demonstra como usar o logging em diferentes contextos
"""

from core.logger import setup_logging, get_logger, log_user_action, log_api_call, log_database_operation
import time
import random


def exemplo_logging_basico():
    """Exemplo de logging básico"""
    logger = get_logger(__name__)
    
    logger.info("Iniciando exemplo de logging básico")
    logger.warning("Este é um aviso de exemplo")
    logger.error("Este é um erro de exemplo")
    
    try:
        # Simular uma operação que pode falhar
        resultado = 10 / 0
    except ZeroDivisionError as e:
        logger.error(f"Erro de divisão por zero: {str(e)}", exc_info=True)


def exemplo_logging_usuario():
    """Exemplo de logging de ações do usuário"""
    logger = get_logger(__name__)
    
    # Simular ações do usuário
    acoes_usuario = [
        "Login realizado",
        "Produto pesquisado: iPhone 15",
        "Produto adicionado ao monitoramento",
        "Alerta configurado",
        "Comparação realizada"
    ]
    
    for acao in acoes_usuario:
        log_user_action(logger, acao)
        time.sleep(0.1)  # Simular delay


def exemplo_logging_api():
    """Exemplo de logging de chamadas de API"""
    logger = get_logger(__name__)
    
    # Simular chamadas de API
    apis = [
        ("search_products", 150),
        ("generate_tags", 75),
        ("analyze_reviews", 200),
        ("compare_products", 300)
    ]
    
    for api_name, tokens in apis:
        # Simular sucesso
        log_api_call(logger, api_name, tokens, True)
        time.sleep(0.1)
        
        # Simular falha ocasional
        if random.random() < 0.2:  # 20% chance de falha
            log_api_call(logger, api_name, 0, False)


def exemplo_logging_database():
    """Exemplo de logging de operações de banco"""
    logger = get_logger(__name__)
    
    # Simular operações de banco
    operacoes = [
        ("INSERT", "products", True, 1),
        ("SELECT", "products", True),
        ("UPDATE", "products", True, 2),
        ("DELETE", "alerts", False)
    ]
    
    for op in operacoes:
        if len(op) == 4:
            log_database_operation(logger, op[0], op[1], op[2], op[3])
        else:
            log_database_operation(logger, op[0], op[1], op[2])
        time.sleep(0.1)


def exemplo_logging_contextual():
    """Exemplo de logging contextual com informações específicas"""
    logger = get_logger(__name__)
    
    # Logging com contexto específico
    produto_id = 123
    produto_nome = "iPhone 15 Pro Max"
    preco_atual = 2999.90
    
    logger.info(f"Processando produto ID {produto_id}: {produto_nome}")
    logger.info(f"Preço atual: R$ {preco_atual:.2f}")
    
    # Simular análise de preço
    if preco_atual < 3000:
        logger.info(f"Produto {produto_nome} com preço competitivo")
    else:
        logger.warning(f"Produto {produto_nome} com preço elevado")
    
    # Simular erro com contexto
    try:
        # Simular operação que pode falhar
        if random.random() < 0.3:
            raise ValueError("Erro simulado na análise")
        logger.info(f"Análise concluída para {produto_nome}")
    except Exception as e:
        logger.error(f"Erro na análise do produto {produto_nome}: {str(e)}", exc_info=True)


def exemplo_logging_performance():
    """Exemplo de logging de performance"""
    logger = get_logger(__name__)
    
    # Medir tempo de execução
    inicio = time.time()
    
    # Simular operação demorada
    logger.info("Iniciando operação de análise de preços")
    time.sleep(0.5)  # Simular processamento
    
    fim = time.time()
    tempo_execucao = fim - inicio
    
    logger.info(f"Operação concluída em {tempo_execucao:.2f} segundos")
    
    # Log de performance baseado no tempo
    if tempo_execucao < 1.0:
        logger.info("Performance excelente")
    elif tempo_execucao < 2.0:
        logger.warning("Performance aceitável")
    else:
        logger.error("Performance abaixo do esperado")


def main():
    """Função principal para demonstrar logging"""
    # Configurar logging
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("Iniciando demonstração do sistema de logging")
    
    try:
        # Executar exemplos
        exemplo_logging_basico()
        exemplo_logging_usuario()
        exemplo_logging_api()
        exemplo_logging_database()
        exemplo_logging_contextual()
        exemplo_logging_performance()
        
        logger.info("Demonstração de logging concluída com sucesso")
        print("✅ Demonstração de logging concluída!")
        print("📁 Verifique os logs em logs/app.log")
        
    except Exception as e:
        logger.error(f"Erro na demonstração: {str(e)}", exc_info=True)
        print(f"❌ Erro na demonstração: {e}")


if __name__ == "__main__":
    main()
