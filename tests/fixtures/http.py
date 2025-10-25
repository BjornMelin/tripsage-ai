"""HTTP-related fixtures using the FastAPI app."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tripsage.api.main import create_app


@pytest.fixture(scope="session")
def app():
    """Return a FastAPI application instance for tests."""
    return create_app()


@pytest_asyncio.fixture
async def async_client(app):
    """Provide an HTTPX async client bound to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
