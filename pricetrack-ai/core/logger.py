"""
Sistema de Logging Centralizado para PriceTrack AI
Usando Loguru para logging moderno e poderoso
"""

import os
import sys
import logging
from datetime import datetime
from loguru import logger
from typing import Optional, Any, Dict


def setup_logging(
    level: str = "INFO",
    log_dir: str = "logs",
    max_size: str = "10 MB",
    rotation: str = "1 day",
    retention: str = "30 days",
    enable_console: bool = True,
    enable_file: bool = True
):
    """
    Configura o sistema de logging global com Loguru
    
    Args:
        level: Nível de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Diretório para arquivos de log
        max_size: Tamanho máximo do arquivo antes da rotação
        rotation: Frequência de rotação dos arquivos
        retention: Tempo de retenção dos logs antigos
        enable_console: Habilitar logs no console
        enable_file: Habilitar logs em arquivo
    """
    # Ajustar nível via env var (prioridade sobre parâmetro)
    env_level = os.getenv("PTAI_LOG_LEVEL")
    if env_level:
        level = env_level

    # Remover handlers padrão do Loguru
    logger.remove()
    
    # Criar diretório de logs se não existir
    os.makedirs(log_dir, exist_ok=True)
    
    # Configurar formato dos logs
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Handler para console (desenvolvimento)
    if enable_console:
        logger.add(
            sys.stdout,
            format=log_format,
            level=level,
            colorize=True,
            backtrace=True,
            diagnose=True
        )
    
    # Handler para arquivo principal
    if enable_file:
        logger.add(
            os.path.join(log_dir, "app.log"),
            format=log_format,
            level=level,
            rotation=rotation,
            retention=retention,
            compression="zip",
            backtrace=True,
            diagnose=True,
            enqueue=True  # Thread-safe
        )
    
    # Handler específico para erros
    logger.add(
        os.path.join(log_dir, "errors.log"),
        format=log_format,
        level="ERROR",
        rotation=rotation,
        retention=retention,
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True
    )
    
    # Handler para auditoria (ações do usuário)
    logger.add(
        os.path.join(log_dir, "audit.log"),
        format=log_format,
        level="INFO",
        rotation=rotation,
        retention=retention,
        compression="zip",
        enqueue=True,
        filter=lambda record: "audit" in record["extra"]
    )
    
    # Handler para performance
    logger.add(
        os.path.join(log_dir, "performance.log"),
        format=log_format,
        level="INFO",
        rotation=rotation,
        retention=retention,
        compression="zip",
        enqueue=True,
        filter=lambda record: "performance" in record["extra"]
    )
    
    logger.info("Sistema de logging Loguru inicializado com sucesso")
    
    # Encaminhar logging padrão (stdlib) para Loguru para unificar a saída
    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            logger.opt(exception=record.exc_info, depth=6).log(level, record.getMessage())

    root_logger = logging.getLogger()
    root_logger.handlers = [InterceptHandler()]
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    return logger


def get_logger(module_name: str) -> logging.Logger:
    """
    Retorna logger configurado para módulo específico
    
    Args:
        module_name: Nome do módulo (geralmente __name__)
    
    Returns:
        Logger configurado
    """
    # Use stdlib logging to satisfy tests expecting `.name` and allow patching
    # via `core.logger.logging.getLogger`.
    full_name = (
        module_name if module_name.startswith("pricetrack_ai.") else f"pricetrack_ai.{module_name}"
    )
    py_logger = logging.getLogger(full_name)
    # Ensure it has at least a NullHandler to avoid "No handler" warnings in tests
    if not py_logger.handlers:
        py_logger.addHandler(logging.NullHandler())
    return py_logger


def log_api_call(logger_instance, function_name: str, tokens_used: int = None, success: bool = True):
    """
    Log padronizado para chamadas de API
    
    Args:
        logger_instance: Instância do logger
        function_name: Nome da função chamada
        tokens_used: Número de tokens utilizados (opcional)
        success: Se a chamada foi bem-sucedida
    """
    if success:
        if tokens_used:
            logger_instance.info(
                f"API call '{function_name}' executada com sucesso. Tokens usados: {tokens_used}",
                extra={"api_call": True, "tokens": tokens_used}
            )
        else:
            logger_instance.info(
                f"API call '{function_name}' executada com sucesso",
                extra={"api_call": True}
            )
    else:
        logger_instance.error(
            f"Falha na API call '{function_name}'",
            extra={"api_call": True, "success": False}
        )


def log_user_action(logger_instance, action: str, details: str = None, user_id: str = None):
    """
    Log padronizado para ações do usuário
    
    Args:
        logger_instance: Instância do logger
        action: Ação realizada pelo usuário
        details: Detalhes adicionais (opcional)
        user_id: ID do usuário (opcional)
    """
    message = f"Ação do usuário: {action}"
    if details:
        message += f" - {details}"
    
    extra_data = {"audit": True, "user_action": True}
    if user_id:
        extra_data["user_id"] = user_id
    
    logger_instance.info(message, extra=extra_data)


def log_database_operation(logger_instance, operation: str, table: str, success: bool = True, record_id: int = None):
    """
    Log padronizado para operações de banco de dados
    
    Args:
        logger_instance: Instância do logger
        operation: Tipo de operação (INSERT, UPDATE, DELETE, SELECT)
        table: Nome da tabela
        success: Se a operação foi bem-sucedida
        record_id: ID do registro (opcional)
    """
    message = f"DB {operation} em {table}"
    if record_id:
        message += f" (ID: {record_id})"
    
    extra_data = {"database": True, "operation": operation, "table": table}
    if record_id:
        extra_data["record_id"] = record_id
    
    if success:
        logger_instance.info(f"{message} executado com sucesso", extra=extra_data)
    else:
        logger_instance.error(f"Falha no {message}", extra=extra_data)


def log_performance(logger_instance, function_name: str, duration: float, **metrics):
    """
    Log de performance com métricas
    
    Args:
        logger_instance: Instância do logger
        function_name: Nome da função
        duration: Duração em segundos
        **metrics: Métricas adicionais
    """
    metrics_str = " | ".join([f"{k}={v}" for k, v in metrics.items()])
    message = f"Performance - {function_name} | Duration: {duration:.3f}s"
    if metrics_str:
        message += f" | {metrics_str}"
    
    logger_instance.info(message, extra={"performance": True, "duration": duration, **metrics})


def log_security_event(logger_instance, event_type: str, severity: str, details: str):
    """
    Log de eventos de segurança
    
    Args:
        logger_instance: Instância do logger
        event_type: Tipo do evento
        severity: Severidade (LOW, MEDIUM, HIGH, CRITICAL)
        details: Detalhes do evento
    """
    message = f"Security Event - Type: {event_type} | Severity: {severity} | Details: {details}"
    
    level = "info" if severity == "LOW" else "warning" if severity in ["MEDIUM", "HIGH"] else "error"
    
    logger_instance.log(
        level.upper(),
        message,
        extra={"security": True, "event_type": event_type, "severity": severity}
    )


def log_business_metric(logger_instance, metric_name: str, value: Any, unit: str = None):
    """
    Log de métricas de negócio
    
    Args:
        logger_instance: Instância do logger
        metric_name: Nome da métrica
        value: Valor da métrica
        unit: Unidade da métrica (opcional)
    """
    message = f"Business Metric - {metric_name}: {value}"
    if unit:
        message += f" {unit}"
    
    logger_instance.info(message, extra={"business_metric": True, "metric_name": metric_name, "value": value})


def log_with_context(logger_instance, level: str, message: str, **context):
    """
    Log com contexto adicional
    
    Args:
        logger_instance: Instância do logger
        level: Nível do log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        message: Mensagem principal
        **context: Contexto adicional
    """
    context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
    full_message = f"{message} | Context: {context_str}"
    
    logger_instance.log(level.upper(), full_message, extra={"context": True, **context})


def configure_logging_for_environment(environment: str = "development"):
    """
    Configura logging específico para ambiente
    
    Args:
        environment: Ambiente (development, production, testing)
    """
    if environment == "development":
        setup_logging(
            level="DEBUG",
            enable_console=True,
            enable_file=True,
            max_size="5 MB",
            rotation="1 day"
        )
    elif environment == "production":
        setup_logging(
            level="INFO",
            enable_console=False,
            enable_file=True,
            max_size="50 MB",
            rotation="1 day",
            retention="90 days"
        )
    elif environment == "testing":
        setup_logging(
            level="WARNING",
            enable_console=False,
            enable_file=True,
            max_size="2 MB",
            rotation="1 day",
            retention="7 days"
        )
    else:
        setup_logging()


# Configuração inicial
if __name__ == "__main__":
    setup_logging()
    test_logger = get_logger(__name__)
    
    # Teste básico
    test_logger.info("Sistema de logging Loguru testado com sucesso")
    test_logger.warning("Este é um aviso de teste")
    test_logger.error("Este é um erro de teste")
    
    # Teste de funcionalidades específicas
    log_user_action(test_logger, "login", "usuário fez login")
    log_api_call(test_logger, "search_products", 150, True)
    log_database_operation(test_logger, "INSERT", "products", True, 123)
    log_performance(test_logger, "process_data", 0.5, items_processed=100)
    log_security_event(test_logger, "login_attempt", "LOW", "Tentativa de login normal")
    log_business_metric(test_logger, "total_users", 150, "users")
    
    print("✅ Sistema de logging Loguru configurado e testado!")
