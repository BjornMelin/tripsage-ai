"""Unit tests for registry-backed API dependencies.

These tests validate that our FastAPI dependency providers resolve services
from the global registry rather than `app.state`, matching the Phase E design.
"""

from __future__ import annotations

from collections.abc import Generator
from types import SimpleNamespace

import pytest

from tripsage.api.core.dependencies import (
    get_activity_service_dep,
    get_cache_service_dep,
    get_maps_service_dep,
)
from tripsage.config.service_registry import (
    register_instance,
    service_registry,
)
from tripsage_core.services.business.activity_service import ActivityService


class _StubCache:
    """Stub cache service for testing."""

    async def connect(self) -> None:  # pragma: no cover - not used in tests
        """Stub connect method."""
        return

    async def disconnect(self) -> None:  # pragma: no cover - not used in tests
        """Stub disconnect method."""
        return


class _StubMaps:
    async def connect(self) -> None:  # pragma: no cover - not used in tests
        """Stub connect method."""
        return

    async def disconnect(self) -> None:  # pragma: no cover - not used in tests
        """Stub disconnect method."""
        return


@pytest.fixture(autouse=True)
def _reset_registry() -> Generator[None]:
    """Ensure a clean registry for each test by clearing internals.

    The global registry is intentionally simple; for unit tests we clear known
    keys that we register during the tests. This avoids cross-test leakage.
    """
    # before
    yield
    # after: clear registered services and instances
    for key in ["cache", "google_maps", "activity", "location"]:
        service_registry._services.pop(key, None)  # type: ignore[attr-defined]
        service_registry._instances.pop(key, None)  # type: ignore[attr-defined]
        service_registry._locks.pop(key, None)  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_get_cache_and_maps_from_registry() -> None:
    """Dependency getters resolve instances from registry."""
    register_instance("cache", _StubCache())
    register_instance("google_maps", _StubMaps())

    # The dependency functions accept a Request, but they ignore it in
    # registry-backed mode. Provide a minimal stub to satisfy the call.
    request = SimpleNamespace()

    cache = await get_cache_service_dep(request)  # type: ignore[arg-type]
    maps = await get_maps_service_dep(request)  # type: ignore[arg-type]

    assert isinstance(cache, _StubCache)
    assert isinstance(maps, _StubMaps)


@pytest.mark.asyncio
async def test_get_activity_service_via_registry_factory() -> None:
    """ActivityService dependency is provided via registry factory adapter."""
    register_instance("cache", _StubCache())
    register_instance("google_maps", _StubMaps())

    # Import here to avoid polluting other tests; registering the adapter adds
    # a factory that composes cache+maps from the registry.
    from tripsage.config.service_registry import register_api_service_adapters

    register_api_service_adapters()

    request = SimpleNamespace()
    activity = await get_activity_service_dep(request)  # type: ignore[arg-type]
    assert isinstance(activity, ActivityService)
