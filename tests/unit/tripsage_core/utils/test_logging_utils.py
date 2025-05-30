"""
Unit tests for TripSage Core logging utilities.

Tests the logging configuration, context adapter, and utility functions.
"""

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tripsage_core.utils.logging_utils import (
    ContextAdapter,
    get_logger,
    log_exception,
    setup_logging,
)


class TestLoggingUtils:
    """Test suite for logging utilities."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for log files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture(autouse=True)
    def reset_logging(self):
        """Reset logging configuration after each test."""
        yield
        # Clear all handlers
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    # NOTE: Tests for private functions _get_log_level and _should_log_to_file
    # have been removed as these are internal implementation details
    # Testing them would break encapsulation

    def test_setup_logging_console_only(self):
        """Test logging setup with console handler only."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            setup_logging(log_level=logging.DEBUG)

        root_logger = logging.getLogger()

        # Should have console handler
        console_handlers = [
            h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)
        ]
        assert len(console_handlers) == 1

        # Should not have file handler
        file_handlers = [
            h for h in root_logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 0

    def test_setup_logging_with_file(self, temp_log_dir):
        """Test logging setup with file handler."""
        log_file = temp_log_dir / "test.log"

        with patch.dict(os.environ, {}, clear=True):
            setup_logging(log_level=logging.INFO, log_file=str(log_file))

        root_logger = logging.getLogger()

        # Should have both console and file handlers
        assert len(root_logger.handlers) == 2

        # Test logging to file
        test_logger = logging.getLogger("test")
        test_logger.info("Test message")

        # Verify log file was created and contains message
        assert log_file.exists()
        with open(log_file) as f:
            content = f.read()
            assert "Test message" in content

    def test_get_logger(self):
        """Test getting a logger instance."""
        # Test without context - returns Logger
        logger1 = get_logger("test.module1")
        logger2 = get_logger("test.module2")
        logger3 = get_logger("test.module1")

        assert isinstance(logger1, logging.Logger)
        assert isinstance(logger2, logging.Logger)
        assert logger1.name == "test.module1"
        assert logger2.name == "test.module2"
        assert logger1 is logger3  # Same logger instance

        # Test with context - returns LoggerAdapter
        logger_with_context = get_logger("test.module3", context={"request_id": "123"})
        assert isinstance(logger_with_context, logging.LoggerAdapter)
        assert logger_with_context.logger.name == "test.module3"

    def test_context_adapter(self):
        """Test ContextAdapter functionality."""
        base_logger = logging.getLogger("test")
        adapter = ContextAdapter(base_logger, {"request_id": "123"})

        # Mock handler to capture log records
        handler = MagicMock()
        base_logger.addHandler(handler)
        base_logger.setLevel(logging.DEBUG)

        # Log with context
        adapter.info("Test message", extra={"user_id": "456"})

        # Verify the handler was called
        handler.handle.assert_called_once()
        record = handler.handle.call_args[0][0]

        # Check that context was added
        assert hasattr(record, "request_id")
        assert record.request_id == "123"
        assert hasattr(record, "user_id")
        assert record.user_id == "456"

    def test_context_adapter_with_missing_attributes(self):
        """Test ContextAdapter with missing context attributes."""
        base_logger = logging.getLogger("test")
        adapter = ContextAdapter(base_logger, {"request_id": "123"})

        handler = MagicMock()
        base_logger.addHandler(handler)
        base_logger.setLevel(logging.DEBUG)

        # Log without extra context
        adapter.info("Test message")

        handler.handle.assert_called_once()
        record = handler.handle.call_args[0][0]

        # Should have default values for missing attributes
        assert hasattr(record, "request_id")
        assert record.request_id == "123"

    def test_log_exception_with_context(self, caplog):
        """Test logging exceptions with context."""
        logger = get_logger("test.exceptions")

        try:
            raise ValueError("Test error")
        except ValueError as e:
            log_exception(logger, e, {"operation": "test", "user_id": "123"})

        # Check that exception was logged
        assert "Exception occurred: Test error" in caplog.text
        assert "operation" in caplog.text
        assert "test" in caplog.text

    def test_log_exception_with_traceback(self, caplog):
        """Test logging exceptions with traceback."""
        logger = get_logger("test.exceptions")

        try:
            raise ValueError("Test error with traceback")
        except ValueError as e:
            log_exception(logger, e, include_traceback=True)

        # Check that traceback was included
        assert "Test error with traceback" in caplog.text
        assert "Traceback" in caplog.text

    def test_logger_hierarchy(self):
        """Test logger hierarchy and inheritance."""
        # Set up parent logger
        parent_logger = get_logger("tripsage")
        parent_logger.logger.setLevel(logging.WARNING)

        # Child logger should inherit settings
        child_logger = get_logger("tripsage.services.test")

        # Test that child inherits parent's level
        assert child_logger.isEnabledFor(logging.WARNING)
        assert not child_logger.isEnabledFor(logging.INFO)

    def test_logging_performance(self):
        """Test that logging doesn't significantly impact performance."""
        logger = get_logger("performance.test")

        import time

        # Time logging operations
        start = time.time()
        for i in range(1000):
            logger.debug(f"Debug message {i}")
        end = time.time()

        # Should complete quickly (less than 100ms for 1000 messages)
        assert (end - start) < 0.1

    def test_logger_formatting(self, caplog):
        """Test log message formatting."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            setup_logging(log_level=logging.INFO)

        logger = get_logger("test.formatting")
        logger.info("Test message with %s", "formatting", extra={"key": "value"})

        # Check format includes expected components
        assert "test.formatting" in caplog.text  # Logger name
        assert "Test message with formatting" in caplog.text  # Message
        assert "INFO" in caplog.text  # Level

    def test_multiline_log_handling(self, caplog):
        """Test handling of multiline log messages."""
        logger = get_logger("test.multiline")

        multiline_message = """This is a
        multiline
        log message"""

        logger.info(multiline_message)

        # All lines should be in the output
        assert "This is a" in caplog.text
        assert "multiline" in caplog.text
        assert "log message" in caplog.text

    def test_unicode_handling(self, caplog):
        """Test handling of unicode in log messages."""
        logger = get_logger("test.unicode")

        # Test various unicode characters
        messages = [
            "Hello 世界",  # Chinese
            "Привет мир",  # Russian
            "🚀 Rocket emoji",  # Emoji
            "Special chars: ñáéíóú",  # Accented
        ]

        for msg in messages:
            logger.info(msg)
            assert msg in caplog.text

    def test_large_context_handling(self):
        """Test handling of large context objects."""
        logger = get_logger("test.large_context")

        # Create large context
        large_context = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}

        # Should handle without error
        logger.info("Message with large context", extra=large_context)

    @pytest.mark.parametrize(
        "level,should_log",
        [
            (logging.DEBUG, False),
            (logging.INFO, True),
            (logging.WARNING, True),
            (logging.ERROR, True),
        ],
    )
    def test_log_level_filtering(self, level, should_log, caplog):
        """Test that log level filtering works correctly."""
        setup_logging(log_level=logging.INFO)
        logger = get_logger("test.filtering")

        test_message = f"Test message at {logging.getLevelName(level)}"
        logger.log(level, test_message)

        if should_log:
            assert test_message in caplog.text
        else:
            assert test_message not in caplog.text

    def test_exception_logging_formats(self, caplog):
        """Test different ways to log exceptions."""
        logger = get_logger("test.exceptions")

        try:
            1 / 0
        except ZeroDivisionError:
            # Method 1: Using exc_info
            logger.error("Division error", exc_info=True)

            # Method 2: Using exception method
            logger.exception("Division error occurred")

            # Method 3: Using log_exception utility
            log_exception(logger, ZeroDivisionError("Cannot divide by zero"))

        # All methods should log the exception
        assert caplog.text.count("ZeroDivisionError") >= 3

    def test_child_logger_context(self):
        """Test that child loggers maintain their own context."""
        parent = get_logger("parent", {"parent_id": "123"})
        child = get_logger("parent.child", {"child_id": "456"})

        # Mock handler
        handler = MagicMock()
        logging.getLogger("parent").addHandler(handler)
        logging.getLogger("parent").setLevel(logging.DEBUG)

        child.info("Test message")

        # Verify child has its own context
        handler.handle.assert_called_once()
        record = handler.handle.call_args[0][0]
        assert record.child_id == "456"

    def test_logging_in_async_context(self):
        """Test logging works correctly in async contexts."""
        import asyncio

        async def async_function():
            logger = get_logger("test.async")
            logger.info("Async log message")
            return True

        # Run async function
        result = asyncio.run(async_function())
        assert result is True
