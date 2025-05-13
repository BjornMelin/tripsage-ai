"""
Pytest configuration for TripSage tests.
"""

import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

# Add the src directory to the path so tests can import modules directly from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set test environment variables
os.environ.setdefault("AIRBNB_MCP_ENDPOINT", "http://localhost:3000")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SUPABASE_URL", "https://test-supabase-url.com")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USERNAME", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "test-password")


@pytest.fixture
def mock_redis():
    """Mock Redis cache for tests that need it.

    Note: This is no longer autouse to avoid initializing the entire dependency chain.
    """
    with patch("src.cache.redis_cache.redis_cache") as mock_cache:
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        yield mock_cache
