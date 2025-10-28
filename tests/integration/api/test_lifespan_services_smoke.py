"""Lifespan DI container smoke tests.

Verifies that the FastAPI lifespan initialises the AppServiceContainer on
``app.state.services`` and that shutdown tears services down cleanly.
"""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tripsage.api.main import app
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.graph import TripSageOrchestrator
from tripsage_core.services.airbnb_mcp import AirbnbMCP
from tripsage_core.services.business.api_key_service import ApiKeyService
from tripsage_core.services.external_apis import GoogleMapsService
from tripsage_core.services.infrastructure import CacheService, DatabaseService


class _StubCacheService:
    """Minimal cache stub implementing the async disconnect contract."""

    def __init__(self) -> None:
        self.disconnected = False

    async def disconnect(self) -> None:
        """Mark the cache service as disconnected without side effects."""
        self.disconnected = True


class _StubGoogleMapsService:
    """Minimal Google Maps stub with async close hook."""

    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        """Mark the service as closed without touching external APIs."""
        self.closed = True


class _StubAirbnbMCP:
    """Minimal MCP stub exposing the async shutdown method."""

    def __init__(self) -> None:
        self.shutdown_called = False

    async def shutdown(self) -> None:
        """Track when shutdown is invoked."""
        self.shutdown_called = True


def _create_stub_services() -> tuple[
    AppServiceContainer,
    CacheService,
    DatabaseService,
    GoogleMapsService,
    ApiKeyService,
    AirbnbMCP,
]:
    """Build an AppServiceContainer populated with typed stub services."""
    services = AppServiceContainer()
    cache_service = cast(CacheService, _StubCacheService())
    database_service = cast(DatabaseService, Mock(spec=DatabaseService))
    google_maps_service = cast(GoogleMapsService, _StubGoogleMapsService())
    api_key_service = cast(ApiKeyService, Mock(spec=ApiKeyService))
    mcp_service = cast(AirbnbMCP, _StubAirbnbMCP())

    services.cache_service = cache_service
    services.database_service = database_service
    services.google_maps_service = google_maps_service
    services.api_key_service = api_key_service
    services.mcp_service = mcp_service

    return (
        services,
        cache_service,
        database_service,
        google_maps_service,
        api_key_service,
        mcp_service,
    )


def _attach_stub_state(
    app_: FastAPI,
) -> tuple[AppServiceContainer, TripSageOrchestrator, dict[str, object]]:
    """Attach stubbed services and orchestrator to ``app.state``."""
    (
        services,
        cache_service,
        database_service,
        google_maps_service,
        api_key_service,
        mcp_service,
    ) = _create_stub_services()
    orchestrator = cast(TripSageOrchestrator, Mock(spec=TripSageOrchestrator))

    state_values: dict[str, object] = {
        "services": services,
        "cache_service": cache_service,
        "google_maps_service": google_maps_service,
        "database_service": database_service,
        "api_key_service": api_key_service,
        "mcp_service": mcp_service,
        "orchestrator": orchestrator,
    }

    for attr, value in state_values.items():
        setattr(app_.state, attr, value)

    return services, orchestrator, state_values


def test_lifespan_initialises_services_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """App lifespan should attach a populated services container."""
    cached_stubs: dict[str, object] = {}

    async def _fake_init(
        app_: FastAPI,
    ) -> tuple[AppServiceContainer, TripSageOrchestrator]:
        services, orchestrator, state_values = _attach_stub_state(app_)
        cached_stubs.clear()
        cached_stubs.update(state_values)
        return services, orchestrator

    monkeypatch.setattr("tripsage.api.main.initialise_app_state", _fake_init)
    close_db_mock = AsyncMock()
    monkeypatch.setattr("tripsage.app_state.close_database_service", close_db_mock)

    with TestClient(app):
        services = getattr(app.state, "services", None)
        assert isinstance(services, AppServiceContainer)

        assert services.database_service is not None
        assert services.cache_service is not None
        assert services.google_maps_service is not None
        assert services.api_key_service is not None
        assert services.mcp_service is not None
        assert getattr(app.state, "orchestrator", None) is not None

        assert app.state.database_service is services.database_service
        assert app.state.cache_service is services.cache_service
        assert app.state.google_maps_service is services.google_maps_service
        assert app.state.api_key_service is services.api_key_service
        assert app.state.mcp_service is services.mcp_service

    assert close_db_mock.await_count == 1
    cache_stub = cast(_StubCacheService, cached_stubs["cache_service"])
    maps_stub = cast(_StubGoogleMapsService, cached_stubs["google_maps_service"])
    mcp_stub = cast(_StubAirbnbMCP, cached_stubs["mcp_service"])
    assert cache_stub.disconnected
    assert maps_stub.closed
    assert mcp_stub.shutdown_called


def test_lifespan_shutdown_clears_services(monkeypatch: pytest.MonkeyPatch) -> None:
    """After client context closes, services should be cleared from app.state."""
    state_attrs: list[str] = []
    cached_stubs: dict[str, object] = {}

    async def _fake_init(
        app_: FastAPI,
    ) -> tuple[AppServiceContainer, TripSageOrchestrator]:
        services, orchestrator, state_values = _attach_stub_state(app_)
        state_attrs[:] = list(state_values.keys())
        cached_stubs.clear()
        cached_stubs.update(state_values)
        return services, orchestrator

    monkeypatch.setattr("tripsage.api.main.initialise_app_state", _fake_init)
    close_db_mock = AsyncMock()
    monkeypatch.setattr("tripsage.app_state.close_database_service", close_db_mock)

    with TestClient(app):
        assert isinstance(app.state.services, AppServiceContainer)
        assert isinstance(app.state.cache_service, _StubCacheService)
        assert isinstance(app.state.google_maps_service, _StubGoogleMapsService)
        assert isinstance(app.state.mcp_service, _StubAirbnbMCP)

    for attr in state_attrs:
        assert not hasattr(app.state, attr)
    assert close_db_mock.await_count == 1
    cache_stub = cast(_StubCacheService, cached_stubs["cache_service"])
    maps_stub = cast(_StubGoogleMapsService, cached_stubs["google_maps_service"])
    mcp_stub = cast(_StubAirbnbMCP, cached_stubs["mcp_service"])
    assert cache_stub.disconnected
    assert maps_stub.closed
    assert mcp_stub.shutdown_called
