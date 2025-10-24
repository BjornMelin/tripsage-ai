"""Lifespan DI container smoke tests.

Verifies that the FastAPI lifespan initialises the AppServiceContainer on
``app.state.services`` and that shutdown tears services down cleanly.
"""

import pytest
from fastapi.testclient import TestClient

from tripsage.api.main import app
from tripsage.app_state import AppServiceContainer


def test_lifespan_initialises_services_container(monkeypatch: pytest.MonkeyPatch):
    """App lifespan should attach a populated services container."""

    async def _fake_init(app_):  # type: ignore[no-redef]
        services = AppServiceContainer()
        services.database_service = object()
        services.cache_service = object()
        services.google_maps_service = object()
        app_.state.services = services
        app_.state.database_service = services.database_service
        app_.state.cache_service = services.cache_service
        app_.state.google_maps_service = services.google_maps_service
        orchestrator = object()
        return services, orchestrator

    async def _fake_shutdown(app_):  # type: ignore[no-redef]
        for attr in (
            "services",
            "cache_service",
            "google_maps_service",
            "websocket_broadcaster",
            "websocket_manager",
            "database_service",
            "api_key_service",
            "mcp_service",
            "orchestrator",
        ):
            if hasattr(app_.state, attr):
                delattr(app_.state, attr)

    monkeypatch.setattr("tripsage.api.main.initialise_app_state", _fake_init)
    monkeypatch.setattr("tripsage.api.main.shutdown_app_state", _fake_shutdown)
    with TestClient(app) as client:  # noqa: F841 - side-effect: triggers startup
        services = getattr(app.state, "services", None)
        assert isinstance(services, AppServiceContainer)
        # A few critical services must be present
        assert services.database_service is not None
        assert services.cache_service is not None
        assert services.google_maps_service is not None


def test_lifespan_shutdown_clears_services(monkeypatch: pytest.MonkeyPatch):
    """After client context closes, services should be cleared from app.state."""

    async def _fake_init(app_):  # type: ignore[no-redef]
        services = AppServiceContainer()
        services.database_service = object()
        app_.state.services = services
        app_.state.database_service = services.database_service
        return services, object()

    async def _fake_shutdown(app_):  # type: ignore[no-redef]
        for attr in (
            "services",
            "database_service",
        ):
            if hasattr(app_.state, attr):
                delattr(app_.state, attr)

    monkeypatch.setattr("tripsage.api.main.initialise_app_state", _fake_init)
    monkeypatch.setattr("tripsage.api.main.shutdown_app_state", _fake_shutdown)
    with TestClient(app) as client:  # noqa: F841
        pass

    # After shutdown, the attributes should be removed by shutdown_app_state
    for attr in (
        "services",
        "cache_service",
        "google_maps_service",
        "websocket_broadcaster",
        "websocket_manager",
        "database_service",
        "api_key_service",
        "mcp_service",
        "orchestrator",
    ):
        assert not hasattr(app.state, attr)
