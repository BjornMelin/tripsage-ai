"""Tests for Activity entity in Neo4j knowledge graph."""

from unittest.mock import AsyncMock, patch

import pytest

from src.db.neo4j.models.activity import Activity

pytestmark = pytest.mark.asyncio


async def test_activity_creation(mock_neo4j_client, sample_activity):
    """Test adding an activity to the knowledge graph."""
    # Setup
    mock_neo4j_client.add_activity = AsyncMock(return_value=sample_activity)

    # Execute
    activity_data = {
        "name": "Eiffel Tower Visit",
        "destination": "Paris",
        "type": "landmark",
        "description": "Visit the iconic Eiffel Tower",
    }
    activity = await mock_neo4j_client.add_activity(activity_data)

    # Assert
    assert activity is not None
    assert activity.name == "Eiffel Tower Visit"
    assert activity.destination == "Paris"
    assert activity.type == "landmark"
    assert activity.description == "Visit the iconic Eiffel Tower"
    mock_neo4j_client.add_activity.assert_called_once()


async def test_activity_relationship_creation(mock_neo4j_client, sample_activity):
    """Test creating a relationship between an activity and destination."""
    # Setup
    mock_neo4j_client.activity_repo.create_activity_destination_relationship = (
        AsyncMock(return_value=True)
    )

    # Execute
    result = (
        await mock_neo4j_client.activity_repo.create_activity_destination_relationship(
            activity_name="Eiffel Tower Visit", destination_name="Paris"
        )
    )

    # Assert
    assert result is True
    mock_neo4j_client.activity_repo.create_activity_destination_relationship.assert_called_once_with(
        activity_name="Eiffel Tower Visit", destination_name="Paris"
    )


async def test_get_activity(mock_neo4j_client, sample_activity):
    """Test retrieving an activity from the knowledge graph."""
    # Setup
    mock_neo4j_client.get_activity = AsyncMock(return_value=sample_activity)

    # Execute
    activity = await mock_neo4j_client.get_activity("Eiffel Tower Visit")

    # Assert
    assert activity is not None
    assert activity.name == "Eiffel Tower Visit"
    assert activity.destination == "Paris"
    assert activity.type == "landmark"
    assert activity.description == "Visit the iconic Eiffel Tower"
    mock_neo4j_client.get_activity.assert_called_once_with("Eiffel Tower Visit")


async def test_update_activity(mock_neo4j_client, sample_activity):
    """Test updating an activity in the knowledge graph."""
    # Setup
    mock_neo4j_client.update_activity = AsyncMock(return_value=True)

    # Execute
    updated_data = sample_activity.dict()
    updated_data["price"] = 30.0  # Changed from 25.0
    updated_data["description"] = "Visit the iconic Eiffel Tower - Skip the line!"

    result = await mock_neo4j_client.update_activity("Eiffel Tower Visit", updated_data)

    # Assert
    assert result is True
    mock_neo4j_client.update_activity.assert_called_once_with(
        "Eiffel Tower Visit", updated_data
    )


async def test_delete_activity(mock_neo4j_client):
    """Test deleting an activity from the knowledge graph."""
    # Setup
    mock_neo4j_client.delete_activity = AsyncMock(return_value=True)

    # Execute
    result = await mock_neo4j_client.delete_activity("Eiffel Tower Visit")

    # Assert
    assert result is True
    mock_neo4j_client.delete_activity.assert_called_once_with("Eiffel Tower Visit")


async def test_find_activities_by_destination(mock_neo4j_client, sample_activity):
    """Test finding activities by destination."""
    # Setup
    mock_neo4j_client.activity_repo.find_by_destination = AsyncMock(
        return_value=[sample_activity]
    )

    # Execute
    activities = await mock_neo4j_client.activity_repo.find_by_destination("Paris")

    # Assert
    assert len(activities) == 1
    assert activities[0].name == "Eiffel Tower Visit"
    assert activities[0].destination == "Paris"
    mock_neo4j_client.activity_repo.find_by_destination.assert_called_once_with("Paris")


async def test_find_activities_by_type(mock_neo4j_client, sample_activity):
    """Test finding activities by type."""
    # Setup
    mock_neo4j_client.activity_repo.find_by_type = AsyncMock(
        return_value=[sample_activity]
    )

    # Execute
    activities = await mock_neo4j_client.activity_repo.find_by_type("landmark")

    # Assert
    assert len(activities) == 1
    assert activities[0].name == "Eiffel Tower Visit"
    assert activities[0].type == "landmark"
    mock_neo4j_client.activity_repo.find_by_type.assert_called_once_with("landmark")


async def test_find_activities_by_price_range(mock_neo4j_client, sample_activity):
    """Test finding activities by price range."""
    # Setup
    mock_neo4j_client.activity_repo.find_by_price_range = AsyncMock(
        return_value=[sample_activity]
    )

    # Execute
    activities = await mock_neo4j_client.activity_repo.find_by_price_range(
        min_price=20.0, max_price=30.0
    )

    # Assert
    assert len(activities) == 1
    assert activities[0].name == "Eiffel Tower Visit"
    assert activities[0].price == 25.0
    mock_neo4j_client.activity_repo.find_by_price_range.assert_called_once_with(
        min_price=20.0, max_price=30.0
    )


async def test_find_activities_by_rating(mock_neo4j_client, sample_activity):
    """Test finding activities by rating."""
    # Setup
    mock_neo4j_client.activity_repo.find_by_rating = AsyncMock(
        return_value=[sample_activity]
    )

    # Execute
    activities = await mock_neo4j_client.activity_repo.find_by_rating(min_rating=4.5)

    # Assert
    assert len(activities) == 1
    assert activities[0].name == "Eiffel Tower Visit"
    assert activities[0].rating == 4.8
    mock_neo4j_client.activity_repo.find_by_rating.assert_called_once_with(
        min_rating=4.5
    )
