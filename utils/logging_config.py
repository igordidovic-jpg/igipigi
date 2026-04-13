"""
CFOS-XG PRO 75 TITAN - Logging Configuration

Structured JSON logging for production monitoring.
"""
import logging
import json
import time
import os
from typing import Optional


class JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "match"):
            log_data["match"] = record.match
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    use_json: bool = True,
) -> None:
    """
    Configure application logging.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional path to log file
        use_json: Use JSON format (True) or plain text (False)
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    formatter: logging.Formatter
    if use_json:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    root = logging.getLogger()
    root.setLevel(numeric_level)

    for handler in root.handlers[:]:
        root.removeHandler(handler)

    for handler in handlers:
        handler.setFormatter(formatter)
        root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
