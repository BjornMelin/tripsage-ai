"""Test initialization to bypass app settings on import."""

import os
import sys
from unittest.mock import MagicMock

# Set all required environment variables
env_vars = {
    "NEO4J_PASSWORD": "test_password",
    "NEO4J_USER": "bjorn",
    "NEO4J_URI": "bolt://localhost:7687",
    "OPENAI_API_KEY": "test_key",
    "ANTHROPIC_API_KEY": "test_key",
    "WEATHER_API_KEY": "test_key",
    "GOOGLE_MAPS_API_KEY": "test_key",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_API_KEY": "test_key",
    "TESTING": "true",
    "TRIPSAGE_ENV": "test",
    # Add more required vars
    "TIME_MCP_URL": "http://localhost:8000",
    "WEATHER_MCP_URL": "http://localhost:8001",
    "GOOGLEMAPS_MCP_URL": "http://localhost:8002",
    "MEMORY_MCP_URL": "http://localhost:8003",
    "WEBCRAWL_MCP_URL": "http://localhost:8004",
    "FLIGHTS_MCP_URL": "http://localhost:8005",
    "ACCOMMODATIONS_MCP_URL": "http://localhost:8006",
}

for key, value in env_vars.items():
    os.environ[key] = value

# Mock settings before they get imported
mock_settings = MagicMock()
mock_settings.weather.url = "http://test"
mock_settings.weather.api_key.get_secret_value.return_value = "test-key"
mock_settings.supabase.enabled = True
mock_settings.supabase.url = "https://test.supabase.co"
mock_settings.supabase.api_key.get_secret_value.return_value = "test-key"
mock_settings.supabase.timeout = 30
mock_settings.supabase.retry_attempts = 3

# Mock the settings modules
sys.modules['tripsage.config.app_settings'] = MagicMock()
sys.modules['tripsage.config.app_settings'].settings = mock_settings
sys.modules['tripsage.utils.settings'] = MagicMock()
sys.modules['tripsage.utils.settings'].settings = mock_settings