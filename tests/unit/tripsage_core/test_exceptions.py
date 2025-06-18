"""Tests for the centralized exception system in tripsage_core.exceptions."""

from unittest.mock import Mock

import pytest
from fastapi import status

from tripsage_core.exceptions.exceptions import (
    CoreAgentError,
    # Authentication and authorization
    CoreAuthenticationError,
    CoreAuthorizationError,
    CoreDatabaseError,
    CoreExternalAPIError,
    CoreKeyValidationError,
    # Specialized exceptions
    CoreMCPError,
    CoreRateLimitError,
    # Resource and validation
    CoreResourceNotFoundError,
    # Service and infrastructure
    CoreServiceError,
    # Base exception
    CoreTripSageError,
    CoreValidationError,
    # Utility classes and functions
    ErrorDetails,
    create_error_response,
    format_exception,
    safe_execute,
    with_error_handling,
)

class TestErrorDetails:
    """Test cases for ErrorDetails class."""

    def test_default_initialization(self):
        """Test ErrorDetails with default values."""
        details = ErrorDetails()

        assert details.service is None
        assert details.operation is None
        assert details.resource_id is None
        assert details.user_id is None
        assert details.request_id is None
        assert details.additional_context == {}

    def test_full_initialization(self):
        """Test ErrorDetails with all fields."""
        additional_context = {"key": "value", "count": 42}
        details = ErrorDetails(
            service="test-service",
            operation="test-operation",
            resource_id="res-123",
            user_id="user-456",
            request_id="req-789",
            additional_context=additional_context,
        )

        assert details.service == "test-service"
        assert details.operation == "test-operation"
        assert details.resource_id == "res-123"
        assert details.user_id == "user-456"
        assert details.request_id == "req-789"
        assert details.additional_context == additional_context

    def test_model_dump(self):
        """Test Pydantic model serialization."""
        details = ErrorDetails(
            service="test-service", additional_context={"key": "value"}
        )

        dumped = details.model_dump(exclude_none=True)
        expected = {"service": "test-service", "additional_context": {"key": "value"}}

        assert dumped == expected

class TestCoreTripSageError:
    """Test cases for CoreTripSageError base class."""

    def test_default_initialization(self):
        """Test default CoreTripSageError initialization."""
        exc = CoreTripSageError()

        assert exc.message == "An unexpected error occurred"
        assert exc.code == "INTERNAL_ERROR"
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert isinstance(exc.details, ErrorDetails)
        assert str(exc) == "INTERNAL_ERROR: An unexpected error occurred"

    def test_full_initialization(self):
        """Test CoreTripSageError with all parameters."""
        details = ErrorDetails(service="test-service")
        exc = CoreTripSageError(
            message="Test error",
            code="TEST_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )

        assert exc.message == "Test error"
        assert exc.code == "TEST_ERROR"
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert exc.details == details

    def test_dict_details_conversion(self):
        """Test that dict details are converted to ErrorDetails."""
        exc = CoreTripSageError(
            message="Test error",
            details={"service": "test-service", "operation": "test-op"},
        )

        assert isinstance(exc.details, ErrorDetails)
        assert exc.details.service == "test-service"
        assert exc.details.operation == "test-op"

    def test_to_dict(self):
        """Test exception serialization to dictionary."""
        exc = CoreTripSageError(
            message="Test error",
            code="TEST_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"service": "test-service"},
        )

        result = exc.to_dict()
        expected = {
            "error": "CoreTripSageError",
            "message": "Test error",
            "code": "TEST_ERROR",
            "status_code": 400,
            "details": {"service": "test-service", "additional_context": {}},
        }

        assert result == expected

    def test_repr(self):
        """Test exception representation."""
        exc = CoreTripSageError(
            message="Test error",
            code="TEST_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

        expected = (
            "CoreTripSageError("
            "message='Test error', "
            "code='TEST_ERROR', "
            "status_code=400)"
        )

        assert repr(exc) == expected

class TestSpecificExceptions:
    """Test cases for specific exception classes."""

    def test_authentication_error(self):
        """Test CoreAuthenticationError."""
        exc = CoreAuthenticationError()

        assert exc.message == "Authentication failed"
        assert exc.code == "AUTHENTICATION_ERROR"
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED

        # Test with custom message
        exc = CoreAuthenticationError(message="Custom auth error")
        assert exc.message == "Custom auth error"

    def test_authorization_error(self):
        """Test CoreAuthorizationError."""
        exc = CoreAuthorizationError()

        assert exc.message == "You are not authorized to perform this action"
        assert exc.code == "AUTHORIZATION_ERROR"
        assert exc.status_code == status.HTTP_403_FORBIDDEN

    def test_resource_not_found_error(self):
        """Test CoreResourceNotFoundError."""
        exc = CoreResourceNotFoundError()

        assert exc.message == "Resource not found"
        assert exc.code == "RESOURCE_NOT_FOUND"
        assert exc.status_code == status.HTTP_404_NOT_FOUND

    def test_validation_error(self):
        """Test CoreValidationError with field details."""
        exc = CoreValidationError(
            message="Invalid field",
            field="username",
            value="",
            constraint="must not be empty",
        )

        assert exc.message == "Invalid field"
        assert exc.code == "VALIDATION_ERROR"
        assert exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert exc.details.additional_context["field"] == "username"
        assert exc.details.additional_context["value"] == ""
        assert exc.details.additional_context["constraint"] == "must not be empty"

    def test_service_error(self):
        """Test CoreServiceError."""
        exc = CoreServiceError(service="test-service")

        assert exc.message == "Service operation failed"
        assert exc.code == "SERVICE_ERROR"
        assert exc.status_code == status.HTTP_502_BAD_GATEWAY
        assert exc.details.service == "test-service"

    def test_rate_limit_error(self):
        """Test CoreRateLimitError with retry_after."""
        exc = CoreRateLimitError(retry_after=300)

        assert exc.message == "Rate limit exceeded"
        assert exc.code == "RATE_LIMIT_EXCEEDED"
        assert exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert exc.details.additional_context["retry_after"] == 300

    def test_key_validation_error(self):
        """Test CoreKeyValidationError."""
        exc = CoreKeyValidationError(key_service="openai")

        assert exc.message == "Invalid API key"
        assert exc.code == "INVALID_API_KEY"
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert exc.details.service == "openai"

    def test_database_error(self):
        """Test CoreDatabaseError."""
        exc = CoreDatabaseError(
            message="Query failed", operation="SELECT", table="users"
        )

        assert exc.message == "Query failed"
        assert exc.code == "DATABASE_ERROR"
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc.details.operation == "SELECT"
        assert exc.details.additional_context["table"] == "users"

    def test_external_api_error(self):
        """Test CoreExternalAPIError."""
        api_response = {"error": "Rate limit exceeded"}
        exc = CoreExternalAPIError(
            api_service="openai", api_status_code=429, api_response=api_response
        )

        assert exc.message == "External API call failed"
        assert exc.code == "EXTERNAL_API_ERROR"
        assert exc.status_code == status.HTTP_502_BAD_GATEWAY
        assert exc.details.service == "openai"
        assert exc.details.additional_context["api_status_code"] == 429
        assert exc.details.additional_context["api_response"] == api_response

    def test_mcp_error(self):
        """Test CoreMCPError."""
        params = {"query": "test"}
        exc = CoreMCPError(server="flights-mcp", tool="search_flights", params=params)

        assert exc.message == "MCP server operation failed"
        assert exc.code == "MCP_ERROR"
        assert exc.status_code == status.HTTP_502_BAD_GATEWAY
        assert exc.details.service == "flights-mcp"
        assert exc.details.additional_context["tool"] == "search_flights"
        assert exc.details.additional_context["params"] == params

    def test_agent_error(self):
        """Test CoreAgentError."""
        exc = CoreAgentError(agent_type="FlightAgent", operation="search_flights")

        assert exc.message == "Agent operation failed"
        assert exc.code == "AGENT_ERROR"
        assert exc.status_code == status.HTTP_502_BAD_GATEWAY
        assert exc.details.service == "FlightAgent"
        assert exc.details.operation == "search_flights"

class TestUtilityFunctions:
    """Test cases for utility functions."""

    def test_format_exception_with_core_exception(self):
        """Test format_exception with CoreTripSageError."""
        exc = CoreAuthenticationError(message="Auth failed")
        result = format_exception(exc)

        expected = {
            "error": "CoreAuthenticationError",
            "message": "Auth failed",
            "code": "AUTHENTICATION_ERROR",
            "status_code": 401,
            "details": {"additional_context": {}},
        }

        assert result == expected

    def test_format_exception_with_standard_exception(self):
        """Test format_exception with standard Python exception."""
        exc = ValueError("Invalid value")
        result = format_exception(exc)

        assert result["error"] == "ValueError"
        assert result["message"] == "Invalid value"
        assert result["code"] == "SYSTEM_ERROR"
        assert result["status_code"] == 500
        assert "traceback" in result["details"]

    def test_create_error_response_without_traceback(self):
        """Test create_error_response excludes traceback by default."""
        exc = ValueError("Invalid value")
        result = create_error_response(exc)

        assert "traceback" not in result.get("details", {})

    def test_create_error_response_with_traceback(self):
        """Test create_error_response includes traceback when requested."""
        exc = ValueError("Invalid value")
        result = create_error_response(exc, include_traceback=True)

        assert "traceback" in result.get("details", {})

    def test_safe_execute_success(self):
        """Test safe_execute with successful function."""

        def test_func(x, y):
            return x + y

        result = safe_execute(test_func, 2, 3)
        assert result == 5

    def test_safe_execute_with_exception(self):
        """Test safe_execute with exception and fallback."""

        def test_func():
            raise ValueError("Test error")

        result = safe_execute(test_func, fallback="fallback")
        assert result == "fallback"

    def test_safe_execute_with_logger(self):
        """Test safe_execute logs exceptions properly."""
        mock_logger = Mock()

        def test_func():
            raise ValueError("Test error")

        result = safe_execute(test_func, fallback="fallback", logger=mock_logger)

        assert result == "fallback"
        mock_logger.error.assert_called_once()

    def test_with_error_handling_decorator_sync(self):
        """Test with_error_handling decorator for sync functions."""
        mock_logger = Mock()

        @with_error_handling(fallback="error_result", logger=mock_logger)
        def test_func():
            raise ValueError("Test error")

        result = test_func()

        assert result == "error_result"
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_error_handling_decorator_async(self):
        """Test with_error_handling decorator for async functions."""
        mock_logger = Mock()

        @with_error_handling(fallback="error_result", logger=mock_logger)
        async def test_func():
            raise ValueError("Test error")

        result = await test_func()

        assert result == "error_result"
        mock_logger.error.assert_called_once()

    def test_with_error_handling_re_raise(self):
        """Test with_error_handling decorator with re_raise=True."""
        mock_logger = Mock()

        @with_error_handling(logger=mock_logger, re_raise=True)
        def test_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            test_func()

        mock_logger.error.assert_called_once()

class TestExceptionInheritance:
    """Test cases for exception inheritance and hierarchy."""

    def test_all_exceptions_inherit_from_base(self):
        """Test that all core exceptions inherit from CoreTripSageError."""
        exception_classes = [
            CoreAuthenticationError,
            CoreAuthorizationError,
            CoreResourceNotFoundError,
            CoreValidationError,
            CoreServiceError,
            CoreRateLimitError,
            CoreKeyValidationError,
            CoreDatabaseError,
            CoreExternalAPIError,
            CoreMCPError,
            CoreAgentError,
        ]

        for exc_class in exception_classes:
            exc = exc_class()
            assert isinstance(exc, CoreTripSageError)
            assert isinstance(exc, Exception)

    def test_specialized_exceptions_inherit_from_service_error(self):
        """Test that specialized exceptions inherit properly."""
        # MCP and Agent errors should inherit from ServiceError
        mcp_error = CoreMCPError()
        agent_error = CoreAgentError()

        assert isinstance(mcp_error, CoreServiceError)
        assert isinstance(mcp_error, CoreTripSageError)

        assert isinstance(agent_error, CoreServiceError)
        assert isinstance(agent_error, CoreTripSageError)

    def test_exception_can_be_caught_by_base_class(self):
        """Test that specific exceptions can be caught by base class."""

        def raise_auth_error():
            raise CoreAuthenticationError("Auth failed")

        def raise_validation_error():
            raise CoreValidationError("Validation failed")

        # Test catching specific exception with base class
        with pytest.raises(CoreTripSageError):
            raise_auth_error()

        with pytest.raises(CoreTripSageError):
            raise_validation_error()

        # Test catching specific exception type
        with pytest.raises(CoreAuthenticationError):
            raise_auth_error()

        with pytest.raises(CoreValidationError):
            raise_validation_error()

class TestExceptionIntegration:
    """Integration test cases for the exception system."""

    def test_end_to_end_error_handling(self):
        """Test complete error handling workflow."""
        # Create an exception with full context
        details = ErrorDetails(
            service="test-service",
            operation="test-operation",
            user_id="user-123",
            request_id="req-456",
            additional_context={"extra": "data"},
        )

        exc = CoreMCPError(
            message="MCP operation failed",
            code="MCP_TIMEOUT_ERROR",
            details=details,
            server="flights-mcp",
            tool="search_flights",
            params={"origin": "NYC", "destination": "LAX"},
        )

        # Test serialization
        serialized = exc.to_dict()

        assert serialized["error"] == "CoreMCPError"
        assert serialized["message"] == "MCP operation failed"
        assert serialized["code"] == "MCP_TIMEOUT_ERROR"
        assert serialized["status_code"] == 502

        details_dict = serialized["details"]
        assert details_dict["service"] == "test-service"
        assert details_dict["operation"] == "test-operation"
        assert details_dict["user_id"] == "user-123"
        assert details_dict["request_id"] == "req-456"

        context = details_dict["additional_context"]
        assert context["extra"] == "data"
        assert context["tool"] == "search_flights"
        assert context["params"] == {"origin": "NYC", "destination": "LAX"}

    def test_error_response_creation(self):
        """Test creating API error responses."""
        exc = CoreValidationError(
            message="Invalid input data",
            field="email",
            value="invalid-email",
            constraint="must be valid email format",
        )

        response = create_error_response(exc)

        assert response["error"] == "CoreValidationError"
        assert response["message"] == "Invalid input data"
        assert response["code"] == "VALIDATION_ERROR"
        assert response["status_code"] == 422

        details = response["details"]
        context = details["additional_context"]
        assert context["field"] == "email"
        assert context["value"] == "invalid-email"
        assert context["constraint"] == "must be valid email format"

    def test_exception_chaining_with_context(self):
        """Test exception handling with enhanced context."""
        original_exc = ValueError("Original error")

        # Create a TripSage exception with the original as context
        details = ErrorDetails(additional_context={"original_error": str(original_exc)})

        tripsage_exc = CoreServiceError(
            message="Service failed due to internal error",
            code="SERVICE_INTERNAL_ERROR",
            details=details,
            service="user-service",
        )

        # Verify context preservation
        assert tripsage_exc.details.service == "user-service"
        assert (
            tripsage_exc.details.additional_context["original_error"]
            == "Original error"
        )

        # Test error formatting
        formatted = format_exception(tripsage_exc)
        assert formatted["error"] == "CoreServiceError"
        assert (
            formatted["details"]["additional_context"]["original_error"]
            == "Original error"
        )
