"""
Tests for the dual storage strategy implementation.

These tests verify that the dual storage strategy correctly stores and retrieves
data using the TripStorageService.

This test file is kept for backwards compatibility during the transition to
the new service-based architecture. New tests should use test_storage_service.py.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.utils.dual_storage import trip_service


@pytest.fixture
def mock_db_client():
    """Fixture providing a mocked database client."""
    with patch("src.utils.trip_storage_service.db_client") as mock_client:
        mock_client.trips = MagicMock()
        mock_client.trips.create = AsyncMock()
        mock_client.trips.get = AsyncMock()
        mock_client.trips.update = AsyncMock()
        mock_client.trips.delete = AsyncMock()
        yield mock_client


@pytest.fixture
def mock_memory_client():
    """Fixture providing a mocked memory client."""
    with patch("src.utils.trip_storage_service.memory_client") as mock_client:
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
                "description": "Beautiful beaches and vibrant nightlife",
            }
        ],
        "accommodations": [
            {
                "name": "Beachfront Resort",
                "type": "hotel",
                "destination": "Miami",
                "description": "Luxury resort with ocean views",
            }
        ],
        "activities": [
            {
                "name": "Snorkeling Tour",
                "destination": "Miami",
                "type": "water",
                "description": "Exploring coral reefs",
            }
        ],
    }


@pytest.mark.asyncio
async def test_trip_service_create(
    mock_db_client, mock_memory_client, sample_trip_data
):
    """Test creating a trip using the TripStorageService."""
    # Arrange
    user_id = str(uuid4())
    sample_trip_data["user_id"] = user_id
    trip_id = str(uuid4())

    mock_db_client.trips.create.return_value = {"id": trip_id, **sample_trip_data}
    mock_memory_client.create_entities.return_value = [{"name": f"Trip:{trip_id}"}]
    mock_memory_client.create_relations.return_value = [
        {"from": f"User:{user_id}", "to": f"Trip:{trip_id}"}
    ]

    # Act
    result = await trip_service.create(sample_trip_data)

    # Assert
    mock_db_client.trips.create.assert_called_once()
    mock_memory_client.create_entities.assert_called_once()
    mock_memory_client.create_relations.assert_called_once()

    assert result["trip_id"] == trip_id
    assert result["entities_created"] == 1
    assert result["relations_created"] == 1


@pytest.mark.asyncio
async def test_trip_service_retrieve(mock_db_client, mock_memory_client):
    """Test retrieving a trip using the TripStorageService."""
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
        "observations": ["Trip from 2025-06-15 to 2025-06-30", "Budget: $5000"],
    }

    mock_db_client.trips.get.return_value = db_trip
    mock_memory_client.open_nodes.return_value = [trip_node]

    # Act
    result = await trip_service.retrieve(trip_id)

    # Assert
    mock_db_client.trips.get.assert_called_once_with(trip_id)
    mock_memory_client.open_nodes.assert_called_once()

    assert result["knowledge_graph"]["trip_node"] == trip_node


@pytest.mark.asyncio
async def test_trip_service_update(mock_db_client, mock_memory_client):
    """Test updating a trip using the TripStorageService."""
    # Arrange
    trip_id = str(uuid4())
    update_data = {
        "title": "Updated Vacation",
        "description": "New description",
        "budget": 6000,
    }

    mock_db_client.trips.update.return_value = True
    mock_memory_client.open_nodes.return_value = [
        {"name": f"Trip:{trip_id}", "type": "Trip", "observations": ["Old observation"]}
    ]
    mock_memory_client.add_observations.return_value = [
        {"name": f"Trip:{trip_id}", "observations": ["New observation"]}
    ]

    # Act
    result = await trip_service.update(trip_id, update_data)

    # Assert
    mock_db_client.trips.update.assert_called_once()
    mock_memory_client.add_observations.assert_called_once()

    assert result["trip_id"] == trip_id
    assert result["primary_db_updated"] is True
    assert result["graph_db_updated"] is True


@pytest.mark.asyncio
async def test_trip_service_delete(mock_db_client, mock_memory_client):
    """Test deleting a trip using the TripStorageService."""
    # Arrange
    trip_id = str(uuid4())

    mock_db_client.trips.delete.return_value = True
    mock_memory_client.delete_entities.return_value = [f"Trip:{trip_id}"]

    # Act
    result = await trip_service.delete(trip_id)

    # Assert
    mock_db_client.trips.delete.assert_called_once_with(trip_id)
    mock_memory_client.delete_entities.assert_called_once_with([f"Trip:{trip_id}"])

    assert result["trip_id"] == trip_id
    assert result["primary_db_deleted"] is True
    assert result["graph_db_deleted"] is True
