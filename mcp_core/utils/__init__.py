"""
Centralized logging utilities for MCP Core.
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
import sys


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, 'job_id'):
            log_entry['job_id'] = record.job_id
        if hasattr(record, 'agent'):
            log_entry['agent'] = record.agent
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)
        
        return json.dumps(log_entry)


def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    """
    Set up logging configuration for MCP Core.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to use JSON formatting
    """
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set up handler
    handler = logging.StreamHandler(sys.stdout)
    
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_job_event(logger: logging.Logger, job_id: str, event: str, 
                 extra: Optional[Dict[str, Any]] = None) -> None:
    """
    Log a job-related event with structured data.
    
    Args:
        logger: Logger instance
        job_id: Job ID
        event: Event description
        extra: Additional data to include
    """
    log_data = {
        "job_id": job_id,
        "event": event,
        "extra": extra or {}
    }
    logger.info(f"Job event: {event}", extra=log_data)


def log_agent_event(logger: logging.Logger, agent_name: str, event: str,
                   job_id: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an agent-related event with structured data.
    
    Args:
        logger: Logger instance
        agent_name: Agent name
        event: Event description
        job_id: Optional job ID
        extra: Additional data to include
    """
    log_data = {
        "agent": agent_name,
        "event": event,
        "extra": extra or {}
    }
    if job_id:
        log_data["job_id"] = job_id
    
    logger.info(f"Agent event: {event}", extra=log_data)
