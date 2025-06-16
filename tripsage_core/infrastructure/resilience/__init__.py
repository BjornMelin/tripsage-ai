"""TripSage Infrastructure Resilience Module.

This module provides configurable resilience patterns for the TripSage application,
including circuit breakers, retry mechanisms, and error handling strategies.

The module supports both simple and enterprise modes based on the enterprise
configuration settings, allowing for development efficiency with opt-in complexity.
"""

from tripsage_core.infrastructure.resilience.circuit_breaker import (
    CircuitBreakerError,
    CircuitState,
    EnterpriseCircuitBreaker,
    SimpleCircuitBreaker,
    circuit_breaker,
    get_circuit_breaker_registry,
    get_circuit_breaker_status,
    register_circuit_breaker,
)

__all__ = [
    # Circuit breaker classes
    "SimpleCircuitBreaker",
    "EnterpriseCircuitBreaker",
    "CircuitBreakerError",
    "CircuitState",
    # Factory function
    "circuit_breaker",
    # Registry functions
    "register_circuit_breaker",
    "get_circuit_breaker_registry",
    "get_circuit_breaker_status",
]
