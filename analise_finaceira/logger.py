import os
import sys
import time
import json
import uuid
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from functools import wraps
from loguru import logger
from collections import defaultdict
from threading import Lock

# Caminho para a pasta de logs
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True, parents=True)

# Dicionário para armazenar métricas de desempenho
_metrics = defaultdict(list)
_metrics_lock = Lock()

# Caminho para a pasta de logs
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Configuração dos níveis de log
class LogLevel:
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# Contexto da requisição atual
class RequestContext:
    _request_id = ""
    _user_id = ""
    _extra = {}
    
    @classmethod
    def set_request_context(cls, request_id: str = None, user_id: str = None, **extra):
        """Define o contexto da requisição atual."""
        cls._request_id = request_id or str(uuid.uuid4())
        cls._user_id = user_id or ""
        cls._extra = extra or {}
        return cls._request_id
        
    @classmethod
    def update_context(cls, **kwargs):
        """Atualiza o contexto da requisição atual.
        
        Args:
            **kwargs: Pares chave-valor para atualizar o contexto
        """
        cls._extra.update(kwargs)
        return cls.get_context()
        
    @classmethod
    def get_request_id(cls) -> str:
        """Obtém o ID da requisição atual."""
        return cls._request_id
        
    @classmethod
    def get_context(cls) -> dict:
        """Obtém todo o contexto da requisição."""
        return {
            "request_id": cls._request_id,
            "user_id": cls._user_id,
            **cls._extra
        }

# Configuração do logger
def setup_logger(module_name: str):
    """Configura o logger para um módulo específico.
    
    Args:
        module_name (str): Nome do módulo (ex: 'upload', 'dashboard')
    """
    # Remove todos os handlers existentes
    logger.remove()
    
    # Formatação personalizada para incluir contexto
    def formatter(record: dict) -> str:
        # Adiciona contexto ao registro
        record["extra"].setdefault("request_id", RequestContext.get_request_id())
        
        # Formata a mensagem base
        log_fmt = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            f"<cyan>{module_name}</cyan> | "
        )
        
        # Adiciona request_id se disponível
        if record["extra"].get("request_id"):
            log_fmt += "<yellow>{extra[request_id]}</yellow> | "
            
        # Adiciona usuário se disponível
        if record["extra"].get("user_id"):
            log_fmt += "<blue>user:{extra[user_id]}</blue> | "
            
        # Adiciona a mensagem
        log_fmt += "<level>{message}</level>"
        
        # Adiciona dados extras se existirem
        extras = {k: v for k, v in record["extra"].items() 
                if k not in ["request_id", "user_id"] and v is not None}
                
        if extras:
            log_fmt += " | {extra[__extras]}"
            record["extra"]["__extras"] = json.dumps(
                extras, 
                default=str,
                ensure_ascii=False
            )
            
        return log_fmt + "\n"
    
    # Configuração do handler de arquivo
    log_file = LOG_DIR / f"{module_name}.log"
    logger.add(
        str(log_file),
        rotation="10 MB",  # Rotaciona o arquivo a cada 10MB
        retention="30 days",  # Mantém os logs por 30 dias
        compression="zip",  # Comprime os arquivos antigos
        level="DEBUG",  # Nível mínimo de log
        format=formatter,
        enqueue=True,  # Thread-safe
        backtrace=True,  # Habilita rastreamento de pilha
        diagnose=True,  # Mostra variáveis locais no traceback
        catch=True,  # Evita que erros no logger quebrem a aplicação
        encoding="utf-8"
    )
    
    # Configuração do handler de console
    logger.add(
        sys.stderr,
        level="INFO",  # Nível mínimo para console
        format=formatter,
        enqueue=True,
        colorize=True,  # Cores no console
        backtrace=True,
        diagnose=True,
        catch=True
    )
    
    return logger

def log_function(logger_instance=None, level=LogLevel.INFO, log_args: bool = True, 
               log_result: bool = True, track_performance: bool = True):
    """Decorador avançado para registrar chamadas de função com métricas.
    
    Args:
        logger_instance: Instância do logger (opcional)
        level: Nível de log (padrão: INFO)
        log_args: Se True, registra os argumentos da função
        log_result: Se True, registra o resultado da função
        track_performance: Se True, rastreia o tempo de execução
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Usa o logger global se nenhum for fornecido
            try:
                log = logger_instance or get_logger(func.__module__)
                
                # Se ainda não houver logger, retorna a função sem log
                if log is None:
                    return func(*args, **kwargs)
                    
                func_name = func.__name__
                
                # Prepara o contexto do log
                log_context = {
                    "function": func_name,
                    "module": func.__module__,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                
                # Adiciona argumentos se solicitado
                if log_args:
                    log_context["args"] = str(args)
                    log_context["kwargs"] = str(kwargs)
                
                # Inicia o temporizador
                start_time = time.monotonic() if track_performance else None
            except Exception as e:
                # Se houver erro ao configurar o log, apenas executa a função
                print(f"Erro ao configurar log: {str(e)}")
                return func(*args, **kwargs)
            
            # Log de início
            log.log(level, f"Iniciando {func_name}", **{"extra": log_context})
            
            try:
                # Executa a função
                result = func(*args, **kwargs)
                
                # Calcula o tempo de execução
                if track_performance and start_time is not None:
                    duration = time.monotonic() - start_time
                    log_context["duration_seconds"] = f"{duration:.4f}"
                    
                    # Registra métrica de desempenho
                    with _metrics_lock:
                        _metrics[func_name].append(duration)
                
                # Adiciona resultado ao contexto se solicitado
                if log_result:
                    log_context["result"] = str(result)[:200]  # Limita o tamanho
                
                # Log de sucesso
                log.log(level, f"{func_name} concluído", **{"extra": log_context})
                
                return result
                
            except Exception as e:
                # Log de erro detalhado
                error_context = {
                    **log_context,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc()
                }
                
                if track_performance and start_time is not None:
                    error_context["duration_seconds"] = f"{time.monotonic() - start_time:.4f}"
                
                log.error(
                    f"Erro em {func_name}",
                    **{"extra": error_context}
                )
                raise
                
        return wrapper
    return decorator

# Função para obter o logger de um módulo
def get_logger(module_name: str) -> logger:
    """Obtém uma instância do logger para o módulo especificado.
    
    Args:
        module_name (str): Nome do módulo
        
    Returns:
        Logger: Instância do logger
    """
    return setup_logger(module_name)

def get_metrics() -> Dict[str, list]:
    """Obtém as métricas de desempenho coletadas.
    
    Returns:
        Dict com as métricas de desempenho por função
    """
    with _metrics_lock:
        return {
            func: {
                "count": len(times),
                "avg": sum(times) / len(times) if times else 0,
                "min": min(times) if times else 0,
                "max": max(times) if times else 0,
                "last_10": times[-10:]
            }
            for func, times in _metrics.items()
        }

def clear_metrics() -> None:
    """Limpa as métricas de desempenho."""
    with _metrics_lock:
        _metrics.clear()

def log_metrics(logger_instance: logger = None) -> None:
    """Registra as métricas de desempenho atuais.
    
    Args:
        logger_instance: Instância do logger (opcional)
    """
    log = logger_instance or logger
    metrics = get_metrics()
    
    if not metrics:
        log.info("Nenhuma métrica de desempenho disponível")
        return
    
    log.info("Métricas de desempenho:")
    for func, data in metrics.items():
        log.info(
            f"{func}: {data['count']} chamadas | "
            f"Média: {data['avg']:.4f}s | "
            f"Min: {data['min']:.4f}s | "
            f"Max: {data['max']:.4f}s"
        )

# Função para limpar logs antigos
def cleanup_old_logs(days: int = 30, logger_instance: logger = None) -> None:
    """Remove arquivos de log mais antigos que o número especificado de dias.
    
    Args:
        days (int): Número de dias para manter os logs
        logger_instance: Instância do logger (opcional)
    """
    log = logger_instance or get_logger("logger")
    cutoff = datetime.now() - timedelta(days=days)
    removed = 0
    errors = 0
    
    log.info(f"Iniciando limpeza de logs antigos (mais de {days} dias)")
    
    for log_file in LOG_DIR.glob("*.log"):
        try:
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_time < cutoff:
                log_file.unlink()
                log.debug(f"Arquivo de log removido: {log_file.name} (modificado em {file_time})")
                removed += 1
        except Exception as e:
            errors += 1
            log.error(
                f"Erro ao remover {log_file.name}",
                error=str(e),
                error_type=type(e).__name__
            )
    
    log.info(
        "Limpeza de logs concluída",
        removed=removed,
        errors=errors,
        kept=len(list(LOG_DIR.glob("*.log"))) - removed
    )

# Exemplo de uso:
if __name__ == "__main__":
    # Configura o logger
    log = get_logger("demo")
    
    # Exemplo de uso básico
    log.info("Iniciando demonstração do sistema de logs")
    
    # Exemplo com contexto
    request_id = RequestContext.set_request_context(
        user_id="usuario123",
        ip="192.168.1.1"
    )
    log.info("Contexto de requisição configurado")
    
    # Exemplo de função decorada
    @log_function(log, level=LogLevel.DEBUG)
    def exemplo_soma(a: int, b: int) -> int:
        """Soma dois números."""
        return a + b
    
    # Chama a função decorada
    resultado = exemplo_soma(5, 3)
    log.info(f"Resultado da soma: {resultado}")
    
    # Exemplo de erro
    try:
        log.info("Tentando divisão por zero...")
        1 / 0
    except Exception as e:
        log.error("Erro ao dividir por zero", error=str(e))
    
    # Exibe métricas
    log_metrics(log)
    
    # Limpa logs antigos (mantendo 7 dias)
    cleanup_old_logs(days=7, logger_instance=log)
    
    log.info("Demonstração concluída")
