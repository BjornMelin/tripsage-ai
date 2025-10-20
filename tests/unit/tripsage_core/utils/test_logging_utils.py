"""Clean tests for logging utilities.

Tests the actual implemented logging functionality.
Follows TripSage standards for focused, actionable testing.
"""

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from tripsage_core.utils.logging_utils import (
    ContextAdapter,
    configure_logging,
    configure_root_logger,
    get_logger,
    log_exception,
)


class TestLoggingUtils:
    """Test logging utilities by testing functions directly."""

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

    def test_context_adapter_process_method(self):
        """Test ContextAdapter process method."""
        base_logger = logging.getLogger("test.process")
        context = {"request_id": "123", "user_id": "456"}
        adapter = ContextAdapter(base_logger, {"context": context})

        # Test process method
        msg, kwargs = adapter.process("Test message", {})

        assert msg == "Test message"
        assert "extra" in kwargs
        assert kwargs["extra"]["request_id"] == "123"
        assert kwargs["extra"]["user_id"] == "456"

    def test_context_adapter_with_existing_extra(self):
        """Test ContextAdapter when extra already exists in kwargs."""
        base_logger = logging.getLogger("test.existing_extra")
        adapter = ContextAdapter(base_logger, {"context": {"service": "test"}})

        # Process with existing extra
        msg, kwargs = adapter.process("Test", {"extra": {"user_id": "123"}})

        assert kwargs["extra"]["service"] == "test"
        assert kwargs["extra"]["user_id"] == "123"

    def test_context_adapter_no_context(self):
        """Test ContextAdapter when no context is provided."""
        base_logger = logging.getLogger("test.no_context")
        adapter = ContextAdapter(base_logger, {})

        msg, kwargs = adapter.process("Test message", {})

        assert msg == "Test message"
        assert kwargs["extra"] == {}

    def test_get_logger_without_context(self):
        """Test getting a logger instance without context."""
        logger1 = get_logger("test.module1")
        logger2 = get_logger("test.module2")
        logger3 = get_logger("test.module1")

        assert isinstance(logger1, logging.Logger)
        assert isinstance(logger2, logging.Logger)
        assert logger1.name == "test.module1"
        assert logger2.name == "test.module2"
        assert logger1 is logger3  # Same logger instance (cached)

    def test_get_logger_with_context(self):
        """Test getting a logger with context."""
        logger_with_context = get_logger("test.module3", context={"request_id": "123"})
        assert isinstance(logger_with_context, ContextAdapter)
        assert logger_with_context.logger.name == "test.module3"

    def test_get_logger_with_custom_level(self):
        """Test getting a logger with custom level."""
        logger = get_logger("test.custom_level", level=logging.WARNING)
        assert logger.level == logging.WARNING

    def test_get_logger_context_not_cached(self):
        """Test that loggers with context are not cached."""
        logger1 = get_logger("test.context", context={"id": "1"})
        logger2 = get_logger("test.context", context={"id": "2"})

        # Should be different instances due to different context
        assert logger1 is not logger2
        assert isinstance(logger1, ContextAdapter)
        assert isinstance(logger2, ContextAdapter)

    def test_configure_root_logger_basic(self):
        """Test basic root logger configuration."""
        configure_root_logger(level=logging.WARNING)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)

    def test_configure_root_logger_clears_handlers(self):
        """Test that configure_root_logger clears existing handlers."""
        root_logger = logging.getLogger()
        # Add a dummy handler
        dummy_handler = logging.StreamHandler()
        root_logger.addHandler(dummy_handler)

        initial_count = len(root_logger.handlers)
        assert initial_count >= 1

        configure_root_logger(level=logging.INFO)

        # Should have only one handler (the new console handler)
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)

    def test_configure_logging_basic(self, temp_log_dir):
        """Test basic configure_logging functionality."""
        adapter = configure_logging(
            "test.configure",
            level=logging.DEBUG,
            log_to_file=False,  # Avoid file handling complexity
            context={"service": "test"},
        )

        assert isinstance(adapter, ContextAdapter)
        assert adapter.logger.name == "test.configure"
        assert adapter.logger.level == logging.DEBUG

    def test_configure_logging_clears_handlers(self):
        """Test that configure_logging clears existing handlers."""
        logger_name = "test.clear_handlers"
        logger = logging.getLogger(logger_name)

        # Add dummy handler
        dummy_handler = logging.StreamHandler()
        logger.addHandler(dummy_handler)
        initial_count = len(logger.handlers)
        assert initial_count >= 1

        adapter = configure_logging(logger_name, log_to_file=False)

        # Should have only new handlers
        assert len(adapter.logger.handlers) == 1
        assert isinstance(adapter.logger.handlers[0], logging.StreamHandler)

    @patch.dict(os.environ, {"TESTING": "true"})
    def test_configure_logging_no_file_in_testing(self):
        """Test configure_logging doesn't create file handlers in testing."""
        adapter = configure_logging("test.no_file", log_to_file=True)

        # Should only have console handler
        handlers = adapter.logger.handlers
        console_handlers = [h for h in handlers if isinstance(h, logging.StreamHandler)]
        file_handlers = [h for h in handlers if isinstance(h, logging.FileHandler)]

        assert len(console_handlers) == 1
        assert len(file_handlers) == 0

    def test_log_exception_basic(self, caplog):
        """Test basic exception logging."""
        logger = get_logger("test.exceptions")

        exception = ValueError("Test error")
        log_exception(logger, exception)

        assert "Exception occurred: Test error" in caplog.text
        # Exception name should be in the extra metadata, not in message text

    def test_log_exception_with_context(self, caplog):
        """Test exception logging with context."""
        logger = get_logger("test.exceptions")

        exception = RuntimeError("Context test error")
        context = {"operation": "test_operation", "user_id": "123"}
        log_exception(logger, exception, context)

        # Basic exception message should be present
        assert "Exception occurred: Context test error" in caplog.text
        # Context and exception type should be in extra metadata

    def test_log_exception_with_logger_adapter(self, caplog):
        """Test exception logging with logger adapter."""
        logger = get_logger("test.exceptions", context={"service": "test"})

        exception = KeyError("Missing key")
        log_exception(logger, exception)

        # Should handle the KeyError string representation with quotes
        assert "Exception occurred: 'Missing key'" in caplog.text

    @patch("tripsage_core.utils.logging_utils.get_settings")
    def test_get_log_level_from_settings(self, mock_settings):
        """Test log level determination from settings."""
        mock_settings.return_value.log_level = "WARNING"

        from tripsage_core.utils.logging_utils import _get_log_level

        level = _get_log_level()

        assert level == logging.WARNING

    @patch("tripsage_core.utils.logging_utils.get_settings")
    def test_get_log_level_invalid_fallback(self, mock_settings):
        """Test log level fallback for invalid settings."""
        mock_settings.return_value.log_level = "INVALID"

        from tripsage_core.utils.logging_utils import _get_log_level

        level = _get_log_level()

        assert level == logging.INFO  # Default fallback

    @patch("tripsage_core.utils.logging_utils.get_settings")
    def test_get_log_level_case_insensitive(self, mock_settings):
        """Test log level parsing is case insensitive."""
        mock_settings.return_value.log_level = "debug"

        from tripsage_core.utils.logging_utils import _get_log_level

        level = _get_log_level()

        assert level == logging.DEBUG

    def test_logger_caching(self):
        """Test that loggers are properly cached."""
        logger1 = get_logger("test.caching")
        logger2 = get_logger("test.caching")
        logger3 = get_logger("test.different")

        # Same name should return same instance
        assert logger1 is logger2
        # Different name should return different instance
        assert logger1 is not logger3

    def test_context_adapter_real_logging(self, caplog):
        """Test ContextAdapter in real logging scenario."""
        base_logger = logging.getLogger("test.real")
        base_logger.setLevel(logging.INFO)

        adapter = ContextAdapter(base_logger, {"context": {"request_id": "123"}})
        adapter.info("Test message", extra={"user_id": "456"})

        # Message should be logged
        assert "Test message" in caplog.text

    def test_logging_with_different_levels(self, caplog):
        """Test logging at different levels."""
        logger = get_logger("test.levels")
        logger.setLevel(logging.DEBUG)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.exception("Error message")
        logger.critical("Critical message")

        # All messages should be captured
        assert "Debug message" in caplog.text
        assert "Info message" in caplog.text
        assert "Warning message" in caplog.text
        assert "Error message" in caplog.text
        assert "Critical message" in caplog.text

    def test_configure_logging_file_handling(self, temp_log_dir):
        """Test file handler creation when not in testing mode."""
        with patch.dict(os.environ, {}, clear=True):  # Clear TESTING env
            with patch(
                "tripsage_core.utils.logging_utils.get_settings"
            ) as mock_settings:
                mock_settings.return_value.is_testing.return_value = False

                adapter = configure_logging(
                    "test.file.handler", log_to_file=True, log_dir=str(temp_log_dir)
                )

                # Should have both console and file handlers
                assert len(adapter.logger.handlers) == 2

                # Check handler types
                handler_types = [type(h).__name__ for h in adapter.logger.handlers]
                assert "StreamHandler" in handler_types
                assert "FileHandler" in handler_types

    def test_adapter_inheritance(self):
        """Test that ContextAdapter properly inherits from LoggerAdapter."""
        base_logger = logging.getLogger("test.inheritance")
        adapter = ContextAdapter(base_logger, {"context": {"key": "value"}})

        assert isinstance(adapter, logging.LoggerAdapter)
        assert adapter.logger is base_logger

    def test_empty_context_handling(self):
        """Test handling of empty context."""
        # Empty context dict is falsy, so returns regular Logger
        logger = get_logger("test.empty_context", context={})
        assert isinstance(logger, logging.Logger)

        # Non-empty context should return ContextAdapter
        logger_with_context = get_logger("test.with_context", context={"key": "value"})
        assert isinstance(logger_with_context, ContextAdapter)
        assert logger_with_context.extra == {"context": {"key": "value"}}

        # Without context parameter, should return regular Logger
        logger_no_context = get_logger("test.no_context_param")
        assert isinstance(logger_no_context, logging.Logger)

    def test_logger_name_normalization(self, temp_log_dir):
        """Test that logger names are normalized for file paths."""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("tripsage_core.utils.logging_utils.get_settings") as mock_settings,
        ):
            mock_settings.return_value.is_testing.return_value = False

            # Use a name with dots that should be converted to underscores
            adapter = configure_logging(
                "test.module.submodule", log_to_file=True, log_dir=str(temp_log_dir)
            )

            # Log a message to trigger file creation
            adapter.info("Test message")

            # Check that log file was created with proper naming
            log_files = list(temp_log_dir.glob("*.log"))
            assert len(log_files) >= 1

            # Verify filename format (dots should be replaced with underscores)
            log_file = log_files[0]
            assert "test_module_submodule" in log_file.name
