"""
Comprehensive tests for Tool Calling Service - Phase 5 Implementation.

This test suite validates the structured tool calling patterns, error handling,
and MCP integration implemented for Phase 5.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from tripsage.mcp_abstraction.manager import MCPManager
from tripsage.services.error_handling_service import (
    FallbackResult,
    FallbackStrategy,
)
from tripsage.services.tool_calling_service import (
    ToolCallRequest,
    ToolCallResponse,
    ToolCallService,
    ToolCallValidationResult,
)


class TestToolCallService:
    """Test suite for ToolCallService Phase 5 implementation."""

    @pytest.fixture
    def mock_mcp_manager(self):
        """Create mock MCP manager."""
        mock_manager = AsyncMock(spec=MCPManager)
        return mock_manager

    @pytest.fixture
    def tool_call_service(self, mock_mcp_manager):
        """Create ToolCallService instance with mocked dependencies."""
        return ToolCallService(mock_mcp_manager)

    @pytest.fixture
    def sample_tool_request(self):
        """Create sample tool call request."""
        return ToolCallRequest(
            id="test_call_1",
            service="duffel_flights",
            method="search_flights",
            params={
                "origin": "NYC",
                "destination": "LAX",
                "departure_date": "2025-06-01",
            },
            timeout=30.0,
            retry_count=3,
        )

    @pytest.mark.asyncio
    async def test_successful_tool_call_execution(
        self, tool_call_service, sample_tool_request, mock_mcp_manager
    ):
        """Test successful tool call execution with structured response."""
        # Arrange
        expected_result = {
            "flights": [
                {"airline": "Delta", "price": 250, "duration": "5h 30m"},
                {"airline": "American", "price": 275, "duration": "5h 45m"},
            ]
        }
        mock_mcp_manager.invoke.return_value = expected_result

        # Act
        response = await tool_call_service.execute_tool_call(sample_tool_request)

        # Assert
        assert isinstance(response, ToolCallResponse)
        assert response.status == "success"
        assert response.result == expected_result
        assert response.service == "duffel_flights"
        assert response.method == "search_flights"
        assert response.execution_time > 0

        # Verify MCP manager was called correctly
        mock_mcp_manager.invoke.assert_called_once_with(
            service="duffel_flights",
            method="search_flights",
            params=sample_tool_request.params,
        )

    @pytest.mark.asyncio
    async def test_tool_call_validation_success(
        self, tool_call_service, sample_tool_request
    ):
        """Test tool call validation for valid requests."""
        # Act
        validation_result = await tool_call_service.validate_tool_call(
            sample_tool_request
        )

        # Assert
        assert isinstance(validation_result, ToolCallValidationResult)
        assert validation_result.is_valid is True
        assert len(validation_result.errors) == 0
        assert validation_result.sanitized_params is not None

    @pytest.mark.asyncio
    async def test_tool_call_validation_invalid_service(self):
        """Test tool call validation with invalid service."""
        # Arrange
        invalid_request = ToolCallRequest(
            id="test_call_invalid",
            service="invalid_service",
            method="search",
            params={},
        )

        # Act & Assert
        with pytest.raises(ValueError, match="not in allowed services"):
            await ToolCallService(AsyncMock()).validate_tool_call(invalid_request)

    @pytest.mark.asyncio
    async def test_tool_call_validation_missing_required_params(
        self, tool_call_service
    ):
        """Test validation failure for missing required parameters."""
        # Arrange
        invalid_request = ToolCallRequest(
            id="test_call_missing_params",
            service="duffel_flights",
            method="search_flights",
            params={},  # Missing required parameters
        )

        # Act
        validation_result = await tool_call_service.validate_tool_call(invalid_request)

        # Assert
        assert validation_result.is_valid is False
        assert len(validation_result.errors) > 0
        assert any(
            "Missing required field" in error for error in validation_result.errors
        )

    @pytest.mark.asyncio
    async def test_tool_call_with_error_recovery(
        self, tool_call_service, sample_tool_request, mock_mcp_manager
    ):
        """Test tool call execution with error recovery fallback."""
        # Arrange
        mock_mcp_manager.invoke.side_effect = Exception(
            "Service temporarily unavailable"
        )

        # Mock error recovery to return successful fallback
        fallback_result = FallbackResult(
            success=True,
            strategy_used=FallbackStrategy.CACHED_RESPONSE,
            result={"cached": True, "flights": []},
            execution_time=0.5,
        )

        with patch.object(
            tool_call_service.error_recovery,
            "handle_mcp_error",
            return_value=fallback_result,
        ):
            # Act
            response = await tool_call_service.execute_tool_call(sample_tool_request)

            # Assert
            assert response.status == "success"
            assert response.result == {"cached": True, "flights": []}
            assert "cached" in response.result

    @pytest.mark.asyncio
    async def test_parallel_tool_calls_execution(
        self, tool_call_service, mock_mcp_manager
    ):
        """Test parallel execution of multiple tool calls."""
        # Arrange
        requests = [
            ToolCallRequest(
                id="call_1",
                service="duffel_flights",
                method="search_flights",
                params={"origin": "NYC", "destination": "LAX"},
            ),
            ToolCallRequest(
                id="call_2",
                service="google_maps",
                method="geocode",
                params={"address": "New York City"},
            ),
            ToolCallRequest(
                id="call_3",
                service="weather",
                method="get_weather",
                params={"location": "Los Angeles"},
            ),
        ]

        # Mock successful responses
        mock_mcp_manager.invoke.side_effect = [
            {"flights": ["flight1", "flight2"]},
            {"coordinates": {"lat": 40.7128, "lng": -74.0060}},
            {"temperature": 72, "condition": "sunny"},
        ]

        # Act
        responses = await tool_call_service.execute_parallel_tool_calls(requests)

        # Assert
        assert len(responses) == 3
        assert all(isinstance(r, ToolCallResponse) for r in responses)
        assert all(r.status == "success" for r in responses)

        # Verify all calls were made
        assert mock_mcp_manager.invoke.call_count == 3

    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self, tool_call_service):
        """Test that rate limiting is properly enforced."""
        # Arrange
        service = "test_service"

        # Fill up the rate limit
        for _ in range(10):  # Max 10 calls per minute per service
            await tool_call_service._log_tool_call(service)

        # Act
        is_within_limit = await tool_call_service._check_rate_limit(service)

        # Assert
        assert is_within_limit is False

    @pytest.mark.asyncio
    async def test_tool_result_formatting_flights(self, tool_call_service):
        """Test formatting of flight search results for chat display."""
        # Arrange
        flight_response = ToolCallResponse(
            id="test_flight_call",
            status="success",
            result={
                "flights": [
                    {"airline": "Delta", "price": 250},
                    {"airline": "American", "price": 275},
                ]
            },
            execution_time=1.5,
            service="duffel_flights",
            method="search_flights",
        )

        # Act
        formatted = await tool_call_service.format_tool_result_for_chat(flight_response)

        # Assert
        assert formatted["type"] == "flights"
        assert formatted["title"] == "Flight Search Results"
        assert "book" in formatted["actions"]
        assert "compare" in formatted["actions"]
        assert "save" in formatted["actions"]

    @pytest.mark.asyncio
    async def test_tool_result_formatting_accommodations(self, tool_call_service):
        """Test formatting of accommodation search results for chat display."""
        # Arrange
        accommodation_response = ToolCallResponse(
            id="test_hotel_call",
            status="success",
            result={
                "properties": [
                    {"name": "Hotel A", "price": 150},
                    {"name": "Hotel B", "price": 200},
                ]
            },
            execution_time=2.0,
            service="airbnb",
            method="search_properties",
        )

        # Act
        formatted = await tool_call_service.format_tool_result_for_chat(
            accommodation_response
        )

        # Assert
        assert formatted["type"] == "accommodations"
        assert formatted["title"] == "Accommodation Options"
        assert "book" in formatted["actions"]
        assert "favorite" in formatted["actions"]

    @pytest.mark.asyncio
    async def test_error_response_handling(
        self, tool_call_service, sample_tool_request, mock_mcp_manager
    ):
        """Test proper error response handling when all recovery fails."""
        # Arrange
        mock_mcp_manager.invoke.side_effect = Exception("Critical error")

        # Mock error recovery to fail
        fallback_result = FallbackResult(
            success=False,
            strategy_used=FallbackStrategy.FAIL_FAST,
            result=None,
            error="All recovery strategies failed",
            execution_time=1.0,
        )

        with patch.object(
            tool_call_service.error_recovery,
            "handle_mcp_error",
            return_value=fallback_result,
        ):
            # Act
            response = await tool_call_service.execute_tool_call(sample_tool_request)

            # Assert
            assert response.status == "error"
            assert "Tool call failed after error recovery" in response.error

    @pytest.mark.asyncio
    async def test_timeout_handling(self, tool_call_service, mock_mcp_manager):
        """Test timeout handling for long-running operations."""
        # Arrange
        timeout_request = ToolCallRequest(
            id="timeout_test",
            service="duffel_flights",
            method="search_flights",
            params={"origin": "NYC", "destination": "LAX"},
            timeout=0.1,  # Very short timeout
        )

        # Mock a slow operation
        async def slow_operation(*args, **kwargs):
            await asyncio.sleep(0.5)  # Longer than timeout
            return {"result": "data"}

        mock_mcp_manager.invoke.side_effect = slow_operation

        # Act
        response = await tool_call_service.execute_tool_call(timeout_request)

        # Assert
        assert response.status == "timeout"
        assert "timed out" in response.error

    @pytest.mark.asyncio
    async def test_execution_history_tracking(
        self, tool_call_service, sample_tool_request, mock_mcp_manager
    ):
        """Test that execution history is properly tracked."""
        # Arrange
        mock_mcp_manager.invoke.return_value = {"result": "test"}

        # Act
        await tool_call_service.execute_tool_call(sample_tool_request)
        history = await tool_call_service.get_execution_history(limit=10)

        # Assert
        assert len(history) == 1
        assert history[0].id == sample_tool_request.id
        assert history[0].service == sample_tool_request.service

    @pytest.mark.asyncio
    async def test_error_statistics_generation(self, tool_call_service):
        """Test generation of error statistics and monitoring data."""
        # Arrange - Add some mock execution history
        tool_call_service.execution_history = [
            ToolCallResponse(
                id="call_1",
                status="success",
                result={},
                execution_time=1.0,
                service="test",
                method="test",
            ),
            ToolCallResponse(
                id="call_2",
                status="error",
                result=None,
                execution_time=0.5,
                service="test",
                method="test",
                error="Test error",
            ),
            ToolCallResponse(
                id="call_3",
                status="timeout",
                result=None,
                execution_time=30.0,
                service="test",
                method="test",
                error="Timeout",
            ),
        ]

        # Act
        stats = await tool_call_service.get_error_statistics()

        # Assert
        assert "tool_calling_stats" in stats
        tool_stats = stats["tool_calling_stats"]
        assert tool_stats["total_calls"] == 3
        assert tool_stats["success_rate"] == 1 / 3
        assert tool_stats["error_rate"] == 1 / 3
        assert tool_stats["timeout_rate"] == 1 / 3
        assert tool_stats["average_execution_time"] > 0

    def test_tool_call_request_validation(self):
        """Test ToolCallRequest validation for edge cases."""
        # Test invalid timeout
        with pytest.raises(ValueError, match="Timeout must be between"):
            ToolCallRequest(
                id="test",
                service="duffel_flights",
                method="search",
                params={},
                timeout=-1.0,  # Invalid negative timeout
            )

        # Test timeout too large
        with pytest.raises(ValueError, match="Timeout must be between"):
            ToolCallRequest(
                id="test",
                service="duffel_flights",
                method="search",
                params={},
                timeout=500.0,  # Too large
            )

    @pytest.mark.asyncio
    async def test_parameter_sanitization(self, tool_call_service):
        """Test that parameters are properly sanitized."""
        # Arrange
        params = {
            "location": "<script>alert('xss')</script>New York",
            "user_input": "  Normal input  ",
            "numeric_param": 123,
        }

        # Act
        sanitized = await tool_call_service._sanitize_params(params)

        # Assert
        assert (
            sanitized["location"] == "scriptalert('xss')/scriptNew York"
        )  # HTML removed
        assert sanitized["user_input"] == "Normal input"  # Trimmed
        assert sanitized["numeric_param"] == 123  # Unchanged

    @pytest.mark.asyncio
    async def test_service_specific_validation(self, tool_call_service):
        """Test service-specific parameter validation."""
        # Test flight validation
        flight_params = {"origin": "NYC"}  # Missing required fields
        errors = await tool_call_service._validate_flight_params(flight_params)
        assert len(errors) >= 2  # Missing destination and departure_date

        # Test accommodation validation
        hotel_params = {"location": "NYC"}  # Missing check_in and check_out
        errors = await tool_call_service._validate_accommodation_params(hotel_params)
        assert len(errors) >= 2

        # Test maps validation
        maps_params = {}  # Missing address or location
        errors = await tool_call_service._validate_maps_params(maps_params)
        assert len(errors) >= 1

        # Test weather validation
        weather_params = {}  # Missing location
        errors = await tool_call_service._validate_weather_params(weather_params)
        assert len(errors) >= 1


class TestToolCallIntegration:
    """Integration tests for tool calling with actual MCP patterns."""

    @pytest.mark.asyncio
    async def test_end_to_end_flight_search_flow(self):
        """Test complete flight search flow from request to formatted response."""
        # This would be an integration test with actual MCP manager
        # For now, we'll test the flow with mocks

        mock_manager = AsyncMock(spec=MCPManager)
        mock_manager.invoke.return_value = {
            "offers": [
                {
                    "id": "offer_1",
                    "total_amount": "250.00",
                    "slices": [{"origin": "NYC", "destination": "LAX"}],
                }
            ]
        }

        tool_service = ToolCallService(mock_manager)

        request = ToolCallRequest(
            id="integration_test",
            service="duffel_flights",
            method="search_flights",
            params={
                "origin": "NYC",
                "destination": "LAX",
                "departure_date": "2025-06-01",
            },
        )

        # Execute the full flow
        response = await tool_service.execute_tool_call(request)
        formatted = await tool_service.format_tool_result_for_chat(response)

        # Verify end-to-end flow
        assert response.status == "success"
        assert formatted["type"] == "flights"
        assert "offers" in response.result

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls_stress_test(self):
        """Stress test for concurrent tool call execution."""
        mock_manager = AsyncMock(spec=MCPManager)
        mock_manager.invoke.return_value = {"test": "result"}

        tool_service = ToolCallService(mock_manager)

        # Create 20 concurrent requests
        requests = [
            ToolCallRequest(
                id=f"concurrent_test_{i}",
                service="duffel_flights",
                method="search_flights",
                params={"origin": "NYC", "destination": "LAX"},
            )
            for i in range(20)
        ]

        # Execute all concurrently
        responses = await tool_service.execute_parallel_tool_calls(requests)

        # Verify all completed successfully
        assert len(responses) == 20
        assert all(r.status == "success" for r in responses)
        assert len(set(r.id for r in responses)) == 20  # All unique IDs
