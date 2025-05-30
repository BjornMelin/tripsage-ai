"""
Comprehensive tests for Error Handling Service - Phase 5 Implementation.

This test suite validates the comprehensive error handling with fallback mechanisms
for MCP operations implemented for Phase 5.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from tripsage.mcp_abstraction.manager import MCPManager
from tripsage_core.services.error_handling_service import (
    ErrorRecoveryService,
    ErrorSeverity,
    FallbackStrategy,
    MCPOperationError,
)


class TestMCPOperationError:
    """Test suite for MCPOperationError class."""

    def test_mcp_operation_error_creation(self):
        """Test creation of MCPOperationError with all parameters."""
        # Arrange
        original_error = ValueError("Original error")

        # Act
        error = MCPOperationError(
            message="Test error message",
            service="duffel_flights",
            method="search_flights",
            severity=ErrorSeverity.HIGH,
            retry_count=2,
            original_error=original_error,
        )

        # Assert
        assert error.service == "duffel_flights"
        assert error.method == "search_flights"
        assert error.severity == ErrorSeverity.HIGH
        assert error.retry_count == 2
        assert error.original_error == original_error
        assert error.timestamp > 0

    def test_mcp_operation_error_default_values(self):
        """Test MCPOperationError with default values."""
        # Act
        error = MCPOperationError(
            message="Test error",
            service="test_service",
            method="test_method",
        )

        # Assert
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.retry_count == 0
        assert error.original_error is None


class TestErrorRecoveryService:
    """Test suite for ErrorRecoveryService implementation."""

    @pytest.fixture
    def mock_mcp_manager(self):
        """Create mock MCP manager."""
        return AsyncMock(spec=MCPManager)

    @pytest.fixture
    def error_recovery_service(self, mock_mcp_manager):
        """Create ErrorRecoveryService instance."""
        return ErrorRecoveryService(mock_mcp_manager)

    @pytest.mark.asyncio
    async def test_error_severity_assessment_critical(self, error_recovery_service):
        """Test error severity assessment for critical errors."""
        # Test authentication error
        auth_error = Exception("Authentication failed")
        severity = error_recovery_service._assess_error_severity(
            auth_error, "duffel_flights", "search_flights"
        )
        assert severity == ErrorSeverity.CRITICAL

        # Test permission error
        perm_error = Exception("Permission denied")
        severity = error_recovery_service._assess_error_severity(
            perm_error, "airbnb", "search_properties"
        )
        assert severity == ErrorSeverity.CRITICAL

        # Test quota error
        quota_error = Exception("Quota exceeded")
        severity = error_recovery_service._assess_error_severity(
            quota_error, "google_maps", "geocode"
        )
        assert severity == ErrorSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_error_severity_assessment_high(self, error_recovery_service):
        """Test error severity assessment for high severity errors."""
        # Test timeout error
        timeout_error = TimeoutError("Request timed out")
        severity = error_recovery_service._assess_error_severity(
            timeout_error, "weather", "get_weather"
        )
        assert severity == ErrorSeverity.HIGH

        # Test connection error
        connection_error = ConnectionError("Connection failed")
        severity = error_recovery_service._assess_error_severity(
            connection_error, "duffel_flights", "search_flights"
        )
        assert severity == ErrorSeverity.HIGH

    @pytest.mark.asyncio
    async def test_error_severity_assessment_medium(self, error_recovery_service):
        """Test error severity assessment for medium severity errors."""
        # Test validation error
        validation_error = ValueError("Invalid parameter")
        severity = error_recovery_service._assess_error_severity(
            validation_error, "airbnb", "search_properties"
        )
        assert severity == ErrorSeverity.MEDIUM

    @pytest.mark.asyncio
    async def test_error_severity_assessment_low(self, error_recovery_service):
        """Test error severity assessment for low severity errors."""
        # Test generic error
        generic_error = Exception("Generic error")
        severity = error_recovery_service._assess_error_severity(
            generic_error, "test_service", "test_method"
        )
        assert severity == ErrorSeverity.LOW

    @pytest.mark.asyncio
    async def test_fallback_strategy_determination_critical(
        self, error_recovery_service
    ):
        """Test fallback strategy determination for critical errors."""
        # Arrange
        critical_error = MCPOperationError(
            message="Authentication failed",
            service="duffel_flights",
            method="search_flights",
            severity=ErrorSeverity.CRITICAL,
        )

        # Act
        strategy = error_recovery_service._determine_fallback_strategy(
            critical_error, {}
        )

        # Assert
        assert strategy == FallbackStrategy.FAIL_FAST

    @pytest.mark.asyncio
    async def test_fallback_strategy_determination_high_with_alternatives(
        self, error_recovery_service
    ):
        """Test fallback strategy for high severity errors with alternatives."""
        # Arrange
        high_error = MCPOperationError(
            message="Connection timeout",
            service="duffel_flights",
            method="search_flights",
            severity=ErrorSeverity.HIGH,
        )

        # Act
        strategy = error_recovery_service._determine_fallback_strategy(high_error, {})

        # Assert
        assert strategy == FallbackStrategy.ALTERNATIVE_SERVICE

    @pytest.mark.asyncio
    async def test_fallback_strategy_determination_medium_retry(
        self, error_recovery_service
    ):
        """Test fallback strategy for medium severity errors with retry."""
        # Arrange
        medium_error = MCPOperationError(
            message="Validation error",
            service="airbnb",
            method="search_properties",
            severity=ErrorSeverity.MEDIUM,
            retry_count=1,  # Less than 2, should retry
        )

        # Act
        strategy = error_recovery_service._determine_fallback_strategy(medium_error, {})

        # Assert
        assert strategy == FallbackStrategy.RETRY

    @pytest.mark.asyncio
    async def test_fallback_strategy_determination_medium_cache(
        self, error_recovery_service
    ):
        """Test fallback strategy for medium severity errors with cache."""
        # Arrange
        medium_error = MCPOperationError(
            message="Validation error",
            service="airbnb",
            method="search_properties",
            severity=ErrorSeverity.MEDIUM,
            retry_count=3,  # More than 2, should use cache
        )

        # Act
        strategy = error_recovery_service._determine_fallback_strategy(medium_error, {})

        # Assert
        assert strategy == FallbackStrategy.CACHED_RESPONSE

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success(
        self, error_recovery_service, mock_mcp_manager
    ):
        """Test successful retry with exponential backoff."""
        # Arrange
        error = MCPOperationError(
            message="Temporary error",
            service="duffel_flights",
            method="search_flights",
            severity=ErrorSeverity.MEDIUM,
        )

        # Mock successful retry on second attempt
        mock_mcp_manager.invoke.side_effect = [
            Exception("First attempt fails"),
            {"flights": ["success"]},  # Second attempt succeeds
        ]

        # Act
        result = await error_recovery_service._retry_with_backoff(
            "duffel_flights", "search_flights", {"test": "params"}, error
        )

        # Assert
        assert result.success is True
        assert result.strategy_used == FallbackStrategy.RETRY
        assert result.result == {"flights": ["success"]}
        assert result.metadata["retry_attempt"] == 2

    @pytest.mark.asyncio
    async def test_retry_with_backoff_all_failed(
        self, error_recovery_service, mock_mcp_manager
    ):
        """Test retry with all attempts failing."""
        # Arrange
        error = MCPOperationError(
            message="Persistent error",
            service="duffel_flights",
            method="search_flights",
            severity=ErrorSeverity.MEDIUM,
        )

        # Mock all retries failing
        mock_mcp_manager.invoke.side_effect = Exception("Always fails")

        # Act
        result = await error_recovery_service._retry_with_backoff(
            "duffel_flights", "search_flights", {"test": "params"}, error
        )

        # Assert
        assert result.success is False
        assert result.strategy_used == FallbackStrategy.RETRY
        assert "All 3 retry attempts failed" in result.error

    @pytest.mark.asyncio
    async def test_alternative_service_success(
        self, error_recovery_service, mock_mcp_manager
    ):
        """Test successful alternative service fallback."""
        # Arrange
        mock_mcp_manager.invoke.return_value = {"flights": ["alternative_result"]}

        with (
            patch.object(
                error_recovery_service, "_is_service_available", return_value=True
            ),
            patch.object(
                error_recovery_service,
                "_adapt_params_for_service",
                return_value={"adapted": "params"},
            ),
        ):
            # Act
            result = await error_recovery_service._try_alternative_service(
                "duffel_flights", "search_flights", {"original": "params"}
            )

            # Assert
            assert result.success is True
            assert result.strategy_used == FallbackStrategy.ALTERNATIVE_SERVICE
            assert result.result == {"flights": ["alternative_result"]}
            assert result.metadata["original_service"] == "duffel_flights"

    @pytest.mark.asyncio
    async def test_alternative_service_no_alternatives(self, error_recovery_service):
        """Test alternative service fallback with no alternatives available."""
        # Act
        result = await error_recovery_service._try_alternative_service(
            "unknown_service", "search", {}
        )

        # Assert
        assert result.success is False
        assert result.strategy_used == FallbackStrategy.ALTERNATIVE_SERVICE
        assert "No alternative services available" in result.error

    @pytest.mark.asyncio
    async def test_cached_response_success(self, error_recovery_service):
        """Test successful cached response fallback."""
        # Arrange
        cache_key = error_recovery_service._generate_cache_key(
            "duffel_flights", "search_flights", {"test": "params"}
        )

        # Pre-populate cache
        error_recovery_service.fallback_cache[cache_key] = {
            "data": {"flights": ["cached_result"]},
            "timestamp": 1000000000,  # Old but valid timestamp
            "service": "duffel_flights",
            "method": "search_flights",
        }

        with patch(
            "time.time", return_value=1000000100
        ):  # 100 seconds later (within 1 hour)
            # Act
            result = await error_recovery_service._get_cached_response(
                "duffel_flights", "search_flights", {"test": "params"}
            )

            # Assert
            assert result.success is True
            assert result.strategy_used == FallbackStrategy.CACHED_RESPONSE
            assert result.result == {"flights": ["cached_result"]}
            assert "cache_age" in result.metadata

    @pytest.mark.asyncio
    async def test_cached_response_expired(self, error_recovery_service):
        """Test cached response fallback with expired cache."""
        # Arrange
        cache_key = error_recovery_service._generate_cache_key(
            "duffel_flights", "search_flights", {"test": "params"}
        )

        # Pre-populate cache with expired entry
        error_recovery_service.fallback_cache[cache_key] = {
            "data": {"flights": ["expired_result"]},
            "timestamp": 1000000000,  # Old timestamp
            "service": "duffel_flights",
            "method": "search_flights",
        }

        with patch("time.time", return_value=1000010000):  # Much later (beyond 1 hour)
            # Act
            result = await error_recovery_service._get_cached_response(
                "duffel_flights", "search_flights", {"test": "params"}
            )

            # Assert
            assert result.success is False
            assert result.strategy_used == FallbackStrategy.CACHED_RESPONSE
            assert "No valid cached response available" in result.error

    @pytest.mark.asyncio
    async def test_graceful_degradation_success(self, error_recovery_service):
        """Test successful graceful degradation fallback."""
        # Act
        result = await error_recovery_service._graceful_degradation(
            "duffel_flights", "search_flights", {"test": "params"}
        )

        # Assert
        assert result.success is True
        assert result.strategy_used == FallbackStrategy.GRACEFUL_DEGRADATION
        assert "Flight search is temporarily unavailable" in result.result["message"]
        assert "suggestions" in result.result
        assert result.metadata["degradation_level"] == "service_unavailable"

    @pytest.mark.asyncio
    async def test_graceful_degradation_unknown_service(self, error_recovery_service):
        """Test graceful degradation for unknown service category."""
        # Act
        result = await error_recovery_service._graceful_degradation(
            "unknown_service", "unknown_method", {}
        )

        # Assert
        assert result.success is False
        assert result.strategy_used == FallbackStrategy.GRACEFUL_DEGRADATION
        assert "No graceful degradation available" in result.error

    @pytest.mark.asyncio
    async def test_handle_mcp_error_complete_flow(
        self, error_recovery_service, mock_mcp_manager
    ):
        """Test complete MCP error handling flow."""
        # Arrange
        original_error = ConnectionError("Service unavailable")

        # Mock successful alternative service
        mock_mcp_manager.invoke.return_value = {"alternative": "result"}

        with (
            patch.object(
                error_recovery_service, "_is_service_available", return_value=True
            ),
            patch.object(
                error_recovery_service,
                "_adapt_params_for_service",
                return_value={"adapted": "params"},
            ),
        ):
            # Act
            result = await error_recovery_service.handle_mcp_error(
                error=original_error,
                service="duffel_flights",
                method="search_flights",
                params={"test": "params"},
                retry_count=0,
            )

            # Assert
            assert result.success is True
            assert result.execution_time > 0
            assert len(error_recovery_service.error_history) == 1

            # Check error was logged correctly
            logged_error = error_recovery_service.error_history[0]
            assert logged_error.service == "duffel_flights"
            assert logged_error.method == "search_flights"
            assert logged_error.original_error == original_error

    @pytest.mark.asyncio
    async def test_store_successful_result(self, error_recovery_service):
        """Test storing successful results for future fallback use."""
        # Arrange
        service = "duffel_flights"
        method = "search_flights"
        params = {"origin": "NYC", "destination": "LAX"}
        result = {"flights": ["test_flight"]}

        # Act
        await error_recovery_service.store_successful_result(
            service, method, params, result
        )

        # Assert
        cache_key = error_recovery_service._generate_cache_key(service, method, params)
        assert cache_key in error_recovery_service.fallback_cache

        cached_entry = error_recovery_service.fallback_cache[cache_key]
        assert cached_entry["data"] == result
        assert cached_entry["service"] == service
        assert cached_entry["method"] == method

    @pytest.mark.asyncio
    async def test_cache_size_limiting(self, error_recovery_service):
        """Test that cache size is properly limited."""
        # Arrange - Fill cache beyond limit
        for i in range(1050):  # More than 1000 limit
            cache_key = f"test_key_{i}"
            error_recovery_service.fallback_cache[cache_key] = {
                "data": f"result_{i}",
                "timestamp": 1000000000 + i,
                "service": "test",
                "method": "test",
            }

        # Act
        await error_recovery_service.store_successful_result(
            "test_service", "test_method", {"new": "params"}, {"new": "result"}
        )

        # Assert
        assert len(error_recovery_service.fallback_cache) <= 1000

    def test_cache_key_generation(self, error_recovery_service):
        """Test cache key generation consistency."""
        # Arrange
        service = "duffel_flights"
        method = "search_flights"
        params1 = {"origin": "NYC", "destination": "LAX", "date": "2025-06-01"}
        params2 = {
            "date": "2025-06-01",
            "origin": "NYC",
            "destination": "LAX",
        }  # Same but different order

        # Act
        key1 = error_recovery_service._generate_cache_key(service, method, params1)
        key2 = error_recovery_service._generate_cache_key(service, method, params2)

        # Assert
        assert key1 == key2  # Should be the same despite different order

    def test_service_category_mapping(self, error_recovery_service):
        """Test service category mapping for degradation responses."""
        # Test known mappings
        assert (
            error_recovery_service._get_service_category("duffel_flights") == "flights"
        )
        assert (
            error_recovery_service._get_service_category("airbnb") == "accommodations"
        )
        assert error_recovery_service._get_service_category("google_maps") == "maps"

        # Test unknown service
        assert error_recovery_service._get_service_category("unknown") == "general"

    def test_error_statistics_generation(self, error_recovery_service):
        """Test error statistics generation."""
        # Arrange - Add some test errors
        error_recovery_service.error_history = [
            MCPOperationError(
                "Error 1", "duffel_flights", "search", ErrorSeverity.HIGH
            ),
            MCPOperationError(
                "Error 2", "duffel_flights", "search", ErrorSeverity.MEDIUM
            ),
            MCPOperationError("Error 3", "airbnb", "search", ErrorSeverity.LOW),
        ]

        # Add some cache entries
        error_recovery_service.fallback_cache = {"key1": {}, "key2": {}}

        # Act
        stats = error_recovery_service.get_error_statistics()

        # Assert
        assert stats["total_errors"] == 3
        assert stats["by_service"]["duffel_flights"] == 2
        assert stats["by_service"]["airbnb"] == 1
        assert stats["by_severity"]["high"] == 1
        assert stats["by_severity"]["medium"] == 1
        assert stats["by_severity"]["low"] == 1
        assert stats["cache_size"] == 2

    def test_error_statistics_empty_history(self, error_recovery_service):
        """Test error statistics with empty history."""
        # Act
        stats = error_recovery_service.get_error_statistics()

        # Assert
        assert stats["total_errors"] == 0
        assert stats["by_service"] == {}
        assert stats["by_severity"] == {}

    @pytest.mark.asyncio
    async def test_service_availability_check(self, error_recovery_service):
        """Test service availability checking."""
        # Test known services
        assert (
            await error_recovery_service._is_service_available("amadeus_flights")
            is True
        )
        assert await error_recovery_service._is_service_available("booking_com") is True

        # Test unknown service
        assert (
            await error_recovery_service._is_service_available("unknown_service")
            is False
        )

    @pytest.mark.asyncio
    async def test_parameter_adaptation(self, error_recovery_service):
        """Test parameter adaptation for different services."""
        # Arrange
        original_params = {"origin": "NYC", "destination": "LAX"}

        # Act
        adapted_params = await error_recovery_service._adapt_params_for_service(
            original_params, "duffel_flights", "amadeus_flights"
        )

        # Assert
        assert adapted_params["origin"] == "NYC"
        assert adapted_params["destination"] == "LAX"
        assert adapted_params["_adapted_from"] == "duffel_flights"
        assert adapted_params["_adapted_to"] == "amadeus_flights"


class TestErrorRecoveryIntegration:
    """Integration tests for error recovery service."""

    @pytest.mark.asyncio
    async def test_end_to_end_error_recovery_flow(self):
        """Test complete error recovery flow from error to successful fallback."""
        # Arrange
        mock_manager = AsyncMock(spec=MCPManager)
        error_service = ErrorRecoveryService(mock_manager)

        # Mock initial failure, then successful alternative
        mock_manager.invoke.side_effect = [
            ConnectionError("Primary service down"),  # Initial failure
            {"flights": ["alternative_result"]},  # Alternative service success
        ]

        with patch.object(error_service, "_is_service_available", return_value=True):
            # Act
            result = await error_service.handle_mcp_error(
                error=ConnectionError("Primary service down"),
                service="duffel_flights",
                method="search_flights",
                params={"origin": "NYC", "destination": "LAX"},
                retry_count=0,
            )

            # Assert
            assert result.success is True
            assert result.strategy_used == FallbackStrategy.ALTERNATIVE_SERVICE
            assert "alternative_result" in str(result.result)

    @pytest.mark.asyncio
    async def test_error_recovery_performance(self):
        """Test error recovery performance under load."""
        mock_manager = AsyncMock(spec=MCPManager)
        error_service = ErrorRecoveryService(mock_manager)

        # Create multiple concurrent error handling requests
        errors = [ConnectionError(f"Error {i}") for i in range(10)]

        # Mock responses
        mock_manager.invoke.return_value = {"result": "success"}

        with patch.object(error_service, "_is_service_available", return_value=True):
            # Execute concurrent error handling
            tasks = [
                error_service.handle_mcp_error(
                    error=error,
                    service="duffel_flights",
                    method="search_flights",
                    params={"test": f"params_{i}"},
                    retry_count=0,
                )
                for i, error in enumerate(errors)
            ]

            results = await asyncio.gather(*tasks)

            # Verify all succeeded
            assert len(results) == 10
            assert all(r.success for r in results)
