"""
Modern test configuration for TripSage.

Simple, clean test setup following 2025 best practices.
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

# Set test environment
os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DATABASE_URL": "https://test.supabase.co",
        "DATABASE_PUBLIC_KEY": "test-anon-key",
        "DATABASE_SERVICE_KEY": "test-service-key",
        "OPENAI_API_KEY": "test-openai-key",
        "REDIS_URL": "redis://localhost:6379/0",
    }
)


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_client():
    """Create test client with modern dependency overrides."""
    from tripsage.api.main import create_app
    from tripsage_core.config import Settings

    # Create test app
    app = create_app()

    # Mock dependencies
    async def mock_get_settings():
        return Settings(
            environment="test",
            database_url="https://test.supabase.co",
            database_public_key="test-anon-key",
            database_service_key="test-service-key",
            openai_api_key="test-openai-key",
        )

    async def mock_get_current_user_id():
        return "test-user-123"

    async def mock_db_session():
        # Return mock database session
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        return session

    # Override dependencies
    from tripsage_core.config import get_settings

    app.dependency_overrides[get_settings] = mock_get_settings

    # Create async client
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    # Cleanup
    app.dependency_overrides.clear()
