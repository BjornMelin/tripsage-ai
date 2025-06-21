"""
Clean, focused test suite for TripSage exception system.

Tests core exception functionality with proper Pydantic v2 compatibility.
"""

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
    """Test ErrorDetails model."""

    def test_error_details_creation_minimal(self):
        """Test ErrorDetails with minimal data."""
        details = ErrorDetails()
        assert details.service is None
        assert details.operation is None
        assert details.additional_context == {}

    def test_error_details_creation_full(self):
        """Test ErrorDetails with all fields."""
        details = ErrorDetails(
            service="test_service",
            operation="test_operation",
            resource_id="resource123",
            user_id="user456",
            request_id="req789",
            additional_context={"key": "value"},
        )
        assert details.service == "test_service"
        assert details.operation == "test_operation"
        assert details.resource_id == "resource123"
        assert details.user_id == "user456"
        assert details.request_id == "req789"
        assert details.additional_context == {"key": "value"}

    def test_error_details_serialization(self):
        """Test ErrorDetails model serialization."""
        details = ErrorDetails(
            service="test_service",
            operation="test_operation",
            additional_context={"nested": {"data": 123}},
        )
        serialized = details.model_dump(exclude_none=True)
        expected = {
            "service": "test_service",
            "operation": "test_operation",
            "additional_context": {"nested": {"data": 123}},
        }
        assert serialized == expected


class TestCoreTripSageError:
    """Test base CoreTripSageError class."""

    def test_basic_initialization(self):
        """Test basic error initialization."""
        error = CoreTripSageError("Test message")
        assert error.message == "Test message"
        assert error.code == "INTERNAL_ERROR"
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert isinstance(error.details, ErrorDetails)

    def test_full_initialization(self):
        """Test error with all parameters."""
        details = ErrorDetails(service="test_service")
        error = CoreTripSageError(
            message="Custom message",
            code="CUSTOM_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )
        assert error.message == "Custom message"
        assert error.code == "CUSTOM_ERROR"
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.details.service == "test_service"

    def test_initialization_with_dict_details(self):
        """Test error initialization with dict details."""
        error = CoreTripSageError(message="Test", details={"service": "test_service", "operation": "test_op"})
        assert isinstance(error.details, ErrorDetails)
        assert error.details.service == "test_service"
        assert error.details.operation == "test_op"

    def test_to_dict(self):
        """Test error dictionary conversion."""
        error = CoreTripSageError(
            message="Test message",
            code="TEST_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"service": "test_service"},
        )
        result = error.to_dict()
        expected = {
            "error": "CoreTripSageError",
            "message": "Test message",
            "code": "TEST_ERROR",
            "status_code": status.HTTP_400_BAD_REQUEST,
            "details": {"service": "test_service", "additional_context": {}},
        }
        assert result == expected

    def test_string_representation(self):
        """Test error string representations."""
        error = CoreTripSageError("Test message", "TEST_ERROR")
        assert str(error) == "TEST_ERROR: Test message"
        assert "CoreTripSageError" in repr(error)
        assert "TEST_ERROR" in repr(error)
        assert "Test message" in repr(error)


class TestSpecificExceptions:
    """Test specific exception types."""

    def test_authentication_error(self):
        """Test CoreAuthenticationError."""
        error = CoreAuthenticationError("Invalid credentials")
        assert error.code == "AUTHENTICATION_ERROR"
        assert error.status_code == status.HTTP_401_UNAUTHORIZED
        assert error.message == "Invalid credentials"

    def test_authorization_error(self):
        """Test CoreAuthorizationError."""
        error = CoreAuthorizationError("Access denied")
        assert error.code == "AUTHORIZATION_ERROR"
        assert error.status_code == status.HTTP_403_FORBIDDEN
        assert error.message == "Access denied"

    def test_resource_not_found_error(self):
        """Test CoreResourceNotFoundError."""
        error = CoreResourceNotFoundError("Resource not found")
        assert error.code == "RESOURCE_NOT_FOUND"
        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.message == "Resource not found"

    def test_validation_error(self):
        """Test CoreValidationError."""
        error = CoreValidationError("Invalid data")
        assert error.code == "VALIDATION_ERROR"
        assert error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert error.message == "Invalid data"

    def test_service_error(self):
        """Test CoreServiceError."""
        error = CoreServiceError("Service failed", service="test_service")
        assert error.code == "SERVICE_ERROR"
        assert error.status_code == status.HTTP_502_BAD_GATEWAY
        assert error.message == "Service failed"
        assert error.details.service == "test_service"

    def test_rate_limit_error(self):
        """Test CoreRateLimitError."""
        error = CoreRateLimitError("Rate limit exceeded")
        assert error.code == "RATE_LIMIT_EXCEEDED"
        assert error.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert error.message == "Rate limit exceeded"

    def test_key_validation_error(self):
        """Test CoreKeyValidationError."""
        error = CoreKeyValidationError("Invalid API key")
        assert error.code == "INVALID_API_KEY"
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.message == "Invalid API key"

    def test_database_error(self):
        """Test CoreDatabaseError."""
        error = CoreDatabaseError("Database connection failed")
        assert error.code == "DATABASE_ERROR"
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error.message == "Database connection failed"

    def test_external_api_error(self):
        """Test CoreExternalAPIError."""
        error = CoreExternalAPIError("API call failed", api_service="test_api")
        assert error.code == "EXTERNAL_API_ERROR"
        assert error.status_code == status.HTTP_502_BAD_GATEWAY
        assert error.message == "API call failed"
        assert error.details.service == "test_api"

    def test_mcp_error(self):
        """Test CoreMCPError."""
        error = CoreMCPError("MCP operation failed", tool="test_tool")
        assert error.code == "MCP_ERROR"
        assert error.status_code == status.HTTP_502_BAD_GATEWAY  # Inherits from CoreServiceError
        assert error.message == "MCP operation failed"
        assert error.details.additional_context["tool"] == "test_tool"

    def test_agent_error(self):
        """Test CoreAgentError."""
        error = CoreAgentError("Agent failed", agent_type="test_agent")
        assert error.code == "AGENT_ERROR"
        assert error.status_code == status.HTTP_502_BAD_GATEWAY  # Inherits from CoreServiceError
        assert error.message == "Agent failed"
        assert error.details.service == "test_agent"


class TestUtilityFunctions:
    """Test utility functions."""

    def test_format_exception_core_error(self):
        """Test formatting TripSage core errors."""
        error = CoreValidationError("Test validation error")
        result = format_exception(error)
        expected = {
            "error": "CoreValidationError",
            "message": "Test validation error",
            "code": "VALIDATION_ERROR",
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "details": {"additional_context": {}},
        }
        assert result == expected

    def test_format_exception_standard_error(self):
        """Test formatting standard Python exceptions."""
        error = ValueError("Standard error")
        result = format_exception(error)

        # Check the basic structure without relying on traceback details
        assert result["error"] == "ValueError"
        assert result["message"] == "Standard error"
        assert result["code"] == "SYSTEM_ERROR"
        assert result["status_code"] == 500
        assert "details" in result
        assert "traceback" in result["details"]

    def test_create_error_response(self):
        """Test error response creation."""
        error = CoreAuthenticationError("Auth failed")
        response = create_error_response(error)

        # Should return a dict with error information
        assert response["error"] == "CoreAuthenticationError"
        assert response["message"] == "Auth failed"
        assert response["code"] == "AUTHENTICATION_ERROR"
        assert response["status_code"] == status.HTTP_401_UNAUTHORIZED

    def test_safe_execute_success(self):
        """Test safe_execute with successful operation."""

        def success_func():
            return "success"

        result = safe_execute(success_func)
        assert result == "success"

    def test_safe_execute_failure(self):
        """Test safe_execute with failing operation."""

        def failing_func():
            raise ValueError("Test error")

        result = safe_execute(failing_func, fallback="default_value")
        assert result == "default_value"

    def test_with_error_handling_decorator_success(self):
        """Test with_error_handling decorator on successful function."""

        @with_error_handling()
        def success_func():
            return "success"

        result = success_func()
        assert result == "success"

    def test_with_error_handling_decorator_failure(self):
        """Test with_error_handling decorator on failing function."""

        @with_error_handling(fallback="default", re_raise=False)
        def failing_func():
            raise ValueError("Test error")

        result = failing_func()
        assert result == "default"


class TestErrorCreationHelpers:
    """Test error creation helper functions."""

    def test_create_authentication_error(self):
        """Test authentication error creation helper."""
        error = create_authentication_error("Invalid token")
        assert isinstance(error, CoreAuthenticationError)
        assert error.message == "Invalid token"
        assert error.code == "AUTHENTICATION_ERROR"

    def test_create_authorization_error(self):
        """Test authorization error creation helper."""
        error = create_authorization_error("No permission")
        assert isinstance(error, CoreAuthorizationError)
        assert error.message == "No permission"
        assert error.code == "AUTHORIZATION_ERROR"

    def test_create_validation_error(self):
        """Test validation error creation helper."""
        error = create_validation_error("Invalid input")
        assert isinstance(error, CoreValidationError)
        assert error.message == "Invalid input"
        assert error.code == "VALIDATION_ERROR"

    def test_create_not_found_error(self):
        """Test not found error creation helper."""
        error = create_not_found_error("Resource missing")
        assert isinstance(error, CoreResourceNotFoundError)
        assert error.message == "Resource missing"
        assert error.code == "RESOURCE_NOT_FOUND"


class TestErrorInheritance:
    """Test exception inheritance relationships."""

    def test_all_errors_inherit_from_base(self):
        """Test that all errors inherit from CoreTripSageError."""
        errors = [
            CoreAuthenticationError("test"),
            CoreAuthorizationError("test"),
            CoreResourceNotFoundError("test"),
            CoreValidationError("test"),
            CoreServiceError("test"),
            CoreRateLimitError("test"),
            CoreKeyValidationError("test"),
            CoreDatabaseError("test"),
            CoreExternalAPIError("test"),
            CoreMCPError("test"),
            CoreAgentError("test"),
        ]

        for error in errors:
            assert isinstance(error, CoreTripSageError)
            assert isinstance(error, Exception)

    def test_service_specific_errors_inherit_from_service_error(self):
        """Test that service-specific errors inherit from CoreServiceError."""
        mcp_error = CoreMCPError("test")
        agent_error = CoreAgentError("test")

        assert isinstance(mcp_error, CoreServiceError)
        assert isinstance(agent_error, CoreServiceError)
        assert isinstance(mcp_error, CoreTripSageError)
        assert isinstance(agent_error, CoreTripSageError)


class TestErrorWithComplexDetails:
    """Test errors with complex detail structures."""

    def test_error_with_nested_details(self):
        """Test error with nested detail structures."""
        details = {
            "service": "test_service",
            "operation": "complex_operation",
            "additional_context": {
                "nested": {"data": 123, "items": [1, 2, 3]},
                "metadata": {"timestamp": "2023-01-01", "version": "1.0"},
            },
        }

        error = CoreServiceError("Complex error", details=details)
        result = error.to_dict()

        assert result["details"]["service"] == "test_service"
        assert result["details"]["operation"] == "complex_operation"
        assert result["details"]["additional_context"]["nested"]["data"] == 123
        assert result["details"]["additional_context"]["metadata"]["version"] == "1.0"

    def test_error_details_exclude_none(self):
        """Test that None values are excluded from serialization."""
        details = ErrorDetails(
            service="test_service",
            operation=None,  # This should be excluded
            resource_id="123",
            user_id=None,  # This should be excluded
        )

        serialized = details.model_dump(exclude_none=True)
        expected = {
            "service": "test_service",
            "resource_id": "123",
            "additional_context": {},
        }
        assert serialized == expected
        assert "operation" not in serialized
        assert "user_id" not in serialized
