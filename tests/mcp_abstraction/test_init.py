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

# Mock the MCP settings module
mcp_settings_mock = MagicMock()
mcp_settings_mock.supabase.enabled = True
mcp_settings_mock.supabase.host = "localhost"
mcp_settings_mock.supabase.port = 5432
mcp_settings_mock.supabase.username = "postgres"
mcp_settings_mock.supabase.password = MagicMock()
mcp_settings_mock.supabase.password.get_secret_value.return_value = "password"
mcp_settings_mock.supabase.database = "postgres"
mcp_settings_mock.supabase.project_ref = "test"
mcp_settings_mock.supabase.anon_key = MagicMock()
mcp_settings_mock.supabase.anon_key.get_secret_value.return_value = "anon_key"
mcp_settings_mock.supabase.service_key = MagicMock()
mcp_settings_mock.supabase.service_key.get_secret_value.return_value = "service_key"

mcp_settings_mock.neo4j_memory = MagicMock()
mcp_settings_mock.neo4j_memory.enabled = True
mcp_settings_mock.neo4j_memory.scheme = "bolt"
mcp_settings_mock.neo4j_memory.host = "localhost"
mcp_settings_mock.neo4j_memory.port = 7687
mcp_settings_mock.neo4j_memory.username = "neo4j"
mcp_settings_mock.neo4j_memory.password = MagicMock()
mcp_settings_mock.neo4j_memory.password.get_secret_value.return_value = "password"

mcp_settings_mock.duffel_flights = MagicMock()
mcp_settings_mock.duffel_flights.enabled = True
mcp_settings_mock.duffel_flights.url = "https://api.duffel.com"
mcp_settings_mock.duffel_flights.api_key = MagicMock()
duffel_key = mcp_settings_mock.duffel_flights.api_key.get_secret_value
duffel_key.return_value = "duffel_key"
mcp_settings_mock.duffel_flights.timeout = 30
mcp_settings_mock.duffel_flights.retry_attempts = 3
mcp_settings_mock.duffel_flights.retry_backoff = 5

mcp_settings_mock.airbnb = MagicMock()
mcp_settings_mock.airbnb.enabled = True
mcp_settings_mock.airbnb.url = "https://api.airbnb.com"
mcp_settings_mock.airbnb.timeout = 30
mcp_settings_mock.airbnb.retry_attempts = 3
mcp_settings_mock.airbnb.retry_backoff = 5

# Mock the mcp_settings module
sys.modules['tripsage.config.mcp_settings'] = MagicMock()
sys.modules['tripsage.config.mcp_settings'].mcp_settings = mcp_settings_mock
sys.modules['tripsage.config.mcp_settings'].get_mcp_settings = MagicMock(
    return_value=mcp_settings_mock
)

# Mock parent modules to ensure they exist
sys.modules['tripsage.clients'] = MagicMock()
sys.modules['tripsage.clients.maps'] = MagicMock()
sys.modules['tripsage.clients.weather'] = MagicMock()
sys.modules['tripsage.clients.webcrawl'] = MagicMock()
sys.modules['tripsage.mcp'] = MagicMock()
sys.modules['tripsage.mcp.time'] = MagicMock()
sys.modules['tripsage.mcp.supabase'] = MagicMock()
sys.modules['tripsage.mcp.memory'] = MagicMock()
sys.modules['tripsage.mcp.flights'] = MagicMock()
sys.modules['tripsage.mcp.accommodations'] = MagicMock()
sys.modules['tripsage.mcp.calendar'] = MagicMock()
sys.modules['tripsage.utils'] = MagicMock()

# Mock cache and logging modules
mock_cache = MagicMock()
sys.modules['tripsage.utils.cache'] = MagicMock()
sys.modules['tripsage.utils.cache'].WebOperationsCache = MagicMock()
sys.modules['tripsage.utils.cache'].web_cache = MagicMock()

sys.modules['tripsage.utils.logging'] = MagicMock()
sys.modules['tripsage.utils.logging'].get_logger = MagicMock(return_value=MagicMock())

# Mock client modules to avoid actual imports
mock_googlemaps_client = MagicMock()
sys.modules['tripsage.clients.maps.google_maps_mcp_client'] = MagicMock()
maps_client_module = sys.modules['tripsage.clients.maps.google_maps_mcp_client']
maps_client_module.GoogleMapsMCPClient = MagicMock()

mock_weather_client = MagicMock()
sys.modules['tripsage.clients.weather.weather_mcp_client'] = MagicMock()
weather_client_module = sys.modules['tripsage.clients.weather.weather_mcp_client']
weather_client_module.WeatherMCPClient = MagicMock()

mock_time_client = MagicMock()
sys.modules['tripsage.mcp.time.client'] = MagicMock()
sys.modules['tripsage.mcp.time.client'].TimeMCPClient = MagicMock()

mock_supabase_client = MagicMock()
sys.modules['tripsage.mcp.supabase.client'] = MagicMock()
sys.modules['tripsage.mcp.supabase.client'].SupabaseMCPClient = MagicMock()

mock_memory_client = MagicMock()
sys.modules['tripsage.mcp.memory.client'] = MagicMock()
sys.modules['tripsage.mcp.memory.client'].MemoryMCPClient = MagicMock()

mock_flights_client = MagicMock() 
sys.modules['tripsage.mcp.flights.client'] = MagicMock()
sys.modules['tripsage.mcp.flights.client'].FlightsMCPClient = MagicMock()

mock_airbnb_client = MagicMock()
sys.modules['tripsage.mcp.accommodations.client'] = MagicMock()
sys.modules['tripsage.mcp.accommodations.client'].AirbnbMCPClient = MagicMock()

mock_crawl4ai_client = MagicMock()
sys.modules['tripsage.clients.webcrawl.crawl4ai_mcp_client'] = MagicMock()
crawl4ai_module = sys.modules['tripsage.clients.webcrawl.crawl4ai_mcp_client']
crawl4ai_module.Crawl4AIMCPClient = MagicMock()

mock_firecrawl_client = MagicMock()  
sys.modules['tripsage.clients.webcrawl.firecrawl_mcp_client'] = MagicMock()
firecrawl_module = sys.modules['tripsage.clients.webcrawl.firecrawl_mcp_client']
firecrawl_module.FirecrawlMCPClient = MagicMock()

mock_calendar_client = MagicMock()
sys.modules['tripsage.mcp.calendar.client'] = MagicMock() 
sys.modules['tripsage.mcp.calendar.client'].CalendarMCPClient = MagicMock()