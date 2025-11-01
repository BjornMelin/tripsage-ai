"""Tests for the tool calling service retry logic and handlers."""

from collections.abc import Awaitable, Callable
from types import MethodType
from typing import Any

import pytest

from tripsage_core.services.business.tool_calling.core import (
    HandlerContext,
    ServiceFactory,
    build_duffel_passengers,
    parse_date_like,
    validate_accommodation_params,
    validate_flight_params,
)
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

    @property
    def validation_handlers(self) -> dict[str, Any]:
        """Expose the internal validation handler mapping."""
        return self._validation_handlers

    @property
    def formatter_handlers(self) -> dict[str, Any]:
        """Expose the internal formatter handler mapping."""
        return self._formatter_handlers

    @property
    def service_cache(self) -> dict[str, Any]:
        """Expose the service cache for testing."""
        return self._factory._service_cache  # type: ignore[reportPrivateUsage]

    async def get_service_instance_for_test(self, service_name: str) -> Any:
        """Expose factory's get_service_instance for testing."""
        return await self._factory.get_service_instance(service_name)  # pylint: disable=not-callable

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

    async def validate_tool_call_public(self, request: ToolCallRequest) -> Any:
        """Invoke `validate_tool_call` for testing."""
        return await self.validate_tool_call(request)

    def override_factory_getter(
        self, getter: Callable[[ServiceFactory, str], Awaitable[Any]]
    ) -> None:
        """Override the factory getter for testing."""
        self._factory.get_service_instance = MethodType(getter, self._factory)


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
    """Test that execute_with_retries retries on timeout."""
    service = TestableToolCallService()
    attempts = 0
    backoff_calls: list[float] = []

    async def fake_handler(method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Fake handler for testing."""
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError
        return {"ok": True}

    async def fake_backoff(delay: float) -> None:
        """Fake backoff for testing."""
        backoff_calls.append(delay)

    service.handlers["google_maps"] = fake_handler
    monkeypatch.setattr(
        "tripsage_core.services.business.tool_calling_service.asyncio.sleep",
        fake_backoff,
    )

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
    assert backoff_calls == [1.0]


@pytest.mark.asyncio
async def test_execute_with_retries_stops_on_tool_error() -> None:
    """Stop retries on ToolCallError."""
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

    async def fake_backoff(_: float) -> None:  # pragma: no cover - trivial awaitable
        """Fake backoff for testing."""
        return

    service.handlers["google_maps"] = fake_handler
    monkeypatch.setattr(
        "tripsage_core.services.business.tool_calling_service.asyncio.sleep",
        fake_backoff,
    )

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
    """Dispatch an unsupported service and expect a ToolCallError."""
    service = TestableToolCallService()

    with pytest.raises(ToolCallError):
        await service.dispatch_service_call_public("unknown", "do", {})


@pytest.mark.asyncio
async def test_handle_airbnb_search_alias() -> None:
    """Test handling Airbnb search with alias parameters."""
    captured: dict[str, Any] = {}

    class StubAirbnb:
        """Stub client used to intercept Airbnb calls."""

        async def search_accommodations(self, **kwargs: Any) -> list[dict[str, Any]]:
            """Fake search accommodations for testing."""
            captured.update(kwargs)
            return [{"id": "listing"}]

    class StubFactory(ServiceFactory):
        """Provide stub service instances."""

        async def get_service_instance(self, service_name: str) -> Any:
            """Return stub instances for known services."""
            assert service_name == "airbnb"
            return StubAirbnb()

    context = HandlerContext(factory=StubFactory(), db=None, safe_tables=set())

    result = await context.handle_airbnb(
        "search_properties", {"location": "Berlin", "adults": 2, "children": 1}
    )

    assert result == {"listings": [{"id": "listing"}]}
    assert captured["location"] == "Berlin"
    assert captured["adults"] == 2
    assert captured["children"] == 1


def test_build_duffel_passengers_from_counts() -> None:
    """Build Duffel passengers from counts."""
    passengers = build_duffel_passengers({"adults": "2", "children": 1, "infants": 0})

    assert passengers == [
        {"type": "adult"},
        {"type": "adult"},
        {"type": "child"},
    ]


def test_parse_date_like_invalid() -> None:
    """Test parsing invalid date-like values."""
    with pytest.raises(ToolCallError):
        parse_date_like("invalid-date", "departure_date")


@pytest.mark.asyncio
async def test_validation_dispatcher() -> None:
    """Test that validation dispatcher routes to correct validators."""
    service = TestableToolCallService()
    assert "duffel_flights" in service.validation_handlers
    assert "airbnb" in service.validation_handlers
    assert "google_maps" in service.validation_handlers
    assert "weather" in service.validation_handlers


@pytest.mark.asyncio
async def test_formatter_dispatcher() -> None:
    """Test that formatter dispatcher routes to correct formatters."""
    service = TestableToolCallService()
    assert "duffel_flights" in service.formatter_handlers
    assert "airbnb" in service.formatter_handlers
    assert "google_maps" in service.formatter_handlers
    assert "weather" in service.formatter_handlers


@pytest.mark.asyncio
async def test_validate_flight_params_search_flights() -> None:
    """Test flight validation for search_flights method."""
    errors = await validate_flight_params(
        {"origin": "NYC", "destination": "LAX", "departure_date": "2024-01-01"},
        "search_flights",
    )
    assert len(errors) == 0

    errors = await validate_flight_params({"origin": "NYC"}, "search_flights")
    assert len(errors) > 0
    assert any("destination" in err for err in errors)


@pytest.mark.asyncio
async def test_validate_flight_params_offer_details() -> None:
    """Test flight validation for offer_details method."""
    errors = await validate_flight_params({"offer_id": "offer-123"}, "offer_details")
    assert len(errors) == 0

    errors = await validate_flight_params({}, "offer_details")
    assert len(errors) > 0
    assert any("offer_id" in err.lower() for err in errors)


@pytest.mark.asyncio
async def test_validate_flight_params_create_order() -> None:
    """Test flight validation for create_order method."""
    errors = await validate_flight_params(
        {"offer_id": "offer-123", "passengers": [{"type": "adult"}]},
        "create_order",
    )
    assert len(errors) == 0

    errors = await validate_flight_params({"offer_id": "offer-123"}, "create_order")
    assert len(errors) > 0
    assert any("passengers" in err.lower() for err in errors)


@pytest.mark.asyncio
async def test_validate_accommodation_params_with_aliases() -> None:
    """Test accommodation validation accepts parameter aliases."""
    # Test with checkin/checkout (no underscore)
    errors = await validate_accommodation_params(
        {"location": "Berlin", "checkin": "2024-01-01", "checkout": "2024-01-05"},
        "search",
    )
    assert len(errors) == 0

    # Test with check_in/check_out (with underscore)
    errors = await validate_accommodation_params(
        {"location": "Berlin", "check_in": "2024-01-01", "check_out": "2024-01-05"},
        "search",
    )
    assert len(errors) == 0

    # Test missing required fields
    errors = await validate_accommodation_params({"location": "Berlin"}, "search")
    assert len(errors) > 0


@pytest.mark.asyncio
async def test_service_factory_caching() -> None:
    """Test that service factory caches instances."""
    service = TestableToolCallService()
    assert len(service.service_cache) == 0

    async def fake_get_service_instance(self: ServiceFactory, service_name: str) -> Any:
        """Return cached sentinel per service."""
        cache = service.service_cache
        if service_name in cache:
            return cache[service_name]
        cache[service_name] = {"service": service_name}
        return cache[service_name]

    service.override_factory_getter(fake_get_service_instance)

    instance1 = await service.get_service_instance_for_test("google_maps")
    assert len(service.service_cache) == 1
    assert "google_maps" in service.service_cache

    instance2 = await service.get_service_instance_for_test("google_maps")
    assert instance1 is instance2  # Same instance cached

    instance3 = await service.get_service_instance_for_test("weather")
    assert len(service.service_cache) == 2
    assert instance3 is not instance1


@pytest.mark.asyncio
async def test_service_factory_unknown_service() -> None:
    """Test service factory raises error for unknown service."""
    service = TestableToolCallService()
    with pytest.raises(ToolCallError):
        await service.get_service_instance_for_test("unknown_service")
