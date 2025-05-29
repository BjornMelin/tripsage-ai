"""Tests for the updated error_handling utilities integration with core exceptions."""

from unittest.mock import Mock, patch

import pytest

from tripsage.utils.error_handling import (
    APIError,
    DatabaseError,
    MCPError,
    # Backwards compatibility aliases
    TripSageError,
    # Error context manager
    TripSageErrorContext,
    ValidationError,
    create_api_error,
    create_database_error,
    # Factory functions
    create_mcp_error,
    create_validation_error,
    # Utility functions
    format_exception,
    log_exception,
    safe_execute,
    with_error_handling,
)
from tripsage_core.exceptions import (
    CoreDatabaseError,
    CoreExternalAPIError,
    CoreMCPError,
    CoreTripSageError,
    CoreValidationError,
)


class TestBackwardsCompatibility:
    """Test backwards compatibility aliases."""

    def test_alias_mappings(self):
        """Test that aliases point to correct core exceptions."""
        assert TripSageError == CoreTripSageError
        assert MCPError == CoreMCPError
        assert APIError == CoreExternalAPIError
        assert ValidationError == CoreValidationError
        assert DatabaseError == CoreDatabaseError

    def test_alias_functionality(self):
        """Test that aliases work identically to core exceptions."""
        # Test with alias
        alias_exc = TripSageError("Test message", "TEST_CODE")

        # Test with core exception
        core_exc = CoreTripSageError("Test message", "TEST_CODE")

        # Should have same functionality
        assert alias_exc.message == core_exc.message
        assert alias_exc.code == core_exc.code
        assert alias_exc.status_code == core_exc.status_code
        assert type(alias_exc) is type(core_exc)


class TestUpdatedUtilityFunctions:
    """Test updated utility functions that use core exceptions."""

    def test_format_exception_delegation(self):
        """Test that format_exception delegates to core implementation."""
        exc = CoreValidationError("Test validation error")
        result = format_exception(exc)

        # Should return the core exception's to_dict() output
        expected = exc.to_dict()
        assert result == expected

    @patch("tripsage.utils.error_handling.get_logger")
    def test_log_exception_with_mcp_error(self, mock_get_logger):
        """Test log_exception with CoreMCPError."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        exc = CoreMCPError(
            message="MCP operation failed",
            server="flights-mcp",
            tool="search_flights",
            params={"query": "NYC to LAX"},
        )

        log_exception(exc)

        # Should log error with MCP-specific details
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0]
        assert "MCP Error" in call_args[0]
        assert "flights-mcp" in call_args
        assert "search_flights" in call_args

    @patch("tripsage.utils.error_handling.get_logger")
    def test_log_exception_with_api_error(self, mock_get_logger):
        """Test log_exception with CoreExternalAPIError."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        exc = CoreExternalAPIError(
            message="API call failed",
            api_service="openai",
            api_status_code=429,
            api_response={"error": "rate limit exceeded"},
        )

        log_exception(exc)

        # Should log error with API-specific details
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0]
        assert "API Error" in call_args[0]
        assert "openai" in call_args
        assert 429 in call_args

    @patch("tripsage.utils.error_handling.get_logger")
    def test_log_exception_with_core_exception(self, mock_get_logger):
        """Test log_exception with generic CoreTripSageError."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        exc = CoreValidationError("Validation failed")

        log_exception(exc)

        # Should log warning for application errors
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0]
        assert "Application error" in call_args[0]
        assert "CoreValidationError" in call_args[1]
        assert "Validation failed" in call_args[2]

    @patch("tripsage.utils.error_handling.get_logger")
    def test_log_exception_with_standard_exception(self, mock_get_logger):
        """Test log_exception with standard Python exception."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        exc = ValueError("Standard error")

        log_exception(exc)

        # Should log error for system errors
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0]
        assert "System error" in call_args[0]
        assert "ValueError" in call_args[1]
        assert "Standard error" in call_args[2]

    def test_safe_execute_delegates_to_core(self):
        """Test that safe_execute delegates to core implementation."""

        def test_func(x, y):
            return x * y

        result = safe_execute(test_func, 3, 4, fallback=0)
        assert result == 12

        # Test with exception
        def failing_func():
            raise ValueError("Test error")

        result = safe_execute(failing_func, fallback="fallback_value")
        assert result == "fallback_value"

    def test_with_error_handling_delegates_to_core(self):
        """Test that with_error_handling delegates to core implementation."""
        mock_logger = Mock()

        @with_error_handling(fallback="error_result", logger_instance=mock_logger)
        def test_func():
            raise ValueError("Test error")

        result = test_func()
        assert result == "error_result"
        mock_logger.error.assert_called_once()


class TestFactoryFunctions:
    """Test factory functions for creating TripSage-specific exceptions."""

    def test_create_mcp_error(self):
        """Test create_mcp_error factory function."""
        exc = create_mcp_error(
            message="MCP operation failed",
            server="flights-mcp",
            tool="search_flights",
            params={"query": "NYC to LAX"},
            category="timeout",
            status_code=408,
        )

        assert isinstance(exc, CoreMCPError)
        assert exc.message == "MCP operation failed"
        assert exc.code == "MCP_TIMEOUT_ERROR"
        assert exc.details.service == "flights-mcp"

        context = exc.details.additional_context
        assert context["tool"] == "search_flights"
        assert context["params"] == {"query": "NYC to LAX"}
        assert context["category"] == "timeout"
        assert context["status_code"] == 408

    def test_create_api_error(self):
        """Test create_api_error factory function."""
        api_response = {"error": "rate limit exceeded"}
        exc = create_api_error(
            message="API call failed",
            service="openai",
            status_code=429,
            response=api_response,
        )

        assert isinstance(exc, CoreExternalAPIError)
        assert exc.message == "API call failed"
        assert exc.code == "OPENAI_API_ERROR"
        assert exc.details.service == "openai"

        context = exc.details.additional_context
        assert context["api_status_code"] == 429
        assert context["api_response"] == api_response

    def test_create_validation_error(self):
        """Test create_validation_error factory function."""
        exc = create_validation_error(
            message="Invalid email format",
            field="email",
            value="invalid-email",
            constraint="must be valid email address",
        )

        assert isinstance(exc, CoreValidationError)
        assert exc.message == "Invalid email format"
        assert exc.code == "VALIDATION_ERROR"

        context = exc.details.additional_context
        assert context["field"] == "email"
        assert context["value"] == "invalid-email"
        assert context["constraint"] == "must be valid email address"

    def test_create_database_error(self):
        """Test create_database_error factory function."""
        exc = create_database_error(
            message="Query execution failed",
            operation="SELECT",
            query="SELECT * FROM users",
            params={"limit": 10},
            table="users",
        )

        assert isinstance(exc, CoreDatabaseError)
        assert exc.message == "Query execution failed"
        assert exc.code == "DATABASE_ERROR"
        assert exc.details.operation == "SELECT"
        assert exc.details.additional_context["table"] == "users"


class TestTripSageErrorContext:
    """Test TripSageErrorContext context manager."""

    def test_successful_operation_context(self):
        """Test context manager with successful operation."""
        mock_logger = Mock()

        with TripSageErrorContext(
            operation="test_operation",
            service="test_service",
            user_id="user123",
            request_id="req456",
            logger_instance=mock_logger,
        ):
            # Simulate successful operation
            pass

        # Should log start and completion
        assert mock_logger.debug.call_count == 2

        # Check start log
        start_call = mock_logger.debug.call_args_list[0]
        assert "Starting operation: test_operation" in start_call[0][0]
        assert start_call[1]["extra"]["service"] == "test_service"
        assert start_call[1]["extra"]["user_id"] == "user123"
        assert start_call[1]["extra"]["request_id"] == "req456"

        # Check completion log
        completion_call = mock_logger.debug.call_args_list[1]
        assert "Completed operation: test_operation" in completion_call[0][0]

    def test_error_context_enhancement(self):
        """Test context manager enhances exceptions with context."""
        mock_logger = Mock()

        original_exc = CoreValidationError("Validation failed")

        with pytest.raises(CoreValidationError) as exc_info:
            with TripSageErrorContext(
                operation="validate_user",
                service="user_service",
                user_id="user123",
                request_id="req456",
                logger_instance=mock_logger,
            ):
                raise original_exc

        # Exception should be enhanced with context
        enhanced_exc = exc_info.value
        assert enhanced_exc.details.operation == "validate_user"
        assert enhanced_exc.details.service == "user_service"
        assert enhanced_exc.details.user_id == "user123"
        assert enhanced_exc.details.request_id == "req456"

        # Should log the error
        assert mock_logger.debug.call_count == 1  # Only start log (no completion)

    def test_context_with_standard_exception(self):
        """Test context manager with non-TripSage exception."""
        mock_logger = Mock()

        with pytest.raises(ValueError):
            with TripSageErrorContext(
                operation="test_operation", logger_instance=mock_logger
            ):
                raise ValueError("Standard error")

        # Should still log the start operation
        assert mock_logger.debug.call_count == 1

    def test_minimal_context(self):
        """Test context manager with minimal parameters."""
        mock_logger = Mock()

        with TripSageErrorContext(
            operation="minimal_test", logger_instance=mock_logger
        ):
            pass

        # Should work with just operation name
        assert mock_logger.debug.call_count == 2
        start_call = mock_logger.debug.call_args_list[0]
        assert "Starting operation: minimal_test" in start_call[0][0]

        # Extra context should handle None values
        extra = start_call[1]["extra"]
        assert extra["service"] is None
        assert extra["user_id"] is None
        assert extra["request_id"] is None


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @patch("tripsage.utils.error_handling.get_logger")
    def test_mcp_service_error_workflow(self, mock_get_logger):
        """Test complete MCP service error handling workflow."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Simulate MCP service operation with error
        with pytest.raises(CoreMCPError) as exc_info:
            with TripSageErrorContext(
                operation="search_flights",
                service="flight_service",
                user_id="user123",
                request_id="req456",
                logger_instance=mock_logger,
            ):
                # Create MCP error as would happen in real service
                exc = create_mcp_error(
                    message="Flight search timeout",
                    server="duffel-mcp",
                    tool="search_flights",
                    params={"origin": "NYC", "destination": "LAX"},
                    category="timeout",
                )
                raise exc

        # Verify exception enhancement
        enhanced_exc = exc_info.value
        assert enhanced_exc.details.operation == "search_flights"
        assert (
            enhanced_exc.details.service == "duffel-mcp"
        )  # Service from MCP error takes precedence
        assert enhanced_exc.details.user_id == "user123"
        assert enhanced_exc.details.request_id == "req456"

        # Verify error formatting
        formatted = format_exception(enhanced_exc)
        assert formatted["error"] == "CoreMCPError"
        assert formatted["message"] == "Flight search timeout"
        assert formatted["code"] == "MCP_TIMEOUT_ERROR"

        details = formatted["details"]
        assert details["operation"] == "search_flights"
        assert details["user_id"] == "user123"
        assert details["request_id"] == "req456"

        context = details["additional_context"]
        assert context["tool"] == "search_flights"
        assert context["params"]["origin"] == "NYC"

    def test_validation_error_with_safe_execute(self):
        """Test validation error handling with safe_execute."""

        def validate_email(email: str) -> bool:
            if "@" not in email:
                raise create_validation_error(
                    message="Invalid email format",
                    field="email",
                    value=email,
                    constraint="must contain @ symbol",
                )
            return True

        # Test successful validation
        result = safe_execute(validate_email, "user@example.com", fallback=False)
        assert result is True

        # Test validation error with fallback
        result = safe_execute(validate_email, "invalid-email", fallback=False)
        assert result is False

    def test_database_error_with_decorator(self):
        """Test database error handling with decorator."""
        mock_logger = Mock()

        @with_error_handling(fallback=[], logger_instance=mock_logger)
        def get_users():
            raise create_database_error(
                message="Connection timeout", operation="SELECT", table="users"
            )

        result = get_users()

        assert result == []
        mock_logger.error.assert_called_once()

    def test_api_error_response_creation(self):
        """Test creating API responses from exceptions."""
        # Create API error
        exc = create_api_error(
            message="OpenAI API rate limit exceeded",
            service="openai",
            status_code=429,
            response={"error": {"code": "rate_limit_exceeded"}},
        )

        # Create error response (like for FastAPI)
        from tripsage_core.exceptions import create_error_response

        response = create_error_response(exc)

        assert response["error"] == "CoreExternalAPIError"
        assert response["message"] == "OpenAI API rate limit exceeded"
        assert response["code"] == "OPENAI_API_ERROR"
        assert response["status_code"] == 502  # Bad Gateway for external API errors

        details = response["details"]
        assert details["service"] == "openai"

        context = details["additional_context"]
        assert context["api_status_code"] == 429
        assert context["api_response"]["error"]["code"] == "rate_limit_exceeded"
