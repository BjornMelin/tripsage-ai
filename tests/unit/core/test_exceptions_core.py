"""
Core tests for tripsage_core.exceptions module.

This module tests the core exception functionality without any FastAPI
or application dependencies.
"""

import asyncio
import json
from unittest.mock import Mock

import pytest

from tripsage_core.exceptions.exceptions import (
    CoreAgentError,
    CoreAuthenticationError,
    CoreAuthorizationError,
    CoreDatabaseError,
    CoreExternalAPIError,
    CoreKeyValidationError,
    CoreMCPError,
    CoreRateLimitError,
    CoreResourceNotFoundError,
    CoreServiceError,
    CoreTripSageError,
    CoreValidationError,
    ErrorDetails,
    format_exception,
    create_error_response,
    safe_execute,
    with_error_handling,
    get_core_exception,
    EXCEPTION_MAPPING,
    create_authentication_error,
    create_authorization_error,
    create_validation_error,
    create_not_found_error,
)


class TestErrorDetails:
    """Test ErrorDetails model."""

    def test_error_details_creation(self):
        """Test ErrorDetails creation with all fields."""
        details = ErrorDetails(
            service="test_service",
            operation="test_operation",
            resource_id="resource123",
            user_id="user456",
            request_id="req789",
            additional_context={"key": "value", "number": 42},
        )
        
        assert details.service == "test_service"
        assert details.operation == "test_operation"
        assert details.resource_id == "resource123"
        assert details.user_id == "user456"
        assert details.request_id == "req789"
        assert details.additional_context["key"] == "value"
        assert details.additional_context["number"] == 42

    def test_error_details_minimal(self):
        """Test ErrorDetails creation with minimal fields."""
        details = ErrorDetails()
        
        assert details.service is None
        assert details.operation is None
        assert details.resource_id is None
        assert details.user_id is None
        assert details.request_id is None
        assert details.additional_context == {}

    def test_error_details_model_dump(self):
        """Test ErrorDetails model_dump functionality."""
        details = ErrorDetails(
            service="test_service",
            operation=None,
            additional_context={"key": "value"},
        )
        
        dumped = details.model_dump(exclude_none=True)
        assert "service" in dumped
        assert "operation" not in dumped
        assert "additional_context" in dumped
        
        dumped_with_none = details.model_dump(exclude_none=False)
        assert "service" in dumped_with_none
        assert "operation" in dumped_with_none
        assert dumped_with_none["operation"] is None


class TestCoreExceptions:
    """Test core exception classes."""

    def test_core_authentication_error(self):
        """Test CoreAuthenticationError."""
        error = CoreAuthenticationError(
            message="Invalid credentials",
            code="INVALID_CREDENTIALS",
            details=ErrorDetails(user_id="user123"),
        )
        
        assert error.status_code == 401
        assert error.code == "INVALID_CREDENTIALS"
        assert error.message == "Invalid credentials"
        assert error.details.user_id == "user123"
        assert isinstance(error, CoreTripSageError)

    def test_core_authentication_error_defaults(self):
        """Test CoreAuthenticationError with default values."""
        error = CoreAuthenticationError()
        
        assert error.status_code == 401
        assert error.code == "AUTHENTICATION_ERROR"
        assert error.message == "Authentication failed"
        assert isinstance(error.details, ErrorDetails)

    def test_core_authorization_error(self):
        """Test CoreAuthorizationError."""
        error = CoreAuthorizationError(
            message="Access denied",
            details=ErrorDetails(resource_id="resource123"),
        )
        
        assert error.status_code == 403
        assert error.code == "AUTHORIZATION_ERROR"
        assert error.message == "Access denied"
        assert error.details.resource_id == "resource123"

    def test_core_resource_not_found_error(self):
        """Test CoreResourceNotFoundError."""
        error = CoreResourceNotFoundError(
            message="Trip not found",
            details=ErrorDetails(resource_id="trip123"),
        )
        
        assert error.status_code == 404
        assert error.code == "RESOURCE_NOT_FOUND"
        assert error.message == "Trip not found"
        assert error.details.resource_id == "trip123"

    def test_core_validation_error(self):
        """Test CoreValidationError."""
        error = CoreValidationError(
            message="Invalid email",
            field="email",
            value="invalid-email",
            constraint="valid email format",
        )
        
        assert error.status_code == 422
        assert error.code == "VALIDATION_ERROR"
        assert error.message == "Invalid email"
        assert error.details.additional_context["field"] == "email"
        assert error.details.additional_context["value"] == "invalid-email"
        assert error.details.additional_context["constraint"] == "valid email format"

    def test_core_service_error(self):
        """Test CoreServiceError."""
        error = CoreServiceError(
            message="Service unavailable",
            service="database",
        )
        
        assert error.status_code == 502
        assert error.code == "SERVICE_ERROR"
        assert error.message == "Service unavailable"
        assert error.details.service == "database"

    def test_core_rate_limit_error(self):
        """Test CoreRateLimitError."""
        error = CoreRateLimitError(
            message="Rate limit exceeded",
            retry_after=60,
        )
        
        assert error.status_code == 429
        assert error.code == "RATE_LIMIT_EXCEEDED"
        assert error.message == "Rate limit exceeded"
        assert error.details.additional_context["retry_after"] == 60

    def test_core_key_validation_error(self):
        """Test CoreKeyValidationError."""
        error = CoreKeyValidationError(
            message="Invalid API key",
            key_service="openai",
        )
        
        assert error.status_code == 400
        assert error.code == "INVALID_API_KEY"
        assert error.message == "Invalid API key"
        assert error.details.service == "openai"

    def test_core_database_error(self):
        """Test CoreDatabaseError."""
        error = CoreDatabaseError(
            message="Connection failed",
            operation="SELECT",
            table="users",
        )
        
        assert error.status_code == 500
        assert error.code == "DATABASE_ERROR"
        assert error.message == "Connection failed"
        assert error.details.operation == "SELECT"
        assert error.details.additional_context["table"] == "users"

    def test_core_external_api_error(self):
        """Test CoreExternalAPIError."""
        error = CoreExternalAPIError(
            message="API call failed",
            api_service="duffel",
            api_status_code=503,
            api_response={"error": "Service unavailable"},
        )
        
        assert error.status_code == 502
        assert error.code == "EXTERNAL_API_ERROR"
        assert error.message == "API call failed"
        assert error.details.service == "duffel"
        assert error.details.additional_context["api_status_code"] == 503
        assert error.details.additional_context["api_response"]["error"] == "Service unavailable"

    def test_core_mcp_error(self):
        """Test CoreMCPError."""
        error = CoreMCPError(
            message="MCP server failed",
            server="flights_mcp",
            tool="search_flights",
            params={"origin": "LAX", "destination": "JFK"},
        )
        
        assert error.status_code == 502
        assert error.code == "MCP_ERROR"
        assert error.message == "MCP server failed"
        assert error.details.service == "flights_mcp"
        assert error.details.additional_context["tool"] == "search_flights"
        assert error.details.additional_context["params"]["origin"] == "LAX"
        assert isinstance(error, CoreServiceError)

    def test_core_agent_error(self):
        """Test CoreAgentError."""
        error = CoreAgentError(
            message="Agent failed",
            agent_type="travel_agent",
            operation="plan_trip",
        )
        
        assert error.status_code == 502
        assert error.code == "AGENT_ERROR"
        assert error.message == "Agent failed"
        assert error.details.service == "travel_agent"
        assert error.details.operation == "plan_trip"
        assert isinstance(error, CoreServiceError)

    def test_core_tripsage_error_base(self):
        """Test base CoreTripSageError."""
        error = CoreTripSageError(
            message="Generic error",
            code="GENERIC_ERROR",
            status_code=500,
        )
        
        assert error.status_code == 500
        assert error.code == "GENERIC_ERROR"
        assert error.message == "Generic error"
        assert isinstance(error.details, ErrorDetails)

    def test_core_tripsage_error_defaults(self):
        """Test CoreTripSageError with defaults."""
        error = CoreTripSageError()
        
        assert error.status_code == 500
        assert error.code == "INTERNAL_ERROR"
        assert error.message == "An unexpected error occurred"


class TestExceptionMethods:
    """Test exception methods and properties."""

    def test_to_dict_method(self):
        """Test exception to_dict method."""
        error = CoreAuthenticationError(
            "Test error",
            details=ErrorDetails(user_id="123"),
        )
        
        error_dict = error.to_dict()
        assert error_dict["error"] == "CoreAuthenticationError"
        assert error_dict["message"] == "Test error"
        assert error_dict["code"] == "AUTHENTICATION_ERROR"
        assert error_dict["status_code"] == 401
        assert error_dict["details"]["user_id"] == "123"

    def test_str_method(self):
        """Test exception __str__ method."""
        error = CoreValidationError("Invalid input")
        assert str(error) == "VALIDATION_ERROR: Invalid input"

    def test_repr_method(self):
        """Test exception __repr__ method."""
        error = CoreAuthenticationError("Test error")
        repr_str = repr(error)
        assert "CoreAuthenticationError" in repr_str
        assert "Test error" in repr_str
        assert "AUTHENTICATION_ERROR" in repr_str
        assert "401" in repr_str

    def test_exception_with_dict_details(self):
        """Test exception creation with dict details."""
        error = CoreServiceError(
            "Service error",
            details={"service": "database", "operation": "connect"},
        )
        
        assert isinstance(error.details, ErrorDetails)
        assert error.details.service == "database"
        assert error.details.operation == "connect"

    def test_exception_with_none_details(self):
        """Test exception creation with None details."""
        error = CoreAuthenticationError("Auth error", details=None)
        assert isinstance(error.details, ErrorDetails)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_format_exception_with_core_error(self):
        """Test format_exception with core error."""
        error = CoreAuthenticationError("Test error")
        formatted = format_exception(error)
        
        assert formatted["error"] == "CoreAuthenticationError"
        assert formatted["message"] == "Test error"
        assert formatted["code"] == "AUTHENTICATION_ERROR"
        assert formatted["status_code"] == 401

    def test_format_exception_with_generic_error(self):
        """Test format_exception with generic error."""
        error = ValueError("Generic error")
        formatted = format_exception(error)
        
        assert formatted["error"] == "ValueError"
        assert formatted["message"] == "Generic error"
        assert formatted["code"] == "SYSTEM_ERROR"
        assert formatted["status_code"] == 500
        assert "traceback" in formatted["details"]

    def test_create_error_response_with_traceback(self):
        """Test create_error_response with traceback."""
        error = ValueError("Test error")
        response = create_error_response(error, include_traceback=True)
        
        assert "traceback" in response["details"]

    def test_create_error_response_without_traceback(self):
        """Test create_error_response without traceback."""
        error = ValueError("Test error")
        response = create_error_response(error, include_traceback=False)
        
        assert "traceback" not in response.get("details", {})

    def test_safe_execute_success(self):
        """Test safe_execute with successful function."""
        def successful_function(x, y):
            return x + y
        
        result = safe_execute(successful_function, 2, 3)
        assert result == 5

    def test_safe_execute_failure_with_fallback(self):
        """Test safe_execute with failing function and fallback."""
        def failing_function():
            raise ValueError("Function failed")
        
        result = safe_execute(failing_function, fallback="fallback_value")
        assert result == "fallback_value"

    def test_safe_execute_with_logger(self):
        """Test safe_execute with logger."""
        logger = Mock()
        
        def failing_function():
            raise ValueError("Function failed")
        
        result = safe_execute(failing_function, fallback="fallback", logger=logger)
        assert result == "fallback"
        logger.error.assert_called_once()

    def test_with_error_handling_decorator_success(self):
        """Test with_error_handling decorator with successful function."""
        @with_error_handling(fallback="fallback")
        def successful_function(x):
            return x * 2
        
        result = successful_function(5)
        assert result == 10

    def test_with_error_handling_decorator_failure(self):
        """Test with_error_handling decorator with failing function."""
        @with_error_handling(fallback="fallback")
        def failing_function():
            raise ValueError("Function failed")
        
        result = failing_function()
        assert result == "fallback"

    def test_with_error_handling_decorator_re_raise(self):
        """Test with_error_handling decorator with re_raise=True."""
        @with_error_handling(re_raise=True)
        def failing_function():
            raise ValueError("Function failed")
        
        with pytest.raises(ValueError):
            failing_function()

    @pytest.mark.asyncio
    async def test_with_error_handling_async_success(self):
        """Test with_error_handling decorator with async function."""
        @with_error_handling(fallback="async_fallback")
        async def async_successful_function(x):
            await asyncio.sleep(0.001)
            return x * 3
        
        result = await async_successful_function(4)
        assert result == 12

    @pytest.mark.asyncio
    async def test_with_error_handling_async_failure(self):
        """Test with_error_handling decorator with failing async function."""
        @with_error_handling(fallback="async_fallback")
        async def async_failing_function():
            await asyncio.sleep(0.001)
            raise ValueError("Async function failed")
        
        result = await async_failing_function()
        assert result == "async_fallback"


class TestExceptionMapping:
    """Test exception mapping functionality."""

    def test_exception_mapping_dict(self):
        """Test EXCEPTION_MAPPING dictionary."""
        assert "TripSageError" in EXCEPTION_MAPPING
        assert EXCEPTION_MAPPING["TripSageError"] == CoreTripSageError
        assert EXCEPTION_MAPPING["AuthenticationError"] == CoreAuthenticationError
        assert EXCEPTION_MAPPING["ValidationError"] == CoreValidationError

    def test_get_core_exception_known(self):
        """Test get_core_exception with known exception."""
        exception_class = get_core_exception("AuthenticationError")
        assert exception_class == CoreAuthenticationError

    def test_get_core_exception_unknown(self):
        """Test get_core_exception with unknown exception."""
        exception_class = get_core_exception("UnknownError")
        assert exception_class == CoreTripSageError


class TestFactoryFunctions:
    """Test factory functions."""

    def test_create_authentication_error(self):
        """Test create_authentication_error factory."""
        error = create_authentication_error("Custom auth error")
        assert isinstance(error, CoreAuthenticationError)
        assert error.message == "Custom auth error"

    def test_create_authentication_error_defaults(self):
        """Test create_authentication_error with defaults."""
        error = create_authentication_error()
        assert isinstance(error, CoreAuthenticationError)
        assert error.message == "Authentication failed"

    def test_create_authorization_error(self):
        """Test create_authorization_error factory."""
        error = create_authorization_error("Custom auth error")
        assert isinstance(error, CoreAuthorizationError)
        assert error.message == "Custom auth error"

    def test_create_validation_error(self):
        """Test create_validation_error factory."""
        error = create_validation_error("Custom validation error")
        assert isinstance(error, CoreValidationError)
        assert error.message == "Custom validation error"

    def test_create_not_found_error(self):
        """Test create_not_found_error factory."""
        error = create_not_found_error("Custom not found error")
        assert isinstance(error, CoreResourceNotFoundError)
        assert error.message == "Custom not found error"


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_exception_with_very_long_message(self):
        """Test exception with very long message."""
        long_message = "Error: " + "X" * 10000
        error = CoreValidationError(long_message)
        
        assert error.message == long_message
        assert len(str(error)) > 10000

    def test_exception_with_unicode_characters(self):
        """Test exception with unicode characters."""
        unicode_message = "Error with unicode: 测试 🚀 Ñoño"
        error = CoreAuthenticationError(unicode_message)
        
        assert error.message == unicode_message
        assert "测试" in str(error)
        assert "🚀" in str(error)
        assert "Ñoño" in str(error)

    def test_exception_with_large_additional_context(self):
        """Test exception with large additional context."""
        large_context = {f"key_{i}": f"value_{i}" for i in range(1000)}
        details = ErrorDetails(additional_context=large_context)
        error = CoreServiceError("Large context", details=details)
        
        assert len(error.details.additional_context) == 1000
        # Should not crash when converting to dict
        error_dict = error.to_dict()
        assert len(error_dict["details"]["additional_context"]) == 1000

    def test_exception_with_nested_objects_in_context(self):
        """Test exception with nested objects in context."""
        nested_context = {
            "level1": {
                "level2": {
                    "level3": ["item1", "item2", {"key": "value"}]
                }
            }
        }
        details = ErrorDetails(additional_context=nested_context)
        error = CoreMCPError("Nested context", details=details)
        
        # Should handle nested structures
        error_dict = error.to_dict()
        assert error_dict["details"]["additional_context"]["level1"]["level2"]["level3"][2]["key"] == "value"

    def test_exception_serialization(self):
        """Test exception serialization to JSON."""
        error = CoreAuthenticationError(
            "Serialization test",
            details=ErrorDetails(
                user_id="user123",
                additional_context={"timestamp": "2024-01-01T00:00:00Z"}
            ),
        )
        
        error_dict = error.to_dict()
        # Should be JSON serializable
        json_str = json.dumps(error_dict)
        assert "user123" in json_str
        assert "Serialization test" in json_str

    def test_error_details_with_none_additional_context(self):
        """Test ErrorDetails with None additional_context."""
        # Test that None additional_context becomes empty dict
        details = ErrorDetails(additional_context=None)
        assert details.additional_context == {}

    def test_exception_inheritance_chain(self):
        """Test exception inheritance chain."""
        auth_error = CoreAuthenticationError()
        assert isinstance(auth_error, CoreTripSageError)
        assert isinstance(auth_error, Exception)
        
        mcp_error = CoreMCPError()
        assert isinstance(mcp_error, CoreServiceError)
        assert isinstance(mcp_error, CoreTripSageError)
        assert isinstance(mcp_error, Exception)

    def test_exception_with_empty_details(self):
        """Test exception with completely empty details."""
        details = ErrorDetails()
        error = CoreServiceError("Empty details", details=details)
        
        error_dict = error.to_dict()
        # All detail fields should be None or empty
        detail_values = list(error_dict["details"].values())
        assert all(v is None or v == {} for v in detail_values)


@pytest.mark.asyncio
class TestAsyncExceptionHandling:
    """Test async exception handling scenarios."""

    async def test_async_exception_creation(self):
        """Test creating exceptions in async context."""
        async def async_function():
            raise CoreAuthenticationError("Async error")
        
        with pytest.raises(CoreAuthenticationError) as exc_info:
            await async_function()
        
        assert exc_info.value.message == "Async error"

    async def test_async_safe_execute(self):
        """Test safe_execute with async function simulation."""
        async def async_failing_function():
            raise ValueError("Async failure")
        
        # Note: safe_execute doesn't handle async functions directly
        # but we can test the pattern
        def sync_wrapper():
            try:
                # In real usage, this would use asyncio.run or similar
                raise ValueError("Async failure")
            except Exception:
                return "fallback"
        
        result = safe_execute(sync_wrapper)
        assert result == "fallback"

    async def test_async_format_exception(self):
        """Test format_exception in async context."""
        async def async_error_formatter():
            error = CoreServiceError("Async service error")
            return format_exception(error)
        
        formatted = await async_error_formatter()
        assert formatted["error"] == "CoreServiceError"
        assert formatted["message"] == "Async service error"