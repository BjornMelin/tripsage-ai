"""
Pytest configuration for tripsage.api tests.

This module provides specific fixtures for testing the agent API configuration
and exception handlers without interference from global mocks.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up clean test environment for agent API tests."""
    # Set test environment variables
    test_env = {
        "SUPABASE_URL": "https://test-project.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "OPENAI_API_KEY": "test-openai-key",
        "DEBUG": "false",
        "ENVIRONMENT": "testing",
        "JWT_SECRET_KEY": "test-jwt-secret-key-for-testing",
        "API_KEY_MASTER_SECRET": "test-master-secret",
    }

    # Store original values to restore later
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def temp_env_file():
    """Create a temporary .env file for testing environment loading."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("TRIPSAGE_API_API_PREFIX=/test/agent\n")
        f.write("TRIPSAGE_API_TOKEN_EXPIRATION_MINUTES=300\n")
        f.write("TRIPSAGE_API_RATE_LIMIT_REQUESTS=2000\n")
        temp_file = f.name

    yield temp_file

    # Clean up
    Path(temp_file).unlink(missing_ok=True)


@pytest.fixture
def mock_redis():
    """Mock Redis client for caching tests."""
    mock_redis_client = Mock()
    mock_redis_client.get = Mock(return_value=None)
    mock_redis_client.set = Mock(return_value=True)
    mock_redis_client.delete = Mock(return_value=1)

    with patch("redis.from_url", return_value=mock_redis_client):
        yield mock_redis_client


@pytest.fixture
def patch_core_settings():
    """Patch to prevent CoreAppSettings from making external calls during testing."""
    # Mock external service calls that might be triggered during settings validation
    with (
        patch(
            "tripsage_core.config.base_app_settings.CoreAppSettings.validate_critical_settings",
            return_value=[],
        ),
        patch("redis.from_url", return_value=Mock()),
    ):
        yield
