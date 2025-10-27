"""Security-focused tests for websocket rate limiting logic."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from tripsage_core.services.infrastructure.websocket_manager import (
    RateLimitConfig,
    RateLimiter,
)


class _StubRedis:
    """Async Redis stub implementing the required subset of commands."""

    def __init__(
        self,
        connection_counts: dict[str, int],
        session_counts: dict[str, int],
        message_response: tuple[int, str, int, int],
    ) -> None:
        self._connection_counts = connection_counts
        self._session_counts = session_counts
        self._message_response = message_response
        self.executed_commands: list[tuple[str, tuple[Any, ...]]] = []

    async def scard(self, key: str) -> int:
        """Return the cardinality for the requested set key."""
        if key.startswith("connections:user:"):
            return self._connection_counts.get(key, 0)
        if key.startswith("connections:session:"):
            return self._session_counts.get(key, 0)
        return 0

    async def execute_command(
        self, command: str, *args: Any
    ) -> tuple[int, str, int, int]:
        """Return the preconfigured message rate response."""
        self.executed_commands.append((command, args))
        return self._message_response


@pytest.mark.security
@pytest.mark.asyncio
async def test_rate_limiter_rejects_when_connection_limit_exceeded() -> None:
    """Connection checks should fail when Redis reports maximum usage."""
    user_id = uuid4()
    session_id = uuid4()
    redis = _StubRedis(
        connection_counts={f"connections:user:{user_id}": 3},
        session_counts={f"connections:session:{session_id}": 2},
        message_response=(1, "allowed", 1, 1),
    )
    config = RateLimitConfig(
        max_connections_per_user=2,
        max_connections_per_session=1,
        max_messages_per_connection_per_second=5,
        max_messages_per_user_per_minute=10,
        window_seconds=60,
    )
    limiter = RateLimiter(redis_client=cast(Any, redis), config=config)
    raw_check_connection = RateLimiter.__dict__["check_connection_limit"]
    raw_check_connection = getattr(
        raw_check_connection, "__wrapped__", raw_check_connection
    )
    check_connection_impl = cast(
        Callable[[RateLimiter, UUID, UUID | None], Awaitable[bool]],
        raw_check_connection,
    )
    allowed: bool = await check_connection_impl(limiter, user_id, session_id)

    assert allowed is False


@pytest.mark.security
@pytest.mark.asyncio
async def test_rate_limiter_reports_message_rate_exceeded() -> None:
    """Message rate checks should surface Redis gate denials."""
    user_id = uuid4()
    redis = _StubRedis(
        connection_counts={f"connections:user:{user_id}": 0},
        session_counts={},
        message_response=(0, "user_limit_exceeded", 12, 5),
    )
    config = RateLimitConfig(
        max_connections_per_user=5,
        max_connections_per_session=3,
        max_messages_per_connection_per_second=2,
        max_messages_per_user_per_minute=10,
        window_seconds=60,
    )
    limiter = RateLimiter(redis_client=cast(Any, redis), config=config)
    raw_message_rate = RateLimiter.__dict__["check_message_rate"]
    raw_message_rate = getattr(raw_message_rate, "__wrapped__", raw_message_rate)
    check_message_rate_impl = cast(
        Callable[[RateLimiter, UUID, str], Awaitable[dict[str, Any]]],
        raw_message_rate,
    )
    result: dict[str, Any] = await check_message_rate_impl(limiter, user_id, "conn-1")

    assert result["allowed"] is False
    assert result["reason"] == "user_limit_exceeded"
    assert result["remaining"] == 0
