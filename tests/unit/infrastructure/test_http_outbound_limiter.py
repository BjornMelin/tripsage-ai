"""Tests for aiolimiter-backed outbound HTTP utilities."""

from __future__ import annotations

import httpx
import pytest

from tripsage_core.utils.outbound import request_with_backoff


class CallState:
    """Holds state for mock transport call counts in tests."""

    def __init__(self) -> None:
        """Initialize call counter to zero."""
        self.calls = 0


def build_transport(succeed_after: int) -> tuple[httpx.MockTransport, CallState]:
    """Create MockTransport that returns 429 until a threshold is met.

    Args:
      succeed_after: Number of calls to return 429 before succeeding.

    Returns:
      A tuple of (MockTransport, CallState) for assertions.
    """
    state = CallState()

    def handler(request: httpx.Request) -> httpx.Response:
        state.calls += 1
        if state.calls <= succeed_after:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"ok": True, "calls": state.calls})

    return httpx.MockTransport(handler), state


@pytest.mark.asyncio
async def test_request_with_backoff_succeeds_after_429_short(monkeypatch):
    """Ensure wrapper retries once and returns 200 after initial 429."""
    transport, state = build_transport(succeed_after=1)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://example.com"
    ) as client:
        resp = await request_with_backoff(
            client, "GET", "https://example.com/test", max_retries=2
        )
        assert resp.status_code == 200
        assert state.calls >= 2


@pytest.mark.asyncio
async def test_request_with_backoff_gives_up_after_max_retries():
    """Ensure wrapper returns final 429 after exceeding retry cap."""
    transport, _ = build_transport(succeed_after=10)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://example.com"
    ) as client:
        resp = await request_with_backoff(
            client, "GET", "https://example.com/test", max_retries=1
        )
        # After 1 retry we still get 429
        assert resp.status_code == 429
