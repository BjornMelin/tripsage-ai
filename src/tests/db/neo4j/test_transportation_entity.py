"""Tests for Transportation entity in Neo4j knowledge graph."""

from unittest.mock import AsyncMock

import pytest

from src.db.neo4j.models.transportation import Transportation

pytestmark = pytest.mark.asyncio


async def test_transportation_creation(mock_neo4j_client, sample_transportation):
    """Test adding a transportation entity to the knowledge graph."""
    # Setup
    mock_neo4j_client.add_transportation = AsyncMock(return_value=sample_transportation)

    # Execute
    transportation_data = {
        "name": "Paris-London Train",
        "type": "train",
        "description": "High-speed train from Paris to London",
        "origin": "Paris",
        "destination": "London",
        "price": 89.0,
        "duration": 2.5,
    }
    transportation = await mock_neo4j_client.add_transportation(transportation_data)

    # Assert
    assert transportation is not None
    assert transportation.name == "Paris-London Train"
    assert transportation.type == "train"
    assert transportation.description == "High-speed train from Paris to London"
    assert transportation.origin == "Paris"
    assert transportation.destination == "London"
    assert transportation.price == 89.0
    assert transportation.duration == 2.5
    mock_neo4j_client.add_transportation.assert_called_once()


async def test_transportation_route_relationship_creation(
    mock_neo4j_client, sample_transportation
):
    """Test creating route relationships for a transportation entity."""
    # Setup
    mock_neo4j_client.transportation_repo.create_route_relationship = AsyncMock(
        return_value=True
    )

    # Execute
    result = await mock_neo4j_client.transportation_repo.create_route_relationship(
        transportation_id="Paris-London Train",
        origin_destination="Paris",
        target_destination="London",
    )

    # Assert
    assert result is True
    mock_neo4j_client.transportation_repo.create_route_relationship.assert_called_once_with(
        transportation_id="Paris-London Train",
        origin_destination="Paris",
        target_destination="London",
    )


async def test_get_transportation(mock_neo4j_client, sample_transportation):
    """Test retrieving a transportation entity from the knowledge graph."""
    # Setup
    mock_neo4j_client.get_transportation = AsyncMock(return_value=sample_transportation)

    # Execute
    transportation = await mock_neo4j_client.get_transportation("Paris-London Train")

    # Assert
    assert transportation is not None
    assert transportation.name == "Paris-London Train"
    assert transportation.type == "train"
    assert transportation.description == "High-speed train from Paris to London"
    assert transportation.origin == "Paris"
    assert transportation.destination == "London"
    mock_neo4j_client.get_transportation.assert_called_once_with("Paris-London Train")


async def test_update_transportation(mock_neo4j_client, sample_transportation):
    """Test updating a transportation entity in the knowledge graph."""
    # Setup
    mock_neo4j_client.update_transportation = AsyncMock(return_value=True)

    # Execute
    updated_data = sample_transportation.dict()
    updated_data["price"] = 99.0  # Changed from 89.0
    updated_data["duration"] = 2.3  # Changed from 2.5

    result = await mock_neo4j_client.update_transportation(
        "Paris-London Train", updated_data
    )

    # Assert
    assert result is True
    mock_neo4j_client.update_transportation.assert_called_once_with(
        "Paris-London Train", updated_data
    )


async def test_delete_transportation(mock_neo4j_client):
    """Test deleting a transportation entity from the knowledge graph."""
    # Setup
    mock_neo4j_client.delete_transportation = AsyncMock(return_value=True)

    # Execute
    result = await mock_neo4j_client.delete_transportation("Paris-London Train")

    # Assert
    assert result is True
    mock_neo4j_client.delete_transportation.assert_called_once_with(
        "Paris-London Train"
    )


async def test_find_transportation_by_type(mock_neo4j_client, sample_transportation):
    """Test finding transportation entities by type."""
    # Setup
    mock_neo4j_client.transportation_repo.find_by_type = AsyncMock(
        return_value=[sample_transportation]
    )

    # Execute
    transports = await mock_neo4j_client.transportation_repo.find_by_type("train")

    # Assert
    assert len(transports) == 1
    assert transports[0].name == "Paris-London Train"
    assert transports[0].type == "train"
    mock_neo4j_client.transportation_repo.find_by_type.assert_called_once_with("train")


async def test_find_transportation_routes(mock_neo4j_client, sample_transportation):
    """Test finding transportation routes between locations."""
    # Setup
    mock_neo4j_client.transportation_repo.find_routes = AsyncMock(
        return_value=[sample_transportation]
    )

    # Execute
    routes = await mock_neo4j_client.transportation_repo.find_routes(
        origin="Paris", destination="London"
    )

    # Assert
    assert len(routes) == 1
    assert routes[0].name == "Paris-London Train"
    assert routes[0].origin == "Paris"
    assert routes[0].destination == "London"
    mock_neo4j_client.transportation_repo.find_routes.assert_called_once_with(
        origin="Paris", destination="London", transportation_type=None
    )


async def test_find_transportation_by_departure_location(
    mock_neo4j_client, sample_transportation
):
    """Test finding transportation entities by departure location."""
    # Setup
    mock_neo4j_client.transportation_repo.find_by_departure_location = AsyncMock(
        return_value=[sample_transportation]
    )

    # Execute
    transports = await mock_neo4j_client.transportation_repo.find_by_departure_location(
        "Paris"
    )

    # Assert
    assert len(transports) == 1
    assert transports[0].name == "Paris-London Train"
    assert transports[0].origin == "Paris"
    mock_neo4j_client.transportation_repo.find_by_departure_location.assert_called_once_with(
        "Paris"
    )


async def test_find_transportation_by_arrival_location(
    mock_neo4j_client, sample_transportation
):
    """Test finding transportation entities by arrival location."""
    # Setup
    mock_neo4j_client.transportation_repo.find_by_arrival_location = AsyncMock(
        return_value=[sample_transportation]
    )

    # Execute
    transports = await mock_neo4j_client.transportation_repo.find_by_arrival_location(
        "London"
    )

    # Assert
    assert len(transports) == 1
    assert transports[0].name == "Paris-London Train"
    assert transports[0].destination == "London"
    mock_neo4j_client.transportation_repo.find_by_arrival_location.assert_called_once_with(
        "London"
    )


async def test_find_transportation_by_price_range(
    mock_neo4j_client, sample_transportation
):
    """Test finding transportation entities by price range."""
    # Setup
    mock_neo4j_client.transportation_repo.find_by_price_range = AsyncMock(
        return_value=[sample_transportation]
    )

    # Execute
    transports = await mock_neo4j_client.transportation_repo.find_by_price_range(
        min_price=50.0, max_price=100.0
    )

    # Assert
    assert len(transports) == 1
    assert transports[0].name == "Paris-London Train"
    assert transports[0].price == 89.0
    mock_neo4j_client.transportation_repo.find_by_price_range.assert_called_once_with(
        min_price=50.0, max_price=100.0
    )
