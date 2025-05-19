"""
Tests for the session memory utilities.

These tests verify that the session memory utilities correctly interact
with the Memory MCP for initializing and updating session memory.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from tripsage.utils.session_memory import (
    initialize_session_memory,
    store_session_summary,
    update_session_memory,
)


@pytest.fixture
def mock_memory_client():
    """Fixture providing a mocked memory client."""
    with patch("src.utils.session_memory.memory_client") as mock_client:
        mock_client.initialize = AsyncMock()
        mock_client.open_nodes = AsyncMock()
        mock_client.search_nodes = AsyncMock()
        mock_client.create_entities = AsyncMock()
        mock_client.create_relations = AsyncMock()
        mock_client.add_observations = AsyncMock()
        mock_client._make_request = AsyncMock()
        yield mock_client


async def test_initialize_session_memory_without_user(mock_memory_client):
    """Test initializing session memory without a user ID."""
    # Arrange
    mock_memory_client._make_request.return_value = [
        {"name": "Paris", "type": "Destination"},
        {"name": "Tokyo", "type": "Destination"},
    ]

    # Act
    result = await initialize_session_memory()

    # Assert
    mock_memory_client.initialize.assert_called_once()
    assert "user" in result
    assert "preferences" in result
    assert "recent_trips" in result
    assert "popular_destinations" in result
    assert result["user"] is None


async def test_initialize_session_memory_with_user(mock_memory_client):
    """Test initializing session memory with a user ID."""
    # Arrange
    user_id = str(uuid4())
    user_node = {
        "name": f"User:{user_id}",
        "type": "User",
        "observations": [
            "TripSage user",
            "Prefers window seats for flights",
            "Prefers budget for accommodation",
        ],
    }
    trip_nodes = [
        {"name": f"Trip:{uuid4()}", "type": "Trip", "observations": ["Recent trip"]}
    ]
    popular_destinations = [
        {"name": "Paris", "count": 120},
        {"name": "Tokyo", "count": 85},
    ]

    mock_memory_client.open_nodes.side_effect = [
        [user_node],  # First call for user node
        trip_nodes,  # Second call for trip nodes
    ]
    mock_memory_client.search_nodes.return_value = [
        {"name": "Trip:123"},
        {"name": "Trip:456"},
    ]
    mock_memory_client._make_request.return_value = popular_destinations

    # Act
    result = await initialize_session_memory(user_id)

    # Assert
    mock_memory_client.initialize.assert_called_once()
    mock_memory_client.open_nodes.assert_called()
    mock_memory_client.search_nodes.assert_called_once_with(f"User:{user_id} PLANS")

    assert result["user"] == user_node
    assert "preferences" in result
    assert "flights" in result["preferences"]
    assert result["preferences"]["flights"] == "window seats"
    assert "accommodation" in result["preferences"]
    assert result["preferences"]["accommodation"] == "budget"
    assert result["recent_trips"] == trip_nodes
    assert result["popular_destinations"] == popular_destinations


async def test_update_session_memory_preferences(mock_memory_client):
    """Test updating session memory with user preferences."""
    # Arrange
    user_id = str(uuid4())
    preferences = {
        "flights": "aisle seats",
        "accommodation": "luxury",
        "dining": "local cuisine",
    }
    mock_memory_client.open_nodes.return_value = []  # User does not exist yet
    mock_memory_client.create_entities.return_value = [{"name": f"User:{user_id}"}]
    mock_memory_client.add_observations.return_value = [{"name": f"User:{user_id}"}]

    # Act
    result = await update_session_memory(user_id, {"preferences": preferences})

    # Assert
    mock_memory_client.initialize.assert_called_once()
    mock_memory_client.open_nodes.assert_called_once_with([f"User:{user_id}"])
    mock_memory_client.create_entities.assert_called_once()
    mock_memory_client.add_observations.assert_called_once()
    assert result["entities_created"] == 1
    assert result["observations_added"] == 3  # One for each preference


async def test_update_session_memory_learned_facts(mock_memory_client):
    """Test updating session memory with learned facts."""
    # Arrange
    user_id = str(uuid4())
    learned_facts = [
        {
            "from": "Paris",
            "relationType": "HAS_LANDMARK",
            "to": "Eiffel Tower",
            "fromType": "Destination",
            "toType": "Landmark",
        },
        {
            "from": "Tokyo",
            "relationType": "KNOWN_FOR",
            "to": "Sushi",
            "fromType": "Destination",
            "toType": "Cuisine",
        },
    ]
    mock_memory_client.open_nodes.return_value = []  # Entities do not exist yet
    mock_memory_client.create_entities.return_value = [
        {"name": "Paris"},
        {"name": "Eiffel Tower"},
    ]
    mock_memory_client.create_relations.return_value = [
        {"from": "Paris", "relationType": "HAS_LANDMARK", "to": "Eiffel Tower"}
    ]

    # Act
    result = await update_session_memory(user_id, {"learned_facts": learned_facts})

    # Assert
    mock_memory_client.initialize.assert_called_once()
    assert (
        mock_memory_client.create_entities.call_count >= 2
    )  # At least two entities created
    assert mock_memory_client.create_relations.call_count == 2  # Two relations created
    assert result["entities_created"] >= 2
    assert result["relations_created"] == 2


async def test_store_session_summary(mock_memory_client):
    """Test storing a session summary."""
    # Arrange
    user_id = str(uuid4())
    session_id = str(uuid4())
    summary = "User researched vacation options in Europe for summer 2025."

    session_entity = {"name": f"Session:{session_id}"}
    session_relation = {"from": f"User:{user_id}", "to": f"Session:{session_id}"}

    mock_memory_client.create_entities.return_value = [session_entity]
    mock_memory_client.create_relations.return_value = [session_relation]

    # Act
    result = await store_session_summary(user_id, summary, session_id)

    # Assert
    mock_memory_client.initialize.assert_called_once()
    mock_memory_client.create_entities.assert_called_once_with(
        [
            {
                "name": f"Session:{session_id}",
                "entityType": "Session",
                "observations": [summary],
            }
        ]
    )
    mock_memory_client.create_relations.assert_called_once_with(
        [
            {
                "from": f"User:{user_id}",
                "relationType": "PARTICIPATED_IN",
                "to": f"Session:{session_id}",
            }
        ]
    )
    assert result["session_entity"] == session_entity
    assert result["session_relation"] == session_relation
