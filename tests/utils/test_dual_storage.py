"""
Tests for the dual storage strategy implementation.

These tests verify that the dual storage strategy correctly stores and retrieves
data from both Supabase and Neo4j via the Memory MCP.
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date

from src.utils.dual_storage import (
    store_trip_with_dual_storage,
    retrieve_trip_with_dual_storage,
    update_trip_with_dual_storage,
    delete_trip_with_dual_storage,
)


@pytest.fixture
def mock_db_client():
    """Fixture providing a mocked database client."""
    with patch("src.utils.dual_storage.db_client") as mock_client:
        mock_client.trips = MagicMock()
        mock_client.trips.create = AsyncMock()
        mock_client.trips.get = AsyncMock()
        mock_client.trips.update = AsyncMock()
        mock_client.trips.delete = AsyncMock()
        yield mock_client


@pytest.fixture
def mock_memory_client():
    """Fixture providing a mocked memory client."""
    with patch("src.utils.dual_storage.memory_client") as mock_client:
        mock_client.initialize = AsyncMock()
        mock_client.create_entities = AsyncMock()
        mock_client.create_relations = AsyncMock()
        mock_client.open_nodes = AsyncMock()
        mock_client.search_nodes = AsyncMock()
        mock_client.delete_entities = AsyncMock()
        yield mock_client


@pytest.fixture
def sample_trip_data():
    """Fixture providing sample trip data."""
    return {
        "title": "Summer Vacation",
        "description": "A relaxing beach vacation",
        "start_date": date(2025, 6, 15),
        "end_date": date(2025, 6, 30),
        "budget": 5000,
        "status": "planning",
        "destinations": [
            {
                "name": "Miami",
                "country": "USA",
                "type": "city",
                "description": "Beautiful beaches and vibrant nightlife"
            }
        ],
        "accommodations": [
            {
                "name": "Beachfront Resort",
                "type": "hotel",
                "destination": "Miami",
                "description": "Luxury resort with ocean views"
            }
        ],
        "activities": [
            {
                "name": "Snorkeling Tour",
                "destination": "Miami",
                "type": "water",
                "description": "Exploring coral reefs"
            }
        ]
    }


async def test_store_trip_with_dual_storage(mock_db_client, mock_memory_client, sample_trip_data):
    """Test storing trip data using the dual storage strategy."""
    # Arrange
    user_id = str(uuid4())
    trip_id = str(uuid4())
    mock_db_client.trips.create.return_value = {"id": trip_id, **sample_trip_data}
    mock_memory_client.create_entities.return_value = [{"name": f"Trip:{trip_id}"}]
    mock_memory_client.create_relations.return_value = [{"from": f"User:{user_id}", "to": f"Trip:{trip_id}"}]
    
    # Act
    result = await store_trip_with_dual_storage(sample_trip_data, user_id)
    
    # Assert
    mock_db_client.trips.create.assert_called_once()
    mock_memory_client.initialize.assert_called_once()
    mock_memory_client.create_entities.assert_called_once()
    mock_memory_client.create_relations.assert_called_once()
    assert result["supabase_id"] == trip_id
    assert result["neo4j_entities"] > 0
    assert result["neo4j_relations"] > 0


async def test_retrieve_trip_with_dual_storage(mock_db_client, mock_memory_client):
    """Test retrieving trip data using the dual storage strategy."""
    # Arrange
    trip_id = str(uuid4())
    db_trip = {
        "id": trip_id,
        "title": "Summer Vacation",
        "description": "A beach trip",
        "start_date": date(2025, 6, 15),
        "end_date": date(2025, 6, 30),
        "budget": 5000,
        "status": "planning",
    }
    trip_node = {
        "name": f"Trip:{trip_id}",
        "type": "Trip",
        "observations": ["Trip from 2025-06-15 to 2025-06-30", "Budget: $5000"]
    }
    mock_db_client.trips.get.return_value = db_trip
    mock_memory_client.open_nodes.return_value = [trip_node]
    
    # Act
    result = await retrieve_trip_with_dual_storage(trip_id)
    
    # Assert
    mock_db_client.trips.get.assert_called_once_with(trip_id)
    mock_memory_client.initialize.assert_called_once()
    mock_memory_client.open_nodes.assert_called_once_with([f"Trip:{trip_id}"])
    assert result["id"] == trip_id
    assert result["title"] == "Summer Vacation"
    assert "knowledge_graph" in result
    assert result["knowledge_graph"]["trip_node"] == trip_node


async def test_retrieve_trip_with_graph(mock_db_client, mock_memory_client):
    """Test retrieving trip data with full knowledge graph."""
    # Arrange
    trip_id = str(uuid4())
    db_trip = {
        "id": trip_id,
        "title": "Summer Vacation",
        "description": "A beach trip",
        "start_date": date(2025, 6, 15),
        "end_date": date(2025, 6, 30),
        "budget": 5000,
        "status": "planning",
    }
    trip_node = {
        "name": f"Trip:{trip_id}",
        "type": "Trip",
        "observations": ["Trip from 2025-06-15 to 2025-06-30", "Budget: $5000"]
    }
    mock_db_client.trips.get.return_value = db_trip
    mock_memory_client.open_nodes.return_value = [trip_node]
    search_results = [
        {"name": f"Trip:{trip_id}"},
        {"name": "Miami"},
        {"name": "Beachfront Resort"}
    ]
    mock_memory_client.search_nodes.return_value = search_results
    
    # Act
    result = await retrieve_trip_with_dual_storage(trip_id, include_graph=True)
    
    # Assert
    mock_db_client.trips.get.assert_called_once_with(trip_id)
    mock_memory_client.initialize.assert_called_once()
    mock_memory_client.open_nodes.assert_called()
    mock_memory_client.search_nodes.assert_called_once_with(f"Trip:{trip_id}")
    assert result["id"] == trip_id
    assert "knowledge_graph" in result
    assert "nodes" in result["knowledge_graph"]


async def test_update_trip_with_dual_storage(mock_db_client, mock_memory_client):
    """Test updating trip data using the dual storage strategy."""
    # Arrange
    trip_id = str(uuid4())
    update_data = {
        "title": "Updated Vacation",
        "description": "New description",
        "budget": 6000,
    }
    db_trip = {
        "id": trip_id,
        "title": "Updated Vacation",
        "description": "New description",
        "start_date": date(2025, 6, 15),
        "end_date": date(2025, 6, 30),
        "budget": 6000,
        "status": "planning",
    }
    mock_db_client.trips.update.return_value = db_trip
    mock_memory_client.open_nodes.return_value = [{
        "name": f"Trip:{trip_id}",
        "type": "Trip",
        "observations": ["Old observation"]
    }]
    mock_memory_client.add_observations.return_value = [{
        "name": f"Trip:{trip_id}",
        "observations": ["New observation"]
    }]
    
    # Act
    result = await update_trip_with_dual_storage(trip_id, update_data)
    
    # Assert
    mock_db_client.trips.update.assert_called_once_with(trip_id, {
        "title": "Updated Vacation",
        "description": "New description",
        "budget": 6000,
    })
    mock_memory_client.initialize.assert_called_once()
    mock_memory_client.open_nodes.assert_called_once_with([f"Trip:{trip_id}"])
    mock_memory_client.add_observations.assert_called_once()
    assert result["supabase_updated"] is True
    assert result["neo4j_updated"] is True


async def test_delete_trip_with_dual_storage(mock_db_client, mock_memory_client):
    """Test deleting trip data using the dual storage strategy."""
    # Arrange
    trip_id = str(uuid4())
    mock_db_client.trips.delete.return_value = True
    mock_memory_client.delete_entities.return_value = [f"Trip:{trip_id}"]
    
    # Act
    result = await delete_trip_with_dual_storage(trip_id)
    
    # Assert
    mock_db_client.trips.delete.assert_called_once_with(trip_id)
    mock_memory_client.initialize.assert_called_once()
    mock_memory_client.delete_entities.assert_called_once_with([f"Trip:{trip_id}"])
    assert result["supabase_deleted"] is True
    assert result["neo4j_deleted"] is True