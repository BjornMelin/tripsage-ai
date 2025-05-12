"""Test fixtures for Neo4j database tests."""

from typing import Any, AsyncGenerator, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.db.neo4j.client import Neo4jClient
from src.db.neo4j.models.accommodation import Accommodation
from src.db.neo4j.models.activity import Activity
from src.db.neo4j.models.destination import Destination
from src.db.neo4j.models.event import Event
from src.db.neo4j.models.transportation import Transportation
from src.mcp.memory.client import MemoryClient


@pytest.fixture
def mock_neo4j_connection() -> MagicMock:
    """Return a mock Neo4j connection."""
    mock_connection = MagicMock()
    mock_session = AsyncMock()

    # Mock run method for Cypher queries
    mock_session.run = AsyncMock()
    mock_records = [MagicMock()]
    mock_session.run.return_value.records = mock_records

    # Mock connection's session context manager
    mock_connection.session.return_value.__aenter__.return_value = mock_session

    return mock_connection


@pytest_asyncio.fixture
async def mock_neo4j_client(mock_neo4j_connection) -> AsyncGenerator[Neo4jClient, None]:
    """Return a mock Neo4j client with testing data."""
    with patch(
        "src.db.neo4j.client.Neo4jConnection", return_value=mock_neo4j_connection
    ):
        client = Neo4jClient()
        await client.initialize()
        yield client


@pytest.fixture
def sample_destination() -> Destination:
    """Return a sample destination for testing."""
    return Destination(
        name="Paris",
        country="France",
        type="city",
        description="The capital of France, known for the Eiffel Tower",
        latitude=48.8566,
        longitude=2.3522,
        region="Île-de-France",
        city="Paris",
        safety_rating=4.5,
        cost_level="high",
    )


@pytest.fixture
def sample_activity() -> Activity:
    """Return a sample activity for testing."""
    return Activity(
        name="Eiffel Tower Visit",
        destination="Paris",
        type="landmark",
        description="Visit the iconic Eiffel Tower",
        duration=3.0,
        price=25.0,
        rating=4.8,
        availability="daily",
        booking_required=True,
    )


@pytest.fixture
def sample_accommodation() -> Accommodation:
    """Return a sample accommodation for testing."""
    return Accommodation(
        name="Grand Hotel Paris",
        destination="Paris",
        type="hotel",
        description="Luxury hotel in the center of Paris",
        rating=4.7,
        price_per_night=250.0,
        address="123 Champs-Élysées, Paris",
        amenities=["wifi", "pool", "spa", "restaurant"],
        available=True,
    )


@pytest.fixture
def sample_event() -> Event:
    """Return a sample event for testing."""
    return Event(
        name="Paris Fashion Week",
        destination="Paris",
        type="cultural",
        description="Annual fashion event in Paris",
        start_date="2025-03-01",
        end_date="2025-03-08",
        venue="Grand Palais",
        ticket_price=150.0,
        website="https://parisfashionweek.example.com",
    )


@pytest.fixture
def sample_transportation() -> Transportation:
    """Return a sample transportation for testing."""
    return Transportation(
        name="Paris-London Train",
        type="train",
        description="High-speed train from Paris to London",
        origin="Paris",
        destination="London",
        price=89.0,
        duration=2.5,
        company="Eurostar",
        schedule="daily",
    )


@pytest_asyncio.fixture
async def memory_client_with_mocks(
    mock_neo4j_client,
) -> AsyncGenerator[MemoryClient, None]:
    """Return a MemoryClient with mocked Neo4j backend."""
    with patch("src.mcp.memory.client.neo4j_client", mock_neo4j_client):
        client = MemoryClient()
        await client.initialize()
        yield client


@pytest.fixture
def sample_entities() -> List[Dict[str, Any]]:
    """Return a list of sample entities in the Memory MCP format."""
    return [
        {
            "name": "Paris",
            "entityType": "Destination",
            "observations": [
                "The capital of France",
                "Known for the Eiffel Tower",
                "A popular romantic destination",
            ],
            "country": "France",
            "type": "city",
        },
        {
            "name": "Eiffel Tower Visit",
            "entityType": "Activity",
            "observations": [
                "Iconic landmark in Paris",
                "Built in 1889",
                "Offers panoramic views of the city",
            ],
            "destination": "Paris",
            "type": "landmark",
        },
        {
            "name": "Grand Hotel Paris",
            "entityType": "Accommodation",
            "observations": [
                "Luxury hotel in central Paris",
                "Walking distance to major attractions",
                "Features a rooftop restaurant",
            ],
            "destination": "Paris",
            "type": "hotel",
        },
        {
            "name": "Paris Fashion Week",
            "entityType": "Event",
            "observations": [
                "Major fashion industry event",
                "Showcases latest designer collections",
                "Attended by celebrities and fashion journalists",
            ],
            "destination": "Paris",
            "type": "cultural",
        },
        {
            "name": "Paris-London Train",
            "entityType": "Transportation",
            "observations": [
                "High-speed rail service",
                "Travels through the Channel Tunnel",
                "Faster than flying when including check-in time",
            ],
            "origin": "Paris",
            "destination": "London",
            "type": "train",
        },
    ]


@pytest.fixture
def sample_relations() -> List[Dict[str, Any]]:
    """Return a list of sample relations in the Memory MCP format."""
    return [
        {"from": "Eiffel Tower Visit", "relationType": "LOCATED_IN", "to": "Paris"},
        {"from": "Grand Hotel Paris", "relationType": "LOCATED_IN", "to": "Paris"},
        {"from": "Paris Fashion Week", "relationType": "TAKES_PLACE_IN", "to": "Paris"},
        {"from": "Paris-London Train", "relationType": "DEPARTS_FROM", "to": "Paris"},
        {"from": "Paris-London Train", "relationType": "ARRIVES_AT", "to": "London"},
    ]
