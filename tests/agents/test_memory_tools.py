"""
Tests for memory tools.

This module contains tests for the memory tools used by TripSage agents.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import sys

import pytest

# Add parent directory to path for imports
sys.path.insert(0, ".")

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
        with patch("src.agents.memory_tools.memory_client") as mock_client:
            # Setup mock methods
            mock_client.initialize = AsyncMock()
            mock_client.read_graph = AsyncMock(
                return_value={"entities": [], "relations": [], "statistics": {}}
            )
            mock_client.search_nodes = AsyncMock(return_value=[])
            mock_client.open_nodes = AsyncMock(return_value=[])
            mock_client.create_entities = AsyncMock(return_value=[])
            mock_client.create_relations = AsyncMock(return_value=[])
            mock_client.add_observations = AsyncMock(return_value=[])
            mock_client.delete_entities = AsyncMock(return_value=[])
            mock_client.delete_relations = AsyncMock(return_value=[])
            mock_client.delete_observations = AsyncMock(return_value=[])
            
            yield mock_client

    @pytest.fixture
    def mock_session_memory(self):
        """Mock session memory functions."""
        with patch("src.agents.memory_tools.initialize_session_memory") as mock_init, \
             patch("src.agents.memory_tools.update_session_memory") as mock_update, \
             patch("src.agents.memory_tools.store_session_summary") as mock_store:
            
            mock_init.return_value = {"user": None, "preferences": {}}
            mock_update.return_value = {"entities_created": 0}
            mock_store.return_value = {"session_entity": {}}
            
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
            Entity(name="Test", entityType="TestType", observations=["Test observation"])
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
        relations = [
            Relation(from_="A", relationType="RELATES_TO", to="B")
        ]
        
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
        observations = [
            Observation(entityName="Test", contents=["New observation"])
        ]
        
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
EOL < /dev/null