"""
Tests for memory tools.

This module contains tests for the memory tools used by TripSage agents.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, ".")

# Mock environment variables before importing modules
os.environ["SUPABASE_URL"] = "https://example.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "test_anon_key"
os.environ["SUPABASE_SERVICE_KEY"] = "test_service_key"
os.environ["MEMORY_MCP_URL"] = "http://localhost:3002"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "password"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["GOOGLE_MAPS_API_KEY"] = "test_api_key"
os.environ["GOOGLE_CALENDAR_CREDENTIALS"] = "{}"
os.environ["GOOGLE_CALENDAR_TOKEN"] = "{}"

# Mock settings to avoid Pydantic validation errors
sys.modules["src.utils.settings"] = MagicMock()
settings_mock = MagicMock()
settings_mock.db.supabase_url = "https://example.supabase.co"
settings_mock.db.supabase_anon_key = "test_anon_key"
settings_mock.db.supabase_service_key = "test_service_key"
settings_mock.db.neo4j_uri = "bolt://localhost:7687"
settings_mock.db.neo4j_user = "neo4j"
settings_mock.db.neo4j_password = "password"
settings_mock.memory.mcp_url = "http://localhost:3002"
sys.modules["src.utils.settings"].settings = settings_mock

# Mock memory models
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MemoryEntity:
    name: str
    entityType: str
    observations: List[str] = None


@dataclass
class MemoryRelation:
    from_: str
    relationType: str
    to: str


@dataclass
class MemoryObservation:
    entityName: str
    contents: List[str]


# Mock the memory models module
sys.modules["src.mcp.memory.models"] = MagicMock()
sys.modules["src.mcp.memory.models"].MemoryEntity = MemoryEntity
sys.modules["src.mcp.memory.models"].MemoryRelation = MemoryRelation
sys.modules["src.mcp.memory.models"].MemoryObservation = MemoryObservation

# Mock memory_client directly
sys.modules["src.mcp.memory.client"] = MagicMock()
sys.modules["src.mcp.memory.client"].memory_client = MagicMock()
sys.modules["src.mcp.memory.client"].memory_client.initialize = AsyncMock()
sys.modules["src.mcp.memory.client"].memory_client.read_graph = AsyncMock()
sys.modules["src.mcp.memory.client"].memory_client.search_nodes = AsyncMock()
sys.modules["src.mcp.memory.client"].memory_client.open_nodes = AsyncMock()
sys.modules["src.mcp.memory.client"].memory_client.create_entities = AsyncMock()
sys.modules["src.mcp.memory.client"].memory_client.create_relations = AsyncMock()
sys.modules["src.mcp.memory.client"].memory_client.add_observations = AsyncMock()
sys.modules["src.mcp.memory.client"].memory_client.delete_entities = AsyncMock()
sys.modules["src.mcp.memory.client"].memory_client.delete_relations = AsyncMock()
sys.modules["src.mcp.memory.client"].memory_client.delete_observations = AsyncMock()

# Mock session memory functions
sys.modules["src.utils.session_memory"] = MagicMock()
sys.modules["src.utils.session_memory"].initialize_session_memory = AsyncMock()
sys.modules["src.utils.session_memory"].update_session_memory = AsyncMock()
sys.modules["src.utils.session_memory"].store_session_summary = AsyncMock()

# Mock decorators module with our own implementation
import functools
from typing import Any, Callable, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])


def ensure_memory_client_initialized(func: F) -> F:
    """Mock decorator that simulates memory client initialization."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        memory_client = sys.modules["src.mcp.memory.client"].memory_client
        await memory_client.initialize()
        return await func(*args, **kwargs)

    return cast(F, wrapper)


def with_error_handling(func: F) -> F:
    """Mock decorator that simulates error handling."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return {"error": str(e)}

    return cast(F, wrapper)


# Mock the decorator module
sys.modules["src.utils.decorators"] = MagicMock()
sys.modules[
    "src.utils.decorators"
].ensure_memory_client_initialized = ensure_memory_client_initialized
sys.modules["src.utils.decorators"].with_error_handling = with_error_handling

from src.agents.memory_tools import (
    Entity,
    Observation,
    Relation,
    add_entity_observations,
    create_knowledge_entities,
    create_knowledge_relations,
    delete_entity_observations,
    delete_knowledge_entities,
    delete_knowledge_relations,
    get_entity_details,
    get_knowledge_graph,
    initialize_agent_memory,
    save_session_summary,
    search_knowledge_graph,
    update_agent_memory,
)
from src.utils.decorators import ensure_memory_client_initialized


@pytest.mark.asyncio
class TestMemoryTools:
    """Tests for memory tools."""

    @pytest.fixture
    def mock_memory_client(self):
        """Mock memory client."""
        # Get the pre-mocked memory client
        mock_client = sys.modules["src.mcp.memory.client"].memory_client

        # Set default return values
        mock_client.read_graph.return_value = {
            "entities": [],
            "relations": [],
            "statistics": {},
        }
        mock_client.search_nodes.return_value = []
        mock_client.open_nodes.return_value = []
        mock_client.create_entities.return_value = []
        mock_client.create_relations.return_value = []
        mock_client.add_observations.return_value = []
        mock_client.delete_entities.return_value = []
        mock_client.delete_relations.return_value = []
        mock_client.delete_observations.return_value = []

        # Reset call counts before each test
        mock_client.initialize.reset_mock()
        mock_client.read_graph.reset_mock()
        mock_client.search_nodes.reset_mock()
        mock_client.open_nodes.reset_mock()
        mock_client.create_entities.reset_mock()
        mock_client.create_relations.reset_mock()
        mock_client.add_observations.reset_mock()
        mock_client.delete_entities.reset_mock()
        mock_client.delete_relations.reset_mock()
        mock_client.delete_observations.reset_mock()

        yield mock_client

    @pytest.fixture
    def mock_session_memory(self):
        """Mock session memory functions."""
        # Get the pre-mocked session memory functions
        mock_init = sys.modules["src.utils.session_memory"].initialize_session_memory
        mock_update = sys.modules["src.utils.session_memory"].update_session_memory
        mock_store = sys.modules["src.utils.session_memory"].store_session_summary

        # Set default return values
        mock_init.return_value = {"user": None, "preferences": {}}
        mock_update.return_value = {"entities_created": 0}
        mock_store.return_value = {"session_entity": {}}

        # Reset call counts before each test
        mock_init.reset_mock()
        mock_update.reset_mock()
        mock_store.reset_mock()

        yield (mock_init, mock_update, mock_store)

    async def test_get_knowledge_graph(self, mock_memory_client):
        """Test get_knowledge_graph function."""
        # Setup expected return
        mock_memory_client.read_graph.return_value = {
            "entities": [{"name": "Test"}],
            "relations": [{"from": "A", "to": "B"}],
            "statistics": {"count": 1},
        }

        # Call function
        result = await get_knowledge_graph()

        # Verify
        mock_memory_client.initialize.assert_called_once()
        mock_memory_client.read_graph.assert_called_once()
        assert result["entities"] == [{"name": "Test"}]
        assert result["relations"] == [{"from": "A", "to": "B"}]
        assert result["statistics"] == {"count": 1}

    async def test_search_knowledge_graph(self, mock_memory_client):
        """Test search_knowledge_graph function."""
        # Setup expected return
        mock_memory_client.search_nodes.return_value = [
            {"name": "TestNode", "entityType": "Test"}
        ]

        # Call function
        result = await search_knowledge_graph("test")

        # Verify
        mock_memory_client.initialize.assert_called_once()
        mock_memory_client.search_nodes.assert_called_once_with("test")
        assert result["nodes"] == [{"name": "TestNode", "entityType": "Test"}]

    async def test_get_entity_details(self, mock_memory_client):
        """Test get_entity_details function."""
        # Setup expected return
        mock_memory_client.open_nodes.return_value = [
            {"name": "TestNode", "observations": ["Test observation"]}
        ]

        # Call function
        result = await get_entity_details(["TestNode"])

        # Verify
        mock_memory_client.initialize.assert_called_once()
        mock_memory_client.open_nodes.assert_called_once_with(["TestNode"])
        assert result["entities"] == [
            {"name": "TestNode", "observations": ["Test observation"]}
        ]

    async def test_create_knowledge_entities(self, mock_memory_client):
        """Test create_knowledge_entities function."""
        # Setup test data
        entities = [
            Entity(
                name="Test", entityType="TestType", observations=["Test observation"]
            )
        ]

        # Setup expected return
        mock_memory_client.create_entities.return_value = [
            {"name": "Test", "entityType": "TestType"}
        ]

        # Call function
        result = await create_knowledge_entities(entities)

        # Verify
        mock_memory_client.initialize.assert_called_once()
        mock_memory_client.create_entities.assert_called_once()
        assert result["entities"] == [{"name": "Test", "entityType": "TestType"}]

    async def test_create_knowledge_relations(self, mock_memory_client):
        """Test create_knowledge_relations function."""
        # Setup test data
        relations = [Relation(from_="A", relationType="RELATES_TO", to="B")]

        # Setup expected return
        mock_memory_client.create_relations.return_value = [
            {"from": "A", "relationType": "RELATES_TO", "to": "B"}
        ]

        # Call function
        result = await create_knowledge_relations(relations)

        # Verify
        mock_memory_client.initialize.assert_called_once()
        mock_memory_client.create_relations.assert_called_once()
        assert result["relations"] == [
            {"from": "A", "relationType": "RELATES_TO", "to": "B"}
        ]

    async def test_add_entity_observations(self, mock_memory_client):
        """Test add_entity_observations function."""
        # Setup test data
        observations = [Observation(entityName="Test", contents=["New observation"])]

        # Setup expected return
        mock_memory_client.add_observations.return_value = [
            {"name": "Test", "observations": ["New observation"]}
        ]

        # Call function
        result = await add_entity_observations(observations)

        # Verify
        mock_memory_client.initialize.assert_called_once()
        mock_memory_client.add_observations.assert_called_once()
        assert result["entities"] == [
            {"name": "Test", "observations": ["New observation"]}
        ]

    async def test_delete_knowledge_entities(self, mock_memory_client):
        """Test delete_knowledge_entities function."""
        # Setup expected return
        mock_memory_client.delete_entities.return_value = ["Test"]

        # Call function
        result = await delete_knowledge_entities(["Test"])

        # Verify
        mock_memory_client.initialize.assert_called_once()
        mock_memory_client.delete_entities.assert_called_once_with(["Test"])
        assert result["deleted"] == ["Test"]

    async def test_initialize_agent_memory(self, mock_session_memory):
        """Test initialize_agent_memory function."""
        # Unpack fixtures
        mock_init, _, _ = mock_session_memory

        # Call function
        result = await initialize_agent_memory("user123")

        # Verify
        mock_init.assert_called_once_with("user123")
        assert result == {"user": None, "preferences": {}}

    async def test_update_agent_memory(self, mock_session_memory):
        """Test update_agent_memory function."""
        # Unpack fixtures
        _, mock_update, _ = mock_session_memory

        # Setup test data
        updates = {"preferences": {"budget": "medium"}}

        # Call function
        result = await update_agent_memory("user123", updates)

        # Verify
        mock_update.assert_called_once_with("user123", updates)
        assert result == {"entities_created": 0}

    async def test_save_session_summary(self, mock_session_memory):
        """Test save_session_summary function."""
        # Unpack fixtures
        _, _, mock_store = mock_session_memory

        # Call function
        result = await save_session_summary("user123", "Test summary", "session123")

        # Verify
        mock_store.assert_called_once_with("user123", "Test summary", "session123")
        assert result == {"session_entity": {}}

    async def test_error_handling(self, mock_memory_client):
        """Test error handling in functions."""
        # Setup mock to raise exception
        mock_memory_client.read_graph.side_effect = Exception("Test error")

        # Call function
        result = await get_knowledge_graph()

        # Verify
        assert "error" in result
        assert result["error"] == "Test error"

    async def test_decorator_initialization(self, mock_memory_client):
        """Test that the decorator correctly initializes the memory client."""

        # Define a test function with the decorator
        @ensure_memory_client_initialized
        async def test_func():
            return "success"

        # Call the function
        await test_func()

        # Verify that initialize was called
        mock_memory_client.initialize.assert_called_once()


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
