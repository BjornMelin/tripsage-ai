"""Pytest configuration for TripSage Core tests."""

import sys
from pathlib import Path

import pytest

# Add the project root to sys.path to ensure imports work
project_root = Path(__file__).parents[3]  # Go up to project root
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import the core module to ensure it's available
import tripsage_core  # noqa: E402, F401


@pytest.fixture(autouse=True)
def mock_core_settings(monkeypatch):
    """Mock settings for TripSage Core tests."""
    # Set minimal required environment variables
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test_anon_key_with_at_least_20_chars")
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_anthropic_key")
    monkeypatch.setenv("JWT_SECRET_KEY", "test_jwt_secret_key_with_256_bits_1234567890")

    # Other environment variables that may be needed
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("DRAGONFLY_URL", "redis://localhost:6380/0")
