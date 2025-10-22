"""Tests for the updated error_handling utilities integration with core exceptions."""

import logging
from unittest.mock import Mock, patch

import pytest

from tripsage_core.exceptions import (
    CoreDatabaseError,
    CoreExternalAPIError,
    CoreValidationError,
)
from tripsage_core.utils.error_handling_utils import (
    # Error context manager
    TripSageErrorContext,
    create_api_error,
    create_database_error,
    # Factory functions
    create_mcp_error,
    create_validation_error,
    # Utility functions
    log_exception,
    safe_execute_with_logging,
    with_error_handling_and_logging,
)


class TestUpdatedUtilityFunctions:
    """Test updated utility functions that use core exceptions."""

    def test_format_exception_delegation(self):
        """Test that error exceptions use core implementation."""
        exc = CoreValidationError("Test validation error")

        # Should have the core exception's to_dict() method
        result = exc.to_dict()
        assert "message" in result
        assert result["message"] == "Test validation error"

    def test_log_exception_with_external_api_error(self, caplog):
        """Test log_exception with CoreExternalAPIError."""
        exc = CoreExternalAPIError(
            message="External API failed",
            api_service="flights-mcp",
            api_status_code=504,
            api_response={"error": "timeout"},
        )

        with caplog.at_level(logging.ERROR):
            log_exception(exc)

        assert any("API Error" in record.message for record in caplog.records)
        assert any("flights-mcp" in record.message for record in caplog.records)

    def test_log_exception_with_api_error(self, caplog):
        """Test log_exception with CoreExternalAPIError."""
        exc = CoreExternalAPIError(
            message="API call failed",
            api_service="openai",
            api_status_code=429,
            api_response={"error": "rate limit exceeded"},
        )

        with caplog.at_level(logging.ERROR):
            log_exception(exc)

        assert any("API Error" in record.message for record in caplog.records)
        assert any("openai" in record.message for record in caplog.records)

    def test_log_exception_with_core_exception(self, caplog):
        """Test log_exception with generic CoreTripSageError."""
        exc = CoreValidationError("Validation failed")

        with caplog.at_level(logging.WARNING):
            log_exception(exc)

        assert any(
            "Application error: CoreValidationError - Validation failed"
            in record.message
            for record in caplog.records
        )

    def test_log_exception_with_standard_exception(self, caplog):
        """Test log_exception with standard Python exception."""
        exc = ValueError("Standard error")

        with caplog.at_level(logging.ERROR):
            log_exception(exc)

        assert any(
            "System error: ValueError - Standard error" in record.message
            for record in caplog.records
        )

    def test_safe_execute_delegates_to_core(self):
        """Test that safe_execute delegates to core implementation."""

        def test_func(x, y):
            return x * y

        result = safe_execute_with_logging(test_func, 3, 4, fallback=0)
        assert result == 12

        # Test with exception
        def failing_func():
            raise ValueError("Test error")

        result = safe_execute_with_logging(failing_func, fallback="fallback_value")
        assert result == "fallback_value"

    def test_with_error_handling_delegates_to_core(self):
        """Test that with_error_handling delegates to core implementation."""
        mock_logger = Mock()

        @with_error_handling_and_logging(
            fallback="error_result", logger_instance=mock_logger
        )
        def test_func():
            raise ValueError("Test error")

        result = test_func()
        assert result == "error_result"
        mock_logger.exception.assert_called_once()


class TestFactoryFunctions:
    """Test factory functions for creating TripSage-specific exceptions."""

    def test_create_mcp_error(self):
        """Test create_mcp_error now maps to CoreExternalAPIError."""
        exc = create_mcp_error(
            message="MCP operation failed",
            server="flights-mcp",
            tool="search_flights",
            params={"query": "NYC to LAX"},
            category="timeout",
            status_code=408,
        )

        assert isinstance(exc, CoreExternalAPIError)
        assert exc.message == "MCP operation failed"
        assert exc.code == "FLIGHTS-MCP_MCP_ERROR"

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
        assert context is not None
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
        assert context is not None
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
        context = exc.details.additional_context
        assert context is not None
        assert context["table"] == "users"


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
        assert start_call.args[0] == "Starting operation: %s"
        assert start_call.args[1] == "test_operation"
        extra = (start_call.kwargs or {}).get("extra", {})
        assert extra["service"] == "test_service"
        assert extra["user_id"] == "user123"
        assert extra["request_id"] == "req456"

        # Check completion log
        completion_call = mock_logger.debug.call_args_list[1]
        assert completion_call.args[0] == "Completed operation: %s"
        assert completion_call.args[1] == "test_operation"

    def test_error_context_enhancement(self):
        """Test context manager enhances exceptions with context."""
        mock_logger = Mock()
        mock_logger.name = "tests.context"

        original_exc = CoreValidationError("Validation failed")

        with (
            pytest.raises(CoreValidationError) as exc_info,
            TripSageErrorContext(
                operation="validate_user",
                service="user_service",
                user_id="user123",
                request_id="req456",
                logger_instance=mock_logger,
            ),
        ):
            raise original_exc

        # Exception should be enhanced with context
        detailed_exc = exc_info.value
        assert detailed_exc.details.operation == "validate_user"
        assert detailed_exc.details.service == "user_service"
        assert detailed_exc.details.user_id == "user123"
        assert detailed_exc.details.request_id == "req456"

        # Should log the error
        assert mock_logger.debug.call_count == 1  # Only start log (no completion)

    def test_context_with_standard_exception(self):
        """Test context manager with non-TripSage exception."""
        mock_logger = Mock()
        mock_logger.name = "tests.context"

        with (
            pytest.raises(ValueError),
            TripSageErrorContext(
                operation="test_operation", logger_instance=mock_logger
            ),
        ):
            raise ValueError("Standard error")

        # Should still log the start operation
        assert mock_logger.debug.call_count == 1

    def test_minimal_context(self):
        """Test context manager with minimal parameters."""
        mock_logger = Mock()
        mock_logger.name = "tests.context"

        with TripSageErrorContext(
            operation="minimal_test", logger_instance=mock_logger
        ):
            pass

        # Should work with just operation name
        assert mock_logger.debug.call_count == 2
        start_call = mock_logger.debug.call_args_list[0]
        assert start_call.args[0] == "Starting operation: %s"
        assert start_call.args[1] == "minimal_test"

        # Extra context should handle None values
        extra = (start_call.kwargs or {}).get("extra", {})
        assert extra["service"] is None
        assert extra["user_id"] is None
        assert extra["request_id"] is None


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @patch("tripsage_core.utils.error_handling_utils.get_logger")
    def test_mcp_manager_error_workflow(self, mock_get_logger):
        """Test complete MCP service error handling workflow."""
        mock_logger = Mock()
        mock_logger.name = "tests.mcp"
        mock_get_logger.return_value = mock_logger

        # Simulate MCP service operation with error
        with (
            pytest.raises(CoreExternalAPIError) as exc_info,
            TripSageErrorContext(
                operation="search_flights",
                service="flight_service",
                user_id="user123",
                request_id="req456",
                logger_instance=mock_logger,
            ),
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
        detailed_exc = exc_info.value
        assert detailed_exc.details.operation == "search_flights"
        assert detailed_exc.details.service == "flight_service"
        assert detailed_exc.details.user_id == "user123"
        assert detailed_exc.details.request_id == "req456"

        # Verify error formatting
        formatted = detailed_exc.to_dict()
        assert formatted["error"] == "CoreExternalAPIError"
        assert formatted["message"] == "Flight search timeout"
        assert formatted["code"] == "DUFFEL-MCP_MCP_ERROR"

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
        result = safe_execute_with_logging(
            validate_email, "user@example.com", fallback=False
        )
        assert result is True

        # Test validation error with fallback
        result = safe_execute_with_logging(
            validate_email, "invalid-email", fallback=False
        )
        assert result is False

    def test_database_error_with_decorator(self):
        """Test database error handling with decorator."""
        mock_logger = Mock()

        @with_error_handling_and_logging(fallback=[], logger_instance=mock_logger)
        def get_users():
            raise create_database_error(
                message="Connection timeout", operation="SELECT", table="users"
            )

        result = get_users()

        assert result == []
        mock_logger.exception.assert_called_once()

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
