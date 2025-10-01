"""Centralized logging configuration for the Budget Agent application.

This module provides structured logging with:
- Consistent log formatting
- Sensitive data redaction
- Correlation ID support for request tracing
- Performance metrics
- Configurable log levels
"""

import logging
import re
import time
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable, Dict, Optional

# Context variable for correlation ID (thread-safe)
correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive information from log records."""

    # Patterns to redact (case-insensitive)
    SENSITIVE_PATTERNS = [
        (re.compile(r"(password|passwd|pwd)[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", re.I), r"\1=***REDACTED***"),
        (re.compile(r"(api[_-]?key|apikey|token)[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", re.I), r"\1=***REDACTED***"),
        (re.compile(r"(authorization|auth)[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", re.I), r"\1=***REDACTED***"),
        (re.compile(r"(secret|credential)[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", re.I), r"\1=***REDACTED***"),
        # Email addresses (partial redaction)
        (re.compile(r"([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", re.I), r"***@\2"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive data from log message."""
        if hasattr(record, "msg") and isinstance(record.msg, str):
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)

        # Also redact args if present
        if hasattr(record, "args") and record.args:
            if isinstance(record.args, dict):
                record.args = self._redact_dict(record.args)
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(self._redact_value(arg) for arg in record.args)

        return True

    def _redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive keys in dictionary."""
        redacted = {}
        for key, value in data.items():
            if any(pattern in key.lower() for pattern in ["password", "token", "secret", "api_key", "apikey"]):
                redacted[key] = "***REDACTED***"
            elif isinstance(value, dict):
                redacted[key] = self._redact_dict(value)
            else:
                redacted[key] = self._redact_value(value)
        return redacted

    def _redact_value(self, value: Any) -> Any:
        """Redact sensitive values."""
        if isinstance(value, str):
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                value = pattern.sub(replacement, value)
        elif isinstance(value, dict):
            return self._redact_dict(value)
        return value


class CorrelationIdFilter(logging.Filter):
    """Filter to add correlation ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation_id to log record."""
        record.correlation_id = correlation_id.get() or "N/A"
        return True


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging output."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured information."""
        # Add correlation ID if available
        correlation = getattr(record, "correlation_id", "N/A")

        # Base format
        log_format = (
            f"%(asctime)s | %(levelname)-8s | "
            f"[{correlation}] | "
            f"%(name)s:%(funcName)s:%(lineno)d | "
            f"%(message)s"
        )

        # Add extra fields if present
        if hasattr(record, "duration_ms"):
            log_format += f" | duration={record.duration_ms:.2f}ms"

        if hasattr(record, "extra_data") and record.extra_data:
            log_format += f" | {record.extra_data}"

        formatter = logging.Formatter(log_format)
        return formatter.format(record)


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    enable_sensitive_filter: bool = True,
) -> logging.Logger:
    """
    Setup structured logging for the application.

    Args:
        level: Logging level (default: INFO)
        log_file: Optional log file path (if None, logs to console only)
        enable_sensitive_filter: Whether to enable sensitive data redaction

    Returns:
        Configured root logger
    """
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Add filters
    console_handler.addFilter(CorrelationIdFilter())
    if enable_sensitive_filter:
        console_handler.addFilter(SensitiveDataFilter())

    # Set formatter
    console_handler.setFormatter(StructuredFormatter())
    logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.addFilter(CorrelationIdFilter())
        if enable_sensitive_filter:
            file_handler.addFilter(SensitiveDataFilter())
        file_handler.setFormatter(StructuredFormatter())
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_execution_time(logger: logging.Logger, level: int = logging.INFO):
    """
    Decorator to log function execution time.

    Args:
        logger: Logger instance to use
        level: Log level (default: INFO)

    Usage:
        @log_execution_time(logger)
        async def my_function():
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__
            logger.log(level, f"Starting {func_name}")

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.log(
                    level,
                    f"Completed {func_name}",
                    extra={"duration_ms": duration_ms},
                )
                return result
            except Exception as exc:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Failed {func_name}: {exc}",
                    extra={"duration_ms": duration_ms},
                    exc_info=True,
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__
            logger.log(level, f"Starting {func_name}")

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.log(
                    level,
                    f"Completed {func_name}",
                    extra={"duration_ms": duration_ms},
                )
                return result
            except Exception as exc:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Failed {func_name}: {exc}",
                    extra={"duration_ms": duration_ms},
                    exc_info=True,
                )
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        import inspect

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def set_correlation_id(new_id: str) -> None:
    """
    Set correlation ID for the current context.

    Args:
        new_id: Correlation ID (e.g., run_id, request_id)
    """
    correlation_id.set(new_id)


def get_correlation_id() -> Optional[str]:
    """
    Get correlation ID for the current context.

    Returns:
        Current correlation ID or None
    """
    return correlation_id.get()


# Initialize default logging configuration
setup_logging()
