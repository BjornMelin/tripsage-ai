"""Unit tests covering websocket infrastructure helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pytest

from tripsage_core.services.infrastructure import websocket_manager as ws_module
from tripsage_core.services.infrastructure.websocket_connection_service import (
    ExponentialBackoffException,
)
from tripsage_core.services.infrastructure.websocket_manager import (
    CircuitBreaker,
    CircuitBreakerState,
    ExponentialBackoff,
    WebSocketMessageLimits,
)


def test_message_limits_selects_specialized_values() -> None:
    """Ensure message size limits route to specialised thresholds."""
    limits = WebSocketMessageLimits(
        default_limit=1000,
        max_limit=2000,
        auth_limit=128,
        heartbeat_limit=32,
    )

    assert limits.get_limit_for_message_type("auth") == 128
    assert limits.get_limit_for_message_type("heartbeat") == 32
    assert limits.get_limit_for_message_type("pong") == 32
    assert limits.get_limit_for_message_type("chat") == 1000


def test_exponential_backoff_sequence_and_reset() -> None:
    """Backoff sequence should double until the maximum attempts trigger."""
    backoff = ExponentialBackoff(
        base_delay=1.0,
        max_delay=10.0,
        max_attempts=3,
        jitter=False,
    )

    assert math.isclose(backoff.next_attempt(), 1.0, rel_tol=1e-9)
    assert math.isclose(backoff.next_attempt(), 2.0, rel_tol=1e-9)
    assert math.isclose(backoff.next_attempt(), 4.0, rel_tol=1e-9)
    with pytest.raises(ExponentialBackoffException):
        backoff.next_attempt()

    backoff.reset()
    assert math.isclose(backoff.next_attempt(), 1.0, rel_tol=1e-9)


@dataclass
class TimeController:
    """Mutable time stub for circuit breaker tests."""

    value: float

    def __call__(self) -> float:
        """Return the current synthetic time."""
        return self.value


def test_circuit_breaker_transitions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Circuit breaker should open, recover, then reset state."""
    controller = TimeController(1_000.0)
    monkeypatch.setattr(ws_module.time, "time", controller)

    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=5)

    assert breaker.can_execute() is True
    breaker.record_failure()
    breaker.record_failure()

    assert breaker.state == CircuitBreakerState.OPEN
    assert breaker.can_execute() is False

    controller.value += 6.0
    assert breaker.can_execute() is True
    assert breaker.state == CircuitBreakerState.HALF_OPEN

    breaker.record_success()
    assert breaker.state == CircuitBreakerState.CLOSED
    assert breaker.failure_count == 0
    assert breaker.can_execute() is True
