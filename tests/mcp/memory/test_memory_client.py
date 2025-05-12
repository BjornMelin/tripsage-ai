"""
Tests for the Memory MCP client.

These tests verify that the MemoryClient correctly interacts with the
Memory MCP service for knowledge graph operations.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.mcp.memory.client import MemoryClient, memory_client


@pytest.fixture
def memory_client_instance():
    """Fixture providing a Memory client instance with mocked HTTP calls."""
    with patch("src.mcp.memory.client.BaseMcpClient._make_request") as mock_request:
        client = MemoryClient(base_url="http://test-memory-mcp:8000")
        client._make_request = AsyncMock()
        yield client


async def test_initialize(memory_client_instance):
    """Test initializing the memory client."""
    # Arrange
    client = memory_client_instance
    
    # Act
    await client.initialize()
    
    # Assert
    assert client._initialized is True


async def test_create_entities(memory_client_instance):
    """Test creating entities in the knowledge graph."""
    # Arrange
    client = memory_client_instance
    entities = [
        {
            "name": "TestEntity",
            "entityType": "TestType",
            "observations": ["Test observation"]
        }
    ]
    client._make_request.return_value = {"entities": entities}
    
    # Act
    result = await client.create_entities(entities)
    
    # Assert
    client._make_request.assert_called_once_with(
        method="POST",
        endpoint="create_entities",
        data={"entities": entities}
    )
    assert result == entities


async def test_create_relations(memory_client_instance):
    """Test creating relations in the knowledge graph."""
    # Arrange
    client = memory_client_instance
    relations = [
        {
            "from": "EntityA",
            "relationType": "RELATES_TO",
            "to": "EntityB"
        }
    ]
    client._make_request.return_value = {"relations": relations}
    
    # Act
    result = await client.create_relations(relations)
    
    # Assert
    client._make_request.assert_called_once_with(
        method="POST",
        endpoint="create_relations",
        data={"relations": relations}
    )
    assert result == relations


async def test_add_observations(memory_client_instance):
    """Test adding observations to entities."""
    # Arrange
    client = memory_client_instance
    observations = [
        {
            "entityName": "TestEntity",
            "contents": ["New observation"]
        }
    ]
    updated_entity = {
        "name": "TestEntity",
        "observations": ["Test observation", "New observation"]
    }
    client._make_request.return_value = {"entities": [updated_entity]}
    
    # Act
    result = await client.add_observations(observations)
    
    # Assert
    client._make_request.assert_called_once_with(
        method="POST",
        endpoint="add_observations",
        data={"observations": observations}
    )
    assert result == [updated_entity]


async def test_delete_entities(memory_client_instance):
    """Test deleting entities from the knowledge graph."""
    # Arrange
    client = memory_client_instance
    entity_names = ["EntityA", "EntityB"]
    client._make_request.return_value = {"deleted": entity_names}
    
    # Act
    result = await client.delete_entities(entity_names)
    
    # Assert
    client._make_request.assert_called_once_with(
        method="POST",
        endpoint="delete_entities",
        data={"entityNames": entity_names}
    )
    assert result == entity_names


async def test_delete_relations(memory_client_instance):
    """Test deleting relations from the knowledge graph."""
    # Arrange
    client = memory_client_instance
    relations = [
        {
            "from": "EntityA",
            "relationType": "RELATES_TO",
            "to": "EntityB"
        }
    ]
    client._make_request.return_value = {"deleted": relations}
    
    # Act
    result = await client.delete_relations(relations)
    
    # Assert
    client._make_request.assert_called_once_with(
        method="POST",
        endpoint="delete_relations",
        data={"relations": relations}
    )
    assert result == relations


async def test_delete_observations(memory_client_instance):
    """Test deleting observations from entities."""
    # Arrange
    client = memory_client_instance
    deletions = [
        {
            "entityName": "TestEntity",
            "observations": ["Observation to delete"]
        }
    ]
    updated_entity = {
        "name": "TestEntity",
        "observations": ["Remaining observation"]
    }
    client._make_request.return_value = {"entities": [updated_entity]}
    
    # Act
    result = await client.delete_observations(deletions)
    
    # Assert
    client._make_request.assert_called_once_with(
        method="POST",
        endpoint="delete_observations",
        data={"deletions": deletions}
    )
    assert result == [updated_entity]


async def test_read_graph(memory_client_instance):
    """Test reading the entire knowledge graph."""
    # Arrange
    client = memory_client_instance
    graph_data = {
        "entities": [{"name": "Entity1"}, {"name": "Entity2"}],
        "relations": [{"from": "Entity1", "to": "Entity2"}],
        "statistics": {"entity_count": 2, "relation_count": 1}
    }
    client._make_request.return_value = graph_data
    
    # Act
    result = await client.read_graph()
    
    # Assert
    client._make_request.assert_called_once_with(
        method="GET",
        endpoint="read_graph"
    )
    assert result == graph_data


async def test_search_nodes(memory_client_instance):
    """Test searching for nodes in the knowledge graph."""
    # Arrange
    client = memory_client_instance
    query = "test query"
    search_results = [
        {"name": "Entity1", "match_score": 0.9},
        {"name": "Entity2", "match_score": 0.7}
    ]
    client._make_request.return_value = {"nodes": search_results}
    
    # Act
    result = await client.search_nodes(query)
    
    # Assert
    client._make_request.assert_called_once_with(
        method="POST",
        endpoint="search_nodes",
        data={"query": query}
    )
    assert result == search_results


async def test_open_nodes(memory_client_instance):
    """Test opening specific nodes in the knowledge graph."""
    # Arrange
    client = memory_client_instance
    names = ["Entity1", "Entity2"]
    node_details = [
        {"name": "Entity1", "observations": ["Observation 1"]},
        {"name": "Entity2", "observations": ["Observation 2"]}
    ]
    client._make_request.return_value = {"nodes": node_details}
    
    # Act
    result = await client.open_nodes(names)
    
    # Assert
    client._make_request.assert_called_once_with(
        method="POST",
        endpoint="open_nodes",
        data={"names": names}
    )
    assert result == node_details


async def test_singleton_instance():
    """Test that the singleton instance is properly initialized."""
    # Assert
    assert memory_client is not None
    assert isinstance(memory_client, MemoryClient)