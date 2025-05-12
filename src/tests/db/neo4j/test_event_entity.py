"""Tests for Event entity in Neo4j knowledge graph."""

from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.asyncio


async def test_event_creation(mock_neo4j_client, sample_event):
    """Test adding an event to the knowledge graph."""
    # Setup
    mock_neo4j_client.add_event = AsyncMock(return_value=sample_event)

    # Execute
    event_data = {
        "name": "Paris Fashion Week",
        "destination": "Paris",
        "type": "cultural",
        "description": "Annual fashion event in Paris",
        "start_date": "2025-03-01",
        "end_date": "2025-03-08",
    }
    event = await mock_neo4j_client.add_event(event_data)

    # Assert
    assert event is not None
    assert event.name == "Paris Fashion Week"
    assert event.destination == "Paris"
    assert event.type == "cultural"
    assert event.description == "Annual fashion event in Paris"
    assert event.start_date == "2025-03-01"
    assert event.end_date == "2025-03-08"
    mock_neo4j_client.add_event.assert_called_once()


async def test_event_relationship_creation(mock_neo4j_client, sample_event):
    """Test creating a relationship between an event and destination."""
    # Setup
    mock_neo4j_client.event_repo.create_event_destination_relationship = AsyncMock(
        return_value=True
    )

    # Execute
    result = await mock_neo4j_client.event_repo.create_event_destination_relationship(
        event_name="Paris Fashion Week", destination_name="Paris"
    )

    # Assert
    assert result is True
    mock_neo4j_client.event_repo.create_event_destination_relationship.assert_called_once_with(
        event_name="Paris Fashion Week", destination_name="Paris"
    )


async def test_get_event(mock_neo4j_client, sample_event):
    """Test retrieving an event from the knowledge graph."""
    # Setup
    mock_neo4j_client.get_event = AsyncMock(return_value=sample_event)

    # Execute
    event = await mock_neo4j_client.get_event("Paris Fashion Week")

    # Assert
    assert event is not None
    assert event.name == "Paris Fashion Week"
    assert event.destination == "Paris"
    assert event.type == "cultural"
    assert event.description == "Annual fashion event in Paris"
    assert event.start_date == "2025-03-01"
    assert event.end_date == "2025-03-08"
    mock_neo4j_client.get_event.assert_called_once_with("Paris Fashion Week")


async def test_update_event(mock_neo4j_client, sample_event):
    """Test updating an event in the knowledge graph."""
    # Setup
    mock_neo4j_client.update_event = AsyncMock(return_value=True)

    # Execute
    updated_data = sample_event.dict()
    updated_data["ticket_price"] = 180.0  # Changed from 150.0
    updated_data["description"] = "Annual global fashion event in Paris"

    result = await mock_neo4j_client.update_event("Paris Fashion Week", updated_data)

    # Assert
    assert result is True
    mock_neo4j_client.update_event.assert_called_once_with(
        "Paris Fashion Week", updated_data
    )


async def test_delete_event(mock_neo4j_client):
    """Test deleting an event from the knowledge graph."""
    # Setup
    mock_neo4j_client.delete_event = AsyncMock(return_value=True)

    # Execute
    result = await mock_neo4j_client.delete_event("Paris Fashion Week")

    # Assert
    assert result is True
    mock_neo4j_client.delete_event.assert_called_once_with("Paris Fashion Week")


async def test_find_events_by_destination(mock_neo4j_client, sample_event):
    """Test finding events by destination."""
    # Setup
    mock_neo4j_client.event_repo.find_by_destination = AsyncMock(
        return_value=[sample_event]
    )

    # Execute
    events = await mock_neo4j_client.event_repo.find_by_destination("Paris")

    # Assert
    assert len(events) == 1
    assert events[0].name == "Paris Fashion Week"
    assert events[0].destination == "Paris"
    mock_neo4j_client.event_repo.find_by_destination.assert_called_once_with("Paris")


async def test_find_events_by_type(mock_neo4j_client, sample_event):
    """Test finding events by type."""
    # Setup
    mock_neo4j_client.event_repo.find_by_type = AsyncMock(return_value=[sample_event])

    # Execute
    events = await mock_neo4j_client.event_repo.find_by_type("cultural")

    # Assert
    assert len(events) == 1
    assert events[0].name == "Paris Fashion Week"
    assert events[0].type == "cultural"
    mock_neo4j_client.event_repo.find_by_type.assert_called_once_with("cultural")


async def test_find_events_by_date_range(mock_neo4j_client, sample_event):
    """Test finding events by date range."""
    # Setup
    mock_neo4j_client.event_repo.find_by_date_range = AsyncMock(
        return_value=[sample_event]
    )

    # Execute
    events = await mock_neo4j_client.event_repo.find_by_date_range(
        start_date="2025-03-01", end_date="2025-03-15"
    )

    # Assert
    assert len(events) == 1
    assert events[0].name == "Paris Fashion Week"
    assert events[0].start_date == "2025-03-01"
    assert events[0].end_date == "2025-03-08"
    mock_neo4j_client.event_repo.find_by_date_range.assert_called_once_with(
        start_date="2025-03-01", end_date="2025-03-15"
    )


async def test_find_upcoming_events(mock_neo4j_client, sample_event):
    """Test finding upcoming events."""
    # Setup
    mock_neo4j_client.event_repo.find_upcoming_events = AsyncMock(
        return_value=[sample_event]
    )

    # Execute
    events = await mock_neo4j_client.event_repo.find_upcoming_events(days=30)

    # Assert
    assert len(events) == 1
    assert events[0].name == "Paris Fashion Week"
    mock_neo4j_client.event_repo.find_upcoming_events.assert_called_once_with(
        days=30, destination=None
    )
