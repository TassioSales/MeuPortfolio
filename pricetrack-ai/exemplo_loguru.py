"""
Exemplo de Uso do Sistema de Logging Loguru - PriceTrack AI
Demonstra as funcionalidades avançadas do Loguru
"""

from core.logger import (
    setup_logging, get_logger, log_user_action, log_api_call, 
    log_database_operation, log_performance, log_security_event,
    log_business_metric, log_with_context, configure_logging_for_environment
)
import time
import random


def exemplo_logging_basico():
    """Exemplo de logging básico com Loguru"""
    logger = get_logger(__name__)
    
    logger.info("Iniciando exemplo de logging básico")
    logger.warning("Este é um aviso de exemplo")
    logger.error("Este é um erro de exemplo")
    logger.debug("Este é um debug de exemplo")
    
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
        ("login", "Usuário fez login no sistema"),
        ("product_search", "Pesquisou por iPhone 15"),
        ("product_add", "Adicionou produto ao monitoramento"),
        ("alert_config", "Configurou alerta de preço"),
        ("comparison", "Realizou comparação de produtos")
    ]
    
    for acao, detalhes in acoes_usuario:
        log_user_action(logger, acao, detalhes, user_id=f"user_{random.randint(100, 999)}")
        time.sleep(0.1)  # Simular delay


def exemplo_logging_api():
    """Exemplo de logging de chamadas de API"""
    logger = get_logger(__name__)
    
    # Simular chamadas de API
    apis = [
        ("search_products", 150),
        ("generate_tags", 75),
        ("analyze_reviews", 200),
        ("compare_products", 300),
        ("suggest_threshold", 50)
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
        ("DELETE", "alerts", False),
        ("INSERT", "alerts", True, 3)
    ]
    
    for op in operacoes:
        if len(op) == 4:
            log_database_operation(logger, op[0], op[1], op[2], op[3])
        else:
            log_database_operation(logger, op[0], op[1], op[2])
        time.sleep(0.1)


def exemplo_logging_performance():
    """Exemplo de logging de performance"""
    logger = get_logger(__name__)
    
    # Simular diferentes operações com métricas
    operacoes = [
        ("search_products", 0.5, {"products_found": 5, "cache_hit": True}),
        ("generate_tags", 0.2, {"tags_count": 7, "cache_hit": False}),
        ("analyze_reviews", 0.8, {"reviews_analyzed": 150, "sentiment_score": 0.7}),
        ("compare_products", 1.2, {"products_compared": 3, "recommendations": 1}),
        ("suggest_threshold", 0.3, {"threshold_value": 299.90, "confidence": 0.8})
    ]
    
    for func_name, duration, metrics in operacoes:
        log_performance(logger, func_name, duration, **metrics)
        time.sleep(0.1)


def exemplo_logging_security():
    """Exemplo de logging de eventos de segurança"""
    logger = get_logger(__name__)
    
    eventos_seguranca = [
        ("login_attempt", "LOW", "Tentativa de login normal"),
        ("api_rate_limit", "MEDIUM", "Limite de taxa de API atingido"),
        ("suspicious_query", "HIGH", "Query suspeita detectada"),
        ("unauthorized_access", "CRITICAL", "Tentativa de acesso não autorizado")
    ]
    
    for event_type, severity, details in eventos_seguranca:
        log_security_event(logger, event_type, severity, details)
        time.sleep(0.1)


def exemplo_logging_business():
    """Exemplo de logging de métricas de negócio"""
    logger = get_logger(__name__)
    
    metricas_negocio = [
        ("total_users", 150, "users"),
        ("products_monitored", 45, "items"),
        ("alerts_active", 12, "alerts"),
        ("api_calls_today", 1250, "calls"),
        ("success_rate", 98.5, "percent")
    ]
    
    for metric_name, value, unit in metricas_negocio:
        log_business_metric(logger, metric_name, value, unit)
        time.sleep(0.1)


def exemplo_logging_contextual():
    """Exemplo de logging contextual com informações específicas"""
    logger = get_logger(__name__)
    
    # Logging com contexto específico
    produto_id = 123
    produto_nome = "iPhone 15 Pro Max"
    preco_atual = 2999.90
    
    log_with_context(
        logger, "INFO", 
        f"Processando produto {produto_nome}",
        product_id=produto_id,
        current_price=preco_atual,
        user_id="user_456",
        session_id="session_789"
    )
    
    # Simular análise de preço
    if preco_atual < 3000:
        log_with_context(
            logger, "INFO",
            f"Produto com preço competitivo",
            product_name=produto_nome,
            price_category="competitive"
        )
    else:
        log_with_context(
            logger, "WARNING",
            f"Produto com preço elevado",
            product_name=produto_nome,
            price_category="expensive"
        )


def exemplo_configuracoes_ambiente():
    """Exemplo de configurações para diferentes ambientes"""
    logger = get_logger(__name__)
    
    # Configurar para desenvolvimento
    configure_logging_for_environment("development")
    logger.info("Logging configurado para desenvolvimento")
    
    # Simular algumas operações
    log_user_action(logger, "config_change", "Ambiente alterado para desenvolvimento")
    
    # Configurar para produção
    configure_logging_for_environment("production")
    logger.info("Logging configurado para produção")
    
    # Configurar para testes
    configure_logging_for_environment("testing")
    logger.info("Logging configurado para testes")


def exemplo_logging_estruturado():
    """Exemplo de logging estruturado com dados complexos"""
    logger = get_logger(__name__)
    
    # Dados estruturados
    produto_data = {
        "id": 123,
        "name": "iPhone 15 Pro Max",
        "price": 2999.90,
        "tags": ["smartphone", "apple", "premium"],
        "reviews": {
            "average_rating": 4.5,
            "total_reviews": 150,
            "sentiment_score": 0.7
        }
    }
    
    # Log com dados estruturados
    logger.info(
        "Produto processado com sucesso",
        extra={
            "product_data": produto_data,
            "processing_time": 0.5,
            "cache_hit": True,
            "user_preferences": {
                "budget": 3000,
                "preferred_brands": ["Apple", "Samsung"]
            }
        }
    )


def main():
    """Função principal para demonstrar logging com Loguru"""
    # Configurar logging
    setup_logging(level="DEBUG", enable_console=True, enable_file=True)
    logger = get_logger(__name__)
    
    logger.info("Iniciando demonstração do sistema de logging Loguru")
    
    try:
        # Executar exemplos
        exemplo_logging_basico()
        exemplo_logging_usuario()
        exemplo_logging_api()
        exemplo_logging_database()
        exemplo_logging_performance()
        exemplo_logging_security()
        exemplo_logging_business()
        exemplo_logging_contextual()
        exemplo_configuracoes_ambiente()
        exemplo_logging_estruturado()
        
        logger.info("Demonstração de logging concluída com sucesso")
        print("✅ Demonstração de logging Loguru concluída!")
        print("📁 Verifique os logs em:")
        print("   - logs/app.log (logs gerais)")
        print("   - logs/errors.log (apenas erros)")
        print("   - logs/audit.log (ações do usuário)")
        print("   - logs/performance.log (métricas de performance)")
        
    except Exception as e:
        logger.error(f"Erro na demonstração: {str(e)}", exc_info=True)
        print(f"❌ Erro na demonstração: {e}")


if __name__ == "__main__":
    main()
