"""
Unit tests for TripSage Core decorator utilities.

Tests error handling decorators, retry logic, timing, async/sync decorators,
and memory service initialization decorators.
"""

import inspect
import time
from unittest.mock import AsyncMock, patch

import pytest

from tripsage_core.utils.decorator_utils import (
    ensure_memory_client_initialized,
    retry_on_failure,
    with_error_handling,
)


class TestWithErrorHandling:
    """Test the with_error_handling decorator."""

    async def test_async_function_success(self):
        """Test error handling decorator with successful async function."""

        @with_error_handling()
        async def async_success():
            return {"result": "success"}

        result = await async_success()
        assert result == {"result": "success"}

    async def test_async_function_with_exception_dict_return(self):
        """Test error handling decorator with async function that fails and
        returns dict."""

        @with_error_handling()
        async def async_fail_dict() -> dict:
            raise ValueError("Test error")

        result = await async_fail_dict()
        assert "error" in result
        assert "Test error" in result["error"]

    async def test_async_function_with_exception_reraise(self):
        """Test error handling decorator with async function that fails and
        re-raises."""

        @with_error_handling()
        async def async_fail_reraise() -> str:
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await async_fail_reraise()

    def test_sync_function_success(self):
        """Test error handling decorator with successful sync function."""

        @with_error_handling()
        def sync_success():
            return {"result": "success"}

        result = sync_success()
        assert result == {"result": "success"}

    def test_sync_function_with_exception_dict_return(self):
        """Test error handling decorator with sync function that fails and
        returns dict."""

        @with_error_handling()
        def sync_fail_dict() -> dict:
            raise ValueError("Test error")

        result = sync_fail_dict()
        assert "error" in result
        assert "Test error" in result["error"]

    def test_sync_function_with_exception_reraise(self):
        """Test error handling decorator with sync function that fails and
        re-raises."""

        @with_error_handling()
        def sync_fail_reraise() -> str:
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            sync_fail_reraise()

    async def test_function_name_in_error_log(self, caplog):
        """Test that function name appears in error logs."""

        @with_error_handling()
        async def test_function_name():
            raise RuntimeError("Function error")

        # Should return error dict, not raise
        result = await test_function_name()
        assert "error" in result

        # Check that function name appears in logs
        assert "test_function_name" in caplog.text
        assert "Function error" in caplog.text

    def test_preserves_function_metadata(self):
        """Test that decorator preserves function metadata."""

        @with_error_handling()
        def original_function():
            """Original docstring."""
            pass

        assert original_function.__name__ == "original_function"
        assert original_function.__doc__ == "Original docstring."

    async def test_with_args_and_kwargs(self):
        """Test error handling decorator with function arguments."""

        @with_error_handling()
        async def function_with_args(arg1, arg2, kwarg1=None):
            return {"arg1": arg1, "arg2": arg2, "kwarg1": kwarg1}

        result = await function_with_args("value1", "value2", kwarg1="value3")
        assert result["arg1"] == "value1"
        assert result["arg2"] == "value2"
        assert result["kwarg1"] == "value3"

    async def test_error_handling_with_complex_exception(self):
        """Test error handling with complex exception objects."""

        class CustomException(Exception):
            def __init__(self, message, code):
                super().__init__(message)
                self.code = code

        @with_error_handling()
        async def fail_with_custom_exception() -> dict:
            raise CustomException("Custom error message", 500)

        result = await fail_with_custom_exception()
        assert "error" in result
        assert "Custom error message" in result["error"]

    def test_return_annotation_detection(self):
        """Test that decorator correctly detects return type annotations."""

        @with_error_handling()
        def dict_return() -> dict:
            raise ValueError("Test")

        @with_error_handling()
        def str_return() -> str:
            raise ValueError("Test")

        @with_error_handling()
        def no_annotation():
            raise ValueError("Test")

        # Dict return should return error dict
        result1 = dict_return()
        assert isinstance(result1, dict)
        assert "error" in result1

        # Non-dict returns should re-raise
        with pytest.raises(ValueError):
            str_return()

        with pytest.raises(ValueError):
            no_annotation()


class TestRetryOnFailure:
    """Test the retry_on_failure decorator."""

    async def test_async_retry_success_first_attempt(self):
        """Test retry decorator with async function that succeeds immediately."""
        call_count = 0

        @retry_on_failure(max_attempts=3)
        async def async_success():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await async_success()
        assert result == "success"
        assert call_count == 1

    async def test_async_retry_success_after_failures(self):
        """Test retry decorator with async function that succeeds after failures."""
        call_count = 0

        @retry_on_failure(max_attempts=3, delay=0.01)
        async def async_retry():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "success"

        result = await async_retry()
        assert result == "success"
        assert call_count == 3

    async def test_async_retry_max_attempts_exceeded(self):
        """Test retry decorator when max attempts are exceeded."""
        call_count = 0

        @retry_on_failure(max_attempts=2, delay=0.01)
        async def async_always_fail():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError, match="Always fails"):
            await async_always_fail()

        assert call_count == 2

    def test_sync_retry_success_after_failures(self):
        """Test retry decorator with sync function that succeeds after failures."""
        call_count = 0

        @retry_on_failure(max_attempts=3, delay=0.01)
        def sync_retry():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retry error")
            return "success"

        result = sync_retry()
        assert result == "success"
        assert call_count == 3

    def test_sync_retry_max_attempts_exceeded(self):
        """Test sync retry decorator when max attempts are exceeded."""
        call_count = 0

        @retry_on_failure(max_attempts=2, delay=0.01)
        def sync_always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            sync_always_fail()

        assert call_count == 2

    async def test_exponential_backoff(self):
        """Test exponential backoff timing."""
        call_times = []

        @retry_on_failure(max_attempts=3, delay=0.1, backoff_factor=2.0)
        async def failing_function():
            call_times.append(time.time())
            raise RuntimeError("Test error")

        with pytest.raises(RuntimeError):
            await failing_function()

        # Check that delays increase exponentially
        assert len(call_times) == 3

        # First retry after ~0.1s
        if len(call_times) > 1:
            delay1 = call_times[1] - call_times[0]
            assert 0.08 <= delay1 <= 0.15

        # Second retry after ~0.2s
        if len(call_times) > 2:
            delay2 = call_times[2] - call_times[1]
            assert 0.18 <= delay2 <= 0.25

    async def test_specific_exception_types(self):
        """Test retry decorator with specific exception types."""
        call_count = 0

        @retry_on_failure(max_attempts=3, delay=0.01, exceptions=(ConnectionError,))
        async def selective_retry():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Network error")  # Should retry
            elif call_count == 2:
                raise ValueError("Value error")  # Should not retry
            return "success"

        with pytest.raises(ValueError, match="Value error"):
            await selective_retry()

        assert call_count == 2

    def test_retry_with_args_and_kwargs(self):
        """Test retry decorator preserves function arguments."""

        @retry_on_failure(max_attempts=2, delay=0.01)
        def function_with_args(arg1, arg2, kwarg1=None):
            if arg1 == "fail":
                raise ValueError("Test error")
            return {"arg1": arg1, "arg2": arg2, "kwarg1": kwarg1}

        # Test success case
        result = function_with_args("success", "value2", kwarg1="value3")
        assert result["arg1"] == "success"

        # Test failure case
        with pytest.raises(ValueError):
            function_with_args("fail", "value2")

    async def test_retry_logging(self, caplog):
        """Test that retry attempts are properly logged."""
        call_count = 0

        @retry_on_failure(max_attempts=3, delay=0.01)
        async def logged_retry():
            nonlocal call_count
            call_count += 1
            raise ConnectionError(f"Attempt {call_count}")

        with pytest.raises(ConnectionError):
            await logged_retry()

        # Check warning logs for retry attempts
        assert "logged_retry failed (attempt 1/3)" in caplog.text
        assert "logged_retry failed (attempt 2/3)" in caplog.text
        assert "logged_retry failed after 3 attempts" in caplog.text

    def test_retry_preserves_function_metadata(self):
        """Test that retry decorator preserves function metadata."""

        @retry_on_failure()
        def original_function():
            """Original docstring."""
            pass

        assert original_function.__name__ == "original_function"
        assert original_function.__doc__ == "Original docstring."

    async def test_no_retry_on_success(self):
        """Test that successful functions don't trigger retry logic."""
        call_count = 0

        @retry_on_failure(max_attempts=3, delay=0.1)
        async def immediate_success():
            nonlocal call_count
            call_count += 1
            return "success"

        start_time = time.time()
        result = await immediate_success()
        end_time = time.time()

        assert result == "success"
        assert call_count == 1
        assert (end_time - start_time) < 0.05  # Should be immediate


class TestEnsureMemoryClientInitialized:
    """Test the ensure_memory_client_initialized decorator."""

    async def test_async_function_success(self):
        """Test memory initialization decorator with successful async function."""

        @ensure_memory_client_initialized
        async def memory_function():
            return {"status": "success"}

        result = await memory_function()
        assert result == {"status": "success"}

    async def test_async_function_with_exception_dict_return(self):
        """Test memory decorator with async function that fails and returns dict."""

        @ensure_memory_client_initialized
        async def memory_fail_dict() -> dict:
            raise RuntimeError("Memory error")

        result = await memory_fail_dict()
        assert "error" in result
        assert "Memory error" in result["error"]

    async def test_async_function_with_exception_reraise(self):
        """Test memory decorator with async function that fails and re-raises."""

        @ensure_memory_client_initialized
        async def memory_fail_reraise() -> str:
            raise RuntimeError("Memory error")

        with pytest.raises(RuntimeError, match="Memory error"):
            await memory_fail_reraise()

    def test_sync_function_raises_error(self):
        """Test that decorator raises error when used on sync function."""
        with pytest.raises(TypeError, match="can only be used with async functions"):

            @ensure_memory_client_initialized
            def sync_function():
                pass

    async def test_function_name_in_error_log(self, caplog):
        """Test that function name appears in error logs."""

        @ensure_memory_client_initialized
        async def memory_test_function() -> dict:
            raise RuntimeError("Memory initialization error")

        result = await memory_test_function()
        assert "error" in result

        # Check that function name appears in logs
        assert "memory_test_function" in caplog.text
        assert "Memory initialization error" in caplog.text

    async def test_preserves_function_metadata(self):
        """Test that decorator preserves function metadata."""

        @ensure_memory_client_initialized
        async def original_memory_function():
            """Original memory function docstring."""
            return {"result": "test"}

        assert original_memory_function.__name__ == "original_memory_function"
        assert original_memory_function.__doc__ == "Original memory function docstring."

    async def test_with_args_and_kwargs(self):
        """Test memory decorator with function arguments."""

        @ensure_memory_client_initialized
        async def memory_function_with_args(user_id, content, metadata=None):
            return {"user_id": user_id, "content": content, "metadata": metadata}

        result = await memory_function_with_args(
            "user123", "test content", metadata={"type": "test"}
        )
        assert result["user_id"] == "user123"
        assert result["content"] == "test content"
        assert result["metadata"]["type"] == "test"

    async def test_memory_service_integration(self):
        """Test that the decorator works with memory service integration."""
        # Mock the memory service to avoid actual initialization
        with patch(
            "tripsage_core.services.business.memory_service.MemoryService"
        ) as mock_service:
            mock_instance = AsyncMock()
            mock_service.return_value = mock_instance
            mock_instance.add_memory.return_value = "memory_id_123"

            @ensure_memory_client_initialized
            async def add_memory_function():
                # This would typically use the memory service
                return {"memory_id": "memory_id_123"}

            result = await add_memory_function()
            assert result["memory_id"] == "memory_id_123"

    async def test_return_annotation_detection(self):
        """Test that decorator correctly detects return type annotations for
        memory functions."""

        @ensure_memory_client_initialized
        async def dict_return() -> dict:
            raise ValueError("Test")

        @ensure_memory_client_initialized
        async def str_return() -> str:
            raise ValueError("Test")

        # Dict return should return error dict
        result1 = await dict_return()
        assert isinstance(result1, dict)
        assert "error" in result1

        # Non-dict returns should re-raise
        with pytest.raises(ValueError):
            await str_return()

    async def test_multiple_decorators_combination(self):
        """Test combining memory decorator with error handling decorator."""
        call_count = 0

        @with_error_handling()
        @ensure_memory_client_initialized
        async def combined_function() -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("First attempt fails")
            return {"status": "success", "attempt": call_count}

        # First call should handle the error and return error dict
        result = await combined_function()
        assert "error" in result
        assert call_count == 1

    async def test_decorator_order_matters(self):
        """Test that decorator order affects behavior."""

        @ensure_memory_client_initialized
        @with_error_handling()
        async def order_test1() -> dict:
            raise ValueError("Test error")

        @with_error_handling()
        @ensure_memory_client_initialized
        async def order_test2() -> dict:
            raise ValueError("Test error")

        # Both should return error dicts, but different decorators handle the error
        result1 = await order_test1()
        result2 = await order_test2()

        assert "error" in result1
        assert "error" in result2


class TestDecoratorHelpers:
    """Test decorator helper functions and edge cases."""

    def test_function_inspection(self):
        """Test that decorators correctly identify async vs sync functions."""

        async def async_func():
            pass

        def sync_func():
            pass

        assert inspect.iscoroutinefunction(async_func)
        assert not inspect.iscoroutinefunction(sync_func)

    async def test_complex_return_annotations(self):
        """Test decorators with complex return type annotations."""
        from typing import Dict, List, Optional

        @with_error_handling()
        async def complex_return() -> Optional[Dict[str, List[str]]]:
            raise ValueError("Complex type error")

        # Should re-raise since it's not exactly Dict
        with pytest.raises(ValueError):
            await complex_return()

    async def test_nested_decorators_performance(self):
        """Test performance impact of nested decorators."""

        @retry_on_failure(max_attempts=1)
        @with_error_handling()
        @ensure_memory_client_initialized
        async def heavily_decorated() -> dict:
            return {"performance": "test"}

        start_time = time.time()
        result = await heavily_decorated()
        end_time = time.time()

        assert result["performance"] == "test"
        # Should complete quickly despite multiple decorators
        assert (end_time - start_time) < 0.1

    async def test_decorator_with_generator_function(self):
        """Test that decorators work with generator functions."""

        @with_error_handling()
        async def async_generator() -> dict:
            yield {"item": 1}
            yield {"item": 2}

        # This should work (though generators return generator objects)
        await async_generator()
        # Note: This test verifies the decorator doesn't break the function,
        # though the actual generator behavior depends on the specific use case

    def test_decorator_import_structure(self):
        """Test that all decorators are properly imported and accessible."""
        # Verify all expected functions are imported
        assert callable(with_error_handling)
        assert callable(retry_on_failure)
        assert callable(ensure_memory_client_initialized)

        # Verify they have proper docstrings
        assert with_error_handling.__doc__ is not None
        assert retry_on_failure.__doc__ is not None
        assert ensure_memory_client_initialized.__doc__ is not None

    async def test_exception_chaining(self):
        """Test that decorators preserve exception chaining."""

        @with_error_handling()
        async def chained_exception() -> dict:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise RuntimeError("Wrapped error") from e

        result = await chained_exception()
        assert "error" in result
        assert "Wrapped error" in result["error"]
