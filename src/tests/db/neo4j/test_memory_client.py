"""Tests for Memory client integration with Neo4j knowledge graph."""

from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.asyncio


async def test_create_entities(
    memory_client_with_mocks,
    sample_entities,
    sample_destination,
    sample_activity,
    sample_accommodation,
    sample_event,
    sample_transportation,
):
    """Test creating multiple entity types in the knowledge graph."""
    # Setup
    mocked_client = memory_client_with_mocks

    # Mock the Neo4j client calls
    mocked_client.neo4j_client.add_destination = AsyncMock(
        return_value=sample_destination
    )
    mocked_client.neo4j_client.add_activity = AsyncMock(return_value=sample_activity)
    mocked_client.neo4j_client.add_accommodation = AsyncMock(
        return_value=sample_accommodation
    )
    mocked_client.neo4j_client.add_event = AsyncMock(return_value=sample_event)
    mocked_client.neo4j_client.add_transportation = AsyncMock(
        return_value=sample_transportation
    )

    # Also mock relationship creation methods
    mocked_client.neo4j_client.activity_repo.create_activity_destination_relationship = AsyncMock(  # noqa: E501
        return_value=True
    )
    mocked_client.neo4j_client.accommodation_repo.create_accommodation_destination_relationship = AsyncMock(  # noqa: E501
        return_value=True
    )
    mocked_client.neo4j_client.event_repo.create_event_destination_relationship = (
        AsyncMock(return_value=True)
    )
    mocked_client.neo4j_client.transportation_repo.create_route_relationship = (
        AsyncMock(return_value=True)
    )

    # Execute
    created_entities = await mocked_client.create_entities(sample_entities)

    # Assert
    assert len(created_entities) == 5
    assert mocked_client.neo4j_client.add_destination.called
    assert mocked_client.neo4j_client.add_activity.called
    assert mocked_client.neo4j_client.add_accommodation.called
    assert mocked_client.neo4j_client.add_event.called
    assert mocked_client.neo4j_client.add_transportation.called

    # Verify relationship creation
    assert mocked_client.neo4j_client.activity_repo.create_activity_destination_relationship.called  # noqa: E501
    assert mocked_client.neo4j_client.accommodation_repo.create_accommodation_destination_relationship.called  # noqa: E501
    assert mocked_client.neo4j_client.event_repo.create_event_destination_relationship.called  # noqa: E501
    assert (
        mocked_client.neo4j_client.transportation_repo.create_route_relationship.called
    )

    # Verify created entity types
    entity_types = [entity["entityType"] for entity in created_entities]
    assert "Destination" in entity_types
    assert "Activity" in entity_types
    assert "Accommodation" in entity_types
    assert "Event" in entity_types
    assert "Transportation" in entity_types


async def test_create_relations(memory_client_with_mocks, sample_relations):
    """Test creating relations between different entity types."""
    # Setup
    mocked_client = memory_client_with_mocks

    # Mock the Neo4j client call for execute_query
    mock_record = {
        "from_name": "Paris-London Train",
        "relation_type": "DEPARTS_FROM",
        "to_name": "Paris",
    }
    mocked_client.neo4j_client.execute_query = AsyncMock(return_value=[mock_record])

    # Execute
    created_relations = await mocked_client.create_relations(sample_relations)

    # Assert
    assert len(created_relations) == len(sample_relations)
    assert mocked_client.neo4j_client.execute_query.call_count == len(sample_relations)

    # Check one of the relations
    assert created_relations[0]["from"] == "Paris-London Train"
    assert created_relations[0]["relationType"] == "DEPARTS_FROM"
    assert created_relations[0]["to"] == "Paris"


async def test_add_observations(
    memory_client_with_mocks,
    sample_destination,
    sample_activity,
    sample_accommodation,
    sample_event,
    sample_transportation,
):
    """Test adding observations to different entity types."""
    # Setup
    mocked_client = memory_client_with_mocks

    # Mock the entity lookup
    mocked_client.neo4j_client.execute_query = AsyncMock()

    # Mock results for entity type lookup
    mocked_client.neo4j_client.execute_query.side_effect = [
        [{"entity_type": "Destination"}],
        [{"entity_type": "Activity"}],
        [{"entity_type": "Accommodation"}],
        [{"entity_type": "Event"}],
        [{"entity_type": "Transportation"}],
    ]

    # Mock get entity methods
    mocked_client.neo4j_client.get_destination = AsyncMock(
        return_value=sample_destination
    )
    mocked_client.neo4j_client.get_activity = AsyncMock(return_value=sample_activity)
    mocked_client.neo4j_client.get_accommodation = AsyncMock(
        return_value=sample_accommodation
    )
    mocked_client.neo4j_client.get_event = AsyncMock(return_value=sample_event)
    mocked_client.neo4j_client.get_transportation = AsyncMock(
        return_value=sample_transportation
    )

    # Mock update entity methods
    mocked_client.neo4j_client.update_destination = AsyncMock(return_value=True)
    mocked_client.neo4j_client.update_activity = AsyncMock(return_value=True)
    mocked_client.neo4j_client.update_accommodation = AsyncMock(return_value=True)
    mocked_client.neo4j_client.update_event = AsyncMock(return_value=True)
    mocked_client.neo4j_client.update_transportation = AsyncMock(return_value=True)

    # Prepare test observations
    observations = [
        {"entityName": "Paris", "contents": ["New observation for Paris"]},
        {
            "entityName": "Eiffel Tower Visit",
            "contents": ["New observation for Eiffel Tower"],
        },
        {
            "entityName": "Grand Hotel Paris",
            "contents": ["New observation for Grand Hotel"],
        },
        {
            "entityName": "Paris Fashion Week",
            "contents": ["New observation for Fashion Week"],
        },
        {"entityName": "Paris-London Train", "contents": ["New observation for train"]},
    ]

    # Execute
    updated_entities = await mocked_client.add_observations(observations)

    # Assert
    assert len(updated_entities) == 5
    assert mocked_client.neo4j_client.update_destination.called
    assert mocked_client.neo4j_client.update_activity.called
    assert mocked_client.neo4j_client.update_accommodation.called
    assert mocked_client.neo4j_client.update_event.called
    assert mocked_client.neo4j_client.update_transportation.called


async def test_delete_entities(
    memory_client_with_mocks,
    sample_destination,
    sample_activity,
    sample_accommodation,
    sample_event,
    sample_transportation,
):
    """Test deleting different entity types."""
    # Setup
    mocked_client = memory_client_with_mocks

    # Mock get entity methods
    mocked_client.neo4j_client.get_destination = AsyncMock(
        side_effect=[sample_destination, None, None, None, None]
    )
    mocked_client.neo4j_client.get_activity = AsyncMock(
        side_effect=[None, sample_activity, None, None, None]
    )
    mocked_client.neo4j_client.get_accommodation = AsyncMock(
        side_effect=[None, None, sample_accommodation, None, None]
    )
    mocked_client.neo4j_client.get_event = AsyncMock(
        side_effect=[None, None, None, sample_event, None]
    )
    mocked_client.neo4j_client.get_transportation = AsyncMock(
        side_effect=[None, None, None, None, sample_transportation]
    )

    # Mock delete entity methods
    mocked_client.neo4j_client.delete_destination = AsyncMock(return_value=True)
    mocked_client.neo4j_client.delete_activity = AsyncMock(return_value=True)
    mocked_client.neo4j_client.delete_accommodation = AsyncMock(return_value=True)
    mocked_client.neo4j_client.delete_event = AsyncMock(return_value=True)
    mocked_client.neo4j_client.delete_transportation = AsyncMock(return_value=True)

    # Prepare entity names to delete
    entity_names = [
        "Paris",
        "Eiffel Tower Visit",
        "Grand Hotel Paris",
        "Paris Fashion Week",
        "Paris-London Train",
    ]

    # Execute
    deleted_entities = await mocked_client.delete_entities(entity_names)

    # Assert
    assert len(deleted_entities) == 5
    assert mocked_client.neo4j_client.delete_destination.called
    assert mocked_client.neo4j_client.delete_activity.called
    assert mocked_client.neo4j_client.delete_accommodation.called
    assert mocked_client.neo4j_client.delete_event.called
    assert mocked_client.neo4j_client.delete_transportation.called

    # Check all entities were deleted
    for name in entity_names:
        assert name in deleted_entities


async def test_delete_observations(
    memory_client_with_mocks,
    sample_destination,
    sample_activity,
    sample_accommodation,
    sample_event,
    sample_transportation,
):
    """Test deleting observations from different entity types."""
    # Setup
    mocked_client = memory_client_with_mocks

    # Mock the entity lookup
    mocked_client.neo4j_client.execute_query = AsyncMock()

    # Mock results for entity type lookup
    mocked_client.neo4j_client.execute_query.side_effect = [
        [{"entity_type": "Destination"}],
        [{"entity_type": "Activity"}],
        [{"entity_type": "Accommodation"}],
        [{"entity_type": "Event"}],
        [{"entity_type": "Transportation"}],
    ]

    # Add descriptions to sample entities
    sample_destination.description = "Line 1\nLine 2\nLine to delete"
    sample_activity.description = "Line 1\nLine 2\nLine to delete"
    sample_accommodation.description = "Line 1\nLine 2\nLine to delete"
    sample_event.description = "Line 1\nLine 2\nLine to delete"
    sample_transportation.description = "Line 1\nLine 2\nLine to delete"

    # Mock get entity methods
    mocked_client.neo4j_client.get_destination = AsyncMock(
        return_value=sample_destination
    )
    mocked_client.neo4j_client.get_activity = AsyncMock(return_value=sample_activity)
    mocked_client.neo4j_client.get_accommodation = AsyncMock(
        return_value=sample_accommodation
    )
    mocked_client.neo4j_client.get_event = AsyncMock(return_value=sample_event)
    mocked_client.neo4j_client.get_transportation = AsyncMock(
        return_value=sample_transportation
    )

    # Mock update entity methods
    mocked_client.neo4j_client.update_destination = AsyncMock(return_value=True)
    mocked_client.neo4j_client.update_activity = AsyncMock(return_value=True)
    mocked_client.neo4j_client.update_accommodation = AsyncMock(return_value=True)
    mocked_client.neo4j_client.update_event = AsyncMock(return_value=True)
    mocked_client.neo4j_client.update_transportation = AsyncMock(return_value=True)

    # Prepare test deletion requests
    deletions = [
        {"entityName": "Paris", "observations": ["Line to delete"]},
        {"entityName": "Eiffel Tower Visit", "observations": ["Line to delete"]},
        {"entityName": "Grand Hotel Paris", "observations": ["Line to delete"]},
        {"entityName": "Paris Fashion Week", "observations": ["Line to delete"]},
        {"entityName": "Paris-London Train", "observations": ["Line to delete"]},
    ]

    # Execute
    updated_entities = await mocked_client.delete_observations(deletions)

    # Assert
    assert len(updated_entities) == 5
    assert mocked_client.neo4j_client.update_destination.called
    assert mocked_client.neo4j_client.update_activity.called
    assert mocked_client.neo4j_client.update_accommodation.called
    assert mocked_client.neo4j_client.update_event.called
    assert mocked_client.neo4j_client.update_transportation.called


async def test_read_graph(memory_client_with_mocks):
    """Test reading the entire knowledge graph."""
    # Setup
    mocked_client = memory_client_with_mocks

    # Mock the Neo4j client call to get statistics
    mocked_client.neo4j_client.get_graph_statistics = AsyncMock(
        return_value={"nodes": 10, "relationships": 5}
    )

    # Mock the Neo4j client calls to execute queries
    entities_result = [
        {
            "e": {"name": "Paris", "description": "Capital of France", "type": "city"},
            "entity_type": "Destination",
        },
        {
            "e": {
                "name": "Eiffel Tower Visit",
                "description": "Famous landmark",
                "type": "landmark",
            },
            "entity_type": "Activity",
        },
        {
            "e": {
                "name": "Grand Hotel Paris",
                "description": "Luxury hotel",
                "type": "hotel",
            },
            "entity_type": "Accommodation",
        },
        {
            "e": {
                "name": "Paris Fashion Week",
                "description": "Fashion event",
                "type": "cultural",
            },
            "entity_type": "Event",
        },
        {
            "e": {
                "name": "Paris-London Train",
                "description": "High-speed train",
                "type": "train",
            },
            "entity_type": "Transportation",
        },
    ]

    relations_result = [
        {
            "from_name": "Eiffel Tower Visit",
            "relation_type": "LOCATED_IN",
            "to_name": "Paris",
        },
        {
            "from_name": "Grand Hotel Paris",
            "relation_type": "LOCATED_IN",
            "to_name": "Paris",
        },
        {
            "from_name": "Paris Fashion Week",
            "relation_type": "TAKES_PLACE_IN",
            "to_name": "Paris",
        },
        {
            "from_name": "Paris-London Train",
            "relation_type": "DEPARTS_FROM",
            "to_name": "Paris",
        },
        {
            "from_name": "Paris-London Train",
            "relation_type": "ARRIVES_AT",
            "to_name": "London",
        },
    ]

    mocked_client.neo4j_client.execute_query = AsyncMock()
    mocked_client.neo4j_client.execute_query.side_effect = [
        entities_result,
        relations_result,
    ]

    # Execute
    graph = await mocked_client.read_graph()

    # Assert
    assert "entities" in graph
    assert "relations" in graph
    assert "statistics" in graph

    assert len(graph["entities"]) == 5
    assert len(graph["relations"]) == 5

    # Check entity types
    entity_types = [entity["entityType"] for entity in graph["entities"]]
    assert "Destination" in entity_types
    assert "Activity" in entity_types
    assert "Accommodation" in entity_types
    assert "Event" in entity_types
    assert "Transportation" in entity_types

    # Check relation types
    relation_types = [relation["relationType"] for relation in graph["relations"]]
    assert "LOCATED_IN" in relation_types
    assert "TAKES_PLACE_IN" in relation_types
    assert "DEPARTS_FROM" in relation_types
    assert "ARRIVES_AT" in relation_types


async def test_search_nodes(memory_client_with_mocks):
    """Test searching for nodes in the knowledge graph."""
    # Setup
    mocked_client = memory_client_with_mocks

    # Mock the Neo4j client call
    search_results = [
        {
            "name": "Paris",
            "description": "Capital of France",
            "type": "Destination",
            "score": 0.95,
        },
        {
            "name": "Eiffel Tower Visit",
            "description": "Famous landmark",
            "type": "Activity",
            "score": 0.85,
        },
        {
            "name": "Grand Hotel Paris",
            "description": "Luxury hotel",
            "type": "Accommodation",
            "score": 0.75,
        },
    ]

    mocked_client.neo4j_client.run_knowledge_graph_search = AsyncMock(
        return_value=search_results
    )

    # Execute
    nodes = await mocked_client.search_nodes("Paris")

    # Assert
    assert len(nodes) == 3
    mocked_client.neo4j_client.run_knowledge_graph_search.assert_called_once_with(
        "Paris"
    )

    # Check node details
    assert nodes[0]["name"] == "Paris"
    assert nodes[0]["type"] == "Destination"
    assert nodes[0]["score"] == 0.95
    assert nodes[0]["observations"] == ["Capital of France"]


async def test_open_nodes(
    memory_client_with_mocks,
    sample_destination,
    sample_activity,
    sample_accommodation,
    sample_event,
    sample_transportation,
):
    """Test retrieving detailed information about specific nodes."""
    # Setup
    mocked_client = memory_client_with_mocks

    # Mock get entity methods
    mocked_client.neo4j_client.get_destination = AsyncMock(
        side_effect=[sample_destination, None, None, None, None]
    )
    mocked_client.neo4j_client.get_activity = AsyncMock(
        side_effect=[None, sample_activity, None, None, None]
    )
    mocked_client.neo4j_client.get_accommodation = AsyncMock(
        side_effect=[None, None, sample_accommodation, None, None]
    )
    mocked_client.neo4j_client.get_event = AsyncMock(
        side_effect=[None, None, None, sample_event, None]
    )
    mocked_client.neo4j_client.get_transportation = AsyncMock(
        side_effect=[None, None, None, None, sample_transportation]
    )
    mocked_client.neo4j_client.execute_query = AsyncMock(return_value=[])

    # Add descriptions to sample entities
    sample_destination.description = "Capital of France"
    sample_activity.description = "Famous landmark"
    sample_accommodation.description = "Luxury hotel"
    sample_event.description = "Fashion event"
    sample_transportation.description = "High-speed train"

    # Prepare node names to open
    node_names = [
        "Paris",
        "Eiffel Tower Visit",
        "Grand Hotel Paris",
        "Paris Fashion Week",
        "Paris-London Train",
    ]

    # Execute
    nodes = await mocked_client.open_nodes(node_names)

    # Assert
    assert len(nodes) == 5

    # Check node types
    node_types = [node["type"] for node in nodes]
    assert "Destination" in node_types
    assert "Activity" in node_types
    assert "Accommodation" in node_types
    assert "Event" in node_types
    assert "Transportation" in node_types

    # Check first node properties
    paris_node = next(node for node in nodes if node["name"] == "Paris")
    assert paris_node["type"] == "Destination"
    assert paris_node["observations"] == ["Capital of France"]
    assert "country" in paris_node["properties"]
    assert "type" in paris_node["properties"]
