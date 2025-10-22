"""Modern test suite for ToolCallService with updated interfaces.

Tests for MCP tool calling, validation, error handling,
and retry mechanisms matching the actual implementation.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from tripsage_core.services.business.tool_calling_service import (
    ToolCallRequest,
    ToolCallResponse,
    ToolCallService,
    ToolCallValidationResult,
    get_tool_calling_service,
)


# Module-level fixtures for pytest discovery


@pytest.fixture
def mock_mcp_manager():
    """Mock MCP manager."""
    mock_manager = AsyncMock()
    # Mock the invoke method to accept method_name and params
    mock_manager.invoke = AsyncMock(return_value={"data": "test result"})
    return mock_manager


@pytest.fixture
def mock_error_recovery_service():
    """Mock error recovery service."""
    mock_service = AsyncMock()
    mock_service.store_successful_result.return_value = None
    mock_service.handle_retry.return_value = True
    mock_service.handle_mcp_error = AsyncMock()
    return mock_service


@pytest.fixture
def tool_calling_service(mock_mcp_manager):
    """Create ToolCallService with mocked dependencies."""
    return ToolCallService(mcp_manager=mock_mcp_manager)


@pytest.fixture
def sample_tool_call_request():
    """Sample tool call request."""
    return ToolCallRequest(
        id=str(uuid4()),
        service="duffel_flights",
        method="search_flights",
        params={
            "origin": "JFK",
            "destination": "LAX",
            "departure_date": "2024-06-01",
            "passengers": 1,
        },
        timeout=30.0,
        retry_count=3,
    )


@pytest.fixture
def sample_tool_call_response():
    """Sample tool call response."""
    return ToolCallResponse(
        id="test_call_123",
        status="success",
        result={"flights": [{"id": "flight_1", "price": 299.99}]},
        error=None,
        execution_time=1.2,
        service="duffel_flights",
        method="search_flights",
        timestamp=time.time(),
    )


class TestToolCallValidation:
    """Test tool call validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_tool_call_valid_request(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test validation of valid tool call request."""
        result = await tool_calling_service.validate_tool_call(sample_tool_call_request)

        assert isinstance(result, ToolCallValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.sanitized_params is not None

    @pytest.mark.asyncio
    async def test_validate_tool_call_invalid_service(self, tool_calling_service):
        """Test validation with invalid service name."""
        # This should raise during model instantiation
        with pytest.raises(
            ValueError, match="Service 'invalid_service' not in allowed services"
        ):
            ToolCallRequest(
                id=str(uuid4()),
                service="invalid_service",
                method="test_method",
                params={},
            )

    @pytest.mark.asyncio
    async def test_validate_tool_call_empty_method(self, tool_calling_service):
        """Test validation with empty method name."""
        # Empty method is allowed by the model, validation happens at service level
        request = ToolCallRequest(
            id=str(uuid4()),
            service="duffel_flights",
            method="",
            params={},
        )

        # This should not raise an error during validation
        result = await tool_calling_service.validate_tool_call(request)

        # Since it's missing required flight params, it should be invalid
        assert result.is_valid is False
        assert any("Missing required field" in error for error in result.errors)

    @pytest.mark.asyncio
    async def test_validate_tool_call_invalid_timeout(self, tool_calling_service):
        """Test validation with invalid timeout."""
        # Invalid timeout should raise during model instantiation
        with pytest.raises(
            ValueError, match="Timeout must be between 0 and 300 seconds"
        ):
            ToolCallRequest(
                id=str(uuid4()),
                service="duffel_flights",
                method="search_flights",
                params={},
                timeout=-1.0,
            )

    @pytest.mark.asyncio
    async def test_validate_tool_call_large_params(self, tool_calling_service):
        """Test validation with large parameter size."""
        # The actual service doesn't validate param size, so large params are allowed
        large_params = {
            "origin": "JFK",
            "destination": "LAX",
            "departure_date": "2024-06-01",
            "data": "x" * 1000,  # Some extra data
        }
        request = ToolCallRequest(
            id=str(uuid4()),
            service="duffel_flights",
            method="search_flights",
            params=large_params,
        )

        result = await tool_calling_service.validate_tool_call(request)

        # Should be valid since all required fields are present
        assert result.is_valid is True
        assert result.sanitized_params is not None


class TestToolCallExecution:
    """Test tool call execution functionality."""

    @pytest.mark.asyncio
    async def test_execute_tool_call_success(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test successful tool call execution."""
        expected_result = {"flights": [{"id": "flight_1", "price": 299.99}]}
        tool_calling_service.mcp_manager.invoke.return_value = expected_result

        response = await tool_calling_service.execute_tool_call(
            sample_tool_call_request
        )

        assert response.status == "success"
        assert response.result == expected_result
        assert response.execution_time > 0
        assert response.error is None
        assert response.service == sample_tool_call_request.service
        assert response.method == sample_tool_call_request.method

    @pytest.mark.asyncio
    async def test_execute_tool_call_mcp_failure(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test tool call execution with MCP failure."""
        tool_calling_service.mcp_manager.invoke.side_effect = Exception(
            "MCP service unavailable"
        )

        response = await tool_calling_service.execute_tool_call(
            sample_tool_call_request
        )

        assert response.status == "error"
        assert response.result is None
        assert "Tool call failed after error recovery" in response.error
        assert response.service == sample_tool_call_request.service
        assert response.method == sample_tool_call_request.method

    @pytest.mark.asyncio
    async def test_execute_tool_call_timeout(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test tool call execution with timeout."""

        async def slow_invoke(*args, **kwargs):
            await asyncio.sleep(2.0)  # Longer than timeout
            return {"result": {}}

        tool_calling_service.mcp_manager.invoke.side_effect = slow_invoke
        sample_tool_call_request.timeout = 0.1  # Very short timeout

        response = await tool_calling_service.execute_tool_call(
            sample_tool_call_request
        )

        # Service now has error recovery that succeeds with alternative service
        assert response.status == "success"
        assert response.result is not None

    @pytest.mark.asyncio
    async def test_execute_tool_call_exception(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test tool call execution with exception."""
        tool_calling_service.mcp_manager.invoke.side_effect = Exception("Network error")

        response = await tool_calling_service.execute_tool_call(
            sample_tool_call_request
        )

        assert response.status == "error"
        assert "Network error" in response.error

    @pytest.mark.asyncio
    async def test_execute_tool_call_with_retry(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test tool call execution with error recovery."""
        # Mock error recovery to return a fallback result
        mock_recovery_result = MagicMock()
        mock_recovery_result.success = True
        mock_recovery_result.result = {"data": "success after recovery"}
        mock_recovery_result.strategy_used = MagicMock(value="retry")

        tool_calling_service.error_recovery.handle_mcp_error = AsyncMock(
            return_value=mock_recovery_result
        )

        # First invoke fails
        tool_calling_service.mcp_manager.invoke.side_effect = Exception(
            "Temporary failure"
        )
        sample_tool_call_request.retry_count = 2

        response = await tool_calling_service.execute_tool_call(
            sample_tool_call_request
        )

        assert response.status == "success"
        assert response.result == {"data": "success after recovery"}
        assert tool_calling_service.error_recovery.handle_mcp_error.called

    @pytest.mark.asyncio
    async def test_execute_tool_call_max_retries_exceeded(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test tool call execution when error recovery fails."""
        # Mock error recovery to fail
        mock_recovery_result = MagicMock()
        mock_recovery_result.success = False
        mock_recovery_result.result = None
        mock_recovery_result.error = "All recovery attempts failed"

        tool_calling_service.error_recovery.handle_mcp_error = AsyncMock(
            return_value=mock_recovery_result
        )

        tool_calling_service.mcp_manager.invoke.side_effect = Exception(
            "Persistent failure"
        )
        sample_tool_call_request.retry_count = 2

        response = await tool_calling_service.execute_tool_call(
            sample_tool_call_request
        )

        assert response.status == "error"
        assert "Tool call failed after error recovery" in response.error


class TestParallelToolCalls:
    """Test parallel tool call functionality."""

    @pytest.mark.asyncio
    async def test_execute_parallel_tool_calls_success(self, tool_calling_service):
        """Test successful parallel tool call execution."""
        requests = [
            ToolCallRequest(
                id="call_1",
                service="duffel_flights",
                method="search_flights",
                params={
                    "origin": "JFK",
                    "destination": "LAX",
                    "departure_date": "2024-06-01",
                },
            ),
            ToolCallRequest(
                id="call_2",
                service="airbnb",
                method="search_properties",
                params={
                    "location": "Los Angeles",
                    "check_in": "2024-06-01",
                    "check_out": "2024-06-05",
                },
            ),
        ]

        # Mock successful responses
        tool_calling_service.mcp_manager.invoke.return_value = {"data": "mock result"}

        responses = await tool_calling_service.execute_parallel_tool_calls(requests)

        assert len(responses) == 2
        assert all(response.status == "success" for response in responses)
        assert responses[0].id == "call_1"
        assert responses[1].id == "call_2"

    @pytest.mark.asyncio
    async def test_execute_parallel_tool_calls_mixed_results(
        self, tool_calling_service
    ):
        """Test parallel tool calls with mixed success/failure results."""
        requests = [
            ToolCallRequest(
                id="call_success",
                service="duffel_flights",
                method="search_flights",
                params={
                    "origin": "JFK",
                    "destination": "LAX",
                    "departure_date": "2024-06-01",
                },
            ),
            ToolCallRequest(
                id="call_failure",
                service="airbnb",
                method="invalid_method",
                params={
                    "location": "LA",
                    "check_in": "2024-06-01",
                    "check_out": "2024-06-05",
                },
            ),
        ]

        # Mock mixed responses
        call_count = 0

        async def mixed_invoke(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"flights": []}
            else:
                raise Exception("Invalid method")

        tool_calling_service.mcp_manager.invoke.side_effect = mixed_invoke

        responses = await tool_calling_service.execute_parallel_tool_calls(requests)

        assert len(responses) == 2
        assert responses[0].status == "success"
        assert responses[1].status == "error"
        assert "Invalid method" in responses[1].error

    @pytest.mark.asyncio
    async def test_execute_parallel_tool_calls_empty_list(self, tool_calling_service):
        """Test parallel tool calls with empty request list."""
        responses = await tool_calling_service.execute_parallel_tool_calls([])

        assert responses == []

    @pytest.mark.asyncio
    async def test_execute_parallel_tool_calls_concurrent_execution(
        self, tool_calling_service
    ):
        """Test that parallel tool calls execute concurrently."""
        requests = [
            ToolCallRequest(
                id=f"call_{i}",
                service="duffel_flights",
                method="search_flights",
                params={
                    "origin": "JFK",
                    "destination": "LAX",
                    "departure_date": "2024-06-01",
                },
            )
            for i in range(5)
        ]

        # Mock slow responses
        async def slow_invoke(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate network delay
            return {"data": "result"}

        tool_calling_service.mcp_manager.invoke.side_effect = slow_invoke

        start_time = time.time()
        responses = await tool_calling_service.execute_parallel_tool_calls(requests)
        execution_time = time.time() - start_time

        # Should take ~0.1s (concurrent) not ~0.5s (sequential)
        assert execution_time < 0.3
        assert len(responses) == 5
        assert all(response.status == "success" for response in responses)


class TestToolCallMetrics:
    """Test tool call metrics and monitoring."""

    @pytest.mark.asyncio
    async def test_get_error_statistics(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test getting error statistics."""
        # Execute some tool calls to generate metrics
        tool_calling_service.mcp_manager.invoke.return_value = {"data": "test"}

        await tool_calling_service.execute_tool_call(sample_tool_call_request)

        stats = await tool_calling_service.get_error_statistics()

        assert "tool_calling_stats" in stats
        assert "total_calls" in stats["tool_calling_stats"]
        assert "success_rate" in stats["tool_calling_stats"]
        assert "error_rate" in stats["tool_calling_stats"]
        assert "average_execution_time" in stats["tool_calling_stats"]
        assert stats["tool_calling_stats"]["total_calls"] >= 1

    @pytest.mark.asyncio
    async def test_get_execution_history(self, tool_calling_service):
        """Test getting execution history."""
        # Generate some history first
        sample_request = ToolCallRequest(
            id=str(uuid4()),
            service="duffel_flights",
            method="search_flights",
            params={
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": "2024-06-01",
            },
        )

        tool_calling_service.mcp_manager.invoke.return_value = {"flights": []}

        await tool_calling_service.execute_tool_call(sample_request)

        # Get history
        history = await tool_calling_service.get_execution_history(limit=10)

        assert isinstance(history, list)
        assert len(history) >= 1
        assert all(isinstance(r, ToolCallResponse) for r in history)

        # Test service filtering
        flight_history = await tool_calling_service.get_execution_history(
            limit=10, service="duffel_flights"
        )
        assert all(r.service == "duffel_flights" for r in flight_history)


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_handle_tool_call_error_logging(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test proper error logging for tool call failures."""
        tool_calling_service.mcp_manager.invoke.side_effect = Exception("Test error")

        with patch(
            "tripsage_core.services.business.tool_calling_service.logger"
        ) as mock_logger:
            response = await tool_calling_service.execute_tool_call(
                sample_tool_call_request
            )

            # Verify error was logged
            mock_logger.exception.assert_called()
            assert response.status == "error"

    @pytest.mark.asyncio
    async def test_error_recovery_integration(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test integration with error recovery service."""
        # Mock successful result
        tool_calling_service.mcp_manager.invoke.return_value = {"data": "test"}
        # Mock the error recovery store_successful_result method
        if hasattr(tool_calling_service.error_recovery, "store_successful_result"):
            tool_calling_service.error_recovery.store_successful_result = AsyncMock()
        else:
            # Create the method if it doesn't exist
            tool_calling_service.error_recovery.store_successful_result = AsyncMock()

        response = await tool_calling_service.execute_tool_call(
            sample_tool_call_request
        )

        # Verify error recovery service was called
        tool_calling_service.error_recovery.store_successful_result.assert_called_once()
        assert response.status == "success"

    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self, tool_calling_service):
        """Test circuit breaker pattern for failing services."""
        # Simulate repeated failures
        tool_calling_service.mcp_manager.invoke.side_effect = Exception("Service down")

        # Mock error recovery to fail immediately
        mock_recovery_result = MagicMock()
        mock_recovery_result.success = False
        mock_recovery_result.error = "Service down"
        tool_calling_service.error_recovery.handle_mcp_error = AsyncMock(
            return_value=mock_recovery_result
        )

        failing_request = ToolCallRequest(
            id=str(uuid4()),
            service="duffel_flights",
            method="search_flights",
            params={
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": "2024-06-01",
            },
            retry_count=0,  # No retries for faster test
        )

        # Execute multiple failing calls
        for _ in range(5):
            response = await tool_calling_service.execute_tool_call(failing_request)
            assert response.status == "error"

        # Check if error statistics are tracked
        stats = await tool_calling_service.get_error_statistics()
        assert stats["tool_calling_stats"]["total_calls"] >= 5
        assert stats["tool_calling_stats"]["error_rate"] > 0


class TestDependencyInjection:
    """Test dependency injection functionality."""

    @pytest.mark.asyncio
    async def test_get_tool_calling_service(self):
        """Test dependency injection function."""
        service = await get_tool_calling_service()

        assert isinstance(service, ToolCallService)
        assert service.mcp_manager is not None
        assert service.error_recovery is not None

    def test_tool_calling_service_initialization(self):
        """Test service initialization with custom parameters."""
        mock_mcp_manager = AsyncMock()

        service = ToolCallService(mcp_manager=mock_mcp_manager)

        assert service.mcp_manager is mock_mcp_manager
        assert service.error_recovery is not None  # Created internally
        assert isinstance(service.execution_history, list)
        assert isinstance(service.rate_limits, dict)


class TestToolCallFormatting:
    """Test tool call formatting and response processing."""

    @pytest.mark.asyncio
    async def test_format_tool_result_for_chat_success(self, tool_calling_service):
        """Test formatting successful tool call result for chat display."""
        response = ToolCallResponse(
            id="test_call",
            status="success",
            result={"flights": [{"id": "flight_1", "price": 299.99}]},
            error=None,
            execution_time=1.2,
            service="duffel_flights",
            method="search_flights",
        )

        formatted = await tool_calling_service.format_tool_result_for_chat(response)

        assert formatted["type"] == "flights"
        assert formatted["title"] == "Flight Search Results"
        assert formatted["data"] == response.result
        assert "actions" in formatted
        assert "book" in formatted["actions"]

    @pytest.mark.asyncio
    async def test_format_tool_result_for_chat_error(self, tool_calling_service):
        """Test formatting error tool call result for chat display."""
        response = ToolCallResponse(
            id="test_call",
            status="error",
            result=None,
            error="Service unavailable",
            execution_time=0.1,
            service="duffel_flights",
            method="search_flights",
        )

        formatted = await tool_calling_service.format_tool_result_for_chat(response)

        assert formatted["type"] == "error"
        assert "Tool call failed" in formatted["message"]
        assert formatted["service"] == "duffel_flights"
        assert formatted["retry_available"] is True

    @pytest.mark.asyncio
    async def test_format_tool_result_for_chat_timeout(self, tool_calling_service):
        """Test formatting timeout tool call result for chat display."""
        response = ToolCallResponse(
            id="test_call",
            status="timeout",
            result=None,
            error="Tool call timed out after 30.0 seconds",
            execution_time=30.0,
            service="weather",
            method="get_forecast",
        )

        formatted = await tool_calling_service.format_tool_result_for_chat(response)

        assert formatted["type"] == "timeout"
        assert "timed out" in formatted["message"]
        assert formatted["service"] == "weather"
        assert formatted["retry_available"] is True
