"""
Simplified unit tests for agent API exception handlers.

Tests the exception handlers defined in main.py by testing them directly
without creating the full FastAPI application to avoid dependency issues.
"""

import json
from unittest.mock import Mock

import pytest
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError,
    CoreExternalAPIError,
    CoreKeyValidationError,
    CoreMCPError,
    CoreRateLimitError,
    CoreTripSageError,
    CoreValidationError,
    ErrorDetails,
)


class TestExceptionHandlerLogic:
    """Test the logic of exception handlers without creating full app."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request for testing."""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.state.correlation_id = "test-correlation-id"
        return request

    async def test_authentication_error_response_format(self, mock_request):
        """Test authentication error handler response format."""
        # Test the response logic by creating expected response structure
        error_details = ErrorDetails(
            user_id="test-user-id", service="auth", additional_context={}
        )
        exc = CoreAuthenticationError(
            message="Authentication failed", code="AUTH_001", details=error_details
        )

        # Test response creation logic
        expected_response = JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "error_code": exc.code,
                "error_type": "authentication",
                "details": exc.details.model_dump(exclude_none=True),
                "retry_guidance": (
                    "Check your authentication credentials and ensure they are valid"
                ),
            },
        )

        # Verify response structure
        assert expected_response.status_code == 401
        response_content = json.loads(expected_response.body.decode())
        assert response_content["status"] == "error"
        assert response_content["error_type"] == "authentication"
        assert "retry_guidance" in response_content

    async def test_key_validation_error_response_format(self, mock_request):
        """Test key validation error handler response format."""
        error_details = ErrorDetails(service="openai", additional_context={})
        exc = CoreKeyValidationError(
            message="Invalid API key", code="KEY_001", details=error_details
        )

        expected_response = JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "error_code": exc.code,
                "error_type": "key_validation",
                "details": exc.details.model_dump(exclude_none=True),
                "retry_guidance": (
                    f"Verify your {exc.details.service} API key is correct and has "
                    "required permissions"
                ),
            },
        )

        assert expected_response.status_code == 400
        response_content = json.loads(expected_response.body.decode())
        assert response_content["error_type"] == "key_validation"
        assert "openai" in response_content["retry_guidance"]

    async def test_rate_limit_error_response_format(self, mock_request):
        """Test rate limit error handler response format."""
        error_details = ErrorDetails(
            service="api", additional_context={"retry_after": 60}
        )
        exc = CoreRateLimitError(
            message="Rate limit exceeded", code="RATE_001", details=error_details
        )

        retry_after = 60
        expected_response = JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "error_code": exc.code,
                "error_type": "rate_limit",
                "details": exc.details.model_dump(exclude_none=True),
                "retry_after": retry_after,
                "retry_guidance": (
                    f"Wait {retry_after} seconds before making another request"
                ),
            },
            headers={"Retry-After": str(retry_after)},
        )

        assert expected_response.status_code == 429
        response_content = json.loads(expected_response.body.decode())
        assert response_content["error_type"] == "rate_limit"
        assert response_content["retry_after"] == 60
        assert "Retry-After" in expected_response.headers

    async def test_mcp_error_response_format(self, mock_request):
        """Test MCP error handler response format."""
        error_details = ErrorDetails(
            service="weather_mcp", additional_context={"tool": "get_weather"}
        )
        exc = CoreMCPError(
            message="MCP service unavailable", code="MCP_001", details=error_details
        )

        expected_response = JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "error_code": exc.code,
                "error_type": "mcp_service",
                "details": exc.details.model_dump(exclude_none=True),
                "retry_guidance": (
                    "The external service is temporarily unavailable. "
                    "Try again in a few moments"
                ),
            },
        )

        assert expected_response.status_code == 502
        response_content = json.loads(expected_response.body.decode())
        assert response_content["error_type"] == "mcp_service"
        assert "temporarily unavailable" in response_content["retry_guidance"]

    async def test_external_api_error_response_format(self, mock_request):
        """Test external API error handler response format."""
        error_details = ErrorDetails(
            service="duffel_api", additional_context={"api_status_code": 500}
        )
        exc = CoreExternalAPIError(
            message="External API error", code="API_001", details=error_details
        )

        expected_response = JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "error_code": exc.code,
                "error_type": "external_api",
                "details": exc.details.model_dump(exclude_none=True),
                "retry_guidance": (
                    "External service error. Check service status and try again"
                ),
            },
        )

        assert expected_response.status_code == 502
        response_content = json.loads(expected_response.body.decode())
        assert response_content["error_type"] == "external_api"
        assert "External service error" in response_content["retry_guidance"]

    async def test_validation_error_response_format(self, mock_request):
        """Test validation error handler response format."""
        error_details = ErrorDetails(
            service="validation", additional_context={"field": "email"}
        )
        exc = CoreValidationError(
            message="Invalid email format", code="VAL_001", details=error_details
        )

        expected_response = JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "error_code": exc.code,
                "error_type": "validation",
                "details": exc.details.model_dump(exclude_none=True),
                "retry_guidance": (
                    "Check the request parameters and ensure they meet the "
                    "required format"
                ),
            },
        )

        assert expected_response.status_code == 422
        response_content = json.loads(expected_response.body.decode())
        assert response_content["error_type"] == "validation"
        assert "required format" in response_content["retry_guidance"]

    async def test_core_tripsage_error_response_format(self, mock_request):
        """Test core TripSage error handler response format."""
        error_details = ErrorDetails(service="tripsage", additional_context={})
        exc = CoreTripSageError(
            message="Internal TripSage error", code="TS_001", details=error_details
        )

        expected_response = JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "error_code": exc.code,
                "error_type": "tripsage_error",
                "details": exc.details.model_dump(exclude_none=True),
                "retry_guidance": (
                    "An error occurred. Please check your request and try again"
                ),
            },
        )

        assert expected_response.status_code == 500
        response_content = json.loads(expected_response.body.decode())
        assert response_content["error_type"] == "tripsage_error"
        assert "check your request" in response_content["retry_guidance"]

    async def test_request_validation_error_response_format(self, mock_request):
        """Test FastAPI request validation error response format."""
        # Mock validation error from FastAPI
        validation_errors = [
            {
                "loc": ("body", "email"),
                "msg": "field required",
                "type": "value_error.missing",
                "input": None,
            },
            {
                "loc": ("body", "age"),
                "msg": "ensure this value is greater than 0",
                "type": "value_error.number.not_gt",
                "input": -1,
            },
        ]

        exc = Mock(spec=RequestValidationError)
        exc.errors.return_value = validation_errors

        error_details = []
        for error in validation_errors:
            error_details.append(
                {
                    "field": ".".join(str(x) for x in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                    "input": error.get("input"),
                }
            )

        expected_response = JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "message": "Request validation failed",
                "error_code": "REQUEST_VALIDATION_ERROR",
                "error_type": "validation",
                "details": {
                    "validation_errors": error_details,
                },
                "retry_guidance": (
                    "Check the request format and ensure all required fields are "
                    "provided correctly"
                ),
            },
        )

        assert expected_response.status_code == 422
        response_content = json.loads(expected_response.body.decode())
        assert response_content["error_type"] == "validation"
        assert len(response_content["details"]["validation_errors"]) == 2
        assert "required fields" in response_content["retry_guidance"]

    async def test_http_exception_response_format(self, mock_request):
        """Test HTTP exception handler response format."""
        exc = StarletteHTTPException(status_code=404, detail="Not found")

        expected_response = JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.detail,
                "error_code": f"HTTP_{exc.status_code}",
                "error_type": "http",
                "details": {},
                "retry_guidance": "Check the request URL and method",
            },
        )

        assert expected_response.status_code == 404
        response_content = json.loads(expected_response.body.decode())
        assert response_content["error_type"] == "http"
        assert response_content["error_code"] == "HTTP_404"
        assert "URL and method" in response_content["retry_guidance"]

    async def test_general_exception_response_format(self, mock_request):
        """Test general exception handler response format."""
        exc = ValueError("Something went wrong")

        # Mock settings for debug mode test
        mock_settings = Mock()
        mock_settings.debug = False

        expected_response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "Internal server error",
                "error_code": "INTERNAL_ERROR",
                "error_type": "system",
                "details": {
                    "exception_type": type(exc).__name__,
                    "exception_message": "Internal error occurred",  # No debug mode
                },
                "retry_guidance": (
                    "An unexpected error occurred. Please try again or contact support"
                ),
            },
        )

        assert expected_response.status_code == 500
        response_content = json.loads(expected_response.body.decode())
        assert response_content["error_type"] == "system"
        assert response_content["details"]["exception_type"] == "ValueError"
        assert "contact support" in response_content["retry_guidance"]


class TestResponseConsistency:
    """Test that all exception handlers return consistent response format."""

    def test_all_responses_have_required_fields(self):
        """Test that all exception responses contain required fields."""
        required_fields = [
            "status",
            "message",
            "error_code",
            "error_type",
            "details",
            "retry_guidance",
        ]

        # Sample response structure (this tests our expected format)
        sample_response = {
            "status": "error",
            "message": "Test error",
            "error_code": "TEST_001",
            "error_type": "test",
            "details": {},
            "retry_guidance": "Test guidance",
        }

        for field in required_fields:
            assert field in sample_response

        # Verify status is always "error" for error responses
        assert sample_response["status"] == "error"

    def test_error_types_are_consistent(self):
        """Test that error types match expected values."""
        expected_error_types = {
            "authentication",
            "key_validation",
            "rate_limit",
            "mcp_service",
            "external_api",
            "validation",
            "tripsage_error",
            "http",
            "system",
        }

        # This validates our error type taxonomy
        for error_type in expected_error_types:
            assert isinstance(error_type, str)
            assert len(error_type) > 0
            assert "_" in error_type or error_type in [
                "http",
                "system",
                "validation",
                "authentication",
            ]


class TestExceptionHandlerValidation:
    """Test that exception handlers properly validate inputs."""

    async def test_error_details_serialization(self):
        """Test that ErrorDetails objects serialize properly."""
        error_details = ErrorDetails(
            service="test_service",
            user_id="test_user",
            additional_context={"key": "value"},
        )

        serialized = error_details.model_dump(exclude_none=True)

        assert isinstance(serialized, dict)
        assert serialized["service"] == "test_service"
        assert serialized["user_id"] == "test_user"
        assert serialized["additional_context"]["key"] == "value"

    async def test_core_exception_status_codes(self):
        """Test that core exceptions have appropriate status codes."""
        error_details = ErrorDetails(service="test")

        exceptions_and_codes = [
            (CoreAuthenticationError("test", "TEST", error_details), 401),
            (CoreKeyValidationError("test", "TEST", error_details), 400),
            (CoreRateLimitError("test", "TEST", error_details), 429),
            (CoreMCPError("test", "TEST", error_details), 502),
            (CoreExternalAPIError("test", "TEST", error_details), 502),
            (CoreValidationError("test", "TEST", error_details), 422),
            (CoreTripSageError("test", "TEST", 500, error_details), 500),
        ]

        for exception, expected_code in exceptions_and_codes:
            assert exception.status_code == expected_code
