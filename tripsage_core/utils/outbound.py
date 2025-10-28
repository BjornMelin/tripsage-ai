"""Outbound HTTP rate limiting utilities using aiolimiter.

This module standardizes outbound throttling for HTTP clients via
``aiolimiter.AsyncLimiter`` per host, plus retry with random exponential
backoff on HTTP 429 responses. It should be used by services that
call third-party APIs.
"""

from __future__ import annotations

import asyncio
import random
import urllib.parse
from collections.abc import MutableMapping
from typing import Any

import httpx
from aiolimiter import AsyncLimiter

from tripsage_core.config import get_settings


_DEFAULT_QPM = get_settings().outbound_default_qpm

_limiters_by_loop: MutableMapping[int, MutableMapping[str, AsyncLimiter]] = {}


def _limiter_for_host(host: str) -> AsyncLimiter:
    """Get or create a limiter for a given hostname.

    Uses environment override ``OUTBOUND_QPM__<HOST>`` (uppercased, dots
    replaced with underscores) when present; otherwise falls back to
    ``OUTBOUND_QPM_DEFAULT``.

    Args:
      host: Hostname (e.g., "api.openai.com").

    Returns:
      AsyncLimiter instance scoped to the host.
    """
    import os

    loop = asyncio.get_running_loop()
    loop_id = id(loop)
    per_loop = _limiters_by_loop.setdefault(loop_id, {})
    key = host.lower()
    if key in per_loop:
        return per_loop[key]

    env_key = f"OUTBOUND_QPM__{host.upper().replace('.', '_')}"
    qpm = float(os.getenv(env_key, str(_DEFAULT_QPM)))
    # Window of 60 seconds for QPM semantics
    limiter = AsyncLimiter(max_rate=qpm, time_period=60)
    per_loop[key] = limiter
    return limiter


async def _retry_delay(attempt: int, *, max_delay: float = 30.0) -> float:
    """Compute random exponential backoff with jitter.

    Args:
      attempt: Zero-based attempt number.
      max_delay: Maximum delay cap in seconds.

    Returns:
      Delay in seconds.
    """
    base = min(2**attempt, max_delay)
    return base + random.random()


async def request_with_backoff(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_retries: int = 6,
    retry_cap_seconds: float = 30.0,
    **kwargs: Any,
) -> httpx.Response:
    """Perform an HTTP request under a per-host limiter with 429 backoff.

    Honors ``Retry-After`` (seconds) when present; otherwise uses random
    exponential backoff. Non-429 responses return immediately.

    Args:
      client: httpx.AsyncClient to use.
      method: HTTP method name (e.g., "GET").
      url: Target URL.
      max_retries: Maximum retry attempts for HTTP 429.
      retry_cap_seconds: Maximum delay for backoff.
      **kwargs: Passed through to httpx request method.

    Returns:
      The final httpx.Response.
    """
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.split("@")[-1]  # strip userinfo if any
    limiter = _limiter_for_host(host)

    attempt = 0
    while True:
        async with limiter:
            resp = await client.request(method.upper(), url, **kwargs)
        if resp.status_code != 429 or attempt >= max_retries:
            return resp

        # Honor Retry-After when provided, else use jittered exponential backoff
        retry_after = resp.headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            delay = float(retry_after)
        else:
            delay = await _retry_delay(attempt, max_delay=retry_cap_seconds)
        attempt += 1
        await asyncio.sleep(delay)
