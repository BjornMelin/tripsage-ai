"""Tests for the logging middleware."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request, Response
from starlette.types import ASGIApp

from tripsage.api.middlewares.logging import LoggingMiddleware


@pytest.fixture
def mock_app():
    """Create a mock ASGI app."""
    return MagicMock(spec=ASGIApp)


@pytest.fixture
def middleware(mock_app):
    """Create middleware instance."""
    return LoggingMiddleware(app=mock_app)


@pytest.fixture
def mock_request():
    """Create a mock request."""
    request = MagicMock(spec=Request)
    request.state = MagicMock()
    request.method = "GET"
    request.url.path = "/api/test"
    request.query_params = {"param1": "value1", "param2": "value2"}
    request.headers = {"user-agent": "Test Agent/1.0"}

    # Mock client
    client = MagicMock()
    client.host = "127.0.0.1"
    request.client = client

    return request


@pytest.fixture
def mock_response():
    """Create a mock response."""
    response = MagicMock(spec=Response)
    response.status_code = 200
    response.headers = {}
    return response


@pytest.fixture
def mock_call_next(mock_response):
    """Create a mock call_next function."""

    async def call_next(request):
        return mock_response

    return call_next


class TestLoggingMiddleware:
    """Test cases for LoggingMiddleware."""

    @patch("tripsage.api.middlewares.logging.uuid.uuid4")
    @patch("tripsage.api.middlewares.logging.logger")
    async def test_successful_request_logging(
        self, mock_logger, mock_uuid, middleware, mock_request, mock_call_next
    ):
        """Test logging for successful requests."""
        # Mock UUID generation
        test_uuid = "test-correlation-id"
        mock_uuid.return_value = test_uuid

        # Dispatch request
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verify correlation ID is set
        assert mock_request.state.correlation_id == test_uuid

        # Verify request logging
        assert mock_logger.info.call_count == 2  # Request start and completion

        # Check request start log
        start_call = mock_logger.info.call_args_list[0]
        assert start_call[0][0] == "Request started"
        extra = start_call[1]["extra"]
        assert extra["correlation_id"] == test_uuid
        assert extra["method"] == "GET"
        assert extra["path"] == "/api/test"
        assert extra["query_params"] == {"param1": "value1", "param2": "value2"}
        assert extra["client_host"] == "127.0.0.1"
        assert extra["user_agent"] == "Test Agent/1.0"

        # Check request completion log
        completion_call = mock_logger.info.call_args_list[1]
        assert completion_call[0][0] == "Request completed: 200"
        extra = completion_call[1]["extra"]
        assert extra["correlation_id"] == test_uuid
        assert extra["status_code"] == 200
        assert "processing_time_ms" in extra

        # Verify correlation ID in response headers
        assert response.headers["X-Correlation-ID"] == test_uuid

    @patch("tripsage.api.middlewares.logging.uuid.uuid4")
    @patch("tripsage.api.middlewares.logging.logger")
    @patch("tripsage.api.middlewares.logging.time.time")
    async def test_processing_time_calculation(
        self,
        mock_time,
        mock_logger,
        mock_uuid,
        middleware,
        mock_request,
        mock_call_next,
    ):
        """Test that processing time is calculated correctly."""
        # Mock UUID
        mock_uuid.return_value = "test-id"

        # Mock time to simulate processing delay
        start_time = 1000.0
        end_time = 1001.5  # 1.5 seconds later
        mock_time.side_effect = [start_time, end_time]

        # Dispatch request
        await middleware.dispatch(mock_request, mock_call_next)

        # Check processing time in completion log
        completion_call = mock_logger.info.call_args_list[1]
        extra = completion_call[1]["extra"]
        assert extra["processing_time_ms"] == 1500  # 1.5 seconds = 1500ms

    @patch("tripsage.api.middlewares.logging.uuid.uuid4")
    @patch("tripsage.api.middlewares.logging.logger")
    async def test_failed_request_logging(
        self, mock_logger, mock_uuid, middleware, mock_request
    ):
        """Test logging for failed requests."""
        # Mock UUID
        test_uuid = "test-correlation-id"
        mock_uuid.return_value = test_uuid

        # Create a call_next that raises an exception
        test_exception = ValueError("Test error")

        async def failing_call_next(request):
            raise test_exception

        # Dispatch request and expect exception
        with pytest.raises(ValueError) as exc_info:
            await middleware.dispatch(mock_request, failing_call_next)

        assert str(exc_info.value) == "Test error"

        # Verify exception logging
        mock_logger.exception.assert_called_once()
        exception_call = mock_logger.exception.call_args
        assert exception_call[0][0] == "Request failed: Test error"
        extra = exception_call[1]["extra"]
        assert extra["correlation_id"] == test_uuid
        assert extra["exception"] == "Test error"
        assert extra["exception_type"] == "ValueError"
        assert "processing_time_ms" in extra

    @patch("tripsage.api.middlewares.logging.uuid.uuid4")
    async def test_correlation_id_propagation(
        self, mock_uuid, middleware, mock_request, mock_call_next
    ):
        """Test that correlation ID is properly propagated."""
        # Mock UUID
        test_uuid = "unique-correlation-id"
        mock_uuid.return_value = test_uuid

        # Dispatch request
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verify correlation ID in request state
        assert mock_request.state.correlation_id == test_uuid

        # Verify correlation ID in response headers
        assert response.headers["X-Correlation-ID"] == test_uuid

    async def test_request_without_client(self, middleware, mock_call_next):
        """Test handling requests without client information."""
        # Create request without client
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.method = "GET"
        request.url.path = "/api/test"
        request.query_params = {}
        request.headers = {}
        request.client = None

        with patch("tripsage.api.middlewares.logging.logger") as mock_logger:
            # Dispatch request
            await middleware.dispatch(request, mock_call_next)

            # Check that client_host is None in logs
            start_call = mock_logger.info.call_args_list[0]
            extra = start_call[1]["extra"]
            assert extra["client_host"] is None

    @patch("tripsage.api.middlewares.logging.logger")
    async def test_empty_query_params(
        self, mock_logger, middleware, mock_request, mock_call_next
    ):
        """Test handling empty query parameters."""
        # Set empty query params
        mock_request.query_params = {}

        # Dispatch request
        await middleware.dispatch(mock_request, mock_call_next)

        # Check that empty dict is logged
        start_call = mock_logger.info.call_args_list[0]
        extra = start_call[1]["extra"]
        assert extra["query_params"] == {}

    @patch("tripsage.api.middlewares.logging.logger")
    async def test_missing_user_agent(
        self, mock_logger, middleware, mock_request, mock_call_next
    ):
        """Test handling missing user agent header."""
        # Remove user agent
        mock_request.headers = {}

        # Dispatch request
        await middleware.dispatch(mock_request, mock_call_next)

        # Check that user_agent is None
        start_call = mock_logger.info.call_args_list[0]
        extra = start_call[1]["extra"]
        assert extra["user_agent"] is None

    @patch("tripsage.api.middlewares.logging.time.time")
    @patch("tripsage.api.middlewares.logging.logger")
    async def test_exception_timing(
        self, mock_logger, mock_time, middleware, mock_request
    ):
        """Test that timing is calculated even when exception occurs."""
        # Mock time
        start_time = 1000.0
        end_time = 1000.5
        mock_time.side_effect = [start_time, end_time]

        # Create failing call_next
        async def failing_call_next(request):
            raise RuntimeError("Test error")

        # Dispatch request
        with pytest.raises(RuntimeError):
            await middleware.dispatch(mock_request, failing_call_next)

        # Check exception log has timing
        exception_call = mock_logger.exception.call_args
        extra = exception_call[1]["extra"]
        assert extra["processing_time_ms"] == 500  # 0.5 seconds = 500ms
