"""
Comprehensive tests for TripSage exception system.

Tests the centralized exception hierarchy and error handling utilities
with modern pytest patterns and complete coverage.
"""

import asyncio
import json
from unittest.mock import Mock

import pytest
from fastapi import status

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
    create_authentication_error,
    create_authorization_error,
    create_error_response,
    create_not_found_error,
    create_validation_error,
    format_exception,
    safe_execute,
    with_error_handling,
)


class TestErrorDetails:
    """Test ErrorDetails model with modern patterns."""

    def test_error_details_creation(self):
        """Test ErrorDetails creation with all fields."""
        details = ErrorDetails(
            service="test_service",
            operation="test_operation",
            resource_id="resource123",
            user_id="user456",
            request_id="req789",
            additional_context={"key": "value", "count": 42},
        )

        assert details.service == "test_service"
        assert details.operation == "test_operation"
        assert details.resource_id == "resource123"
        assert details.user_id == "user456"
        assert details.request_id == "req789"
        assert details.additional_context["key"] == "value"
        assert details.additional_context["count"] == 42

    def test_error_details_optional_fields(self):
        """Test ErrorDetails with optional fields."""
        details = ErrorDetails()

        assert details.service is None
        assert details.operation is None
        assert details.resource_id is None
        assert details.user_id is None
        assert details.request_id is None
        assert details.additional_context == {}

    def test_error_details_json_serialization(self):
        """Test ErrorDetails JSON serialization."""
        details = ErrorDetails(
            service="api",
            operation="create_user",
            additional_context={"timestamp": "2025-06-04T12:00:00Z"},
        )

        json_data = details.model_dump_json()
        parsed = json.loads(json_data)

        assert parsed["service"] == "api"
        assert parsed["operation"] == "create_user"
        assert parsed["additional_context"]["timestamp"] == "2025-06-04T12:00:00Z"


class TestCoreExceptions:
    """Test core exception hierarchy."""

    def test_core_tripsage_error_basic(self):
        """Test basic CoreTripSageError creation."""
        error = CoreTripSageError("Test error")

        assert str(error) == "Test error"
        assert error.code == "INTERNAL_ERROR"
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error.details == {}

    def test_core_tripsage_error_with_details(self):
        """Test CoreTripSageError with full details."""
        details = ErrorDetails(service="test", operation="testing")
        error = CoreTripSageError(
            message="Detailed error",
            code="TEST_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )

        assert error.message == "Detailed error"
        assert error.code == "TEST_ERROR"
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.details["service"] == "test"
        assert error.details["operation"] == "testing"

    def test_core_validation_error(self):
        """Test CoreValidationError specifics."""
        error = CoreValidationError(
            message="Invalid input",
            field="email",
            value="invalid-email",
            details={"format": "email"},
        )

        assert error.message == "Invalid input"
        assert error.code == "VALIDATION_ERROR"
        assert error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        # Access field through details since it's stored there
        assert error.details["additional_context"]["field"] == "email"
        assert error.details["additional_context"]["value"] == "invalid-email"

    def test_core_authentication_error(self):
        """Test CoreAuthenticationError specifics."""
        error = CoreAuthenticationError(
            message="Invalid credentials",
            method="jwt",
            details={"realm": "api"},
        )

        assert error.message == "Invalid credentials"
        assert error.code == "AUTHENTICATION_ERROR"
        assert error.status_code == status.HTTP_401_UNAUTHORIZED
        # Method is stored in additional_context
        assert error.details["additional_context"]["method"] == "jwt"

    def test_core_authorization_error(self):
        """Test CoreAuthorizationError specifics."""
        error = CoreAuthorizationError(
            message="Insufficient permissions",
            resource="trips",
            action="delete",
            required_permissions=["admin", "owner"],
        )

        assert error.message == "Insufficient permissions"
        assert error.code == "AUTHORIZATION_ERROR"
        assert error.status_code == status.HTTP_403_FORBIDDEN
        # Check fields in additional_context
        assert error.details["additional_context"]["resource"] == "trips"
        assert error.details["additional_context"]["action"] == "delete"

    def test_core_resource_not_found_error(self):
        """Test CoreResourceNotFoundError specifics."""
        error = CoreResourceNotFoundError(
            message="Trip not found",
            resource_type="trip",
            resource_id="trip123",
        )

        assert error.message == "Trip not found"
        assert error.code == "RESOURCE_NOT_FOUND"
        assert error.status_code == status.HTTP_404_NOT_FOUND
        # Check fields in additional_context
        assert error.details["additional_context"]["resource_type"] == "trip"
        assert error.details["additional_context"]["resource_id"] == "trip123"

    def test_core_rate_limit_error(self):
        """Test CoreRateLimitError specifics."""
        error = CoreRateLimitError(
            message="Rate limit exceeded",
            limit=100,
            window_seconds=3600,
            retry_after=1800,
        )

        assert error.message == "Rate limit exceeded"
        assert error.code == "RATE_LIMIT_EXCEEDED"
        assert error.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        # Check fields in additional_context
        assert error.details["additional_context"]["limit"] == 100
        assert error.details["additional_context"]["window_seconds"] == 3600

    def test_core_database_error(self):
        """Test CoreDatabaseError specifics."""
        error = CoreDatabaseError(
            message="Database connection failed",
            operation="connect",
            table="users",
            database="tripsage",
        )

        assert error.message == "Database connection failed"
        assert error.code == "DATABASE_ERROR"
        assert error.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        # Check fields in additional_context
        assert error.details["additional_context"]["operation"] == "connect"
        assert error.details["additional_context"]["table"] == "users"

    def test_core_external_api_error(self):
        """Test CoreExternalAPIError specifics."""
        error = CoreExternalAPIError(
            message="External API failed",
            service_name="weather_api",
            endpoint="/forecast",
            response_status=500,
            response_body={"error": "Internal server error"},
        )

        assert error.message == "External API failed"
        assert error.code == "EXTERNAL_API_ERROR"
        assert error.status_code == status.HTTP_502_BAD_GATEWAY
        # Check fields in additional_context
        assert error.details["additional_context"]["service_name"] == "weather_api"
        assert error.details["additional_context"]["endpoint"] == "/forecast"

    def test_core_service_error(self):
        """Test CoreServiceError specifics."""
        error = CoreServiceError(
            message="Service operation failed",
            service="FlightService",
        )

        assert error.message == "Service operation failed"
        assert error.code == "SERVICE_ERROR"
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error.details["service"] == "FlightService"

    def test_core_agent_error(self):
        """Test CoreAgentError specifics."""
        error = CoreAgentError(
            message="Agent execution failed",
            agent_name="flight_agent",
        )

        assert error.message == "Agent execution failed"
        assert error.code == "AGENT_ERROR"
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        # Check fields in additional_context
        assert error.details["additional_context"]["agent_name"] == "flight_agent"

    def test_core_mcp_error(self):
        """Test CoreMCPError specifics."""
        error = CoreMCPError(
            message="MCP invocation failed",
            mcp_name="weather",
            method="get_forecast",
        )

        assert error.message == "MCP invocation failed"
        assert error.code == "MCP_ERROR"
        assert error.status_code == status.HTTP_502_BAD_GATEWAY
        # Check fields in additional_context
        assert error.details["additional_context"]["mcp_name"] == "weather"
        assert error.details["additional_context"]["method"] == "get_forecast"

    def test_core_key_validation_error(self):
        """Test CoreKeyValidationError specifics."""
        error = CoreKeyValidationError(
            message="Invalid API key format",
            key_type="openai",
        )

        assert error.message == "Invalid API key format"
        assert error.code == "KEY_VALIDATION_ERROR"
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        # Check fields in additional_context
        assert error.details["additional_context"]["key_type"] == "openai"


class TestErrorCreationHelpers:
    """Test error creation helper functions."""

    def test_create_validation_error(self):
        """Test create_validation_error helper."""
        error = create_validation_error(
            field="age",
            value=-5,
            message="Age must be positive",
        )

        assert isinstance(error, CoreValidationError)
        assert error.details["additional_context"]["field"] == "age"
        assert error.details["additional_context"]["value"] == -5
        assert "Age must be positive" in error.message

    def test_create_authentication_error(self):
        """Test create_authentication_error helper."""
        error = create_authentication_error(
            message="Token expired",
            method="bearer",
        )

        assert isinstance(error, CoreAuthenticationError)
        assert error.details["additional_context"]["method"] == "bearer"
        assert "Token expired" in error.message

    def test_create_authorization_error(self):
        """Test create_authorization_error helper."""
        error = create_authorization_error(
            resource="users",
            action="update",
        )

        assert isinstance(error, CoreAuthorizationError)
        assert error.details["additional_context"]["resource"] == "users"
        assert error.details["additional_context"]["action"] == "update"

    def test_create_not_found_error(self):
        """Test create_not_found_error helper."""
        error = create_not_found_error(
            resource_type="flight",
            resource_id="FL123",
        )

        assert isinstance(error, CoreResourceNotFoundError)
        assert error.details["additional_context"]["resource_type"] == "flight"
        assert error.details["additional_context"]["resource_id"] == "FL123"


class TestErrorResponseCreation:
    """Test error response creation utilities."""

    def test_create_error_response_basic(self):
        """Test basic error response creation."""
        error = CoreValidationError("Invalid input", field="email")
        response = create_error_response(error)

        assert response["error"]["code"] == "VALIDATION_ERROR"
        assert response["error"]["message"] == "Invalid input"
        assert "timestamp" in response["error"]
        assert response["status"] == "error"

    def test_create_error_response_with_request_id(self):
        """Test error response with request ID."""
        error = CoreServiceError("Service failed")
        response = create_error_response(error, request_id="req123")

        assert response["error"]["request_id"] == "req123"

    def test_create_error_response_with_path(self):
        """Test error response with request path."""
        error = CoreResourceNotFoundError("Not found")
        response = create_error_response(error, path="/api/v1/trips/123")

        assert response["error"]["path"] == "/api/v1/trips/123"


class TestExceptionFormatting:
    """Test exception formatting utilities."""

    def test_format_exception_basic(self):
        """Test basic exception formatting."""
        try:
            raise ValueError("Test error")
        except Exception as e:
            formatted = format_exception(e)

            assert "ValueError: Test error" in str(formatted)
            assert "traceback" in formatted
            assert "test_format_exception_basic" in formatted["traceback"]

    def test_format_exception_with_cause(self):
        """Test formatting exception with cause."""
        try:
            try:
                raise KeyError("Original error")
            except Exception as original:
                raise ValueError("Wrapped error") from original
        except Exception as e:
            formatted = format_exception(e)

            assert "ValueError: Wrapped error" in str(formatted["exception"])
            assert "KeyError: Original error" in formatted["traceback"]


class TestSafeExecute:
    """Test safe_execute decorator with async support."""

    @pytest.mark.asyncio
    async def test_safe_execute_success(self):
        """Test safe_execute with successful execution."""

        @safe_execute(default_return="default")
        async def successful_func():
            return "success"

        result = await successful_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_safe_execute_with_exception(self):
        """Test safe_execute catching exceptions."""

        @safe_execute(default_return="fallback")
        async def failing_func():
            raise ValueError("Test error")

        result = await failing_func()
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_safe_execute_with_logger(self):
        """Test safe_execute with custom logger."""
        mock_logger = Mock()

        @safe_execute(default_return=None, logger=mock_logger)
        async def failing_func():
            raise RuntimeError("Test error")

        result = await failing_func()
        assert result is None
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_execute_reraise(self):
        """Test safe_execute with reraise option."""

        @safe_execute(default_return=None, reraise=True)
        async def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await failing_func()

    def test_safe_execute_sync_function(self):
        """Test safe_execute with synchronous function."""

        @safe_execute(default_return="default")
        def sync_func():
            return "sync_result"

        result = sync_func()
        assert result == "sync_result"

    def test_safe_execute_sync_with_exception(self):
        """Test safe_execute with sync function that raises."""

        @safe_execute(default_return="fallback")
        def sync_failing_func():
            raise KeyError("Missing key")

        result = sync_failing_func()
        assert result == "fallback"


class TestWithErrorHandling:
    """Test with_error_handling decorator."""

    @pytest.mark.asyncio
    async def test_with_error_handling_success(self):
        """Test with_error_handling with successful execution."""

        @with_error_handling()()
        async def successful_operation():
            return {"status": "success", "data": [1, 2, 3]}

        result = await successful_operation()
        assert result == {"status": "success", "data": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_with_error_handling_core_exception(self):
        """Test with_error_handling with CoreTripSageError."""

        @with_error_handling()
        async def failing_operation():
            raise CoreServiceError(
                message="Service unavailable",
                code="SERVICE_UNAVAILABLE",
                service="TestService",
            )

        with pytest.raises(CoreServiceError) as exc_info:
            await failing_operation()

        assert exc_info.value.code == "SERVICE_UNAVAILABLE"
        assert exc_info.value.details["service"] == "TestService"

    @pytest.mark.asyncio
    async def test_with_error_handling_generic_error(self):
        """Test with_error_handling converting generic exception."""

        @with_error_handling()
        async def generic_error_operation():
            raise RuntimeError("Unexpected failure")

        with pytest.raises(CoreServiceError) as exc_info:
            await generic_error_operation()

        assert exc_info.value.message == "Unexpected failure"

    def test_with_error_handling_sync_function(self):
        """Test with_error_handling with synchronous function."""

        @with_error_handling()
        def sync_operation():
            return "sync_result"

        result = sync_operation()
        assert result == "sync_result"

    def test_with_error_handling_sync_with_error(self):
        """Test with_error_handling with sync function that raises."""

        @with_error_handling()
        def sync_error_operation():
            raise KeyError("not_found")

        with pytest.raises(CoreServiceError):
            sync_error_operation()


class TestExceptionInheritance:
    """Test exception inheritance and isinstance checks."""

    def test_exception_inheritance_chain(self):
        """Test that all exceptions inherit from CoreTripSageError."""
        exceptions = [
            CoreValidationError("test"),
            CoreAuthenticationError("test"),
            CoreAuthorizationError("test"),
            CoreResourceNotFoundError("test"),
            CoreRateLimitError("test"),
            CoreDatabaseError("test"),
            CoreExternalAPIError("test"),
            CoreServiceError("test"),
            CoreAgentError("test"),
            CoreMCPError("test"),
            CoreKeyValidationError("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, CoreTripSageError)
            assert isinstance(exc, Exception)

    def test_exception_type_checking(self):
        """Test exception type checking for error handling."""
        validation_error = CoreValidationError("Invalid")
        auth_error = CoreAuthenticationError("Unauthorized")

        # Check specific types
        assert isinstance(validation_error, CoreValidationError)
        assert not isinstance(validation_error, CoreAuthenticationError)

        assert isinstance(auth_error, CoreAuthenticationError)
        assert not isinstance(auth_error, CoreValidationError)

        # Both are CoreTripSageError
        assert isinstance(validation_error, CoreTripSageError)
        assert isinstance(auth_error, CoreTripSageError)


class TestExceptionSerialization:
    """Test exception serialization for API responses."""

    def test_exception_to_dict(self):
        """Test converting exception to dictionary."""
        error = CoreServiceError(
            message="Service failed",
            code="SERVICE_FAILURE",
            service="TestService",
            details={"request_id": "123", "retry_count": 3},
        )

        # Test to_dict method
        error_dict = error.to_dict()

        assert error_dict["code"] == "SERVICE_FAILURE"
        assert error_dict["message"] == "Service failed"
        assert error_dict["service"] == "TestService"

    def test_exception_json_serialization(self):
        """Test JSON serialization of exceptions."""
        error = CoreValidationError(
            message="Invalid email",
            field="email",
            value="not-an-email",
        )

        error_dict = error.to_dict()
        json_str = json.dumps(error_dict)
        parsed = json.loads(json_str)

        assert parsed["code"] == "VALIDATION_ERROR"
        assert parsed["message"] == "Invalid email"


class TestComplexErrorScenarios:
    """Test complex error handling scenarios."""

    @pytest.mark.asyncio
    async def test_nested_error_handling(self):
        """Test nested error handling with multiple decorators."""

        @with_error_handling()
        async def outer_operation():
            @with_error_handling()
            async def inner_operation():
                raise ValueError("Inner error")

            await inner_operation()

        with pytest.raises(CoreServiceError):
            await outer_operation()

    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self):
        """Test error handling with concurrent operations."""

        @safe_execute(default_return=None)
        async def maybe_failing_operation(should_fail: bool):
            if should_fail:
                raise RuntimeError("Deliberate failure")
            return "success"

        # Run concurrent operations with mixed success/failure
        results = await asyncio.gather(
            maybe_failing_operation(False),
            maybe_failing_operation(True),
            maybe_failing_operation(False),
            maybe_failing_operation(True),
        )

        assert results[0] == "success"
        assert results[1] is None  # Failed, returned default
        assert results[2] == "success"
        assert results[3] is None  # Failed, returned default


# Test module initialization and exports
def test_module_exports():
    """Test that all expected exceptions and utilities are exported."""
    from tripsage_core.exceptions import exceptions

    # Check exception classes
    assert hasattr(exceptions, "CoreTripSageError")
    assert hasattr(exceptions, "CoreValidationError")
    assert hasattr(exceptions, "CoreAuthenticationError")
    assert hasattr(exceptions, "CoreAuthorizationError")
    assert hasattr(exceptions, "CoreResourceNotFoundError")
    assert hasattr(exceptions, "CoreRateLimitError")
    assert hasattr(exceptions, "CoreDatabaseError")
    assert hasattr(exceptions, "CoreExternalAPIError")
    assert hasattr(exceptions, "CoreServiceError")
    assert hasattr(exceptions, "CoreAgentError")
    assert hasattr(exceptions, "CoreMCPError")
    assert hasattr(exceptions, "CoreKeyValidationError")

    # Check utilities
    assert hasattr(exceptions, "ErrorDetails")
    assert hasattr(exceptions, "create_validation_error")
    assert hasattr(exceptions, "create_authentication_error")
    assert hasattr(exceptions, "create_authorization_error")
    assert hasattr(exceptions, "create_not_found_error")
    assert hasattr(exceptions, "create_error_response")
    assert hasattr(exceptions, "format_exception")
    assert hasattr(exceptions, "safe_execute")
    assert hasattr(exceptions, "with_error_handling")
