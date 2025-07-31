import os
import sys
from pathlib import Path
from loguru import logger
from datetime import datetime

# Create logs directory if it doesn't exist
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Generate log file name with current date
current_date = datetime.now().strftime("%Y-%m-%d")
LOG_FILE = LOG_DIR / f"app_{current_date}.log"
ERROR_LOG_FILE = LOG_DIR / f"error_{current_date}.log"

# Remove default logger
logger.remove()

# Custom log format
log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | " \
             "<level>{level: <8}</level> | " \
             "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

# Console handler
logger.add(
    sys.stderr,
    format=log_format,
    level="INFO",
    colorize=True,
    backtrace=True,
    diagnose=True
)

# File handler for all logs
logger.add(
    LOG_FILE,
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    level="DEBUG",
    format=log_format,
    backtrace=True,
    diagnose=True,
    enqueue=True  # Makes logging thread-safe
)

# Separate error file handler
logger.add(
    ERROR_LOG_FILE,
    rotation="10 MB",
    retention="90 days",
    compression="zip",
    level="ERROR",
    format=log_format,
    backtrace=True,
    diagnose=True,
    enqueue=True
)

def get_logger(name: str = None):
    """
    Get a logger instance with the specified name.
    
    Args:
        name (str, optional): Name of the logger. Defaults to None (root logger).
        
    Returns:
        Logger: Configured logger instance
    """
    return logger.bind(logger_name=name) if name else logger

def log_exceptions():
    """
    Decorator to log exceptions that occur in the decorated function.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {str(e)}")
                raise
        return wrapper
    return decorator

# Example usage:
if __name__ == "__main__":
    logger.info("Logger configured successfully!")
    logger.debug("This is a debug message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    try:
        1 / 0
    except ZeroDivisionError as e:
        logger.exception("Division by zero error")

# This allows importing the logger directly from this module
log = logger
