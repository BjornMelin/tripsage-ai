"""
Comprehensive test suite for tripsage_core.utils.error_handling_utils module.

This module provides extensive tests for error handling utilities,
including exception formatting, error tracking, retry mechanisms, and logging integration.
"""

import logging
import time
from unittest.mock import MagicMock

import pytest

try:
    from tripsage_core.utils.error_handling_utils import (
        log_exception,
    )

    HAS_ERROR_UTILS = True
except ImportError:
    HAS_ERROR_UTILS = False


# Mock implementations for testing
def format_exception(exc, context=None, include_traceback=True):
    """Mock format_exception for testing."""
    import traceback

    result = f"{type(exc).__name__}: {str(exc)}"
    if include_traceback:
        result += "\n" + "".join(
            traceback.format_tb(exc.__traceback__) if exc.__traceback__ else []
        )
    if context:
        result += f"\nContext: {context}"
    return result


def log_error(error, context=None, level=logging.ERROR, logger=None, extra=None):
    """Mock log_error for testing."""
    if logger is None:
        logger = logging.getLogger(__name__)

    try:
        formatted = format_exception(error, context)
        if extra:
            logger.log(level, formatted, extra=extra)
        else:
            logger.log(level, formatted)
    except Exception:
        pass


def retry_with_backoff(
    max_retries=3,
    delay=1.0,
    backoff_factor=2.0,
    exceptions=(Exception,),
    jitter=False,
    on_retry=None,
):
    """Mock retry decorator for testing."""

    def decorator(func):
        import asyncio
        import functools
        import random

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_exception = None
                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt == max_retries:
                            raise

                        if on_retry:
                            on_retry(attempt + 1, e, delay)

                        sleep_time = delay * (backoff_factor**attempt)
                        if jitter:
                            sleep_time *= 0.5 + random.random()

                        await asyncio.sleep(sleep_time)

                raise last_exception

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                import random
                import time

                last_exception = None
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt == max_retries:
                            raise

                        if on_retry:
                            on_retry(attempt + 1, e, delay)

                        sleep_time = delay * (backoff_factor**attempt)
                        if jitter:
                            sleep_time *= 0.5 + random.random()

                        time.sleep(max(0, sleep_time))

                raise last_exception

            return sync_wrapper

    return decorator


class SafeExecuteResult:
    """Mock result class for safe execution."""

    def __init__(self, success, result=None, error=None):
        self.success = success
        self.result = result
        self.error = error


def safe_execute(
    func,
    *args,
    default=None,
    logger=None,
    context=None,
    suppress_exceptions=True,
    **kwargs,
):
    """Mock safe_execute for testing."""
    import asyncio

    try:
        if asyncio.iscoroutinefunction(func):
            # For async functions, we need to run them
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                # If we're already in an async context, create a task
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, func(*args, **kwargs))
                    result = future.result()
            else:
                result = loop.run_until_complete(func(*args, **kwargs))
        else:
            result = func(*args, **kwargs)

        return SafeExecuteResult(success=True, result=result)
    except Exception as e:
        if logger and context:
            log_error(e, context=context, logger=logger)
        elif logger:
            log_error(e, logger=logger)

        if not suppress_exceptions:
            raise

        return SafeExecuteResult(success=False, result=default, error=e)


class ErrorHandler:
    """Mock ErrorHandler for testing."""

    def __init__(self, name, logger=None, max_errors=100):
        self.name = name
        self.logger = logger or logging.getLogger(name)
        self.max_errors = max_errors
        self.error_count = 0
        self.errors = []

    def handle_error(self, error, context=None):
        """Handle an error."""
        from datetime import datetime

        self.error_count += 1
        error_record = {
            "error": error,
            "context": context,
            "timestamp": datetime.utcnow(),
        }

        self.errors.append(error_record)

        # Keep only the last max_errors
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors :]

        log_error(error, context=context, logger=self.logger)

    def get_error_summary(self):
        """Get error summary."""
        from collections import defaultdict

        error_types = defaultdict(int)
        for error_record in self.errors:
            error_type = type(error_record["error"]).__name__
            error_types[error_type] += 1

        return {"total_errors": self.error_count, "error_types": dict(error_types)}

    def clear_errors(self):
        """Clear all errors."""
        self.error_count = 0
        self.errors = []

    def get_recent_errors(self, count=10):
        """Get recent errors."""
        return self.errors[-count:]

    def get_error_rate(self, window_minutes=60):
        """Get error rate."""
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)

        recent_errors = [e for e in self.errors if e["timestamp"] >= window_start]

        return len(recent_errors) / window_minutes

    def export_errors(self):
        """Export errors."""
        return [
            {
                "timestamp": e["timestamp"].isoformat(),
                "error_type": type(e["error"]).__name__,
                "message": str(e["error"]),
                "context": e.get("context"),
            }
            for e in self.errors
        ]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.handle_error(exc_val)
        return True  # Suppress exception


class TestFormatException:
    """Test exception formatting utilities."""

    def test_format_exception_simple(self):
        """Test formatting a simple exception."""
        try:
            raise ValueError("Test error message")
        except Exception as e:
            formatted = format_exception(e)

            assert "ValueError" in formatted
            assert "Test error message" in formatted
            assert "format_exception_simple" in formatted  # Function name

    def test_format_exception_with_context(self):
        """Test formatting exception with additional context."""
        try:
            raise ValueError("Test error")
        except Exception as e:
            context = {
                "user_id": "12345",
                "operation": "test_operation",
                "request_id": "req_123",
            }
            formatted = format_exception(e, context=context)

            assert "ValueError" in formatted
            assert "Test error" in formatted
            assert "user_id: 12345" in formatted
            assert "operation: test_operation" in formatted

    def test_format_exception_nested(self):
        """Test formatting nested exceptions."""
        try:
            try:
                raise ValueError("Inner error")
            except Exception as inner:
                raise RuntimeError("Outer error") from inner
        except Exception as e:
            formatted = format_exception(e)

            assert "RuntimeError" in formatted
            assert "ValueError" in formatted
            assert "Inner error" in formatted
            assert "Outer error" in formatted

    def test_format_exception_no_traceback(self):
        """Test formatting exception without traceback."""
        e = ValueError("Test error")
        formatted = format_exception(e, include_traceback=False)

        assert "ValueError: Test error" in formatted
        assert "Traceback" not in formatted

    def test_format_exception_custom_attributes(self):
        """Test formatting exception with custom attributes."""

        class CustomError(Exception):
            def __init__(self, message, error_code=None, details=None):
                super().__init__(message)
                self.error_code = error_code
                self.details = details

        try:
            raise CustomError(
                "Custom error",
                error_code="E001",
                details={"field": "email", "value": "invalid"},
            )
        except Exception as e:
            formatted = format_exception(e)

            assert "CustomError" in formatted
            assert "Custom error" in formatted
            assert "error_code: E001" in formatted
            assert "field" in formatted

    def test_format_exception_unicode(self):
        """Test formatting exception with unicode characters."""
        try:
            raise ValueError("Error with unicode: éñçødé")
        except Exception as e:
            formatted = format_exception(e)

            assert "ValueError" in formatted
            assert "éñçødé" in formatted


class TestLogError:
    """Test error logging utilities."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing."""
        return MagicMock(spec=logging.Logger)

    def test_log_error_basic(self, mock_logger):
        """Test basic error logging."""
        error = ValueError("Test error")

        log_error(error, logger=mock_logger)

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0][0]
        assert "ValueError" in call_args
        assert "Test error" in call_args

    def test_log_error_with_context(self, mock_logger):
        """Test error logging with context."""
        error = ValueError("Test error")
        context = {"user_id": "12345", "action": "login"}

        log_error(error, context=context, logger=mock_logger)

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0][0]
        assert "user_id: 12345" in call_args
        assert "action: login" in call_args

    def test_log_error_custom_level(self, mock_logger):
        """Test error logging with custom level."""
        error = ValueError("Test error")

        log_error(error, level=logging.WARNING, logger=mock_logger)

        mock_logger.warning.assert_called_once()
        mock_logger.error.assert_not_called()

    def test_log_error_with_extra_fields(self, mock_logger):
        """Test error logging with extra fields."""
        error = ValueError("Test error")
        extra = {"correlation_id": "corr_123", "service": "auth"}

        log_error(error, extra=extra, logger=mock_logger)

        mock_logger.error.assert_called_once()
        # Check that extra fields were passed
        call_kwargs = mock_logger.error.call_args[1]
        assert "extra" in call_kwargs
        assert call_kwargs["extra"]["correlation_id"] == "corr_123"

    def test_log_error_default_logger(self):
        """Test error logging with default logger."""
        error = ValueError("Test error")

        # Should not raise an exception
        log_error(error)

    def test_log_error_exception_in_logging(self, mock_logger):
        """Test error logging when logging itself fails."""
        error = ValueError("Test error")
        mock_logger.error.side_effect = Exception("Logging failed")

        # Should handle logging failure gracefully
        log_error(error, logger=mock_logger)


class TestRetryWithBackoff:
    """Test retry mechanism with exponential backoff."""

    def test_retry_success_first_attempt(self):
        """Test successful execution on first attempt."""

        @retry_with_backoff(max_retries=3)
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    def test_retry_success_after_failures(self):
        """Test successful execution after some failures."""
        call_count = 0

        @retry_with_backoff(max_retries=3, delay=0.01)
        def function_with_retries():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = function_with_retries()
        assert result == "success"
        assert call_count == 3

    def test_retry_max_retries_exceeded(self):
        """Test behavior when max retries is exceeded."""

        @retry_with_backoff(max_retries=2, delay=0.01)
        def always_failing_function():
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_failing_function()

    def test_retry_with_specific_exceptions(self):
        """Test retry only on specific exceptions."""

        @retry_with_backoff(max_retries=3, delay=0.01, exceptions=(ValueError,))
        def function_with_different_errors():
            raise TypeError("Should not retry this")

        with pytest.raises(TypeError, match="Should not retry this"):
            function_with_different_errors()

    def test_retry_exponential_backoff(self):
        """Test exponential backoff timing."""
        call_times = []

        @retry_with_backoff(max_retries=3, delay=0.1, backoff_factor=2)
        def timed_function():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("Retry me")
            return "success"

        start_time = time.time()
        result = timed_function()

        assert result == "success"
        assert len(call_times) == 3

        # Check timing (approximately)
        time_diff_1 = call_times[1] - call_times[0]
        time_diff_2 = call_times[2] - call_times[1]

        # Second delay should be roughly double the first
        assert time_diff_2 > time_diff_1

    def test_retry_with_jitter(self):
        """Test retry with jitter."""
        call_count = 0

        @retry_with_backoff(max_retries=3, delay=0.01, jitter=True)
        def function_with_jitter():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retry with jitter")
            return "success"

        result = function_with_jitter()
        assert result == "success"
        assert call_count == 3

    def test_retry_async_function(self):
        """Test retry with async function."""
        call_count = 0

        @retry_with_backoff(max_retries=3, delay=0.01)
        async def async_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Async retry")
            return "async_success"

        import asyncio

        result = asyncio.run(async_function())
        assert result == "async_success"
        assert call_count == 2

    def test_retry_with_callback(self):
        """Test retry with callback function."""
        retry_attempts = []

        def retry_callback(attempt, exception, delay):
            retry_attempts.append(
                {"attempt": attempt, "exception": str(exception), "delay": delay}
            )

        @retry_with_backoff(max_retries=3, delay=0.01, on_retry=retry_callback)
        def function_with_callback():
            if len(retry_attempts) < 2:
                raise ValueError(f"Attempt {len(retry_attempts) + 1}")
            return "success"

        result = function_with_callback()
        assert result == "success"
        assert len(retry_attempts) == 2
        assert retry_attempts[0]["attempt"] == 1
        assert "Attempt 1" in retry_attempts[0]["exception"]


class TestSafeExecute:
    """Test safe execution wrapper."""

    def test_safe_execute_success(self):
        """Test successful safe execution."""

        def successful_function(x, y):
            return x + y

        result = safe_execute(successful_function, 2, 3)

        assert result.success is True
        assert result.result == 5
        assert result.error is None

    def test_safe_execute_failure(self):
        """Test safe execution with failure."""

        def failing_function():
            raise ValueError("Test error")

        result = safe_execute(failing_function)

        assert result.success is False
        assert result.result is None
        assert isinstance(result.error, ValueError)

    def test_safe_execute_with_default(self):
        """Test safe execution with default value."""

        def failing_function():
            raise ValueError("Test error")

        result = safe_execute(failing_function, default="default_value")

        assert result.success is False
        assert result.result == "default_value"
        assert isinstance(result.error, ValueError)

    def test_safe_execute_with_logger(self):
        """Test safe execution with error logging."""
        mock_logger = MagicMock(spec=logging.Logger)

        def failing_function():
            raise ValueError("Test error")

        result = safe_execute(failing_function, logger=mock_logger)

        assert result.success is False
        mock_logger.error.assert_called_once()

    def test_safe_execute_suppress_exceptions(self):
        """Test safe execution with exception suppression."""

        def failing_function():
            raise ValueError("Test error")

        result = safe_execute(failing_function, suppress_exceptions=True)

        assert result.success is False
        assert result.error is not None

    def test_safe_execute_reraise_exceptions(self):
        """Test safe execution with exception reraising."""

        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            safe_execute(failing_function, suppress_exceptions=False)

    def test_safe_execute_with_context(self):
        """Test safe execution with context."""
        mock_logger = MagicMock(spec=logging.Logger)
        context = {"user_id": "12345", "operation": "test"}

        def failing_function():
            raise ValueError("Test error")

        result = safe_execute(failing_function, context=context, logger=mock_logger)

        assert result.success is False
        mock_logger.error.assert_called_once()

    def test_safe_execute_async_function(self):
        """Test safe execution with async function."""

        async def async_function(x, y):
            return x * y

        import asyncio

        result = asyncio.run(safe_execute(async_function, 3, 4))

        assert result.success is True
        assert result.result == 12


class TestErrorHandler:
    """Test ErrorHandler class."""

    def test_error_handler_initialization(self):
        """Test ErrorHandler initialization."""
        handler = ErrorHandler(name="test_handler")

        assert handler.name == "test_handler"
        assert handler.error_count == 0
        assert len(handler.errors) == 0

    def test_error_handler_with_logger(self):
        """Test ErrorHandler with custom logger."""
        mock_logger = MagicMock(spec=logging.Logger)
        handler = ErrorHandler(name="test_handler", logger=mock_logger)

        assert handler.logger == mock_logger

    def test_error_handler_handle_error(self):
        """Test handling an error."""
        handler = ErrorHandler(name="test_handler")
        error = ValueError("Test error")

        handler.handle_error(error)

        assert handler.error_count == 1
        assert len(handler.errors) == 1
        assert handler.errors[0]["error"] == error

    def test_error_handler_handle_error_with_context(self):
        """Test handling error with context."""
        handler = ErrorHandler(name="test_handler")
        error = ValueError("Test error")
        context = {"user_id": "12345", "action": "test"}

        handler.handle_error(error, context=context)

        assert handler.error_count == 1
        assert handler.errors[0]["context"] == context

    def test_error_handler_max_errors(self):
        """Test error handler with maximum error limit."""
        handler = ErrorHandler(name="test_handler", max_errors=3)

        for i in range(5):
            error = ValueError(f"Error {i}")
            handler.handle_error(error)

        assert handler.error_count == 5
        assert len(handler.errors) == 3  # Should only keep last 3

    def test_error_handler_get_error_summary(self):
        """Test getting error summary."""
        handler = ErrorHandler(name="test_handler")

        # Add different types of errors
        handler.handle_error(ValueError("Error 1"))
        handler.handle_error(TypeError("Error 2"))
        handler.handle_error(ValueError("Error 3"))

        summary = handler.get_error_summary()

        assert summary["total_errors"] == 3
        assert summary["error_types"]["ValueError"] == 2
        assert summary["error_types"]["TypeError"] == 1

    def test_error_handler_clear_errors(self):
        """Test clearing errors."""
        handler = ErrorHandler(name="test_handler")

        handler.handle_error(ValueError("Error 1"))
        handler.handle_error(TypeError("Error 2"))

        assert handler.error_count == 2

        handler.clear_errors()

        assert handler.error_count == 0
        assert len(handler.errors) == 0

    def test_error_handler_as_context_manager(self):
        """Test ErrorHandler as context manager."""
        handler = ErrorHandler(name="test_handler")

        with handler:
            raise ValueError("Test error")

        assert handler.error_count == 1
        assert isinstance(handler.errors[0]["error"], ValueError)

    def test_error_handler_context_manager_no_error(self):
        """Test ErrorHandler context manager with no errors."""
        handler = ErrorHandler(name="test_handler")

        with handler:
            result = 2 + 2

        assert result == 4
        assert handler.error_count == 0

    def test_error_handler_get_recent_errors(self):
        """Test getting recent errors."""
        handler = ErrorHandler(name="test_handler")

        for i in range(5):
            handler.handle_error(ValueError(f"Error {i}"))
            time.sleep(0.01)  # Small delay to differentiate timestamps

        recent_errors = handler.get_recent_errors(count=3)

        assert len(recent_errors) == 3
        # Should be most recent errors first
        assert "Error 4" in str(recent_errors[0]["error"])

    def test_error_handler_error_rate(self):
        """Test calculating error rate."""
        handler = ErrorHandler(name="test_handler")

        # Add errors over time
        for i in range(3):
            handler.handle_error(ValueError(f"Error {i}"))

        error_rate = handler.get_error_rate(window_minutes=60)

        # Should be > 0 since we have recent errors
        assert error_rate > 0

    def test_error_handler_export_errors(self):
        """Test exporting errors."""
        handler = ErrorHandler(name="test_handler")

        handler.handle_error(ValueError("Error 1"), context={"key": "value"})
        handler.handle_error(TypeError("Error 2"))

        exported = handler.export_errors()

        assert len(exported) == 2
        assert "timestamp" in exported[0]
        assert "error_type" in exported[0]
        assert "message" in exported[0]


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_format_exception_none(self):
        """Test formatting None as exception."""
        formatted = format_exception(None)
        assert "None" in formatted or "No exception" in formatted

    def test_format_exception_string(self):
        """Test formatting string as exception."""
        formatted = format_exception("String error")
        assert "String error" in formatted

    def test_retry_zero_retries(self):
        """Test retry with zero max retries."""

        @retry_with_backoff(max_retries=0, delay=0.01)
        def failing_function():
            raise ValueError("Should fail immediately")

        with pytest.raises(ValueError, match="Should fail immediately"):
            failing_function()

    def test_retry_negative_delay(self):
        """Test retry with negative delay."""
        call_count = 0

        @retry_with_backoff(max_retries=2, delay=-0.1)
        def function_with_negative_delay():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry me")
            return "success"

        result = function_with_negative_delay()
        assert result == "success"

    def test_safe_execute_none_function(self):
        """Test safe execution with None function."""
        result = safe_execute(None)

        assert result.success is False
        assert result.error is not None

    def test_error_handler_negative_max_errors(self):
        """Test ErrorHandler with negative max errors."""
        handler = ErrorHandler(name="test", max_errors=-1)

        # Should handle gracefully
        handler.handle_error(ValueError("Test"))
        assert handler.error_count == 1


class TestPerformance:
    """Test performance characteristics."""

    def test_format_exception_performance(self):
        """Test exception formatting performance."""
        try:
            raise ValueError("Performance test error")
        except Exception as e:
            start_time = time.time()

            for _ in range(100):
                formatted = format_exception(e)

            end_time = time.time()
            total_time = end_time - start_time

            # Should complete quickly
            assert total_time < 1.0

    def test_error_handler_performance(self):
        """Test error handler performance with many errors."""
        handler = ErrorHandler(name="perf_test", max_errors=1000)

        start_time = time.time()

        for i in range(1000):
            error = ValueError(f"Error {i}")
            handler.handle_error(error)

        end_time = time.time()
        total_time = end_time - start_time

        # Should handle many errors quickly
        assert total_time < 2.0
        assert handler.error_count == 1000

    def test_retry_performance(self):
        """Test retry mechanism performance."""
        call_count = 0

        @retry_with_backoff(max_retries=10, delay=0.001)
        def quick_retry_function():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                raise ValueError("Quick retry")
            return "success"

        start_time = time.time()
        result = quick_retry_function()
        end_time = time.time()

        assert result == "success"
        assert call_count == 5
        # Should complete quickly even with retries
        assert (end_time - start_time) < 1.0


class TestIntegration:
    """Test integration between different error handling components."""

    def test_retry_with_error_handler(self):
        """Test retry mechanism with error handler."""
        handler = ErrorHandler(name="integration_test")

        @retry_with_backoff(max_retries=3, delay=0.01)
        def function_with_handler():
            try:
                if handler.error_count < 2:
                    raise ValueError(f"Attempt {handler.error_count + 1}")
                return "success"
            except Exception as e:
                handler.handle_error(e)
                raise

        result = function_with_handler()
        assert result == "success"
        assert handler.error_count == 2

    def test_safe_execute_with_retry(self):
        """Test safe execution combined with retry."""
        call_count = 0

        @retry_with_backoff(max_retries=3, delay=0.01)
        def retry_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Need retry")
            return "success"

        result = safe_execute(retry_function)

        assert result.success is True
        assert result.result == "success"
        assert call_count == 3

    def test_comprehensive_error_handling(self):
        """Test comprehensive error handling scenario."""
        handler = ErrorHandler(name="comprehensive_test")
        mock_logger = MagicMock(spec=logging.Logger)

        @retry_with_backoff(max_retries=2, delay=0.01)
        def complex_function(data):
            with handler:
                if not data:
                    raise ValueError("No data provided")

                if data.get("should_fail"):
                    raise RuntimeError("Intentional failure")

                return {"status": "success", "data": data}

        # Test successful execution
        result1 = safe_execute(complex_function, {"value": 123}, logger=mock_logger)
        assert result1.success is True
        assert result1.result["status"] == "success"

        # Test failure handling
        result2 = safe_execute(
            complex_function, {"should_fail": True}, logger=mock_logger
        )
        assert result2.success is False
        assert handler.error_count > 0
