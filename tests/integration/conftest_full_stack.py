"""
Configuration for full stack integration tests.

This module provides fixtures and setup for comprehensive integration testing
with real database and cache dependencies.
"""

import os
import uuid
from typing import Any
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as redis
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from tripsage.api.main import app
from tripsage_core.config import get_settings

@pytest.fixture(scope="session")
def integration_test_settings():
    """Create settings for integration tests."""
    # Override with test-specific values
    test_env = {
        "ENVIRONMENT": "integration_testing",
        "DEBUG": "True",
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "DATABASE_PUBLIC_KEY": "test-public-key-for-integration",
        "DATABASE_SERVICE_KEY": "test-service-key-for-integration",
        "DATABASE_JWT_SECRET": "test-jwt-secret-for-integration-testing-only",
        "SECRET_KEY": "test-application-secret-key-for-integration-testing-only",
        "REDIS_URL": os.getenv("TEST_REDIS_URL", "redis://localhost:6379/15"),
        "REDIS_PASSWORD": "",
        "OPENAI_API_KEY": "sk-test-integration-key",
        "WEATHER_API_KEY": "test-weather-integration-key",
        "GOOGLE_MAPS_API_KEY": "test-maps-integration-key",
    }

    # Set environment variables
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    try:
        settings = get_settings()
        yield settings
    finally:
        # Restore original environment
        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value

@pytest.fixture(scope="session")
async def integration_redis():
    """Create Redis connection for integration tests."""
    try:
        redis_client = redis.from_url(
            os.getenv("TEST_REDIS_URL", "redis://localhost:6379/15"),
            decode_responses=True,
        )
        await redis_client.ping()

        # Clean up any existing test data
        await redis_client.flushdb()

        yield redis_client

        # Clean up after tests
        await redis_client.flushdb()
        await redis_client.close()

    except Exception as e:
        # Fallback to mock for CI environments without Redis
        print(f"Redis not available, using mock: {e}")
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.flushdb.return_value = True
        mock_redis.close.return_value = None
        yield mock_redis

@pytest.fixture(scope="session")
async def integration_db_engine():
    """Create database engine for integration tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    # Create full schema
    async with engine.begin() as conn:
        # Users table
        await conn.execute(
            text("""
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE,
                full_name TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                is_active BOOLEAN DEFAULT TRUE,
                is_verified BOOLEAN DEFAULT FALSE
            )
        """)
        )

        # API Keys table
        await conn.execute(
            text("""
            CREATE TABLE api_keys (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                service TEXT NOT NULL,
                encrypted_key TEXT NOT NULL,
                description TEXT,
                is_valid BOOLEAN DEFAULT TRUE,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                expires_at TEXT,
                last_used TEXT,
                last_validated TEXT,
                usage_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        )

        # API Key Usage Logs table
        await conn.execute(
            text("""
            CREATE TABLE api_key_usage_logs (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                key_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                service TEXT NOT NULL,
                operation TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                timestamp TEXT DEFAULT (datetime('now')),
                response_time REAL,
                error_message TEXT,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (key_id) REFERENCES api_keys (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        )

        # Audit logs table
        await conn.execute(
            text("""
            CREATE TABLE audit_logs (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                event_type TEXT NOT NULL,
                outcome TEXT NOT NULL,
                user_id TEXT,
                key_id TEXT,
                service TEXT,
                ip_address TEXT,
                message TEXT,
                timestamp TEXT DEFAULT (datetime('now')),
                details TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (key_id) REFERENCES api_keys (id)
            )
        """)
        )

        # Indexes for performance
        await conn.execute(
            text("CREATE INDEX idx_api_keys_user_id ON api_keys(user_id)")
        )
        await conn.execute(
            text("CREATE INDEX idx_api_keys_service ON api_keys(service)")
        )
        await conn.execute(
            text("CREATE INDEX idx_usage_logs_key_id ON api_key_usage_logs(key_id)")
        )
        await conn.execute(
            text(
                "CREATE INDEX idx_usage_logs_timestamp ON api_key_usage_logs(timestamp)"
            )
        )
        await conn.execute(
            text("CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp)")
        )

    yield engine
    await engine.dispose()

@pytest.fixture
async def integration_db_session(
    integration_db_engine,
) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for each test."""
    async with AsyncSession(integration_db_engine) as session:
        yield session
        # Clean up after each test
        await session.rollback()

@pytest.fixture
async def test_user_factory(integration_db_session):
    """Factory for creating test users."""

    async def create_user(
        email: str = None,
        username: str = None,
        full_name: str = None,
        is_active: bool = True,
        is_verified: bool = True,
    ) -> dict[str, Any]:
        user_id = str(uuid.uuid4())
        user_data = {
            "id": user_id,
            "email": email or f"test_{user_id[:8]}@example.com",
            "username": username or f"testuser_{user_id[:8]}",
            "full_name": full_name or f"Test User {user_id[:8]}",
            "is_active": is_active,
            "is_verified": is_verified,
        }

        await integration_db_session.execute(
            text("""
                INSERT INTO users (id, email, username, full_name, is_active,
                                   is_verified)
                VALUES (:id, :email, :username, :full_name, :is_active, :is_verified)
            """),
            user_data,
        )
        await integration_db_session.commit()

        return user_data

    return create_user

@pytest.fixture
async def authenticated_test_client(test_user_factory):
    """Create TestClient with authenticated user."""
    user = await test_user_factory()

    with patch(
        "tripsage.api.core.dependencies.get_principal_id", return_value=user["id"]
    ):
        with patch("tripsage.api.core.dependencies.require_principal") as mock_auth:
            mock_principal = MagicMock()
            mock_principal.user_id = user["id"]
            mock_principal.email = user["email"]
            mock_auth.return_value = mock_principal

            client = TestClient(app)
            client.user = user  # Attach user data for test access
            yield client

@pytest.fixture
def mock_external_apis():
    """Mock external API responses for testing."""
    with patch("httpx.AsyncClient.get") as mock_get:

        def api_response_factory(
            service: str, status_code: int = 200, valid: bool = True
        ):
            response = MagicMock()
            response.status_code = status_code

            if service == "openai" and status_code == 200:
                response.json.return_value = {
                    "data": [
                        {"id": "gpt-4"},
                        {"id": "gpt-3.5-turbo"},
                        {"id": "dall-e-3"},
                    ]
                }
            elif service == "weather" and status_code == 200:
                response.json.return_value = {
                    "name": "London",
                    "weather": [{"main": "Clear"}],
                    "main": {"temp": 20},
                }
            elif service == "googlemaps" and status_code == 200:
                response.json.return_value = {
                    "status": "OK" if valid else "REQUEST_DENIED",
                    "results": [{"formatted_address": "Test Address"}] if valid else [],
                }
            elif status_code == 401:
                response.json.return_value = {"error": {"message": "Invalid API key"}}
            elif status_code == 429:
                response.headers = {
                    "retry-after": "60",
                    "x-ratelimit-limit": "100",
                    "x-ratelimit-remaining": "0",
                }
                response.json.return_value = {
                    "error": {"message": "Rate limit exceeded"}
                }

            return response

        # Default to successful OpenAI response
        mock_get.return_value = api_response_factory("openai")
        mock_get.api_response_factory = api_response_factory

        yield mock_get

@pytest.fixture
def mock_encryption():
    """Mock encryption for faster tests."""
    with patch(
        "tripsage_core.services.business.api_key_service.ApiKeyService._encrypt_api_key"
    ) as mock_encrypt:
        with patch(
            "tripsage_core.services.business.api_key_service.ApiKeyService._decrypt_api_key"
        ) as mock_decrypt:
            # Simple mock encryption/decryption
            def encrypt(key_value: str) -> str:
                return f"encrypted_{key_value}"

            def decrypt(encrypted_key: str) -> str:
                return encrypted_key.replace("encrypted_", "")

            mock_encrypt.side_effect = encrypt
            mock_decrypt.side_effect = decrypt

            yield {"encrypt": mock_encrypt, "decrypt": mock_decrypt}

@pytest.fixture(autouse=True)
async def cleanup_redis_after_test(integration_redis):
    """Clean up Redis after each test."""
    yield
    # Clean up any test data
    try:
        if hasattr(integration_redis, "flushdb"):
            await integration_redis.flushdb()
    except Exception:
        pass  # Ignore cleanup errors

# Test markers for different test categories
pytest_plugins = ["pytest_asyncio"]

def pytest_configure(config):
    """Configure pytest with custom markers for integration tests."""
    config.addinivalue_line(
        "markers", "integration: Integration tests with real dependencies"
    )
    config.addinivalue_line("markers", "full_stack: Full stack integration tests")
    config.addinivalue_line("markers", "performance: Performance and load tests")
    config.addinivalue_line(
        "markers", "external_api: Tests requiring external API mocking"
    )
    config.addinivalue_line("markers", "database: Tests requiring database operations")
    config.addinivalue_line("markers", "cache: Tests requiring cache operations")

def pytest_collection_modifyitems(config, items):
    """Modify test collection for integration tests."""
    for item in items:
        # Add integration marker to all tests in this directory
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Add specific markers based on test names
        if "full_stack" in item.name:
            item.add_marker(pytest.mark.full_stack)
        if "performance" in item.name or "load" in item.name:
            item.add_marker(pytest.mark.performance)
        if "external" in item.name or "api" in item.name:
            item.add_marker(pytest.mark.external_api)
        if "database" in item.name or "db" in item.name:
            item.add_marker(pytest.mark.database)
        if "cache" in item.name or "redis" in item.name:
            item.add_marker(pytest.mark.cache)
