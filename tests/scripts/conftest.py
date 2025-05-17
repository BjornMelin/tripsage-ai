"""Conftest for scripts tests."""

import os
import pytest
from unittest.mock import patch

# Mock environment variables before importing MCP settings
@pytest.fixture(autouse=True)
def mock_mcp_settings():
    """Mock MCP settings for tests"""
    with patch.dict(
        os.environ,
        {
            "SUPABASE_HOST": "localhost",
            "SUPABASE_PORT": "54321",
            "SUPABASE_USERNAME": "postgres",
            "SUPABASE_PASSWORD": "test-password",
            "SUPABASE_DATABASE": "test-db",
            "SUPABASE_PROJECT_REF": "test-project",
            "SUPABASE_ANON_KEY": "test-anon-key",
            "SUPABASE_SERVICE_KEY": "test-service-key",
            "GOOGLE_MAPS_API_KEY": "test-maps-key",
            "AUTH_URL": "http://localhost:3000",
            "API_KEY": "test-api-key",
            "BASE_URL": "http://localhost:8000",
            "WEATHER_API_KEY": "test-weather-key",
            "WEATHER_API_KEY_OPENWEATHER": "test-openweather-key",
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_AUTH": "neo4j/password",
            "NEO4J_SSL_CERT": "",
        },
    ):
        yield