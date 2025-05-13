"""
Fixtures for testing the utils module.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Set environment variables for testing
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "password"
os.environ["SUPABASE_URL"] = "https://example.supabase.com"
os.environ["SUPABASE_KEY"] = "test-key"
os.environ["SUPABASE_SERVICE_KEY"] = "test-service-key"
os.environ["MEMORY_MCP_ENDPOINT"] = "https://memory-mcp.example.com"
os.environ["MEMORY_MCP_API_KEY"] = "test-memory-key"
os.environ["TRIPSAGE_SUPABASE_URL"] = "https://example.supabase.com"
os.environ["TRIPSAGE_SUPABASE_KEY"] = "test-key"
os.environ["TRIPSAGE_MEMORY_MCP_URL"] = "http://localhost:8000"
os.environ["TRIPSAGE_TEST_MODE"] = "true"

# Mock settings
@pytest.fixture(scope="session", autouse=True)
def mock_settings():
    """Mock settings for all tests."""
    with patch('src.utils.settings.Settings.model_validate') as mock_validate:
        mock_validate.return_value = MagicMock(
            NEO4J_URI="bolt://localhost:7687",
            NEO4J_USER="neo4j",
            NEO4J_PASSWORD="password",
            SUPABASE_URL="https://example.supabase.com",
            SUPABASE_KEY="test-key",
            SUPABASE_SERVICE_KEY="test-service-key",
            MEMORY_MCP_ENDPOINT="https://memory-mcp.example.com",
            MEMORY_MCP_API_KEY="test-memory-key",
            TRIPSAGE_SUPABASE_URL="https://example.supabase.com",
            TRIPSAGE_SUPABASE_KEY="test-key",
            TRIPSAGE_MEMORY_MCP_URL="http://localhost:8000",
            TRIPSAGE_TEST_MODE=True
        )
        # Mock Neo4jConfig
        with patch('src.utils.settings.Neo4jConfig') as mock_neo4j_config:
            mock_neo4j_config.return_value = MagicMock(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="password"
            )
            # Mock SupabaseConfig
            with patch('src.utils.settings.SupabaseConfig') as mock_supabase_config:
                mock_supabase_config.return_value = MagicMock(
                    url="https://example.supabase.com",
                    key="test-key",
                    service_key="test-service-key"
                )
                yield


@pytest.fixture
def mock_db_client():
    """Fixture providing a mocked database client."""
    client = MagicMock()
    client.trips = MagicMock()
    client.trips.create = AsyncMock(return_value={
        "id": "test-trip-id",
        "user_id": "test-user-id",
        "title": "Test Trip",
        "description": "Test Description",
        "start_date": "2023-01-01",
        "end_date": "2023-01-07",
        "budget": 1000,
        "status": "planning",
    })
    client.trips.get = AsyncMock(return_value={
        "id": "test-trip-id",
        "user_id": "test-user-id",
        "title": "Test Trip",
        "description": "Test Description",
        "start_date": "2023-01-01",
        "end_date": "2023-01-07",
        "budget": 1000,
        "status": "planning",
    })
    client.trips.update = AsyncMock(return_value=True)
    client.trips.delete = AsyncMock(return_value=True)
    client.trips.list = AsyncMock(return_value=[
        {"id": "test-trip-1", "title": "Trip 1"},
        {"id": "test-trip-2", "title": "Trip 2"}
    ])
    return client


@pytest.fixture
def mock_memory_client():
    """Fixture providing a mocked memory client."""
    client = MagicMock()
    client.initialize = AsyncMock()
    client.create_entities = AsyncMock(return_value=[
        {
            "name": "Trip:test-trip-id",
            "entityType": "Trip",
            "observations": ["Test Trip from 2023-01-01 to 2023-01-07", "Budget: $1000"],
        },
        {
            "name": "User:test-user-id",
            "entityType": "User",
            "observations": ["TripSage user"],
        },
    ])
    client.create_relations = AsyncMock(return_value=[
        {
            "from": "User:test-user-id",
            "relationType": "PLANS",
            "to": "Trip:test-trip-id",
        },
    ])
    client.open_nodes = AsyncMock(return_value=[
        {
            "name": "Trip:test-trip-id",
            "entityType": "Trip",
            "observations": ["Test Trip from 2023-01-01 to 2023-01-07", "Budget: $1000"],
        },
    ])
    client.search_nodes = AsyncMock(return_value=[
        {
            "name": "Trip:test-trip-id",
            "entityType": "Trip",
            "observations": ["Test Trip from 2023-01-01 to 2023-01-07", "Budget: $1000"],
        },
        {
            "name": "User:test-user-id",
            "entityType": "User",
            "observations": ["TripSage user"],
        },
        {
            "name": "Miami",
            "entityType": "Destination",
            "observations": ["Beautiful beaches and vibrant nightlife"]
        }
    ])
    client.add_observations = AsyncMock(return_value=[
        {
            "entityName": "Trip:test-trip-id", 
            "observations": ["Updated information"]
        }
    ])
    client.delete_entities = AsyncMock(return_value=["Trip:test-trip-id"])
    return client


@pytest.fixture
def patch_both_clients(mock_db_client, mock_memory_client):
    """Fixture to patch both db_client and memory_client together."""
    with patch('src.utils.trip_storage_service.db_client', mock_db_client), \
         patch('src.utils.trip_storage_service.memory_client', mock_memory_client), \
         patch('src.db.client.db_client', mock_db_client), \
         patch('src.mcp.memory.client.memory_client', mock_memory_client):
        yield


@pytest.fixture
def mock_settings():
    """Fixture to mock settings for testing."""
    settings_mock = MagicMock()
    settings_mock.SUPABASE_URL = "https://example.supabase.com"
    settings_mock.SUPABASE_KEY = "test-key"
    settings_mock.MEMORY_MCP_URL = "http://localhost:8000"
    settings_mock.TEST_MODE = True
    
    with patch('src.utils.settings.settings', settings_mock):
        yield settings_mock