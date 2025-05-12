"""
Tests for the memory tools for TripSage agents.

These tests verify that the memory tools correctly wrap the Memory MCP client
for use with the OpenAI Agents SDK.
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from src.agents.memory_tools import (
    Entity,
    Relation,
    Observation,
    DeletionRequest,
    get_knowledge_graph,
    search_knowledge_graph,
    get_entity_details,
    create_knowledge_entities,
    create_knowledge_relations,
    add_entity_observations,
    delete_knowledge_entities,
    delete_knowledge_relations,
    delete_entity_observations,
    initialize_agent_memory,
    update_agent_memory,
    save_session_summary,
)


@pytest.fixture
def mock_memory_client():
    """Fixture providing a mocked memory client."""
    with patch("src.agents.memory_tools.memory_client") as mock_client:
        mock_client.initialize = AsyncMock()
        mock_client.read_graph = AsyncMock()
        mock_client.search_nodes = AsyncMock()
        mock_client.open_nodes = AsyncMock()
        mock_client.create_entities = AsyncMock()
        mock_client.create_relations = AsyncMock()
        mock_client.add_observations = AsyncMock()
        mock_client.delete_entities = AsyncMock()
        mock_client.delete_relations = AsyncMock()
        mock_client.delete_observations = AsyncMock()
        yield mock_client


@pytest.fixture
def mock_session_memory():
    """Fixture providing mocked session memory functions."""
    with patch("src.agents.memory_tools.initialize_session_memory") as mock_init, \
         patch("src.agents.memory_tools.update_session_memory") as mock_update, \
         patch("src.agents.memory_tools.store_session_summary") as mock_store:
        mock_init.return_value = {"user": None, "preferences": {}}
        mock_update.return_value = {"entities_created": 1}
        mock_store.return_value = {"session_entity": {"name": "Session:123"}}
        yield mock_init, mock_update, mock_store


async def test_get_knowledge_graph(mock_memory_client):
    """Test retrieving the entire knowledge graph."""
    # Arrange
    graph_data = {
        "entities": [{"name": "EntityA"}, {"name": "EntityB"}],
        "relations": [{"from": "EntityA", "to": "EntityB"}],
        "statistics": {"entity_count": 2, "relation_count": 1}
    }
    mock_memory_client.read_graph.return_value = graph_data
    
    # Act
    result = await get_knowledge_graph()
    
    # Assert
    mock_memory_client.initialize.assert_called_once()
    mock_memory_client.read_graph.assert_called_once()
    assert result == graph_data


async def test_search_knowledge_graph(mock_memory_client):
    """Test searching the knowledge graph."""
    # Arrange
    query = "test query"
    search_results = [
        {"name": "EntityA", "match_score": 0.9},
        {"name": "EntityB", "match_score": 0.7}
    ]
    mock_memory_client.search_nodes.return_value = search_results
    
    # Act
    result = await search_knowledge_graph(query)
    
    # Assert
    mock_memory_client.initialize.assert_called_once()
    mock_memory_client.search_nodes.assert_called_once_with(query)
    assert result["nodes"] == search_results


async def test_get_entity_details(mock_memory_client):
    """Test getting detailed information about entities."""
    # Arrange
    entity_names = ["EntityA", "EntityB"]
    entity_details = [
        {"name": "EntityA", "observations": ["Observation 1"]},
        {"name": "EntityB", "observations": ["Observation 2"]}
    ]
    mock_memory_client.open_nodes.return_value = entity_details
    
    # Act
    result = await get_entity_details(entity_names)
    
    # Assert
    mock_memory_client.initialize.assert_called_once()
    mock_memory_client.open_nodes.assert_called_once_with(entity_names)
    assert result["entities"] == entity_details


async def test_create_knowledge_entities(mock_memory_client):
    """Test creating new entities in the knowledge graph."""
    # Arrange
    entities = [
        Entity(name="EntityA", entityType="TypeA", observations=["Observation A"]),
        Entity(name="EntityB", entityType="TypeB", observations=["Observation B"])
    ]
    entity_dicts = [entity.model_dump(by_alias=True) for entity in entities]
    created_entities = [
        {"name": "EntityA", "type": "TypeA", "id": "1"},
        {"name": "EntityB", "type": "TypeB", "id": "2"}
    ]
    mock_memory_client.create_entities.return_value = created_entities
    
    # Act
    result = await create_knowledge_entities(entities)
    
    # Assert
    mock_memory_client.initialize.assert_called_once()
    mock_memory_client.create_entities.assert_called_once()
    # Check that the entities were converted to dictionaries
    args, _ = mock_memory_client.create_entities.call_args
    assert args[0] == entity_dicts
    assert result["entities"] == created_entities


async def test_create_knowledge_relations(mock_memory_client):
    """Test creating new relations in the knowledge graph."""
    # Arrange
    relations = [
        Relation(from_="EntityA", relationType="RELATES_TO", to="EntityB"),
        Relation(from_="EntityB", relationType="BELONGS_TO", to="EntityC")
    ]
    relation_dicts = [relation.model_dump(by_alias=True) for relation in relations]
    created_relations = [
        {"from": "EntityA", "relationType": "RELATES_TO", "to": "EntityB", "id": "1"},
        {"from": "EntityB", "relationType": "BELONGS_TO", "to": "EntityC", "id": "2"}
    ]
    mock_memory_client.create_relations.return_value = created_relations
    
    # Act
    result = await create_knowledge_relations(relations)
    
    # Assert
    mock_memory_client.initialize.assert_called_once()
    mock_memory_client.create_relations.assert_called_once()
    # Check that the relations were converted to dictionaries
    args, _ = mock_memory_client.create_relations.call_args
    assert args[0] == relation_dicts
    assert result["relations"] == created_relations


async def test_add_entity_observations(mock_memory_client):
    """Test adding observations to entities."""
    # Arrange
    observations = [
        Observation(entityName="EntityA", contents=["New observation"]),
        Observation(entityName="EntityB", contents=["Another observation"])
    ]
    observation_dicts = [obs.model_dump() for obs in observations]
    updated_entities = [
        {"name": "EntityA", "observations": ["Old observation", "New observation"]},
        {"name": "EntityB", "observations": ["Another observation"]}
    ]
    mock_memory_client.add_observations.return_value = updated_entities
    
    # Act
    result = await add_entity_observations(observations)
    
    # Assert
    mock_memory_client.initialize.assert_called_once()
    mock_memory_client.add_observations.assert_called_once()
    # Check that the observations were converted to dictionaries
    args, _ = mock_memory_client.add_observations.call_args
    assert args[0] == observation_dicts
    assert result["entities"] == updated_entities


async def test_delete_knowledge_entities(mock_memory_client):
    """Test deleting entities from the knowledge graph."""
    # Arrange
    entity_names = ["EntityA", "EntityB"]
    mock_memory_client.delete_entities.return_value = entity_names
    
    # Act
    result = await delete_knowledge_entities(entity_names)
    
    # Assert
    mock_memory_client.initialize.assert_called_once()
    mock_memory_client.delete_entities.assert_called_once_with(entity_names)
    assert result["deleted"] == entity_names


async def test_delete_knowledge_relations(mock_memory_client):
    """Test deleting relations from the knowledge graph."""
    # Arrange
    relations = [
        Relation(from_="EntityA", relationType="RELATES_TO", to="EntityB"),
        Relation(from_="EntityB", relationType="BELONGS_TO", to="EntityC")
    ]
    relation_dicts = [relation.model_dump(by_alias=True) for relation in relations]
    deleted_relations = [
        {"from": "EntityA", "relationType": "RELATES_TO", "to": "EntityB"},
        {"from": "EntityB", "relationType": "BELONGS_TO", "to": "EntityC"}
    ]
    mock_memory_client.delete_relations.return_value = deleted_relations
    
    # Act
    result = await delete_knowledge_relations(relations)
    
    # Assert
    mock_memory_client.initialize.assert_called_once()
    mock_memory_client.delete_relations.assert_called_once()
    # Check that the relations were converted to dictionaries
    args, _ = mock_memory_client.delete_relations.call_args
    assert args[0] == relation_dicts
    assert result["deleted"] == deleted_relations


async def test_delete_entity_observations(mock_memory_client):
    """Test deleting observations from entities."""
    # Arrange
    deletions = [
        DeletionRequest(entityName="EntityA", observations=["Observation to delete"]),
        DeletionRequest(entityName="EntityB", observations=["Another observation"])
    ]
    deletion_dicts = [deletion.model_dump() for deletion in deletions]
    updated_entities = [
        {"name": "EntityA", "observations": ["Remaining observation"]},
        {"name": "EntityB", "observations": []}
    ]
    mock_memory_client.delete_observations.return_value = updated_entities
    
    # Act
    result = await delete_entity_observations(deletions)
    
    # Assert
    mock_memory_client.initialize.assert_called_once()
    mock_memory_client.delete_observations.assert_called_once()
    # Check that the deletions were converted to dictionaries
    args, _ = mock_memory_client.delete_observations.call_args
    assert args[0] == deletion_dicts
    assert result["entities"] == updated_entities


async def test_initialize_agent_memory(mock_session_memory):
    """Test initializing agent memory."""
    # Arrange
    mock_init, _, _ = mock_session_memory
    user_id = str(uuid4())
    session_data = {
        "user": {"name": f"User:{user_id}"},
        "preferences": {"flights": "window seats"},
        "recent_trips": []
    }
    mock_init.return_value = session_data
    
    # Act
    result = await initialize_agent_memory(user_id)
    
    # Assert
    mock_init.assert_called_once_with(user_id)
    assert result == session_data


async def test_update_agent_memory(mock_session_memory):
    """Test updating agent memory."""
    # Arrange
    _, mock_update, _ = mock_session_memory
    user_id = str(uuid4())
    updates = {
        "preferences": {
            "flights": "aisle seats",
            "accommodation": "luxury"
        }
    }
    update_result = {
        "entities_created": 0,
        "relations_created": 0,
        "observations_added": 2
    }
    mock_update.return_value = update_result
    
    # Act
    result = await update_agent_memory(user_id, updates)
    
    # Assert
    mock_update.assert_called_once_with(user_id, updates)
    assert result == update_result


async def test_save_session_summary(mock_session_memory):
    """Test saving a session summary."""
    # Arrange
    _, _, mock_store = mock_session_memory
    user_id = str(uuid4())
    session_id = str(uuid4())
    summary = "User researched vacation options in Europe for summer 2025."
    store_result = {
        "session_entity": {"name": f"Session:{session_id}"},
        "session_relation": {"from": f"User:{user_id}", "to": f"Session:{session_id}"}
    }
    mock_store.return_value = store_result
    
    # Act
    result = await save_session_summary(user_id, summary, session_id)
    
    # Assert
    mock_store.assert_called_once_with(user_id, summary, session_id)
    assert result == store_result