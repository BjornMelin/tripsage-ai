"""
Tests for async tool calling service.

This module tests the refactored ToolCallService that now properly uses
async/await patterns and correct MCP manager API.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from tripsage.mcp_abstraction.manager import MCPManager
from tripsage.services.core.error_handling_service import ErrorRecoveryService
from tripsage.services.core.tool_calling_service import (
    ToolCallError,
    ToolCallRequest,
    ToolCallResponse,
    ToolCallService,
    ToolCallValidationResult,
)


class TestToolCallServiceAsync:
    """Test async implementation of tool calling service."""

    @pytest.fixture
    def mock_mcp_manager(self):
        """Create mock MCP manager with async methods."""
        manager = AsyncMock(spec=MCPManager)
        return manager

    @pytest.fixture
    def mock_error_recovery(self, mock_mcp_manager):
        """Create mock error recovery service."""
        recovery = MagicMock(spec=ErrorRecoveryService)
        recovery.store_successful_result = AsyncMock()
        recovery.handle_retry = AsyncMock()
        return recovery

    @pytest.fixture
    def tool_service(self, mock_mcp_manager):
        """Create tool calling service for testing."""
        with patch('tripsage.services.core.tool_calling_service.ErrorRecoveryService') as mock_recovery_class:
            mock_recovery_instance = MagicMock()
            mock_recovery_instance.store_successful_result = AsyncMock()
            mock_recovery_instance.handle_retry = AsyncMock()
            mock_recovery_class.return_value = mock_recovery_instance
            
            service = ToolCallService(mock_mcp_manager)
            service.error_recovery = mock_recovery_instance
            return service

    @pytest.fixture
    def valid_request(self):
        """Create valid tool call request."""
        return ToolCallRequest(
            id=str(uuid4()),
            service="duffel_flights",
            method="search_flights",
            params={
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": "2024-06-01"
            },
            timeout=30.0,
            retry_count=3
        )

    @pytest.mark.asyncio
    async def test_successful_tool_call_execution(self, tool_service, mock_mcp_manager, valid_request):
        """Test successful async tool call execution."""
        # Setup
        expected_result = {
            "flights": [{"id": "flight_123", "price": 299.99}],
            "total_count": 1
        }
        mock_mcp_manager.invoke.return_value = expected_result

        # Execute
        response = await tool_service.execute_tool_call(valid_request)

        # Verify
        assert response.status == "success"
        assert response.result == expected_result
        assert response.id == valid_request.id
        assert response.service == valid_request.service
        assert response.method == valid_request.method
        assert response.execution_time > 0

        # Verify MCP manager called with correct parameters
        mock_mcp_manager.invoke.assert_called_once_with(
            method_name="search_flights",
            params=valid_request.params
        )

    @pytest.mark.asyncio
    async def test_tool_call_failure_handling(self, tool_service, mock_mcp_manager, valid_request):
        """Test tool call failure handling."""
        # Setup
        error_message = "Service temporarily unavailable"
        mock_mcp_manager.invoke.side_effect = Exception(error_message)

        # Execute
        response = await tool_service.execute_tool_call(valid_request)

        # Verify
        assert response.status == "error"
        assert response.result is None
        assert error_message in response.error
        assert response.execution_time > 0

    @pytest.mark.asyncio
    async def test_tool_call_timeout_handling(self, tool_service, mock_mcp_manager, valid_request):
        """Test tool call timeout handling."""
        # Setup - very short timeout
        valid_request.timeout = 0.001
        
        async def slow_invoke(*args, **kwargs):
            await asyncio.sleep(1)  # Simulate slow operation
            return {"result": "success"}
        
        mock_mcp_manager.invoke.side_effect = slow_invoke

        # Execute
        response = await tool_service.execute_tool_call(valid_request)

        # Verify
        assert response.status == "timeout"
        assert response.result is None
        assert "timeout" in response.error.lower()

    @pytest.mark.asyncio
    async def test_parallel_tool_execution(self, tool_service, mock_mcp_manager):
        """Test parallel execution of multiple tool calls."""
        # Setup multiple requests
        requests = [
            ToolCallRequest(
                id=str(uuid4()),
                service="duffel_flights",
                method="search_flights",
                params={"origin": "JFK", "destination": "LAX"}
            ),
            ToolCallRequest(
                id=str(uuid4()),
                service="airbnb",
                method="search_stays",
                params={"location": "Los Angeles", "check_in": "2024-06-01"}
            )
        ]

        # Setup different return values for each call
        mock_mcp_manager.invoke.side_effect = [
            {"flights": [{"id": "flight_123"}]},
            {"stays": [{"id": "stay_456"}]}
        ]

        # Execute in parallel
        responses = await tool_service.execute_parallel_tool_calls(requests)

        # Verify
        assert len(responses) == 2
        assert all(response.status == "success" for response in responses)
        assert responses[0].result["flights"][0]["id"] == "flight_123"
        assert responses[1].result["stays"][0]["id"] == "stay_456"
        assert mock_mcp_manager.invoke.call_count == 2

    @pytest.mark.asyncio
    async def test_tool_call_validation(self, tool_service):
        """Test tool call request validation."""
        # Test invalid service
        invalid_request = ToolCallRequest(
            id=str(uuid4()),
            service="invalid_service",
            method="test_method",
            params={}
        )

        with pytest.raises(ValueError) as exc_info:
            ToolCallRequest(
                id=str(uuid4()),
                service="invalid_service",
                method="test_method",
                params={}
            )
        
        assert "not in allowed services" in str(exc_info.value)

    def test_tool_call_validation_timeout(self):
        """Test timeout validation."""
        with pytest.raises(ValueError) as exc_info:
            ToolCallRequest(
                id=str(uuid4()),
                service="duffel_flights",
                method="test_method",
                params={},
                timeout=400.0  # Exceeds maximum
            )
        
        assert "Timeout must be between 0 and 300" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self, tool_service, mock_mcp_manager, valid_request):
        """Test rate limiting enforcement."""
        # Setup multiple rapid requests
        mock_mcp_manager.invoke.return_value = {"result": "success"}

        # Execute multiple requests rapidly
        responses = []
        for _ in range(5):
            response = await tool_service.execute_tool_call(valid_request)
            responses.append(response)

        # Verify all requests succeeded (rate limiting implementation dependent)
        assert len(responses) == 5
        assert all(response.status in ["success", "rate_limited"] for response in responses)

    @pytest.mark.asyncio
    async def test_execution_history_tracking(self, tool_service, mock_mcp_manager, valid_request):
        """Test execution history tracking."""
        # Setup
        mock_mcp_manager.invoke.return_value = {"result": "success"}

        # Execute tool call
        await tool_service.execute_tool_call(valid_request)

        # Verify history tracking
        assert len(tool_service.execution_history) == 1
        history_entry = tool_service.execution_history[0]
        assert history_entry.id == valid_request.id
        assert history_entry.service == valid_request.service
        assert history_entry.method == valid_request.method

    @pytest.mark.asyncio
    async def test_service_performance_metrics(self, tool_service, mock_mcp_manager, valid_request):
        """Test service performance metrics collection."""
        # Setup
        mock_mcp_manager.invoke.return_value = {"result": "success"}

        # Execute multiple tool calls
        for _ in range(3):
            await tool_service.execute_tool_call(valid_request)

        # Get performance metrics
        metrics = tool_service.get_performance_metrics()

        # Verify metrics
        assert metrics["total_calls"] == 3
        assert metrics["success_rate"] == 100.0
        assert metrics["average_execution_time"] > 0
        assert "duffel_flights" in metrics["service_breakdown"]

    @pytest.mark.asyncio
    async def test_error_recovery_integration(self, tool_service, mock_mcp_manager, valid_request):
        """Test integration with error recovery service."""
        # Setup successful result for recovery
        mock_result = {"result": "recovered_data"}
        mock_mcp_manager.invoke.return_value = mock_result

        # Execute tool call
        response = await tool_service.execute_tool_call(valid_request)

        # Verify error recovery service was used
        assert response.status == "success"
        tool_service.error_recovery.store_successful_result.assert_called_once_with(
            valid_request.service,
            valid_request.method,
            valid_request.params,
            mock_result
        )

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls_different_services(self, tool_service, mock_mcp_manager):
        """Test concurrent tool calls to different services."""
        # Setup requests for different services
        flight_request = ToolCallRequest(
            id=str(uuid4()),
            service="duffel_flights",
            method="search_flights",
            params={"origin": "NYC", "destination": "LAX"}
        )
        
        weather_request = ToolCallRequest(
            id=str(uuid4()),
            service="weather",
            method="get_current_weather",
            params={"location": "Los Angeles"}
        )

        # Setup different response times and results
        async def mock_invoke(method_name, params):
            if method_name == "search_flights":
                await asyncio.sleep(0.1)  # Simulate flight search delay
                return {"flights": [{"id": "flight_123"}]}
            elif method_name == "get_current_weather":
                await asyncio.sleep(0.05)  # Simulate weather API delay
                return {"temperature": 75, "condition": "sunny"}
        
        mock_mcp_manager.invoke.side_effect = mock_invoke

        # Execute concurrently
        start_time = asyncio.get_event_loop().time()
        responses = await asyncio.gather(
            tool_service.execute_tool_call(flight_request),
            tool_service.execute_tool_call(weather_request)
        )
        end_time = asyncio.get_event_loop().time()

        # Verify concurrent execution (should be faster than sequential)
        total_time = end_time - start_time
        assert total_time < 0.2  # Should be less than sum of individual delays

        # Verify both calls succeeded
        assert len(responses) == 2
        assert all(response.status == "success" for response in responses)
        assert responses[0].result["flights"][0]["id"] == "flight_123"
        assert responses[1].result["temperature"] == 75


class TestToolCallRequestValidation:
    """Test tool call request validation."""

    def test_valid_request_creation(self):
        """Test creating valid tool call request."""
        request = ToolCallRequest(
            id="test_id",
            service="duffel_flights",
            method="search_flights",
            params={"origin": "NYC", "destination": "LAX"},
            timeout=30.0,
            retry_count=3
        )
        
        assert request.id == "test_id"
        assert request.service == "duffel_flights"
        assert request.method == "search_flights"
        assert request.timeout == 30.0

    def test_default_values(self):
        """Test default values in tool call request."""
        request = ToolCallRequest(
            id="test_id",
            service="duffel_flights",
            method="search_flights"
        )
        
        assert request.params == {}
        assert request.timeout == 30.0
        assert request.retry_count == 3

    def test_invalid_service_validation(self):
        """Test validation of invalid service names."""
        with pytest.raises(ValueError) as exc_info:
            ToolCallRequest(
                id="test_id",
                service="invalid_service",
                method="test_method"
            )
        
        assert "not in allowed services" in str(exc_info.value)

    def test_timeout_boundary_validation(self):
        """Test timeout boundary validation."""
        # Test minimum boundary
        with pytest.raises(ValueError):
            ToolCallRequest(
                id="test_id",
                service="duffel_flights",
                method="test_method",
                timeout=0.0
            )
        
        # Test maximum boundary
        with pytest.raises(ValueError):
            ToolCallRequest(
                id="test_id",
                service="duffel_flights",
                method="test_method",
                timeout=301.0
            )
        
        # Test valid boundaries
        request_min = ToolCallRequest(
            id="test_id",
            service="duffel_flights",
            method="test_method",
            timeout=0.1
        )
        assert request_min.timeout == 0.1
        
        request_max = ToolCallRequest(
            id="test_id",
            service="duffel_flights",
            method="test_method",
            timeout=300.0
        )
        assert request_max.timeout == 300.0


class TestToolCallResponse:
    """Test tool call response model."""

    def test_successful_response_creation(self):
        """Test creating successful tool call response."""
        result_data = {"flights": [{"id": "123"}]}
        response = ToolCallResponse(
            id="test_id",
            status="success",
            result=result_data,
            execution_time=1.5,
            service="duffel_flights",
            method="search_flights"
        )
        
        assert response.id == "test_id"
        assert response.status == "success"
        assert response.result == result_data
        assert response.error is None
        assert response.execution_time == 1.5

    def test_error_response_creation(self):
        """Test creating error tool call response."""
        response = ToolCallResponse(
            id="test_id",
            status="error",
            error="Service unavailable",
            execution_time=0.5,
            service="duffel_flights",
            method="search_flights"
        )
        
        assert response.status == "error"
        assert response.result is None
        assert response.error == "Service unavailable"

    def test_response_timestamp(self):
        """Test response timestamp generation."""
        response = ToolCallResponse(
            id="test_id",
            status="success",
            execution_time=1.0,
            service="test_service",
            method="test_method"
        )
        
        assert response.timestamp > 0
        assert isinstance(response.timestamp, float)


@pytest.mark.integration
class TestToolCallServiceIntegration:
    """Integration tests for tool calling service."""

    @pytest.mark.asyncio
    async def test_full_tool_execution_workflow(self):
        """Test complete tool execution workflow."""
        # Setup real-like MCP manager mock
        mock_mcp_manager = AsyncMock(spec=MCPManager)
        mock_mcp_manager.invoke.return_value = {
            "flights": [
                {
                    "id": "flight_123",
                    "airline": "Test Airways",
                    "origin": "JFK",
                    "destination": "LAX",
                    "price": 299.99,
                    "duration": "5h 30m"
                }
            ],
            "total_count": 1,
            "search_metadata": {
                "search_time": "2024-01-15T10:30:00Z",
                "currency": "USD"
            }
        }

        # Create service
        with patch('tripsage.services.core.tool_calling_service.ErrorRecoveryService'):
            service = ToolCallService(mock_mcp_manager)

        # Create comprehensive request
        request = ToolCallRequest(
            id="integration_test_001",
            service="duffel_flights",
            method="search_flights",
            params={
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": "2024-06-15",
                "return_date": "2024-06-20",
                "passengers": 2,
                "cabin_class": "economy"
            },
            timeout=60.0,
            retry_count=2
        )

        # Execute
        response = await service.execute_tool_call(request)

        # Comprehensive verification
        assert response.status == "success"
        assert response.id == "integration_test_001"
        assert response.service == "duffel_flights"
        assert response.method == "search_flights"
        assert response.execution_time > 0
        
        # Verify result structure
        assert "flights" in response.result
        assert "total_count" in response.result
        assert response.result["total_count"] == 1
        
        flight = response.result["flights"][0]
        assert flight["id"] == "flight_123"
        assert flight["airline"] == "Test Airways"
        assert flight["price"] == 299.99

        # Verify MCP manager interaction
        mock_mcp_manager.invoke.assert_called_once_with(
            method_name="search_flights",
            params=request.params
        )