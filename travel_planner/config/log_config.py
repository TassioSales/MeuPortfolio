"""Logging configuration for the Travel Planner application.

This module configures Loguru for structured logging with file rotation and console output.
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
import uuid

from loguru import logger
from loguru._defaults import LOGURU_FORMAT

from .settings import settings


def get_session_id() -> str:
    """Generate a unique session ID for request tracking."""
    return str(uuid.uuid4())


def formatter(record: Dict[str, Any]) -> str:
    """Format log records with additional context."""
    # Add session ID to log records if available
    session_id = record.get("extra", {}).get("session_id", "")
    if session_id:
        record["extra"]["session_id"] = f"[{session_id}] "
    else:
        record["extra"]["session_id"] = ""
    
    return "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[session_id]}{name}:{function}:{line} - {message}\n{exception}"


def serialize(record: Dict[str, Any]) -> str:
    """Serialize log record to JSON."""
    subset = {
        "timestamp": record["time"].timestamp(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
    }
    
    # Add extra fields if present
    if record["exception"]:
        subset["exception"] = str(record["exception"])
    
    if "session_id" in record["extra"]:
        subset["session_id"] = record["extra"]["session_id"]
    
    return json.dumps(subset)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure Loguru logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Remove default logger
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stderr,
        level=log_level,
        format=formatter,
        colorize=True,
        backtrace=True,
        diagnose=settings.DEBUG,
    )
    
    # Add file handler if LOG_FILE is set
    if settings.LOG_FILE:
        log_file = settings.log_file_path
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            rotation="10 MB",
            retention="7 days",
            level=log_level,
            format=formatter,
            backtrace=True,
            diagnose=settings.DEBUG,
            encoding="utf-8",
        )
    
    # Configure loguru to use the same log level as the application
    logger.configure(handlers=[{"sink": sys.stderr, "level": log_level}])
    
    # Log configuration
    logger.info("Logging configured", log_level=log_level, log_file=str(settings.log_file_path) if settings.LOG_FILE else "None")


# Initialize logging when module is imported
setup_logging(settings.LOG_LEVEL)

# Create a logger with session context
def get_logger(name: Optional[str] = None, session_id: Optional[str] = None):
    """Get a logger with session context.
    
    Args:
        name: Logger name (usually __name__)
        session_id: Optional session ID for request tracking
        
    Returns:
        Configured logger instance
    """
    logger_ = logger.bind(session_id=session_id or get_session_id())
    if name:
        return logger_.bind(name=name)
    return logger_
