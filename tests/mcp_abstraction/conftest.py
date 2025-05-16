"""Configuration for MCP abstraction tests."""

import os
import sys
from unittest.mock import MagicMock


def pytest_configure(config):
    """Configure test environment before tests run."""
    # Set environment variables first
    os.environ["NEO4J_PASSWORD"] = "test_password"
    os.environ["NEO4J_USER"] = "bjorn"
    os.environ["NEO4J_URI"] = "bolt://localhost:7687"
    os.environ["OPENAI_API_KEY"] = "test_key"
    os.environ["ANTHROPIC_API_KEY"] = "test_key"
    os.environ["WEATHER_API_KEY"] = "test_key"
    os.environ["GOOGLE_MAPS_API_KEY"] = "test_key"
    os.environ["SUPABASE_URL"] = "https://test.supabase.co"
    os.environ["SUPABASE_API_KEY"] = "test_key"
    os.environ["TESTING"] = "true"
    os.environ["TRIPSAGE_ENV"] = "test"

    # Mock the settings module before imports
    sys.modules["tripsage.config.app_settings"] = MagicMock()

    # Mock the settings object
    mock_settings = MagicMock()
    sys.modules["tripsage.config.app_settings"].settings = mock_settings
