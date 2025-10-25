"""HTTP-related fixtures using the FastAPI app."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tripsage.api import main
from tripsage.api.main import create_app


@pytest.fixture()
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """Return a FastAPI application instance prepared for tests.

    Args:
        monkeypatch: Pytest monkeypatch helper for altering module attributes.

    Returns:
        FastAPI: Configured application with a stubbed lifespan and cleared overrides.
    """
    def _noop_setup_otel(**_: object) -> None:
        """Disable OpenTelemetry initialization for tests."""
        return

    monkeypatch.setattr(main, "setup_otel", _noop_setup_otel)

    @asynccontextmanager
    async def _lifespan_stub(_app: FastAPI) -> AsyncIterator[None]:
        """Stub the lifespan context manager to avoid side effects.

        Args:
            _app: The FastAPI application under test.

        Yields:
            None: Indicates the lifespan context executed without side effects.
        """
        yield

    monkeypatch.setattr(main, "lifespan", _lifespan_stub)

    application = create_app()
    application.dependency_overrides.clear()
    return application


@pytest_asyncio.fixture
async def async_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Provide an HTTPX async client bound to the FastAPI test app.

    Args:
        app: FastAPI application fixture configured for tests.

    Yields:
        AsyncIterator[AsyncClient]: Async HTTP client configured with ASGITransport.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
