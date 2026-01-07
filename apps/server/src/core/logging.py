"""Structured logging configuration for Observer."""

import logging
import sys
import traceback
from contextvars import ContextVar
from typing import Any

# Context variable for request ID tracking
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class SensitiveDataFilter(logging.Filter):
    """Filter to prevent logging sensitive data."""

    SENSITIVE_KEYS = {
        "password",
        "token",
        "secret",
        "api_key",
        "apikey",
        "api-key",
        "authorization",
        "auth",
        "credential",
        "private_key",
        "secret_key",
        "access_token",
        "refresh_token",
        "claude_oauth_token",
        "ccproxy_internal_token",
    }

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive data from log records."""
        if hasattr(record, "msg"):
            record.msg = self._sanitize(record.msg)
        if hasattr(record, "args") and record.args:
            record.args = tuple(self._sanitize(arg) for arg in record.args)
        return True

    def _sanitize(self, obj: Any) -> Any:
        """Recursively sanitize objects to remove sensitive data."""
        if isinstance(obj, dict):
            return {
                k: "***REDACTED***" if k.lower() in self.SENSITIVE_KEYS else self._sanitize(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, (list, tuple)):
            return type(obj)(self._sanitize(item) for item in obj)
        elif isinstance(obj, str):
            # Check if string contains sensitive patterns
            lower_str = obj.lower()
            for key in self.SENSITIVE_KEYS:
                if key in lower_str and "=" in obj:
                    # Simple pattern matching for key=value
                    parts = obj.split("=")
                    if len(parts) >= 2:
                        return f"{parts[0]}=***REDACTED***"
            return obj
        return obj


class StructuredFormatter(logging.Formatter):
    """Custom formatter that adds structure and context to logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured data."""
        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            record.request_id = request_id
        else:
            record.request_id = "-"

        # Add structured fields
        if not hasattr(record, "event_type"):
            record.event_type = "general"

        # Format the base message
        formatted = super().format(record)

        # Add exception info with full stack trace if present
        if record.exc_info:
            formatted += "\n" + "".join(
                traceback.format_exception(*record.exc_info)
            )

        return formatted


def setup_logging(
    level: str = "INFO",
    json_logs: bool = False,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to output logs in JSON format (for production)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Add sensitive data filter
    console_handler.addFilter(SensitiveDataFilter())

    if json_logs:
        # JSON format for production (structured logging)
        try:
            import json
            from datetime import datetime

            class JsonFormatter(logging.Formatter):
                """JSON formatter for structured logging."""

                def format(self, record: logging.LogRecord) -> str:
                    log_data = {
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "level": record.levelname,
                        "logger": record.name,
                        "message": record.getMessage(),
                        "module": record.module,
                        "function": record.funcName,
                        "line": record.lineno,
                        "request_id": getattr(record, "request_id", "-"),
                        "event_type": getattr(record, "event_type", "general"),
                    }

                    # Add extra fields
                    for key, value in record.__dict__.items():
                        if key not in [
                            "name", "msg", "args", "created", "filename", "funcName",
                            "levelname", "levelno", "lineno", "module", "msecs",
                            "message", "pathname", "process", "processName",
                            "relativeCreated", "thread", "threadName", "exc_info",
                            "exc_text", "stack_info", "request_id", "event_type",
                        ]:
                            log_data[key] = value

                    # Add exception info if present
                    if record.exc_info:
                        log_data["exception"] = "".join(
                            traceback.format_exception(*record.exc_info)
                        )

                    return json.dumps(log_data)

            console_handler.setFormatter(JsonFormatter())
        except ImportError:
            # Fallback to structured text format
            format_str = (
                "%(asctime)s | %(levelname)-8s | %(request_id)s | "
                "%(name)s:%(funcName)s:%(lineno)d | %(message)s"
            )
            console_handler.setFormatter(StructuredFormatter(format_str))
    else:
        # Human-readable format for development
        format_str = (
            "%(asctime)s | %(levelname)-8s | %(request_id)s | "
            "%(name)s:%(funcName)s:%(lineno)d | %(message)s"
        )
        console_handler.setFormatter(StructuredFormatter(format_str))

    root_logger.addHandler(console_handler)

    # Set logging level for third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_error(
    logger: logging.Logger,
    message: str,
    error: Exception | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """
    Log an error with full stack trace and context.

    Args:
        logger: Logger instance
        message: Error message
        error: Exception instance (optional)
        extra: Additional context data (optional)
    """
    extra_data = extra or {}
    extra_data["event_type"] = "error"

    if error:
        logger.error(
            f"{message}: {error}",
            exc_info=True,
            extra=extra_data,
        )
    else:
        logger.error(message, extra=extra_data)


def log_security_event(
    logger: logging.Logger,
    event: str,
    details: dict[str, Any] | None = None,
    level: str = "WARNING",
) -> None:
    """
    Log security-relevant events.

    Args:
        logger: Logger instance
        event: Security event description
        details: Event details (optional)
        level: Log level (default: WARNING)
    """
    details = details or {}
    details["event_type"] = "security"

    log_level = getattr(logging, level.upper(), logging.WARNING)
    logger.log(log_level, f"SECURITY: {event}", extra=details)


def set_request_id(request_id: str) -> None:
    """Set request ID for the current context."""
    request_id_var.set(request_id)


def get_request_id() -> str | None:
    """Get request ID from the current context."""
    return request_id_var.get()


def clear_request_id() -> None:
    """Clear request ID from the current context."""
    request_id_var.set(None)
