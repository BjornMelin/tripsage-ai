"""HTTP-related fixtures using the FastAPI app."""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tripsage.api import main
from tripsage.api.main import create_app


@pytest.fixture()
def app(monkeypatch: pytest.MonkeyPatch):
    """Return a FastAPI application instance for tests."""

    @asynccontextmanager
    async def _lifespan_stub(_app):
        """Stub the lifespan context manager."""
        yield

    monkeypatch.setattr(main, "lifespan", _lifespan_stub)

    application = create_app()
    application.dependency_overrides.clear()
    return application


@pytest_asyncio.fixture
async def async_client(app):
    """Provide an HTTPX async client bound to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
