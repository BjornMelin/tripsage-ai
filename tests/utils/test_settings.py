"""
Tests for the centralized settings system.
"""

import os
from unittest.mock import patch

import pytest

from src.utils.settings import AppSettings
from src.utils.settings_init import init_settings


@pytest.fixture
def mock_env_vars():
    """
    Mock environment variables for testing.
    """
    env_vars = {
        "DEBUG": "true",
        "ENVIRONMENT": "testing",
        "PORT": "9000",
        "OPENAI_API_KEY": "sk-test-key",
        "SUPABASE_URL": "https://test-project.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_PASSWORD": "test-password",
        "WEATHER_MCP_ENDPOINT": "http://localhost:3001",
        "OPENWEATHERMAP_API_KEY": "test-openweathermap-key",
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars


def test_app_settings_initialization(mock_env_vars):
    """
    Test that AppSettings can be initialized with environment variables.
    """
    settings = AppSettings()

    # Check basic settings
    assert settings.debug is True
    assert settings.environment == "testing"
    assert settings.port == 9000

    # Check API keys
    assert settings.openai_api_key.get_secret_value() == "sk-test-key"

    # Check database settings
    assert settings.database.supabase_url == "https://test-project.supabase.co"
    assert settings.database.supabase_anon_key.get_secret_value() == "test-anon-key"

    # Check Neo4j settings
    assert settings.neo4j.uri == "bolt://localhost:7687"
    assert settings.neo4j.password.get_secret_value() == "test-password"

    # Check MCP settings
    assert settings.weather_mcp.endpoint == "http://localhost:3001"
    assert (
        settings.weather_mcp.openweathermap_api_key.get_secret_value()
        == "test-openweathermap-key"
    )


def test_settings_init(mock_env_vars):
    """
    Test that init_settings validates settings.
    """
    settings = init_settings()
    assert settings.environment == "testing"


@patch.dict(os.environ, {"ENVIRONMENT": "invalid"})
def test_settings_validation_error():
    """
    Test that validation errors are raised for invalid settings.
    """
    with pytest.raises(ValueError):
        init_settings()


def test_default_values():
    """
    Test that default values are used when environment variables are not set.
    """
    # Test with minimal required environment variables
    minimal_env = {
        "OPENAI_API_KEY": "sk-test-key",
        "SUPABASE_URL": "https://test-project.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "NEO4J_PASSWORD": "test-password",
        "OPENWEATHERMAP_API_KEY": "test-openweathermap-key",
    }

    with patch.dict(os.environ, minimal_env, clear=True):
        settings = AppSettings()

        # Check default values
        assert settings.debug is False
        assert settings.environment == "development"
        assert settings.port == 8000
        assert settings.neo4j.uri == "bolt://localhost:7687"
        assert settings.neo4j.user == "neo4j"
