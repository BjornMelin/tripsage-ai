"""Test setup for MCP abstraction tests."""

import os

# Set test environment variables before importing any tripsage modules
os.environ["NEO4J_PASSWORD"] = "test_password"
os.environ["NEO4J_USER"] = "bjorn"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["OPENAI_API_KEY"] = "test_key"
os.environ["ANTHROPIC_API_KEY"] = "test_key"
os.environ["WEATHER_API_KEY"] = "test_key"
os.environ["GOOGLE_MAPS_API_KEY"] = "test_key"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_API_KEY"] = "test_key"

# Configure test environment
os.environ["TESTING"] = "true"
