"""Tests for the tool calling service retry logic and handlers."""

from typing import Any

import pytest

from tripsage_core.services.business.tool_calling_service import (
    ToolCallError,
    ToolCallRequest,
    ToolCallService,
)


class TestableToolCallService(ToolCallService):
    """Expose protected members needed for unit testing."""

    @property
    def handlers(self) -> dict[str, Any]:
        """Expose the internal service handler mapping."""
        return self._service_handlers

    async def execute_with_retries_public(
        self, request: ToolCallRequest, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Wrapper around `_execute_with_retries` for tests."""
        return await self._execute_with_retries(request, params)

    async def dispatch_service_call_public(
        self, service: str, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Invoke `_dispatch_service_call` in a test-friendly way."""
        return await self._dispatch_service_call(service, method, params)

    def build_duffel_passengers_public(
        self, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Return passengers using the internal Duffel helper."""
        return self._build_duffel_passengers(params)

    async def handle_airbnb_public(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Expose the Airbnb handler for unit testing."""
        return await self._handle_airbnb(method, params)

    @staticmethod
    def parse_date_like_public(value: Any, field_name: str) -> Any:
        """Proxy to the date parsing helper used internally."""
        return ToolCallService._parse_date_like(value, field_name)


@pytest.mark.asyncio
async def test_execute_with_retries_returns_handler_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return the handler result without invoking retries."""
    service = TestableToolCallService()
    calls: list[tuple[str, dict[str, Any]]] = []

    async def fake_handler(method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Fake handler for testing."""
        calls.append((method, params))
        return {"ok": True}

    service.handlers["google_maps"] = fake_handler

    request = ToolCallRequest(
        id="req-1",
        service="google_maps",
        method="geocode",
        params={"address": "NYC"},
        retry_count=1,
        timeout=None,
    )

    result = await service.execute_with_retries_public(request, request.params)

    assert result == {"ok": True}
    assert calls == [("geocode", {"address": "NYC"})]


@pytest.mark.asyncio
async def test_execute_with_retries_retries_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry once when the handler raises `asyncio.TimeoutError`."""
    service = TestableToolCallService()
    attempts = 0
    backoff_calls: list[int] = []

    async def fake_handler(method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Fake handler for testing."""
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError
        return {"ok": True}

    async def fake_backoff(attempt: int) -> None:
        """Fake backoff for testing."""
        backoff_calls.append(attempt)

    service.handlers["google_maps"] = fake_handler
    monkeypatch.setattr(service, "_apply_retry_backoff", fake_backoff)

    request = ToolCallRequest(
        id="req-2",
        service="google_maps",
        method="geocode",
        params={"address": "NYC"},
        retry_count=2,
        timeout=None,
    )

    result = await service.execute_with_retries_public(request, request.params)

    assert result == {"ok": True}
    assert attempts == 2
    assert backoff_calls == [1]


@pytest.mark.asyncio
async def test_execute_with_retries_stops_on_tool_error() -> None:
    """Stop retrying when the handler raises `ToolCallError`."""
    service = TestableToolCallService()
    attempts = 0

    async def fake_handler(method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Fake handler for testing."""
        nonlocal attempts
        attempts += 1
        raise ToolCallError("boom")

    service.handlers["google_maps"] = fake_handler

    request = ToolCallRequest(
        id="req-3",
        service="google_maps",
        method="geocode",
        params={"address": "NYC"},
        retry_count=3,
        timeout=None,
    )

    with pytest.raises(ToolCallError):
        await service.execute_with_retries_public(request, request.params)

    assert attempts == 1


@pytest.mark.asyncio
async def test_execute_with_retries_retries_on_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry once when a connection error is raised."""
    service = TestableToolCallService()
    attempts = 0

    async def fake_handler(method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Fake handler for testing."""
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ConnectionError("transient")
        return {"ok": True}

    async def fake_backoff(_: int) -> None:  # pragma: no cover - trivial awaitable
        """Fake backoff for testing."""
        return

    service.handlers["google_maps"] = fake_handler
    monkeypatch.setattr(service, "_apply_retry_backoff", fake_backoff)

    request = ToolCallRequest(
        id="req-4",
        service="google_maps",
        method="geocode",
        params={"address": "NYC"},
        retry_count=2,
        timeout=None,
    )

    result = await service.execute_with_retries_public(request, request.params)

    assert result == {"ok": True}
    assert attempts == 2


@pytest.mark.asyncio
async def test_dispatch_unsupported_service() -> None:
    """Raise an error for unsupported services."""
    service = TestableToolCallService()

    with pytest.raises(ToolCallError):
        await service.dispatch_service_call_public("unknown", "do", {})


@pytest.mark.asyncio
async def test_handle_airbnb_search_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    """Normalize Airbnb search aliases and return listings."""
    service = TestableToolCallService()
    captured: dict[str, Any] = {}

    class StubAirbnb:
        """Stub client used to intercept Airbnb calls."""

        async def search_accommodations(self, **kwargs: Any) -> list[dict[str, Any]]:
            """Fake search accommodations for testing."""
            captured.update(kwargs)
            return [{"id": "listing"}]

    monkeypatch.setattr(
        "tripsage_core.clients.airbnb_mcp_client.AirbnbMCPClient",
        StubAirbnb,
    )

    result = await service.handle_airbnb_public(
        "search_properties",
        {"location": "Berlin", "adults": 2, "children": 1},
    )

    assert result == {"listings": [{"id": "listing"}]}
    assert captured["location"] == "Berlin"
    assert captured["adults"] == 2
    assert captured["children"] == 1


def test_build_duffel_passengers_from_counts() -> None:
    """Convert passenger counts into Duffel passenger dictionaries."""
    service = TestableToolCallService()

    passengers = service.build_duffel_passengers_public(
        {"adults": "2", "children": 1, "infants": 0}
    )

    assert passengers == [
        {"type": "adult"},
        {"type": "adult"},
        {"type": "child"},
    ]


def test_parse_date_like_invalid() -> None:
    """Raise `ToolCallError` when dates cannot be parsed."""
    with pytest.raises(ToolCallError):
        TestableToolCallService.parse_date_like_public("invalid-date", "departure_date")
