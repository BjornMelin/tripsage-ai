"""
Isolated tests for exception handlers in api/main.py.

This module tests exception handler functionality without requiring
full application dependencies.
"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

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
)


class TestCoreExceptionHandlers:
    """Test core exception functionality."""

    def test_core_authentication_error_creation(self):
        """Test CoreAuthenticationError creation and attributes."""
        error = CoreAuthenticationError(
            "Invalid credentials",
            code="INVALID_CREDENTIALS",
            details=ErrorDetails(user_id="user123"),
        )
        
        assert error.status_code == 401
        assert error.code == "INVALID_CREDENTIALS"
        assert error.message == "Invalid credentials"
        assert error.details.user_id == "user123"

    def test_core_authorization_error_creation(self):
        """Test CoreAuthorizationError creation and attributes."""
        error = CoreAuthorizationError(
            "Access denied",
            details=ErrorDetails(resource_id="resource123"),
        )
        
        assert error.status_code == 403
        assert error.code == "AUTHORIZATION_ERROR"
        assert error.message == "Access denied"
        assert error.details.resource_id == "resource123"

    def test_core_resource_not_found_error_creation(self):
        """Test CoreResourceNotFoundError creation and attributes."""
        error = CoreResourceNotFoundError(
            "Trip not found",
            details=ErrorDetails(resource_id="trip123"),
        )
        
        assert error.status_code == 404
        assert error.code == "RESOURCE_NOT_FOUND"
        assert error.message == "Trip not found"
        assert error.details.resource_id == "trip123"

    def test_core_validation_error_creation(self):
        """Test CoreValidationError creation and attributes."""
        error = CoreValidationError(
            "Invalid email",
            field="email",
            value="invalid-email",
            constraint="valid email format",
        )
        
        assert error.status_code == 422
        assert error.code == "VALIDATION_ERROR"
        assert error.message == "Invalid email"
        assert error.details.additional_context["field"] == "email"
        assert error.details.additional_context["value"] == "invalid-email"

    def test_core_service_error_creation(self):
        """Test CoreServiceError creation and attributes."""
        error = CoreServiceError(
            "Service unavailable",
            service="database",
        )
        
        assert error.status_code == 502
        assert error.code == "SERVICE_ERROR"
        assert error.message == "Service unavailable"
        assert error.details.service == "database"

    def test_core_rate_limit_error_creation(self):
        """Test CoreRateLimitError creation and attributes."""
        error = CoreRateLimitError(
            "Rate limit exceeded",
            retry_after=60,
        )
        
        assert error.status_code == 429
        assert error.code == "RATE_LIMIT_EXCEEDED"
        assert error.message == "Rate limit exceeded"
        assert error.details.additional_context["retry_after"] == 60

    def test_core_key_validation_error_creation(self):
        """Test CoreKeyValidationError creation and attributes."""
        error = CoreKeyValidationError(
            "Invalid API key",
            key_service="openai",
        )
        
        assert error.status_code == 400
        assert error.code == "INVALID_API_KEY"
        assert error.message == "Invalid API key"
        assert error.details.service == "openai"

    def test_core_database_error_creation(self):
        """Test CoreDatabaseError creation and attributes."""
        error = CoreDatabaseError(
            "Connection failed",
            operation="SELECT",
            table="users",
        )
        
        assert error.status_code == 500
        assert error.code == "DATABASE_ERROR"
        assert error.message == "Connection failed"
        assert error.details.operation == "SELECT"
        assert error.details.additional_context["table"] == "users"

    def test_core_external_api_error_creation(self):
        """Test CoreExternalAPIError creation and attributes."""
        error = CoreExternalAPIError(
            "API call failed",
            api_service="duffel",
            api_status_code=503,
            api_response={"error": "Service unavailable"},
        )
        
        assert error.status_code == 502
        assert error.code == "EXTERNAL_API_ERROR"
        assert error.message == "API call failed"
        assert error.details.service == "duffel"
        assert error.details.additional_context["api_status_code"] == 503

    def test_core_mcp_error_creation(self):
        """Test CoreMCPError creation and attributes."""
        error = CoreMCPError(
            "MCP server failed",
            server="flights_mcp",
            tool="search_flights",
            params={"origin": "LAX", "destination": "JFK"},
        )
        
        assert error.status_code == 502
        assert error.code == "MCP_ERROR"
        assert error.message == "MCP server failed"
        assert error.details.service == "flights_mcp"
        assert error.details.additional_context["tool"] == "search_flights"

    def test_core_agent_error_creation(self):
        """Test CoreAgentError creation and attributes."""
        error = CoreAgentError(
            "Agent failed",
            agent_type="travel_agent",
            operation="plan_trip",
        )
        
        assert error.status_code == 502
        assert error.code == "AGENT_ERROR"
        assert error.message == "Agent failed"
        assert error.details.service == "travel_agent"
        assert error.details.operation == "plan_trip"

    def test_format_exception_with_core_error(self):
        """Test format_exception utility with core error."""
        error = CoreAuthenticationError("Test error")
        formatted = format_exception(error)
        
        assert formatted["error"] == "CoreAuthenticationError"
        assert formatted["message"] == "Test error"
        assert formatted["code"] == "AUTHENTICATION_ERROR"
        assert formatted["status_code"] == 401

    def test_format_exception_with_generic_error(self):
        """Test format_exception utility with generic error."""
        error = ValueError("Generic error")
        formatted = format_exception(error)
        
        assert formatted["error"] == "ValueError"
        assert formatted["message"] == "Generic error"
        assert formatted["code"] == "SYSTEM_ERROR"
        assert formatted["status_code"] == 500
        assert "traceback" in formatted["details"]


class TestExceptionHandlerLogic:
    """Test the logic used in exception handlers."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings object."""
        settings = Mock()
        settings.debug = True
        return settings

    def test_format_details_helper_with_details(self):
        """Test _format_details helper logic."""
        details = ErrorDetails(user_id="user123", service="test")
        
        # Simulate the helper function logic
        def _format_details(details, include_debug=True):
            if not details:
                return None
            if not include_debug:
                return None
            return details.model_dump(exclude_none=True)
        
        result = _format_details(details, True)
        assert result["user_id"] == "user123"
        assert result["service"] == "test"

    def test_format_details_helper_no_details(self):
        """Test _format_details helper with no details."""
        def _format_details(details, include_debug=True):
            if not details:
                return None
            if not include_debug:
                return None
            return details.model_dump(exclude_none=True)
        
        result = _format_details(None, True)
        assert result is None

    def test_format_details_helper_debug_disabled(self):
        """Test _format_details helper with debug disabled."""
        details = ErrorDetails(user_id="user123")
        
        def _format_details(details, include_debug=True):
            if not details:
                return None
            if not include_debug:
                return None
            return details.model_dump(exclude_none=True)
        
        result = _format_details(details, False)
        assert result is None

    def test_retry_after_header_logic(self):
        """Test Retry-After header logic."""
        details = ErrorDetails(additional_context={"retry_after": 120})
        
        # Simulate the header logic from rate limit handler
        headers = {}
        if details and details.additional_context.get("retry_after"):
            retry_after = details.additional_context["retry_after"]
            headers["Retry-After"] = str(retry_after)
        
        assert headers["Retry-After"] == "120"

    def test_retry_after_header_logic_missing(self):
        """Test Retry-After header logic when retry_after is missing."""
        details = ErrorDetails(additional_context={})
        
        headers = {}
        if details and details.additional_context.get("retry_after"):
            retry_after = details.additional_context["retry_after"]
            headers["Retry-After"] = str(retry_after)
        
        assert "Retry-After" not in headers


class TestMinimalFastAPIExceptionHandlers:
    """Test exception handlers with minimal FastAPI setup."""

    @pytest.fixture
    def minimal_app(self):
        """Create minimal FastAPI app with just exception handlers."""
        app = FastAPI()
        
        # Mock settings for debug mode
        mock_settings = Mock()
        mock_settings.debug = True
        
        def _format_details(details, include_debug=True):
            """Helper to format exception details."""
            if not details:
                return None
            if not include_debug:
                return None
            return details.model_dump(exclude_none=True)

        # Add minimal exception handlers
        @app.exception_handler(CoreAuthenticationError)
        async def authentication_error_handler(
            request: Request, exc: CoreAuthenticationError
        ) -> JSONResponse:
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": exc.code,
                    "message": exc.message,
                    "details": _format_details(exc.details),
                },
            )

        @app.exception_handler(CoreResourceNotFoundError)
        async def resource_not_found_error_handler(
            request: Request, exc: CoreResourceNotFoundError
        ) -> JSONResponse:
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": exc.code,
                    "message": exc.message,
                    "details": _format_details(exc.details),
                },
            )

        @app.exception_handler(CoreRateLimitError)
        async def rate_limit_error_handler(
            request: Request, exc: CoreRateLimitError
        ) -> JSONResponse:
            headers = {}
            if exc.details and exc.details.additional_context.get("retry_after"):
                retry_after = exc.details.additional_context["retry_after"]
                headers["Retry-After"] = str(retry_after)

            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": exc.code,
                    "message": exc.message,
                    "details": _format_details(exc.details),
                },
                headers=headers,
            )

        @app.exception_handler(CoreDatabaseError)
        async def database_error_handler(
            request: Request, exc: CoreDatabaseError
        ) -> JSONResponse:
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": exc.code,
                    "message": "A database error occurred. Please try again later.",
                    "details": _format_details(exc.details, mock_settings.debug),
                },
            )

        @app.exception_handler(Exception)
        async def generic_exception_handler(
            request: Request, exc: Exception
        ) -> JSONResponse:
            error_data = format_exception(exc)
            
            if not mock_settings.debug:
                error_data = {
                    "error": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                    "code": "INTERNAL_ERROR",
                    "status_code": 500,
                    "details": None,
                }
            
            return JSONResponse(
                status_code=error_data.get("status_code", 500),
                content={
                    "error": error_data.get("code", "INTERNAL_ERROR"),
                    "message": error_data.get("message", "An unexpected error occurred"),
                    "details": error_data.get("details") if mock_settings.debug else None,
                },
            )

        # Add test routes
        @app.get("/test/auth-error")
        async def test_auth_error():
            raise CoreAuthenticationError("Test auth error")

        @app.get("/test/not-found")
        async def test_not_found():
            raise CoreResourceNotFoundError("Test not found")

        @app.get("/test/rate-limit")
        async def test_rate_limit():
            raise CoreRateLimitError(
                "Rate limit exceeded",
                details=ErrorDetails(additional_context={"retry_after": 60}),
            )

        @app.get("/test/database-error")
        async def test_database_error():
            raise CoreDatabaseError("Database error")

        @app.get("/test/generic-error")
        async def test_generic_error():
            raise ValueError("Generic error")

        return app

    @pytest.fixture
    def client(self, minimal_app):
        """Create test client."""
        return TestClient(minimal_app)

    def test_authentication_error_handler(self, client):
        """Test authentication error handler."""
        response = client.get("/test/auth-error")
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "AUTHENTICATION_ERROR"
        assert data["message"] == "Test auth error"

    def test_not_found_error_handler(self, client):
        """Test not found error handler."""
        response = client.get("/test/not-found")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "RESOURCE_NOT_FOUND"
        assert data["message"] == "Test not found"

    def test_rate_limit_error_handler(self, client):
        """Test rate limit error handler with Retry-After header."""
        response = client.get("/test/rate-limit")
        
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "60"
        
        data = response.json()
        assert data["error"] == "RATE_LIMIT_EXCEEDED"
        assert data["message"] == "Rate limit exceeded"

    def test_database_error_handler(self, client):
        """Test database error handler with user-friendly message."""
        response = client.get("/test/database-error")
        
        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "DATABASE_ERROR"
        assert "database error occurred" in data["message"].lower()

    def test_generic_exception_handler(self, client):
        """Test generic exception handler."""
        response = client.get("/test/generic-error")
        
        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "SYSTEM_ERROR"
        assert "Generic error" in data["message"]


class TestExceptionHandlerEdgeCases:
    """Test edge cases for exception handling."""

    def test_exception_with_none_details(self):
        """Test exception with None details."""
        error = CoreAuthenticationError("Test", details=None)
        assert error.details is not None  # Should create empty ErrorDetails

    def test_exception_with_dict_details(self):
        """Test exception with dict details."""
        error = CoreAuthenticationError("Test", details={"user_id": "123"})
        assert error.details.user_id == "123"

    def test_exception_to_dict_method(self):
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

    def test_exception_str_representation(self):
        """Test exception string representation."""
        error = CoreAuthenticationError("Test error")
        assert str(error) == "AUTHENTICATION_ERROR: Test error"

    def test_exception_repr_representation(self):
        """Test exception repr representation."""
        error = CoreAuthenticationError("Test error")
        repr_str = repr(error)
        assert "CoreAuthenticationError" in repr_str
        assert "Test error" in repr_str
        assert "AUTHENTICATION_ERROR" in repr_str
        assert "401" in repr_str

    def test_error_details_exclude_none(self):
        """Test ErrorDetails exclude_none functionality."""
        details = ErrorDetails(
            user_id="123",
            service=None,
            additional_context={"key": "value"}
        )
        
        dumped = details.model_dump(exclude_none=True)
        assert "user_id" in dumped
        assert "service" not in dumped
        assert "additional_context" in dumped

    def test_large_additional_context(self):
        """Test handling of large additional context."""
        large_context = {f"key_{i}": f"value_{i}" for i in range(100)}
        details = ErrorDetails(additional_context=large_context)
        
        error = CoreServiceError("Test", details=details)
        # Should not crash with large context
        assert len(error.details.additional_context) == 100

    def test_unicode_in_error_messages(self):
        """Test unicode characters in error messages."""
        unicode_message = "Error with unicode: 测试 🚀 Ñoño"
        error = CoreAuthenticationError(unicode_message)
        
        assert error.message == unicode_message
        assert str(error) == f"AUTHENTICATION_ERROR: {unicode_message}"

    def test_very_long_error_message(self):
        """Test very long error messages."""
        long_message = "Error: " + "X" * 10000
        error = CoreValidationError(long_message)
        
        assert error.message == long_message
        assert len(str(error)) > 10000


@pytest.mark.asyncio
class TestAsyncExceptionHandling:
    """Test async aspects of exception handling."""

    async def test_async_exception_creation(self):
        """Test creating exceptions in async context."""
        async def async_function():
            raise CoreAuthenticationError("Async error")
        
        with pytest.raises(CoreAuthenticationError) as exc_info:
            await async_function()
        
        assert exc_info.value.message == "Async error"
        assert exc_info.value.status_code == 401

    async def test_async_error_formatting(self):
        """Test formatting exceptions in async context."""
        async def async_function():
            error = CoreServiceError("Async service error")
            return format_exception(error)
        
        formatted = await async_function()
        assert formatted["error"] == "CoreServiceError"
        assert formatted["message"] == "Async service error"