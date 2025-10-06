"""
Configurações Avançadas de Logging - PriceTrack AI
Exemplos de configurações personalizadas para diferentes ambientes
"""

import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os
from datetime import datetime


def setup_development_logging():
    """Configuração de logging para desenvolvimento"""
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Handler para arquivo de desenvolvimento
    dev_handler = RotatingFileHandler(
        os.path.join(log_dir, 'dev.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    
    # Handler para console (desenvolvimento)
    console_handler = logging.StreamHandler()
    
    # Formatação para desenvolvimento
    dev_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    dev_handler.setFormatter(dev_formatter)
    console_handler.setFormatter(dev_formatter)
    
    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(dev_handler)
    root_logger.addHandler(console_handler)
    
    return logging.getLogger(__name__)


def setup_production_logging():
    """Configuração de logging para produção"""
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Handler para arquivo principal
    main_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    
    # Handler para erros separado
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, 'errors.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    
    # Handler para auditoria
    audit_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, 'audit.log'),
        when='midnight',
        interval=1,
        backupCount=30  # 30 dias
    )
    audit_handler.setLevel(logging.INFO)
    
    # Formatação para produção
    prod_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    main_handler.setFormatter(prod_formatter)
    error_handler.setFormatter(prod_formatter)
    audit_handler.setFormatter(prod_formatter)
    
    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(main_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(audit_handler)
    
    return logging.getLogger(__name__)


def setup_testing_logging():
    """Configuração de logging para testes"""
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Handler para arquivo de testes
    test_handler = RotatingFileHandler(
        os.path.join(log_dir, 'tests.log'),
        maxBytes=2*1024*1024,  # 2MB
        backupCount=2
    )
    
    # Formatação para testes
    test_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    test_handler.setFormatter(test_formatter)
    
    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)  # Apenas warnings e erros
    root_logger.addHandler(test_handler)
    
    return logging.getLogger(__name__)


def setup_custom_logging(level=logging.INFO, max_bytes=10*1024*1024, backup_count=5):
    """Configuração personalizada de logging"""
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Handler personalizado
    custom_handler = RotatingFileHandler(
        os.path.join(log_dir, 'custom.log'),
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    
    # Formatação personalizada
    custom_formatter = logging.Formatter(
        f'%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    custom_handler.setFormatter(custom_formatter)
    
    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(custom_handler)
    
    return logging.getLogger(__name__)


def log_with_context(logger, level, message, **context):
    """Log com contexto adicional"""
    context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
    full_message = f"{message} | Context: {context_str}"
    logger.log(level, full_message)


def log_performance(logger, func_name, start_time, end_time, **metrics):
    """Log de performance com métricas"""
    duration = end_time - start_time
    metrics_str = " | ".join([f"{k}={v}" for k, v in metrics.items()])
    
    logger.info(
        f"Performance - {func_name} | Duration: {duration:.3f}s | {metrics_str}"
    )


def log_user_activity(logger, user_id, action, details=None):
    """Log de atividade do usuário"""
    message = f"User Activity - ID: {user_id} | Action: {action}"
    if details:
        message += f" | Details: {details}"
    logger.info(message)


def log_security_event(logger, event_type, severity, details):
    """Log de eventos de segurança"""
    logger.warning(
        f"Security Event - Type: {event_type} | Severity: {severity} | Details: {details}"
    )


def log_business_metric(logger, metric_name, value, unit=None):
    """Log de métricas de negócio"""
    message = f"Business Metric - {metric_name}: {value}"
    if unit:
        message += f" {unit}"
    logger.info(message)


# Exemplo de uso
if __name__ == "__main__":
    # Configurar logging para desenvolvimento
    logger = setup_development_logging()
    
    # Exemplos de uso
    logger.info("Sistema iniciado")
    
    # Log com contexto
    log_with_context(
        logger, logging.INFO, 
        "Produto processado",
        product_id=123,
        price=2999.90,
        user_id="user_456"
    )
    
    # Log de performance
    import time
    start = time.time()
    time.sleep(0.1)  # Simular operação
    end = time.time()
    
    log_performance(
        logger, "process_product",
        start, end,
        products_processed=1,
        memory_used="50MB"
    )
    
    # Log de atividade do usuário
    log_user_activity(
        logger, "user_123", 
        "product_search",
        "iPhone 15 Pro Max"
    )
    
    # Log de métrica de negócio
    log_business_metric(
        logger, "total_products", 
        150, "items"
    )
    
    print("✅ Exemplos de logging executados!")
    print("📁 Verifique os logs em logs/")
