"""Unit tests for TripSage Core decorator utilities.

Tests error handling decorators, retry logic, timing, async/sync decorators,
and memory service initialization decorators.
"""

import inspect
import time
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest

from tripsage_core.utils.decorator_utils import (
    ensure_memory_client_initialized,
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
        """Test error handler returns dict on async failure."""

        @with_error_handling()
        async def async_fail_dict() -> dict:
            raise ValueError("Test error")

        result = await async_fail_dict()
        assert "error" in result
        assert "Test error" in result["error"]

    async def test_async_function_with_exception_reraise(self):
        """Test error handler re-raises on async failure."""

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
        """Test behavior with error handling."""

        @with_error_handling()
        def sync_fail_dict() -> dict:
            raise ValueError("Test error")

        result = sync_fail_dict()
        assert "error" in result
        assert "Test error" in result["error"]

    def test_sync_function_with_exception_reraise(self):
        """Test error re-raised."""

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
            """Custom exception."""

            def __init__(self, message, code):
                """Custom exception initializer."""
                super().__init__(message)
                self.code = code

        @with_error_handling()
        async def fail_with_custom_exception() -> dict:
            """Fail with custom exception."""
            raise CustomException("Custom error message", code=500)

        result = await fail_with_custom_exception()
        assert "error" in result
        assert "Custom error message" in result["error"]

    def test_return_annotation_detection(self):
        """Test that decorator correctly detects return type annotations."""

        @with_error_handling()
        def dict_return() -> dict:
            """Fail with value error."""
            raise ValueError("Test")

        @with_error_handling()
        def str_return() -> str:
            """Fail with value error."""
            raise ValueError("Test")

        @with_error_handling()
        def no_annotation():
            """Fail with value error."""
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


class TestRetryRemoved:
    """Sanity check: legacy retry decorator is removed."""

    def test_retry_removed(self):
        """Import no longer exposes retry_on_failure."""
        mod = __import__("tripsage_core.utils.decorator_utils", fromlist=["*"])
        assert not hasattr(mod, "retry_on_failure")


class TestEnsureMemoryClientInitialized:
    """Test the ensure_memory_client_initialized decorator."""

    async def test_async_function_success(self):
        """Test memory initialization decorator with successful async function."""

        @ensure_memory_client_initialized
        async def memory_function():
            """Memory function."""
            return {"status": "success"}

        result = await memory_function()
        assert result == {"status": "success"}

    async def test_async_function_with_exception_dict_return(self):
        """Test memory decorator with async function that fails and returns dict."""

        @ensure_memory_client_initialized
        async def memory_fail_dict() -> dict:
            """Memory fail dict."""
            raise RuntimeError("Memory error")

        result = await memory_fail_dict()
        assert "error" in result
        assert "Memory error" in result["error"]

    async def test_async_function_with_exception_reraise(self):
        """Test memory decorator with async function that fails and re-raises."""

        @ensure_memory_client_initialized
        async def memory_fail_reraise() -> str:
            """Memory fail re-raise."""
            raise RuntimeError("Memory error")

        with pytest.raises(RuntimeError, match="Memory error"):
            await memory_fail_reraise()

    def test_sync_function_raises_error(self):
        """Test that decorator raises error when used on sync function."""
        with pytest.raises(TypeError, match="can only be used with async functions"):

            @ensure_memory_client_initialized
            def sync_function():
                """Sync function."""

    async def test_function_name_in_error_log(self, caplog):
        """Test that function name appears in error logs."""

        @ensure_memory_client_initialized
        async def memory_test_function() -> dict:
            """Memory test function."""
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
                """Add memory function."""
                # This would typically use the memory service
                return {"memory_id": "memory_id_123"}

            result = await add_memory_function()
            assert result["memory_id"] == "memory_id_123"

    async def test_return_annotation_detection(self):
        """Test decorator detects return type annotations."""

        @ensure_memory_client_initialized
        async def dict_return() -> dict:
            """Fail with value error."""
            raise ValueError("Test")

        @ensure_memory_client_initialized
        async def str_return() -> str:
            """Fail with value error."""
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
            """Combined function."""
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
            """Order test 1."""
            raise ValueError("Test error")

        @with_error_handling()
        @ensure_memory_client_initialized
        async def order_test2() -> dict:
            """Order test 2."""
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
            """Async function."""

        def sync_func():
            """Sync function."""

        assert inspect.iscoroutinefunction(async_func)
        assert not inspect.iscoroutinefunction(sync_func)

    async def test_complex_return_annotations(self):
        """Test decorators with complex return type annotations."""

        @with_error_handling()
        async def complex_return() -> dict[str, list[str]] | None:
            """Complex return."""
            raise ValueError("Complex type error")

        # Should re-raise since it's not exactly Dict
        with pytest.raises(ValueError):
            await complex_return()

    async def test_nested_decorators_performance(self):
        """Test performance impact of nested decorators."""

        @with_error_handling()
        @ensure_memory_client_initialized
        async def heavily_decorated() -> dict:
            """Heavily decorated function."""
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
        async def async_generator() -> AsyncGenerator[dict[str, int]]:
            """Async generator."""
            yield {"item": 1}
            yield {"item": 2}

        # This should work (though generators return generator objects)
        async for _ in async_generator():
            pass
        # Note: This test verifies the decorator doesn't break the function,
        # though the actual generator behavior depends on the specific use case

    def test_decorator_import_structure(self):
        """Test that all decorators are properly imported and accessible."""
        # Verify all expected functions are imported
        assert callable(with_error_handling)
        assert callable(ensure_memory_client_initialized)

        # Verify they have proper docstrings
        assert with_error_handling.__doc__ is not None
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
