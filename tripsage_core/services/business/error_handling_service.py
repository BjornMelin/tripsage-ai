"""
Error Handling Service for Phase 5 MCP Operations.

This service implements comprehensive error handling with fallback mechanisms
for MCP operations, following Phase 5 implementation patterns.
"""

import asyncio
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from tripsage_core.exceptions.exceptions import CoreTripSageError as TripSageError
from tripsage_core.infrastructure.resilience import (
    CircuitBreakerError,
    circuit_breaker,
    register_circuit_breaker,
)
from tripsage_core.mcp_abstraction.manager import MCPManager
from tripsage_core.utils.decorator_utils import with_error_handling
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for MCP operations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FallbackStrategy(Enum):
    """Fallback strategies for failed MCP operations."""

    RETRY = "retry"
    ALTERNATIVE_SERVICE = "alternative_service"
    CACHED_RESPONSE = "cached_response"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    FAIL_FAST = "fail_fast"


class MCPOperationError(TripSageError):
    """Error raised when MCP operation fails."""

    def __init__(
        self,
        message: str,
        service: str,
        method: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        retry_count: int = 0,
        original_error: Optional[Exception] = None,
    ):
        """Initialize MCP operation error.

        Args:
            message: Error message
            service: MCP service name
            method: Method that failed
            severity: Error severity level
            retry_count: Number of retries attempted
            original_error: Original exception that caused the error
        """
        super().__init__(message)
        self.service = service
        self.method = method
        self.severity = severity
        self.retry_count = retry_count
        self.original_error = original_error
        self.timestamp = time.time()


class FallbackResult(BaseModel):
    """Result of fallback operation."""

    success: bool = Field(..., description="Whether fallback succeeded")
    strategy_used: FallbackStrategy = Field(..., description="Fallback strategy used")
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Fallback result data"
    )
    error: Optional[str] = Field(default=None, description="Fallback error message")
    execution_time: float = Field(..., description="Fallback execution time")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ErrorRecoveryService:
    """
    Service for handling MCP operation errors with comprehensive fallback mechanisms.

    This service implements Phase 5 error handling patterns with multiple
    fallback strategies and graceful degradation.
    """

    def __init__(self, mcp_manager: MCPManager):
        """Initialize error recovery service.

        Args:
            mcp_manager: MCP manager instance
        """
        self.mcp_manager = mcp_manager
        self.error_history: List[MCPOperationError] = []
        self.fallback_cache: Dict[str, Any] = {}

        # Service fallback mappings
        self.service_alternatives = {
            "duffel_flights": ["amadeus_flights", "skyscanner"],
            "airbnb": ["booking_com", "expedia"],
            "google_maps": ["mapbox", "openstreetmap"],
            "weather": ["openweather", "weatherapi"],
        }

        # Initialize configurable circuit breakers for each service
        self.circuit_breakers = {}
        self._initialize_circuit_breakers()

        # Cached responses for graceful degradation
        self.degraded_responses = {
            "flights": {
                "message": "Flight search is temporarily unavailable. "
                "Please try again later.",
                "suggestions": [
                    "Check airline websites directly",
                    "Try alternative dates",
                ],
                "fallback_data": {"status": "unavailable", "service": "flights"},
            },
            "accommodations": {
                "message": "Accommodation search is temporarily "
                "unavailable. Please try again later.",
                "suggestions": [
                    "Check hotel websites directly",
                    "Try booking platforms",
                ],
                "fallback_data": {"status": "unavailable", "service": "accommodations"},
            },
            "maps": {
                "message": "Location services are temporarily unavailable.",
                "suggestions": ["Try searching for the location manually"],
                "fallback_data": {"status": "unavailable", "service": "maps"},
            },
        }

    def _initialize_circuit_breakers(self) -> None:
        """Initialize configurable circuit breakers for all services."""
        # All services that need circuit breaker protection
        services = [
            "duffel_flights",
            "amadeus_flights",
            "skyscanner",
            "airbnb",
            "booking_com",
            "expedia",
            "google_maps",
            "mapbox",
            "openstreetmap",
            "openweather",
            "weatherapi",
            "visual_crossing",
        ]

        for service in services:
            # Create circuit breaker with service-specific configuration
            breaker = circuit_breaker(
                name=f"{service}_circuit_breaker",
                failure_threshold=5,  # Open after 5 failures
                success_threshold=3,  # Close after 3 successes in half-open
                timeout=60.0,  # Wait 60s before trying half-open
                max_retries=3,  # Retry up to 3 times
                base_delay=1.0,  # Start with 1s delay
                max_delay=30.0,  # Max 30s delay
                exceptions=[Exception],  # Catch all exceptions
            )

            self.circuit_breakers[service] = breaker
            register_circuit_breaker(breaker)

        logger.info(
            f"Initialized {len(self.circuit_breakers)} configurable circuit breakers"
        )

    @with_error_handling()
    async def handle_mcp_error(
        self,
        error: Exception,
        service: str,
        method: str,
        params: Dict[str, Any],
        retry_count: int = 0,
    ) -> FallbackResult:
        """Handle MCP operation error with comprehensive fallback strategies.

        Args:
            error: Original error
            service: MCP service name
            method: Method that failed
            params: Original method parameters
            retry_count: Number of retries attempted

        Returns:
            Fallback operation result
        """
        start_time = time.time()

        try:
            # Determine error severity
            severity = self._assess_error_severity(error, service, method)

            # Log the error
            mcp_error = MCPOperationError(
                message=str(error),
                service=service,
                method=method,
                severity=severity,
                retry_count=retry_count,
                original_error=error,
            )
            self.error_history.append(mcp_error)

            logger.error(f"MCP operation failed: {service}.{method} - {str(error)}")

            # Determine fallback strategy
            strategy = self._determine_fallback_strategy(mcp_error, params)

            # Execute fallback strategy
            result = await self._execute_fallback_strategy(
                strategy, service, method, params, mcp_error
            )

            result.execution_time = time.time() - start_time
            return result

        except Exception as fallback_error:
            logger.error(f"Fallback handling failed: {str(fallback_error)}")
            return FallbackResult(
                success=False,
                strategy_used=FallbackStrategy.FAIL_FAST,
                error=f"Fallback failed: {str(fallback_error)}",
                execution_time=time.time() - start_time,
            )

    async def _execute_fallback_strategy(
        self,
        strategy: FallbackStrategy,
        service: str,
        method: str,
        params: Dict[str, Any],
        error: MCPOperationError,
    ) -> FallbackResult:
        """Execute specific fallback strategy.

        Args:
            strategy: Fallback strategy to execute
            service: Original service name
            method: Original method name
            params: Original parameters
            error: MCP operation error

        Returns:
            Fallback result
        """
        if strategy == FallbackStrategy.RETRY:
            return await self._retry_with_backoff(service, method, params, error)

        elif strategy == FallbackStrategy.ALTERNATIVE_SERVICE:
            return await self._try_alternative_service(service, method, params)

        elif strategy == FallbackStrategy.CACHED_RESPONSE:
            return await self._get_cached_response(service, method, params)

        elif strategy == FallbackStrategy.GRACEFUL_DEGRADATION:
            return await self._graceful_degradation(service, method, params)

        else:  # FAIL_FAST
            return FallbackResult(
                success=False,
                strategy_used=strategy,
                error=f"Operation failed: {error.message}",
                execution_time=0.0,
            )

    async def _retry_with_backoff(
        self,
        service: str,
        method: str,
        params: Dict[str, Any],
        error: MCPOperationError,
    ) -> FallbackResult:
        """Retry operation using configurable circuit breaker."""
        # Get the circuit breaker for this service
        breaker = self.circuit_breakers.get(service)

        if not breaker:
            # Fallback to simple retry if no circuit breaker available
            return await self._simple_retry(service, method, params, error)

        try:
            # Use circuit breaker to manage retries and failures
            @breaker
            async def protected_operation():
                return await self.mcp_manager.invoke(
                    service=service, method=method, params=params
                )

            result = await protected_operation()

            logger.info(f"Circuit breaker retry succeeded for {service}.{method}")
            return FallbackResult(
                success=True,
                strategy_used=FallbackStrategy.RETRY,
                result=result,
                execution_time=0.0,  # Will be set by caller
                metadata={
                    "circuit_breaker": breaker.name,
                    "circuit_mode": "simple"
                    if hasattr(breaker, "max_retries")
                    else "enterprise",
                },
            )

        except CircuitBreakerError as cb_error:
            logger.warning(f"Circuit breaker {service} is open: {cb_error}")
            return FallbackResult(
                success=False,
                strategy_used=FallbackStrategy.RETRY,
                error=f"Circuit breaker open: {str(cb_error)}",
                execution_time=0.0,
                metadata={
                    "circuit_breaker": breaker.name,
                    "circuit_state": "open",
                    "failure_count": cb_error.failure_count,
                },
            )

        except Exception as retry_error:
            logger.warning(
                f"Circuit breaker retry failed for {service}.{method}: {str(retry_error)}"
            )
            return FallbackResult(
                success=False,
                strategy_used=FallbackStrategy.RETRY,
                error=f"Circuit breaker retry failed: {str(retry_error)}",
                execution_time=0.0,
                metadata={
                    "circuit_breaker": breaker.name,
                    "error_type": type(retry_error).__name__,
                },
            )

    async def _simple_retry(
        self,
        service: str,
        method: str,
        params: Dict[str, Any],
        error: MCPOperationError,
    ) -> FallbackResult:
        """Simple retry fallback when no circuit breaker is available."""
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                # Wait with exponential backoff
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)

                # Retry the operation
                result = await self.mcp_manager.invoke(
                    service=service, method=method, params=params
                )

                logger.info(
                    f"Simple retry succeeded for {service}.{method} on attempt {attempt + 1}"
                )
                return FallbackResult(
                    success=True,
                    strategy_used=FallbackStrategy.RETRY,
                    result=result,
                    execution_time=0.0,  # Will be set by caller
                    metadata={
                        "retry_attempt": attempt + 1,
                        "total_retries": max_retries,
                        "retry_type": "simple",
                    },
                )

            except Exception as retry_error:
                logger.warning(
                    f"Simple retry attempt {attempt + 1} failed: {str(retry_error)}"
                )
                continue

        return FallbackResult(
            success=False,
            strategy_used=FallbackStrategy.RETRY,
            error=f"All {max_retries} simple retry attempts failed",
            execution_time=0.0,
        )

    async def _try_alternative_service(
        self, original_service: str, method: str, params: Dict[str, Any]
    ) -> FallbackResult:
        """Try alternative services for the same functionality."""
        alternatives = self.service_alternatives.get(original_service, [])

        if not alternatives:
            return FallbackResult(
                success=False,
                strategy_used=FallbackStrategy.ALTERNATIVE_SERVICE,
                error="No alternative services available",
                execution_time=0.0,
            )

        for alt_service in alternatives:
            try:
                # Check if alternative service is available
                if await self._is_service_available(alt_service):
                    # Adapt parameters for alternative service if needed
                    adapted_params = await self._adapt_params_for_service(
                        params, original_service, alt_service
                    )

                    result = await self.mcp_manager.invoke(
                        service=alt_service, method=method, params=adapted_params
                    )

                    logger.info(f"Alternative service {alt_service} succeeded")
                    return FallbackResult(
                        success=True,
                        strategy_used=FallbackStrategy.ALTERNATIVE_SERVICE,
                        result=result,
                        execution_time=0.0,
                        metadata={
                            "original_service": original_service,
                            "alternative_service": alt_service,
                        },
                    )

            except Exception as alt_error:
                logger.warning(
                    f"Alternative service {alt_service} failed: {str(alt_error)}"
                )
                continue

        return FallbackResult(
            success=False,
            strategy_used=FallbackStrategy.ALTERNATIVE_SERVICE,
            error="All alternative services failed",
            execution_time=0.0,
        )

    async def _get_cached_response(
        self, service: str, method: str, params: Dict[str, Any]
    ) -> FallbackResult:
        """Get cached response for the operation."""
        cache_key = self._generate_cache_key(service, method, params)

        if cache_key in self.fallback_cache:
            cached_result = self.fallback_cache[cache_key]

            # Check if cache is still valid (1 hour TTL)
            if time.time() - cached_result.get("timestamp", 0) < 3600:
                logger.info(f"Using cached response for {service}.{method}")
                return FallbackResult(
                    success=True,
                    strategy_used=FallbackStrategy.CACHED_RESPONSE,
                    result=cached_result["data"],
                    execution_time=0.0,
                    metadata={"cache_age": time.time() - cached_result["timestamp"]},
                )

        return FallbackResult(
            success=False,
            strategy_used=FallbackStrategy.CACHED_RESPONSE,
            error="No valid cached response available",
            execution_time=0.0,
        )

    async def _graceful_degradation(
        self, service: str, method: str, params: Dict[str, Any]
    ) -> FallbackResult:
        """Provide graceful degradation response."""
        # Map service to degradation category
        service_category = self._get_service_category(service)

        if service_category in self.degraded_responses:
            degraded_response = self.degraded_responses[service_category].copy()
            degraded_response["fallback_data"]["original_params"] = params
            degraded_response["fallback_data"]["timestamp"] = time.time()

            logger.info(f"Providing graceful degradation for {service}.{method}")
            return FallbackResult(
                success=True,
                strategy_used=FallbackStrategy.GRACEFUL_DEGRADATION,
                result=degraded_response,
                execution_time=0.0,
                metadata={"degradation_level": "service_unavailable"},
            )

        return FallbackResult(
            success=False,
            strategy_used=FallbackStrategy.GRACEFUL_DEGRADATION,
            error="No graceful degradation available",
            execution_time=0.0,
        )

    def _assess_error_severity(
        self, error: Exception, service: str, method: str
    ) -> ErrorSeverity:
        """Assess error severity based on error type and context."""
        error_type = type(error).__name__

        # Critical errors
        if any(
            keyword in str(error).lower()
            for keyword in ["authentication", "permission", "quota"]
        ):
            return ErrorSeverity.CRITICAL

        # High severity errors
        if any(keyword in error_type.lower() for keyword in ["timeout", "connection"]):
            return ErrorSeverity.HIGH

        # Medium severity errors
        if any(
            keyword in error_type.lower() for keyword in ["validation", "parameter"]
        ):
            return ErrorSeverity.MEDIUM

        # Default to low severity
        return ErrorSeverity.LOW

    def _determine_fallback_strategy(
        self, error: MCPOperationError, params: Dict[str, Any]
    ) -> FallbackStrategy:
        """Determine appropriate fallback strategy based on error characteristics."""
        # Critical errors should fail fast
        if error.severity == ErrorSeverity.CRITICAL:
            return FallbackStrategy.FAIL_FAST

        # High severity errors try alternative services first
        if error.severity == ErrorSeverity.HIGH:
            if error.service in self.service_alternatives:
                return FallbackStrategy.ALTERNATIVE_SERVICE
            return FallbackStrategy.GRACEFUL_DEGRADATION

        # Medium severity errors retry first
        if error.severity == ErrorSeverity.MEDIUM:
            if error.retry_count < 2:
                return FallbackStrategy.RETRY
            return FallbackStrategy.CACHED_RESPONSE

        # Low severity errors try cache first
        return FallbackStrategy.CACHED_RESPONSE

    async def _is_service_available(self, service: str) -> bool:
        """Check if an alternative service is available."""
        # In production, this would check service health/availability
        # For now, return True for known services
        known_services = [
            "amadeus_flights",
            "skyscanner",
            "booking_com",
            "expedia",
            "mapbox",
            "openstreetmap",
            "openweather",
            "weatherapi",
        ]
        return service in known_services

    async def _adapt_params_for_service(
        self, params: Dict[str, Any], original_service: str, target_service: str
    ) -> Dict[str, Any]:
        """Adapt parameters for different service APIs."""
        # In production, this would handle parameter mapping between services
        # For now, return original parameters
        adapted_params = params.copy()
        adapted_params["_adapted_from"] = original_service
        adapted_params["_adapted_to"] = target_service
        return adapted_params

    def _generate_cache_key(
        self, service: str, method: str, params: Dict[str, Any]
    ) -> str:
        """Generate cache key for operation."""
        import hashlib

        # Create deterministic key from service, method, and params
        key_data = f"{service}:{method}:{str(sorted(params.items()))}"
        return hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()

    def _get_service_category(self, service: str) -> str:
        """Map service name to category for degradation responses."""
        service_mapping = {
            "duffel_flights": "flights",
            "amadeus_flights": "flights",
            "skyscanner": "flights",
            "airbnb": "accommodations",
            "booking_com": "accommodations",
            "expedia": "accommodations",
            "google_maps": "maps",
            "mapbox": "maps",
            "openstreetmap": "maps",
        }
        return service_mapping.get(service, "general")

    @with_error_handling()
    async def store_successful_result(
        self, service: str, method: str, params: Dict[str, Any], result: Any
    ) -> None:
        """Store successful result in cache for future fallback use."""
        try:
            cache_key = self._generate_cache_key(service, method, params)
            self.fallback_cache[cache_key] = {
                "data": result,
                "timestamp": time.time(),
                "service": service,
                "method": method,
            }

            # Limit cache size
            if len(self.fallback_cache) > 1000:
                # Remove oldest entries
                sorted_items = sorted(
                    self.fallback_cache.items(), key=lambda x: x[1]["timestamp"]
                )
                for key, _ in sorted_items[:100]:  # Remove oldest 100
                    del self.fallback_cache[key]

        except Exception as e:
            logger.warning(f"Failed to cache result: {str(e)}")

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        if not self.error_history:
            return {"total_errors": 0, "by_service": {}, "by_severity": {}}

        by_service = {}
        by_severity = {}

        for error in self.error_history:
            # Count by service
            if error.service not in by_service:
                by_service[error.service] = 0
            by_service[error.service] += 1

            # Count by severity
            severity_key = error.severity.value
            if severity_key not in by_severity:
                by_severity[severity_key] = 0
            by_severity[severity_key] += 1

        return {
            "total_errors": len(self.error_history),
            "by_service": by_service,
            "by_severity": by_severity,
            "cache_size": len(self.fallback_cache),
        }

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get status of all circuit breakers for enterprise monitoring."""
        status = {}

        for service, breaker in self.circuit_breakers.items():
            if hasattr(breaker, "get_state"):
                # Enterprise circuit breaker
                status[service] = breaker.get_state()
            else:
                # Simple circuit breaker
                status[service] = {
                    "name": breaker.name,
                    "type": "simple",
                    "max_retries": breaker.max_retries,
                    "metrics": breaker.metrics.get_summary(),
                }

        return status

    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error handling and circuit breaker statistics."""
        error_stats = self.get_error_statistics()
        circuit_stats = self.get_circuit_breaker_status()

        return {
            "timestamp": time.time(),
            "error_handling": error_stats,
            "circuit_breakers": {
                "total_breakers": len(self.circuit_breakers),
                "status": circuit_stats,
            },
            "fallback_strategies": {
                "cache_size": len(self.fallback_cache),
                "service_alternatives": len(self.service_alternatives),
            },
        }
