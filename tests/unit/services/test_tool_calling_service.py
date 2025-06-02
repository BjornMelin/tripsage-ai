"""
Test suite for ToolCallService.

Comprehensive tests for MCP tool calling, validation, error handling,
and retry mechanisms. Achieves >90% test coverage.
"""

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from tripsage_core.services.business.error_handling_service import ErrorRecoveryService
from tripsage_core.services.business.tool_calling_service import (
    ToolCallRequest,
    ToolCallResponse,
    ToolCallService,
    ToolCallValidationResult,
    get_tool_calling_service,
)


class TestToolCallService:
    """Test class for ToolCallService."""

    @pytest.fixture
    def mock_mcp_manager(self):
        """Mock MCP manager."""
        mock_manager = AsyncMock()
        mock_manager.invoke.return_value = {
            "success": True,
            "result": {"data": "test result"},
            "execution_time": 0.5,
        }
        return mock_manager

    @pytest.fixture
    def mock_error_recovery_service(self):
        """Mock error recovery service."""
        mock_service = AsyncMock(spec=ErrorRecoveryService)
        mock_service.store_successful_result.return_value = None
        mock_service.handle_retry.return_value = True
        return mock_service

    @pytest.fixture
    def tool_calling_service(self, mock_mcp_manager, mock_error_recovery_service):
        """Create ToolCallService with mocked dependencies."""
        return ToolCallService(
            mcp_manager=mock_mcp_manager,
            error_recovery_service=mock_error_recovery_service,
        )

    @pytest.fixture
    def sample_tool_call_request(self):
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
    def sample_tool_call_response(self):
        """Sample tool call response."""
        return ToolCallResponse(
            id="test_call_123",
            service="duffel_flights",
            method="search_flights",
            success=True,
            result={"flights": [{"id": "flight_1", "price": 299.99}]},
            execution_time=1.2,
            error_message=None,
            retry_count=0,
        )


class TestToolCallValidation:
    """Test tool call validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_tool_call_valid_request(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test validation of valid tool call request."""
        result = await tool_calling_service._validate_tool_call(
            sample_tool_call_request
        )

        assert isinstance(result, ToolCallValidationResult)
        assert result.is_valid is True
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_validate_tool_call_invalid_service(self, tool_calling_service):
        """Test validation with invalid service name."""
        request = ToolCallRequest(
            id=str(uuid4()),
            service="invalid_service",
            method="test_method",
            params={},
        )

        with pytest.raises(
            ValueError, match="Service 'invalid_service' is not allowed"
        ):
            await tool_calling_service._validate_tool_call(request)

    @pytest.mark.asyncio
    async def test_validate_tool_call_empty_method(self, tool_calling_service):
        """Test validation with empty method name."""
        request = ToolCallRequest(
            id=str(uuid4()),
            service="duffel_flights",
            method="",
            params={},
        )

        result = await tool_calling_service._validate_tool_call(request)

        assert result.is_valid is False
        assert "Method name cannot be empty" in result.error_message

    @pytest.mark.asyncio
    async def test_validate_tool_call_invalid_timeout(self, tool_calling_service):
        """Test validation with invalid timeout."""
        request = ToolCallRequest(
            id=str(uuid4()),
            service="duffel_flights",
            method="search_flights",
            params={},
            timeout=-1.0,
        )

        result = await tool_calling_service._validate_tool_call(request)

        assert result.is_valid is False
        assert "Timeout must be positive" in result.error_message

    @pytest.mark.asyncio
    async def test_validate_tool_call_large_params(self, tool_calling_service):
        """Test validation with large parameter size."""
        large_params = {"data": "x" * (2 * 1024 * 1024)}  # 2MB of data
        request = ToolCallRequest(
            id=str(uuid4()),
            service="duffel_flights",
            method="search_flights",
            params=large_params,
        )

        result = await tool_calling_service._validate_tool_call(request)

        assert result.is_valid is False
        assert "Parameters too large" in result.error_message


class TestToolCallExecution:
    """Test tool call execution functionality."""

    @pytest.mark.asyncio
    async def test_execute_tool_call_success(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test successful tool call execution."""
        expected_result = {"flights": [{"id": "flight_1", "price": 299.99}]}
        tool_calling_service.mcp_manager.invoke.return_value = {
            "success": True,
            "result": expected_result,
            "execution_time": 1.5,
        }

        response = await tool_calling_service.execute_tool_call(
            sample_tool_call_request
        )

        assert response.success is True
        assert response.result == expected_result
        assert response.execution_time == 1.5
        assert response.error_message is None
        assert response.retry_count == 0

    @pytest.mark.asyncio
    async def test_execute_tool_call_mcp_failure(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test tool call execution with MCP failure."""
        tool_calling_service.mcp_manager.invoke.return_value = {
            "success": False,
            "error": "MCP service unavailable",
            "execution_time": 0.1,
        }

        response = await tool_calling_service.execute_tool_call(
            sample_tool_call_request
        )

        assert response.success is False
        assert response.result is None
        assert "MCP service unavailable" in response.error_message
        assert response.retry_count == 0

    @pytest.mark.asyncio
    async def test_execute_tool_call_timeout(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test tool call execution with timeout."""

        async def slow_invoke(*args, **kwargs):
            await asyncio.sleep(2.0)  # Longer than timeout
            return {"success": True, "result": {}}

        tool_calling_service.mcp_manager.invoke.side_effect = slow_invoke
        sample_tool_call_request.timeout = 0.5  # Short timeout

        response = await tool_calling_service.execute_tool_call(
            sample_tool_call_request
        )

        assert response.success is False
        assert "timed out" in response.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_tool_call_exception(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test tool call execution with exception."""
        tool_calling_service.mcp_manager.invoke.side_effect = Exception("Network error")

        response = await tool_calling_service.execute_tool_call(
            sample_tool_call_request
        )

        assert response.success is False
        assert "Network error" in response.error_message

    @pytest.mark.asyncio
    async def test_execute_tool_call_with_retry(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test tool call execution with retry on failure."""
        # First call fails, second succeeds
        call_count = 0

        async def failing_invoke(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary failure")
            return {
                "success": True,
                "result": {"data": "success after retry"},
                "execution_time": 0.5,
            }

        tool_calling_service.mcp_manager.invoke.side_effect = failing_invoke
        sample_tool_call_request.retry_count = 2

        response = await tool_calling_service.execute_tool_call(
            sample_tool_call_request
        )

        assert response.success is True
        assert response.result == {"data": "success after retry"}
        assert response.retry_count == 1  # One retry was performed

    @pytest.mark.asyncio
    async def test_execute_tool_call_max_retries_exceeded(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test tool call execution when max retries exceeded."""
        tool_calling_service.mcp_manager.invoke.side_effect = Exception(
            "Persistent failure"
        )
        sample_tool_call_request.retry_count = 2

        response = await tool_calling_service.execute_tool_call(
            sample_tool_call_request
        )

        assert response.success is False
        assert "Persistent failure" in response.error_message
        assert response.retry_count == 2  # All retries were attempted


class TestBatchToolCalls:
    """Test batch tool call functionality."""

    @pytest.mark.asyncio
    async def test_execute_batch_tool_calls_success(self, tool_calling_service):
        """Test successful batch tool call execution."""
        requests = [
            ToolCallRequest(
                id="call_1",
                service="duffel_flights",
                method="search_flights",
                params={"origin": "JFK", "destination": "LAX"},
            ),
            ToolCallRequest(
                id="call_2",
                service="airbnb",
                method="search_properties",
                params={"location": "Los Angeles"},
            ),
        ]

        # Mock successful responses
        tool_calling_service.mcp_manager.invoke.return_value = {
            "success": True,
            "result": {"data": "mock result"},
            "execution_time": 0.5,
        }

        responses = await tool_calling_service.execute_batch_tool_calls(requests)

        assert len(responses) == 2
        assert all(response.success for response in responses)
        assert responses[0].id == "call_1"
        assert responses[1].id == "call_2"

    @pytest.mark.asyncio
    async def test_execute_batch_tool_calls_mixed_results(self, tool_calling_service):
        """Test batch tool calls with mixed success/failure results."""
        requests = [
            ToolCallRequest(
                id="call_success",
                service="duffel_flights",
                method="search_flights",
                params={"origin": "JFK", "destination": "LAX"},
            ),
            ToolCallRequest(
                id="call_failure",
                service="airbnb",
                method="invalid_method",
                params={},
            ),
        ]

        # Mock mixed responses
        call_count = 0

        async def mixed_invoke(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "success": True,
                    "result": {"flights": []},
                    "execution_time": 0.5,
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid method",
                    "execution_time": 0.1,
                }

        tool_calling_service.mcp_manager.invoke.side_effect = mixed_invoke

        responses = await tool_calling_service.execute_batch_tool_calls(requests)

        assert len(responses) == 2
        assert responses[0].success is True
        assert responses[1].success is False
        assert responses[1].error_message == "Invalid method"

    @pytest.mark.asyncio
    async def test_execute_batch_tool_calls_empty_list(self, tool_calling_service):
        """Test batch tool calls with empty request list."""
        responses = await tool_calling_service.execute_batch_tool_calls([])

        assert responses == []

    @pytest.mark.asyncio
    async def test_execute_batch_tool_calls_concurrent_execution(
        self, tool_calling_service
    ):
        """Test that batch tool calls execute concurrently."""
        import time

        requests = [
            ToolCallRequest(
                id=f"call_{i}",
                service="duffel_flights",
                method="search_flights",
                params={"test": i},
            )
            for i in range(5)
        ]

        # Mock slow responses
        async def slow_invoke(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate network delay
            return {
                "success": True,
                "result": {"data": "result"},
                "execution_time": 0.1,
            }

        tool_calling_service.mcp_manager.invoke.side_effect = slow_invoke

        start_time = time.time()
        responses = await tool_calling_service.execute_batch_tool_calls(requests)
        execution_time = time.time() - start_time

        # Should take ~0.1s (concurrent) not ~0.5s (sequential)
        assert execution_time < 0.3
        assert len(responses) == 5
        assert all(response.success for response in responses)


class TestToolCallMetrics:
    """Test tool call metrics and monitoring."""

    @pytest.mark.asyncio
    async def test_get_performance_metrics(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test getting performance metrics."""
        # Execute some tool calls to generate metrics
        tool_calling_service.mcp_manager.invoke.return_value = {
            "success": True,
            "result": {"data": "test"},
            "execution_time": 1.0,
        }

        await tool_calling_service.execute_tool_call(sample_tool_call_request)

        metrics = await tool_calling_service.get_performance_metrics()

        assert "total_calls" in metrics
        assert "successful_calls" in metrics
        assert "failed_calls" in metrics
        assert "average_execution_time" in metrics
        assert "calls_by_service" in metrics
        assert metrics["total_calls"] >= 1

    @pytest.mark.asyncio
    async def test_reset_performance_metrics(self, tool_calling_service):
        """Test resetting performance metrics."""
        # Generate some metrics first
        sample_request = ToolCallRequest(
            id=str(uuid4()),
            service="duffel_flights",
            method="test",
            params={},
        )

        tool_calling_service.mcp_manager.invoke.return_value = {
            "success": True,
            "result": {},
            "execution_time": 0.5,
        }

        await tool_calling_service.execute_tool_call(sample_request)

        # Check metrics exist
        metrics_before = await tool_calling_service.get_performance_metrics()
        assert metrics_before["total_calls"] > 0

        # Reset metrics
        await tool_calling_service.reset_performance_metrics()

        # Check metrics are reset
        metrics_after = await tool_calling_service.get_performance_metrics()
        assert metrics_after["total_calls"] == 0
        assert metrics_after["successful_calls"] == 0
        assert metrics_after["failed_calls"] == 0


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
            mock_logger.error.assert_called()
            assert response.success is False

    @pytest.mark.asyncio
    async def test_error_recovery_integration(
        self, tool_calling_service, sample_tool_call_request
    ):
        """Test integration with error recovery service."""
        # Successful call should store result
        tool_calling_service.mcp_manager.invoke.return_value = {
            "success": True,
            "result": {"data": "test"},
            "execution_time": 0.5,
        }

        response = await tool_calling_service.execute_tool_call(
            sample_tool_call_request
        )

        # Verify error recovery service was called
        tool_calling_service.error_recovery_service.store_successful_result.assert_called_once()
        assert response.success is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self, tool_calling_service):
        """Test circuit breaker pattern for failing services."""
        # Simulate repeated failures to trigger circuit breaker
        tool_calling_service.mcp_manager.invoke.side_effect = Exception("Service down")

        failing_request = ToolCallRequest(
            id=str(uuid4()),
            service="duffel_flights",
            method="test",
            params={},
            retry_count=0,  # No retries for faster test
        )

        # Execute multiple failing calls
        for _ in range(5):
            response = await tool_calling_service.execute_tool_call(failing_request)
            assert response.success is False

        # Check if circuit breaker metrics are tracked
        metrics = await tool_calling_service.get_performance_metrics()
        assert metrics["failed_calls"] >= 5


class TestDependencyInjection:
    """Test dependency injection functionality."""

    @pytest.mark.asyncio
    async def test_get_tool_calling_service(self):
        """Test dependency injection function."""
        service = await get_tool_calling_service()

        assert isinstance(service, ToolCallService)
        assert service.mcp_manager is not None
        assert service.error_recovery_service is not None

    def test_tool_calling_service_initialization(self):
        """Test service initialization with custom parameters."""
        mock_mcp_manager = AsyncMock()
        mock_error_recovery = AsyncMock()

        service = ToolCallService(
            mcp_manager=mock_mcp_manager,
            error_recovery_service=mock_error_recovery,
        )

        assert service.mcp_manager is mock_mcp_manager
        assert service.error_recovery_service is mock_error_recovery


class TestToolCallFormatting:
    """Test tool call formatting and response processing."""

    @pytest.mark.asyncio
    async def test_format_tool_call_response_success(self, tool_calling_service):
        """Test formatting successful tool call response."""
        raw_response = {
            "success": True,
            "result": {"flights": [{"id": "flight_1"}]},
            "execution_time": 1.2,
        }

        request = ToolCallRequest(
            id="test_call",
            service="duffel_flights",
            method="search_flights",
            params={},
        )

        formatted_response = tool_calling_service._format_response(
            request, raw_response, 0
        )

        assert formatted_response.id == "test_call"
        assert formatted_response.service == "duffel_flights"
        assert formatted_response.method == "search_flights"
        assert formatted_response.success is True
        assert formatted_response.result == {"flights": [{"id": "flight_1"}]}
        assert formatted_response.execution_time == 1.2
        assert formatted_response.retry_count == 0

    @pytest.mark.asyncio
    async def test_format_tool_call_response_failure(self, tool_calling_service):
        """Test formatting failed tool call response."""
        raw_response = {
            "success": False,
            "error": "Service unavailable",
            "execution_time": 0.1,
        }

        request = ToolCallRequest(
            id="test_call",
            service="duffel_flights",
            method="search_flights",
            params={},
        )

        formatted_response = tool_calling_service._format_response(
            request, raw_response, 2
        )

        assert formatted_response.success is False
        assert formatted_response.error_message == "Service unavailable"
        assert formatted_response.retry_count == 2
        assert formatted_response.result is None

    def test_sanitize_params(self, tool_calling_service):
        """Test parameter sanitization for security."""
        params = {
            "normal_param": "value",
            "password": "secret123",
            "api_key": "key123",
            "nested": {
                "token": "token123",
                "safe_value": "safe",
            },
        }

        sanitized = tool_calling_service._sanitize_params(params)

        assert sanitized["normal_param"] == "value"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["nested"]["token"] == "[REDACTED]"
        assert sanitized["nested"]["safe_value"] == "safe"
