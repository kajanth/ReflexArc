"""
🧠 NSA Structured Logging Configuration

Provides structured logging with JSON output for production and
human-readable console output for development.

Usage:
    from utils.logging_config import get_logger
    
    logger = get_logger(__name__)
    logger.info("spike_detected", sense_type="vision", novelty=0.85)
"""

import logging
import os
import sys
import json
import time
from typing import Any, Dict
from pathlib import Path

import structlog


def get_log_level() -> int:
    """Get log level from environment variable."""
    level_name = os.environ.get("NSA_LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_name, logging.INFO)


def is_production() -> bool:
    """Check if running in production mode."""
    return os.environ.get("NSA_ENV", "development").lower() == "production"


def configure_logging() -> None:
    """
    Configure structured logging for the NSA system.
    
    Production mode: JSON output for log aggregation
    Development mode: Colored console output for readability
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=get_log_level(),
    )
    
    # Shared processors for all environments
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        redact_sensitive_data,
        intercept_errors_processor,
    ]
    
    if is_production():
        # Production: JSON output
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: Colored console output
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            ),
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured structured logger
        
    Example:
        logger = get_logger(__name__)
        logger.info("processing_spike", 
                   sense_type="vision",
                   novelty_distance=0.85,
                   layer="RAS")
    """
    return structlog.get_logger(name)


def redact_sensitive_data(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processor to redact sensitive data from logs.
    
    Redacts:
    - API keys
    - Tokens
    - Passwords
    - Authorization headers
    """
    sensitive_keys = {
        "api_key", "apikey", "token", "password", "secret",
        "authorization", "auth", "credentials"
    }
    
    for key in list(event_dict.keys()):
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            event_dict[key] = "***REDACTED***"
    
    return event_dict


def intercept_errors_processor(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Interceptor that grabs any error/critical logs and writes 
    them to a task list file for the ADK Swarm to fix overnight.
    """
    if method_name in ("error", "exception", "critical"):
        try:
            # Ensure memory directory exists
            memory_dir = Path("memory")
            memory_dir.mkdir(exist_ok=True)
            
            task_file = memory_dir / "error_tasks.json"
            
            # Load existing tasks
            tasks = []
            if task_file.exists():
                with open(task_file, "r") as f:
                    try:
                        tasks = json.load(f)
                    except json.JSONDecodeError:
                        pass
                        
            # Create new task entry
            new_task = {
                "id": f"err_{int(time.time()*1000)}",
                "timestamp": time.time(),
                "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
                "logger": event_dict.get("logger", "unknown"),
                "message": event_dict.get("event", "Unknown Error"),
                "context": {k: v for k, v in event_dict.items() if k not in ("event", "timestamp", "level", "logger")},
                "status": "pending",
                "severity": method_name
            }
            
            tasks.append(new_task)
            
            # Write back to file
            with open(task_file, "w") as f:
                json.dump(tasks, f, indent=2)
                
        except Exception:
            # We must fail silently here so we don't break the logging pipeline itself
            pass
            
    return event_dict


# Auto-configure on import
configure_logging()
