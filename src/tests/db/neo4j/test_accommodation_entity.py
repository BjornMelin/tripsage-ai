"""Tests for Accommodation entity in Neo4j knowledge graph."""

from unittest.mock import AsyncMock, patch

import pytest

from src.db.neo4j.models.accommodation import Accommodation

pytestmark = pytest.mark.asyncio


async def test_accommodation_creation(mock_neo4j_client, sample_accommodation):
    """Test adding an accommodation to the knowledge graph."""
    # Setup
    mock_neo4j_client.add_accommodation = AsyncMock(return_value=sample_accommodation)

    # Execute
    accommodation_data = {
        "name": "Grand Hotel Paris",
        "destination": "Paris",
        "type": "hotel",
        "description": "Luxury hotel in the center of Paris",
        "price_per_night": 250.0,
    }
    accommodation = await mock_neo4j_client.add_accommodation(accommodation_data)

    # Assert
    assert accommodation is not None
    assert accommodation.name == "Grand Hotel Paris"
    assert accommodation.destination == "Paris"
    assert accommodation.type == "hotel"
    assert accommodation.description == "Luxury hotel in the center of Paris"
    assert accommodation.price_per_night == 250.0
    mock_neo4j_client.add_accommodation.assert_called_once()


async def test_accommodation_relationship_creation(
    mock_neo4j_client, sample_accommodation
):
    """Test creating a relationship between an accommodation and destination."""
    # Setup
    mock_neo4j_client.accommodation_repo.create_accommodation_destination_relationship = AsyncMock(
        return_value=True
    )

    # Execute
    result = await mock_neo4j_client.accommodation_repo.create_accommodation_destination_relationship(
        accommodation_name="Grand Hotel Paris", destination_name="Paris"
    )

    # Assert
    assert result is True
    mock_neo4j_client.accommodation_repo.create_accommodation_destination_relationship.assert_called_once_with(
        accommodation_name="Grand Hotel Paris", destination_name="Paris"
    )


async def test_get_accommodation(mock_neo4j_client, sample_accommodation):
    """Test retrieving an accommodation from the knowledge graph."""
    # Setup
    mock_neo4j_client.get_accommodation = AsyncMock(return_value=sample_accommodation)

    # Execute
    accommodation = await mock_neo4j_client.get_accommodation("Grand Hotel Paris")

    # Assert
    assert accommodation is not None
    assert accommodation.name == "Grand Hotel Paris"
    assert accommodation.destination == "Paris"
    assert accommodation.type == "hotel"
    assert accommodation.description == "Luxury hotel in the center of Paris"
    assert accommodation.price_per_night == 250.0
    mock_neo4j_client.get_accommodation.assert_called_once_with("Grand Hotel Paris")


async def test_update_accommodation(mock_neo4j_client, sample_accommodation):
    """Test updating an accommodation in the knowledge graph."""
    # Setup
    mock_neo4j_client.update_accommodation = AsyncMock(return_value=True)

    # Execute
    updated_data = sample_accommodation.dict()
    updated_data["price_per_night"] = 275.0  # Changed from 250.0
    updated_data["rating"] = 4.8  # Changed from 4.7

    result = await mock_neo4j_client.update_accommodation(
        "Grand Hotel Paris", updated_data
    )

    # Assert
    assert result is True
    mock_neo4j_client.update_accommodation.assert_called_once_with(
        "Grand Hotel Paris", updated_data
    )


async def test_delete_accommodation(mock_neo4j_client):
    """Test deleting an accommodation from the knowledge graph."""
    # Setup
    mock_neo4j_client.delete_accommodation = AsyncMock(return_value=True)

    # Execute
    result = await mock_neo4j_client.delete_accommodation("Grand Hotel Paris")

    # Assert
    assert result is True
    mock_neo4j_client.delete_accommodation.assert_called_once_with("Grand Hotel Paris")


async def test_find_accommodations_by_destination(
    mock_neo4j_client, sample_accommodation
):
    """Test finding accommodations by destination."""
    # Setup
    mock_neo4j_client.accommodation_repo.find_by_destination = AsyncMock(
        return_value=[sample_accommodation]
    )

    # Execute
    accommodations = await mock_neo4j_client.accommodation_repo.find_by_destination(
        "Paris"
    )

    # Assert
    assert len(accommodations) == 1
    assert accommodations[0].name == "Grand Hotel Paris"
    assert accommodations[0].destination == "Paris"
    mock_neo4j_client.accommodation_repo.find_by_destination.assert_called_once_with(
        "Paris"
    )


async def test_find_accommodations_by_type(mock_neo4j_client, sample_accommodation):
    """Test finding accommodations by type."""
    # Setup
    mock_neo4j_client.accommodation_repo.find_by_type = AsyncMock(
        return_value=[sample_accommodation]
    )

    # Execute
    accommodations = await mock_neo4j_client.accommodation_repo.find_by_type("hotel")

    # Assert
    assert len(accommodations) == 1
    assert accommodations[0].name == "Grand Hotel Paris"
    assert accommodations[0].type == "hotel"
    mock_neo4j_client.accommodation_repo.find_by_type.assert_called_once_with("hotel")


async def test_find_accommodations_by_price_range(
    mock_neo4j_client, sample_accommodation
):
    """Test finding accommodations by price range."""
    # Setup
    mock_neo4j_client.accommodation_repo.find_by_price_range = AsyncMock(
        return_value=[sample_accommodation]
    )

    # Execute
    accommodations = await mock_neo4j_client.accommodation_repo.find_by_price_range(
        min_price=200.0, max_price=300.0
    )

    # Assert
    assert len(accommodations) == 1
    assert accommodations[0].name == "Grand Hotel Paris"
    assert accommodations[0].price_per_night == 250.0
    mock_neo4j_client.accommodation_repo.find_by_price_range.assert_called_once_with(
        min_price=200.0, max_price=300.0
    )


async def test_find_accommodations_with_amenities(
    mock_neo4j_client, sample_accommodation
):
    """Test finding accommodations with specific amenities."""
    # Setup
    mock_neo4j_client.accommodation_repo.find_with_amenities = AsyncMock(
        return_value=[sample_accommodation]
    )

    # Execute
    amenities = ["wifi", "pool"]
    accommodations = await mock_neo4j_client.accommodation_repo.find_with_amenities(
        amenities=amenities
    )

    # Assert
    assert len(accommodations) == 1
    assert accommodations[0].name == "Grand Hotel Paris"
    assert "wifi" in accommodations[0].amenities
    assert "pool" in accommodations[0].amenities
    mock_neo4j_client.accommodation_repo.find_with_amenities.assert_called_once_with(
        amenities=amenities, destination=None
    )
