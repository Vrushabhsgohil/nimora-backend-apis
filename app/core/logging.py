import logging
import sys
import json
from datetime import datetime
from uuid import uuid4
from contextvars import ContextVar

from app.core.config import settings

# Correlation ID context var
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="unknown")

class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the LogRecord.
    """
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "correlation_id": correlation_id.get(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def setup_logging():
    """
    Configures the logging for the application.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    
    # clear existing handlers
    root_logger.handlers = []
    root_logger.addHandler(handler)
    
    # Quiet down some libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

def get_logger(name: str):
    return logging.getLogger(name)
