"""Setup test environment before any imports."""

import os

# Set all required environment variables
env_vars = {
    # Core settings
    "TESTING": "true",
    "TRIPSAGE_ENV": "test",
    "SKIP_REDIS_INIT": "true",  # Skip Redis initialization in tests
    # Database
    "NEO4J_PASSWORD": "test_password",
    "NEO4J_USER": "neo4j",
    "NEO4J_URI": "bolt://localhost:7687",
    # API keys
    "OPENAI_API_KEY": "test_key",
    "ANTHROPIC_API_KEY": "test_key",
    "WEATHER_API_KEY": "test_key",
    "GOOGLE_MAPS_API_KEY": "test_key",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_API_KEY": "test_key",
    # Cache
    "REDIS_URL": "redis://localhost:6379/0",
    # MCP URLs
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
