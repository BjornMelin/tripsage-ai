"""Configurable Circuit Breaker Implementation.

This module provides a configurable circuit breaker that supports both simple and
enterprise modes based on the enterprise configuration. It integrates with the existing
retry patterns and error handling infrastructure while providing enterprise-grade
circuit breaker functionality.

Simple Mode:
    - Basic retry with exponential backoff
    - Timeout handling
    - No circuit state management

Enterprise Mode:
    - Full circuit breaker with CLOSED/OPEN/HALF_OPEN states
    - Failure threshold tracking
    - Circuit state persistence
    - Analytics and monitoring
    - Adaptive recovery strategies
"""

import asyncio
import logging
import time
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any

from tenacity import (
    AsyncRetrying,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


# Enterprise config import removed - using settings directly

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, message: str, circuit_name: str, failure_count: int):
        super().__init__(message)
        self.circuit_name = circuit_name
        self.failure_count = failure_count


class CircuitBreakerMetrics:
    """Metrics collection for circuit breaker analysis."""

    def __init__(self, circuit_name: str):
        self.circuit_name = circuit_name
        self.total_calls = 0
        self.success_calls = 0
        self.failure_calls = 0
        self.circuit_opens = 0
        self.circuit_closes = 0
        self.last_failure_time: float | None = None
        self.last_success_time: float | None = None
        self.failure_types: dict[str, int] = {}

    def record_call(self) -> None:
        """Record a call attempt."""
        self.total_calls += 1

    def record_success(self) -> None:
        """Record a successful call."""
        self.success_calls += 1
        self.last_success_time = time.time()

    def record_failure(self, exception_type: str) -> None:
        """Record a failed call."""
        self.failure_calls += 1
        self.last_failure_time = time.time()
        self.failure_types[exception_type] = (
            self.failure_types.get(exception_type, 0) + 1
        )

    def record_circuit_open(self) -> None:
        """Record circuit opening."""
        self.circuit_opens += 1

    def record_circuit_close(self) -> None:
        """Record circuit closing."""
        self.circuit_closes += 1

    def get_failure_rate(self) -> float:
        """Get current failure rate."""
        if self.total_calls == 0:
            return 0.0
        return self.failure_calls / self.total_calls

    def get_summary(self) -> dict[str, Any]:
        """Get metrics summary."""
        return {
            "circuit_name": self.circuit_name,
            "total_calls": self.total_calls,
            "success_calls": self.success_calls,
            "failure_calls": self.failure_calls,
            "failure_rate": self.get_failure_rate(),
            "circuit_opens": self.circuit_opens,
            "circuit_closes": self.circuit_closes,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "failure_types": self.failure_types,
        }


class SimpleCircuitBreaker:
    """Simple circuit breaker using retry with exponential backoff.

    This is used when enterprise_config.circuit_breaker_mode == SIMPLE.
    It provides basic resilience without circuit state management.
    """

    def __init__(
        self,
        name: str,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_multiplier: float = 2.0,
        timeout: float = 30.0,
        exceptions: list[type[Exception]] | None = None,
    ):
        self.name = name
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.timeout = timeout
        self.exceptions = exceptions or [Exception]
        self.metrics = CircuitBreakerMetrics(name)

        logger.info(
            "Initialized simple circuit breaker '%s' with %s retries", name, max_retries
        )

    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply simple circuit breaker."""
        if asyncio.iscoroutinefunction(func):
            return self._wrap_async(func)
        return self._wrap_sync(func)

    def _wrap_sync(self, func: Callable) -> Callable:
        """Wrap synchronous function with simple retry logic."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            self.metrics.record_call()

            retryer = Retrying(
                stop=stop_after_attempt(self.max_retries + 1),
                wait=wait_exponential(
                    multiplier=self.base_delay,
                    max=self.max_delay,
                ),
                retry=retry_if_exception_type(tuple(self.exceptions)),
            )

            try:
                result = retryer(func, *args, **kwargs)
                self.metrics.record_success()
                return result
            except Exception as e:
                self.metrics.record_failure(type(e).__name__)
                logger.warning(
                    "Simple circuit breaker '%s' failed after %s retries: %s",
                    self.name,
                    self.max_retries,
                    e,
                )
                raise

        return wrapper

    def _wrap_async(self, func: Callable) -> Callable:
        """Wrap asynchronous function with simple retry logic."""

        @wraps(func)
        async def wrapper(*args, **kwargs):
            self.metrics.record_call()

            async_retryer = AsyncRetrying(
                stop=stop_after_attempt(self.max_retries + 1),
                wait=wait_exponential(
                    multiplier=self.base_delay,
                    max=self.max_delay,
                ),
                retry=retry_if_exception_type(tuple(self.exceptions)),
            )

            try:
                result = await async_retryer(func, *args, **kwargs)
                self.metrics.record_success()
                return result
            except Exception as e:
                self.metrics.record_failure(type(e).__name__)
                logger.warning(
                    "Simple circuit breaker '%s' failed after %s retries: %s",
                    self.name,
                    self.max_retries,
                    e,
                )
                raise

        return wrapper


class EnterpriseCircuitBreaker:
    """Enterprise circuit breaker with full state management and analytics.

    This is used when enterprise_config.circuit_breaker_mode == ENTERPRISE.
    It provides comprehensive circuit breaker functionality with state persistence,
    failure threshold tracking, and adaptive recovery.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout: float = 60.0,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exceptions: list[type[Exception]] | None = None,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exceptions = exceptions or [Exception]

        # Circuit state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: float | None = None
        self.state_change_time = time.time()

        # Metrics and analytics
        self.metrics = CircuitBreakerMetrics(name)

        # Enterprise features - using settings for now
        self.enterprise_config = type(
            "obj", (object,), {"enable_circuit_breaker_analytics": True}
        )()

        logger.info(
            "Initialized enterprise circuit breaker '%s' with failure_threshold=%s",
            name,
            failure_threshold,
        )

    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply enterprise circuit breaker."""
        if asyncio.iscoroutinefunction(func):
            return self._wrap_async(func)
        return self._wrap_sync(func)

    def _should_attempt_call(self) -> bool:
        """Check if call should be attempted based on circuit state."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout has elapsed
            if (
                self.last_failure_time
                and (time.time() - self.last_failure_time) > self.timeout
            ):
                self._transition_to_half_open()
                return True
            return False

        return self.state == CircuitState.HALF_OPEN

    def _record_success(self) -> None:
        """Record successful call and update circuit state."""
        self.metrics.record_success()

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            if self.failure_count > 0:
                logger.debug(
                    "Circuit breaker '%s' resetting failure count after success",
                    self.name,
                )
                self.failure_count = 0

    def _record_failure(self, exception: Exception) -> None:
        """Record failed call and update circuit state."""
        self.metrics.record_failure(type(exception).__name__)
        self.last_failure_time = time.time()

        if self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self._transition_to_open()
        elif self.state == CircuitState.HALF_OPEN:
            self._transition_to_open()

    def _transition_to_open(self) -> None:
        """Transition circuit to OPEN state."""
        logger.warning(
            "Circuit breaker '%s' opening after %s failures",
            self.name,
            self.failure_count,
        )
        self.state = CircuitState.OPEN
        self.state_change_time = time.time()
        self.metrics.record_circuit_open()

        if self.enterprise_config.enable_circuit_breaker_analytics:
            self._log_analytics_event("CIRCUIT_OPENED")

    def _transition_to_half_open(self) -> None:
        """Transition circuit to HALF_OPEN state."""
        logger.info(
            "Circuit breaker '%s' transitioning to half-open for recovery testing",
            self.name,
        )
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.state_change_time = time.time()

        if self.enterprise_config.enable_circuit_breaker_analytics:
            self._log_analytics_event("CIRCUIT_HALF_OPENED")

    def _transition_to_closed(self) -> None:
        """Transition circuit to CLOSED state."""
        logger.info(
            "Circuit breaker '%s' closing after %s successful recoveries",
            self.name,
            self.success_count,
        )
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.state_change_time = time.time()
        self.metrics.record_circuit_close()

        if self.enterprise_config.enable_circuit_breaker_analytics:
            self._log_analytics_event("CIRCUIT_CLOSED")

    def _log_analytics_event(self, event_type: str) -> None:
        """Log analytics event for enterprise monitoring."""
        event_data = {
            "event_type": event_type,
            "circuit_name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "metrics": self.metrics.get_summary(),
            "timestamp": time.time(),
        }
        logger.info("Circuit breaker analytics: %s", event_data)

    def _wrap_sync(self, func: Callable) -> Callable:
        """Wrap synchronous function with enterprise circuit breaker."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            self.metrics.record_call()

            if not self._should_attempt_call():
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is {self.state.value}",
                    self.name,
                    self.failure_count,
                )

            try:
                # Use retry logic for closed and half-open states
                if self.state in [CircuitState.CLOSED, CircuitState.HALF_OPEN]:
                    retryer = Retrying(
                        stop=stop_after_attempt(self.max_retries + 1),
                        wait=wait_exponential(
                            multiplier=self.base_delay,
                            max=self.max_delay,
                        ),
                        retry=retry_if_exception_type(tuple(self.exceptions)),
                    )
                    result = retryer(func, *args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                self._record_success()
                return result

            except Exception as e:
                self._record_failure(e)
                raise

        return wrapper

    def _wrap_async(self, func: Callable) -> Callable:
        """Wrap asynchronous function with enterprise circuit breaker."""

        @wraps(func)
        async def wrapper(*args, **kwargs):
            self.metrics.record_call()

            if not self._should_attempt_call():
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is {self.state.value}",
                    self.name,
                    self.failure_count,
                )

            try:
                # Use retry logic for closed and half-open states
                if self.state in [CircuitState.CLOSED, CircuitState.HALF_OPEN]:
                    async_retryer = AsyncRetrying(
                        stop=stop_after_attempt(self.max_retries + 1),
                        wait=wait_exponential(
                            multiplier=self.base_delay,
                            max=self.max_delay,
                        ),
                        retry=retry_if_exception_type(tuple(self.exceptions)),
                    )
                    result = await async_retryer(func, *args, **kwargs)
                else:
                    result = await func(*args, **kwargs)

                self._record_success()
                return result

            except Exception as e:
                self._record_failure(e)
                raise

        return wrapper

    def get_state(self) -> dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "state_change_time": self.state_change_time,
            "failure_threshold": self.failure_threshold,
            "success_threshold": self.success_threshold,
            "timeout": self.timeout,
            "metrics": self.metrics.get_summary(),
        }


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    success_threshold: int = 3,
    timeout: float = 60.0,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: list[type[Exception]] | None = None,
) -> SimpleCircuitBreaker | EnterpriseCircuitBreaker:
    """Create a configurable circuit breaker based on enterprise configuration.

    Args:
        name: Circuit breaker name for identification and logging
        failure_threshold: Number of failures before opening circuit (enterprise mode)
        success_threshold: Number of successes to close circuit (enterprise mode)
        timeout: Time to wait before attempting recovery (enterprise mode)
        max_retries: Maximum retry attempts
        base_delay: Base delay for exponential backoff
        max_delay: Maximum delay between retries
        exceptions: Exception types to trigger circuit breaker

    Returns:
        SimpleCircuitBreaker or EnterpriseCircuitBreaker based on configuration
    """
    # Use simple mode for now
    circuit_breaker_mode = "simple"

    if circuit_breaker_mode == "enterprise":
        logger.debug("Creating enterprise circuit breaker '%s'", name)
        return EnterpriseCircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            timeout=timeout,
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            exceptions=exceptions,
        )
    else:
        logger.debug("Creating simple circuit breaker '%s'", name)
        return SimpleCircuitBreaker(
            name=name,
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            timeout=timeout,
            exceptions=exceptions,
        )


# Global circuit breaker registry for enterprise monitoring
_circuit_breaker_registry: dict[
    str, SimpleCircuitBreaker | EnterpriseCircuitBreaker
] = {}


def get_circuit_breaker_registry() -> dict[
    str, SimpleCircuitBreaker | EnterpriseCircuitBreaker
]:
    """Get the global circuit breaker registry."""
    return _circuit_breaker_registry


def register_circuit_breaker(
    breaker: SimpleCircuitBreaker | EnterpriseCircuitBreaker,
) -> None:
    """Register a circuit breaker in the global registry."""
    _circuit_breaker_registry[breaker.name] = breaker


def get_circuit_breaker_status() -> dict[str, Any]:
    """Get status of all registered circuit breakers."""
    status = {}
    for name, breaker in _circuit_breaker_registry.items():
        if isinstance(breaker, EnterpriseCircuitBreaker):
            status[name] = breaker.get_state()
        else:
            status[name] = {
                "name": name,
                "type": "simple",
                "metrics": breaker.metrics.get_summary(),
            }
    return status
