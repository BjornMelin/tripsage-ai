"""Tests for WeatherService Tenacity retry behavior."""
# pylint: disable=import-error

from __future__ import annotations

from typing import Any, cast

import httpx
import pytest
from pydantic import SecretStr

from tripsage_core.services.external_apis.weather_service import (
    WeatherService,
    WeatherServiceError,
)


class _DummyResponse:
    """Dummy response for WeatherService."""

    def __init__(self, json_data: dict[str, Any], status_code: int = 200) -> None:
        """Initialize dummy response for WeatherService."""
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """Raise for status for WeatherService."""
        if self.status_code >= 400:
            request = httpx.Request("GET", "http://example.com")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self) -> dict[str, Any]:
        """Return JSON data for WeatherService."""
        return self._json


class _DummyClient:
    """Dummy client for WeatherService."""

    def __init__(self, side_effects: list[Exception | _DummyResponse]) -> None:
        """Initialize dummy client for WeatherService."""
        self.side_effects = side_effects
        self.calls = 0

    async def get(self, url: str, params: dict[str, Any]) -> _DummyResponse:  # type: ignore[override]
        """Get for WeatherService."""
        self.calls += 1
        effect = self.side_effects.pop(0)
        if isinstance(effect, Exception):
            raise effect
        return effect

    async def aclose(self) -> None:  # pragma: no cover - cleanup helper
        """Close for WeatherService."""
        return


class _FakeSettings:
    """Fake settings for WeatherService."""

    def __init__(self) -> None:
        """Initialize fake settings for WeatherService."""
        self.openweathermap_api_key = SecretStr("k")


@pytest.mark.asyncio
async def test_weather_retries_on_timeouts_then_succeeds(monkeypatch):
    """Test that WeatherService retries on timeouts and then succeeds."""
    svc = WeatherService(settings=cast(Any, _FakeSettings()))
    # Inject dummy client
    dummy = _DummyClient(
        [
            httpx.TimeoutException("t1"),
            httpx.ConnectError("c1"),
            _DummyResponse({"ok": True}, 200),
        ]
    )
    svc._client = dummy  # type: ignore[attr-defined]
    svc._connected = True  # type: ignore[attr-defined]

    data = await svc.get_current_weather(1.0, 2.0)
    assert data == {"ok": True}
    assert dummy.calls == 3


@pytest.mark.asyncio
async def test_weather_does_not_retry_http_status_error(monkeypatch):
    """Test that WeatherService does not retry on HTTP status errors."""
    svc = WeatherService(settings=cast(Any, _FakeSettings()))
    # Raise status on first attempt
    dummy = _DummyClient([_DummyResponse({"err": True}, 429)])
    svc._client = dummy  # type: ignore[attr-defined]
    svc._connected = True  # type: ignore[attr-defined]

    with pytest.raises(WeatherServiceError):
        await svc.get_current_weather(1.0, 2.0)
    assert dummy.calls == 1


@pytest.mark.asyncio
async def test_weather_does_not_retry_404(monkeypatch):
    """Test that WeatherService does not retry on 404 errors."""
    svc = WeatherService(settings=cast(Any, _FakeSettings()))
    # 404 should not trigger retry
    dummy = _DummyClient([_DummyResponse({"message": "not found"}, 404)])
    svc._client = dummy  # type: ignore[attr-defined]
    svc._connected = True  # type: ignore[attr-defined]

    with pytest.raises(WeatherServiceError):
        await svc.get_current_weather(1.0, 2.0)
    assert dummy.calls == 1
