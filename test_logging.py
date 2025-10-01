"""Tests for structured logging functionality.

This module tests logging configuration, sensitive data redaction,
correlation IDs, and log output validation.
"""

import logging
from unittest.mock import Mock

import pytest

from services.api.app.logging_config import (
    CorrelationIdFilter,
    SensitiveDataFilter,
    StructuredFormatter,
    get_correlation_id,
    get_logger,
    set_correlation_id,
    setup_logging,
)


class TestSensitiveDataFilter:
    """Test sensitive data redaction in log messages."""

    def test_password_redaction(self):
        """Test that passwords are redacted from log messages."""
        log_filter = SensitiveDataFilter()

        record = Mock()
        record.msg = "Connecting with password=secret123"
        record.args = ()

        log_filter.filter(record)

        assert "secret123" not in record.msg
        assert "***REDACTED***" in record.msg

    def test_api_key_redaction(self):
        """Test that API keys are redacted from log messages."""
        log_filter = SensitiveDataFilter()

        record = Mock()
        record.msg = "Using api_key: sk-1234567890abcdef"
        record.args = ()

        log_filter.filter(record)

        assert "sk-1234567890abcdef" not in record.msg
        assert "***REDACTED***" in record.msg

    def test_token_redaction(self):
        """Test that tokens are redacted from log messages."""
        log_filter = SensitiveDataFilter()

        record = Mock()
        record.msg = "Authorization token=xyz123"
        record.args = ()

        log_filter.filter(record)

        assert "xyz123" not in record.msg
        assert "***REDACTED***" in record.msg

    def test_email_partial_redaction(self):
        """Test that emails are partially redacted (keep domain)."""
        log_filter = SensitiveDataFilter()

        record = Mock()
        record.msg = "User email: user@example.com"
        record.args = ()

        log_filter.filter(record)

        assert "user" not in record.msg
        assert "example.com" in record.msg
        assert "***@example.com" in record.msg

    def test_dict_arg_redaction(self):
        """Test that sensitive data in dict args is redacted."""
        log_filter = SensitiveDataFilter()

        record = Mock()
        record.msg = "Connecting to service"
        record.args = {"password": "secret", "username": "user"}

        log_filter.filter(record)

        assert record.args["password"] == "***REDACTED***"
        assert record.args["username"] == "user"  # Not sensitive

    def test_multiple_patterns_redaction(self):
        """Test that multiple sensitive patterns are redacted."""
        log_filter = SensitiveDataFilter()

        record = Mock()
        record.msg = "Config: password=pw123, api_key=key456, secret=sec789"
        record.args = ()

        log_filter.filter(record)

        assert "pw123" not in record.msg
        assert "key456" not in record.msg
        assert "sec789" not in record.msg
        assert record.msg.count("***REDACTED***") == 3


class TestCorrelationIdFilter:
    """Test correlation ID injection into log records."""

    def test_correlation_id_added_to_record(self):
        """Test that correlation ID is added to log record."""
        set_correlation_id("test-correlation-123")
        log_filter = CorrelationIdFilter()

        record = Mock()
        log_filter.filter(record)

        assert hasattr(record, "correlation_id")
        assert record.correlation_id == "test-correlation-123"

    def test_correlation_id_default_value(self):
        """Test that default correlation ID is used when not set."""
        # Clear correlation ID
        set_correlation_id(None)
        log_filter = CorrelationIdFilter()

        record = Mock()
        log_filter.filter(record)

        assert hasattr(record, "correlation_id")
        assert record.correlation_id == "N/A"

    def test_correlation_id_context_isolation(self):
        """Test that correlation IDs are context-isolated."""
        set_correlation_id("context-1")

        log_filter = CorrelationIdFilter()
        record1 = Mock()
        log_filter.filter(record1)

        set_correlation_id("context-2")
        record2 = Mock()
        log_filter.filter(record2)

        # Second call should have new correlation ID
        assert record2.correlation_id == "context-2"


class TestStructuredFormatter:
    """Test structured log formatting."""

    def test_basic_log_formatting(self):
        """Test that logs are formatted with all required fields."""
        set_correlation_id("format-test-123")

        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_function",
        )
        record.correlation_id = "format-test-123"

        formatter = StructuredFormatter()
        formatted = formatter.format(record)

        # Check all required fields are present
        assert "INFO" in formatted
        assert "[format-test-123]" in formatted
        assert "test.module:test_function:42" in formatted
        assert "Test message" in formatted

    def test_duration_formatting(self):
        """Test that duration is formatted when present."""
        set_correlation_id("duration-test")

        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Operation completed",
            args=(),
            exc_info=None,
            func="test_operation",
        )
        record.correlation_id = "duration-test"
        record.duration_ms = 123.45

        formatter = StructuredFormatter()
        formatted = formatter.format(record)

        assert "duration=123.45ms" in formatted

    def test_extra_data_formatting(self):
        """Test that extra data is formatted when present."""
        set_correlation_id("extra-test")

        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Data processed",
            args=(),
            exc_info=None,
            func="process_data",
        )
        record.correlation_id = "extra-test"
        record.extra_data = "rows=100, errors=0"

        formatter = StructuredFormatter()
        formatted = formatter.format(record)

        assert "rows=100, errors=0" in formatted


class TestLoggingSetup:
    """Test logging setup and configuration."""

    def test_setup_logging_configures_root_logger(self):
        """Test that setup_logging configures the root logger."""
        logger = setup_logging(level=logging.INFO)

        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0

    def test_get_logger_returns_configured_logger(self):
        """Test that get_logger returns a properly configured logger."""
        setup_logging()
        logger = get_logger("test.module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_sensitive_filter_enabled_by_default(self):
        """Test that sensitive data filter is enabled by default."""
        logger = setup_logging(enable_sensitive_filter=True)

        # Check that at least one handler has SensitiveDataFilter
        has_sensitive_filter = False
        for handler in logger.handlers:
            for log_filter in handler.filters:
                if isinstance(log_filter, SensitiveDataFilter):
                    has_sensitive_filter = True
                    break

        assert has_sensitive_filter


class TestCorrelationIdManagement:
    """Test correlation ID getter/setter."""

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        test_id = "test-12345"
        set_correlation_id(test_id)

        retrieved_id = get_correlation_id()

        assert retrieved_id == test_id

    def test_get_correlation_id_returns_none_when_not_set(self):
        """Test that get_correlation_id returns None when not set."""
        set_correlation_id(None)
        retrieved_id = get_correlation_id()

        assert retrieved_id is None

    def test_correlation_id_updates(self):
        """Test that correlation ID can be updated."""
        set_correlation_id("first-id")
        set_correlation_id("second-id")

        retrieved_id = get_correlation_id()

        assert retrieved_id == "second-id"


class TestLogOutputCapture:
    """Test that critical operations emit expected log entries."""

    def test_info_log_emitted(self):
        """Test that INFO level logs can be emitted without errors."""
        logger = get_logger("test.capture")

        # This test just ensures logging works without raising exceptions
        try:
            logger.info("Test info message")
            success = True
        except Exception:
            success = False

        assert success

    def test_error_log_emitted(self):
        """Test that ERROR level logs can be emitted without errors."""
        logger = get_logger("test.capture")

        # This test just ensures logging works without raising exceptions
        try:
            logger.error("Test error message")
            success = True
        except Exception:
            success = False

        assert success

    def test_debug_log_emitted(self):
        """Test that DEBUG logs can be emitted without errors."""
        logger = get_logger("test.capture")

        # This test just ensures logging works without raising exceptions
        try:
            logger.debug("Debug message")
            success = True
        except Exception:
            success = False

        assert success

    def test_log_with_extra_fields_emitted(self):
        """Test that logs with extra fields can be emitted without errors."""
        logger = get_logger("test.capture")

        # This test just ensures logging with extra fields works
        try:
            logger.info("Operation completed", extra={"duration_ms": 100})
            success = True
        except Exception:
            success = False

        assert success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
