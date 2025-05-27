"""
Tests for the dual storage service pattern implementation.

This module tests the DualStorageService and TripStorageService classes.
"""

from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

# Import path takes care of the environment setup via conftest.py


# Create mock models for testing
class MockPrimaryModel(BaseModel):
    """Mock model for the primary database."""

    id: Optional[str] = None
    name: str
    description: Optional[str] = None


class MockGraphModel(BaseModel):
    """Mock model for the graph database."""

    name: str
    entityType: str
    observations: List[str]


# Import after setting environment variables
from tripsage.utils.dual_storage_service import DualStorageService  # noqa: E402
from tripsage.utils.trip_storage_service import TripStorageService  # noqa: E402


class TestDualStorageService:
    """Test class for the DualStorageService base class.

    This class tests the generic DualStorageService functionality using
    a concrete mock implementation that demonstrates the correct pattern
    for implementing entity-specific storage services.
    """

    class MockDualStorageService(DualStorageService[MockPrimaryModel, MockGraphModel]):
        """Concrete implementation of DualStorageService for testing."""

        def __init__(self, primary_client, graph_client):
            """Initialize the mock service."""
            super().__init__(primary_client=primary_client, graph_client=graph_client)

        async def _store_in_primary(self, data: Dict[str, Any]) -> str:
            result = await self.primary_client.create(data)
            return result["id"]

        async def _create_graph_entities(
            self, data: Dict[str, Any], entity_id: str
        ) -> List[Dict[str, Any]]:
            entities = [
                {
                    "name": f"Entity:{entity_id}",
                    "entityType": "TestEntity",
                    "observations": [data.get("description", "No description")],
                }
            ]
            return await self.graph_client.create_entities(entities)

        async def _create_graph_relations(
            self,
            data: Dict[str, Any],
            entity_id: str,
            created_entities: List[Dict[str, Any]],
        ) -> List[Dict[str, Any]]:
            relations = [
                {
                    "from": f"User:{data.get('user_id')}",
                    "relationType": "OWNS",
                    "to": f"Entity:{entity_id}",
                }
            ]
            return await self.graph_client.create_relations(relations)

        async def _retrieve_from_primary(
            self, entity_id: str
        ) -> Optional[Dict[str, Any]]:
            return await self.primary_client.get(entity_id)

        async def _retrieve_from_graph(
            self, entity_id: str, include_graph: bool = False
        ) -> Dict[str, Any]:
            nodes = await self.graph_client.open_nodes([f"Entity:{entity_id}"])
            result = {"entity_node": nodes[0] if nodes else None}

            if include_graph:
                all_nodes = await self.graph_client.search_nodes(f"Entity:{entity_id}")
                result["nodes"] = all_nodes

            return result

        async def _combine_data(
            self, primary_data: Dict[str, Any], graph_data: Dict[str, Any]
        ) -> Dict[str, Any]:
            result = primary_data.copy()
            result["knowledge_graph"] = graph_data
            return result

        async def _update_in_primary(
            self, entity_id: str, data: Dict[str, Any]
        ) -> bool:
            return await self.primary_client.update(entity_id, data)

        async def _update_in_graph(self, entity_id: str, data: Dict[str, Any]) -> bool:
            if "description" in data:
                await self.graph_client.add_observations(
                    [
                        {
                            "entityName": f"Entity:{entity_id}",
                            "contents": [data["description"]],
                        }
                    ]
                )
                return True
            return False

        async def _delete_from_primary(self, entity_id: str) -> bool:
            return await self.primary_client.delete(entity_id)

        async def _delete_from_graph(self, entity_id: str) -> bool:
            return await self.graph_client.delete_entities([f"Entity:{entity_id}"])

    @pytest.fixture
    def mock_primary_client(self):
        """Create a mock primary database client."""
        client = MagicMock()
        client.create = AsyncMock(
            return_value={"id": "test-id-123", "name": "Test Entity"}
        )
        client.get = AsyncMock(
            return_value={
                "id": "test-id-123",
                "name": "Test Entity",
                "description": "Test description",
            }
        )
        client.update = AsyncMock(return_value=True)
        client.delete = AsyncMock(return_value=True)
        return client

    @pytest.fixture
    def mock_graph_client(self):
        """Create a mock graph database client."""
        client = MagicMock()
        client.initialize = AsyncMock()
        client.create_entities = AsyncMock(
            return_value=[
                {
                    "name": "Entity:test-id-123",
                    "entityType": "TestEntity",
                    "observations": ["Test description"],
                }
            ]
        )
        client.create_relations = AsyncMock(
            return_value=[
                {
                    "from": "User:test-user",
                    "relationType": "OWNS",
                    "to": "Entity:test-id-123",
                }
            ]
        )
        client.open_nodes = AsyncMock(
            return_value=[
                {
                    "name": "Entity:test-id-123",
                    "entityType": "TestEntity",
                    "observations": ["Test description"],
                }
            ]
        )
        client.search_nodes = AsyncMock(
            return_value=[
                {
                    "name": "Entity:test-id-123",
                    "entityType": "TestEntity",
                    "observations": ["Test description"],
                },
                {
                    "name": "User:test-user",
                    "entityType": "User",
                    "observations": ["TripSage user"],
                },
            ]
        )
        client.add_observations = AsyncMock(return_value=True)
        client.delete_entities = AsyncMock(return_value=["Entity:test-id-123"])
        return client

    @pytest.fixture
    def mock_service(self, mock_primary_client, mock_graph_client):
        """Create a mock dual storage service."""
        return self.MockDualStorageService(
            primary_client=mock_primary_client, graph_client=mock_graph_client
        )

    @pytest.mark.asyncio
    async def test_create(self, mock_service, mock_primary_client, mock_graph_client):
        """Test the create method."""
        # Arrange
        test_data = {
            "name": "Test Entity",
            "description": "Test description",
            "user_id": "test-user",
        }

        # Act
        result = await mock_service.create(test_data)

        # Assert
        assert result["entity_id"] == "test-id-123"
        assert result["entities_created"] == 1
        assert result["relations_created"] == 1

        # Verify the client methods were called
        mock_primary_client.create.assert_called_once_with(test_data)
        mock_graph_client.create_entities.assert_called_once()
        mock_graph_client.create_relations.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve(self, mock_service, mock_primary_client, mock_graph_client):
        """Test the retrieve method."""
        # Act
        result = await mock_service.retrieve("test-id-123")

        # Assert
        assert result["id"] == "test-id-123"
        assert result["name"] == "Test Entity"
        assert "knowledge_graph" in result
        assert result["knowledge_graph"]["entity_node"]["name"] == "Entity:test-id-123"

        # Verify the client methods were called
        mock_primary_client.get.assert_called_once_with("test-id-123")
        mock_graph_client.open_nodes.assert_called_once()

    @pytest.mark.asyncio
    async def test_update(self, mock_service, mock_primary_client, mock_graph_client):
        """Test the update method."""
        # Arrange
        update_data = {"name": "Updated Entity", "description": "Updated description"}

        # Act
        result = await mock_service.update("test-id-123", update_data)

        # Assert
        assert result["entity_id"] == "test-id-123"
        assert result["primary_db_updated"] is True
        assert result["graph_db_updated"] is True

        # Verify the client methods were called
        mock_primary_client.update.assert_called_once_with("test-id-123", update_data)
        mock_graph_client.add_observations.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete(self, mock_service, mock_primary_client, mock_graph_client):
        """Test the delete method."""
        # Act
        result = await mock_service.delete("test-id-123")

        # Assert
        assert result["entity_id"] == "test-id-123"
        assert result["primary_db_deleted"] is True
        assert result["graph_db_deleted"] is True

        # Verify the client methods were called
        mock_primary_client.delete.assert_called_once_with("test-id-123")
        mock_graph_client.delete_entities.assert_called_once_with(
            ["Entity:test-id-123"]
        )


class TestTripStorageService:
    """Test class for the TripStorageService.

    This class tests the concrete implementation of DualStorageService
    specifically for Trip entities, ensuring it properly handles all
    CRUD operations with both primary and graph databases.
    """

    @pytest.fixture
    def mock_db_client(self):
        """Create a mock database client."""
        client = MagicMock()
        client.trips = MagicMock()
        client.trips.create = AsyncMock(
            return_value={
                "id": "trip-123",
                "user_id": "user-456",
                "title": "Test Trip",
                "description": "A test trip",
                "start_date": "2025-06-15",
                "end_date": "2025-06-30",
                "budget": 5000,
                "status": "planning",
            }
        )
        client.trips.get = AsyncMock(
            return_value={
                "id": "trip-123",
                "user_id": "user-456",
                "title": "Test Trip",
                "description": "A test trip",
                "start_date": "2025-06-15",
                "end_date": "2025-06-30",
                "budget": 5000,
                "status": "planning",
            }
        )
        client.trips.update = AsyncMock(return_value=True)
        client.trips.delete = AsyncMock(return_value=True)
        return client

    @pytest.fixture
    def mock_memory_client(self):
        """Create a mock memory client."""
        client = MagicMock()
        client.initialize = AsyncMock()
        client.create_entities = AsyncMock(
            return_value=[
                {
                    "name": "Trip:trip-123",
                    "entityType": "Trip",
                    "observations": [
                        "Trip from 2025-06-15 to 2025-06-30",
                        "Budget: $5000",
                    ],
                },
                {
                    "name": "User:user-456",
                    "entityType": "User",
                    "observations": ["TripSage user"],
                },
                {
                    "name": "Miami",
                    "entityType": "Destination",
                    "observations": ["Beautiful beaches and vibrant nightlife"],
                },
            ]
        )
        client.create_relations = AsyncMock(
            return_value=[
                {
                    "from": "User:user-456",
                    "relationType": "PLANS",
                    "to": "Trip:trip-123",
                },
                {"from": "Trip:trip-123", "relationType": "INCLUDES", "to": "Miami"},
            ]
        )
        client.open_nodes = AsyncMock(
            return_value=[
                {
                    "name": "Trip:trip-123",
                    "entityType": "Trip",
                    "observations": [
                        "Trip from 2025-06-15 to 2025-06-30",
                        "Budget: $5000",
                    ],
                }
            ]
        )
        client.search_nodes = AsyncMock(
            return_value=[
                {
                    "name": "Trip:trip-123",
                    "entityType": "Trip",
                    "observations": [
                        "Trip from 2025-06-15 to 2025-06-30",
                        "Budget: $5000",
                    ],
                },
                {
                    "name": "User:user-456",
                    "entityType": "User",
                    "observations": ["TripSage user"],
                },
                {
                    "name": "Miami",
                    "entityType": "Destination",
                    "observations": ["Beautiful beaches and vibrant nightlife"],
                },
            ]
        )
        client.add_observations = AsyncMock(
            return_value=[
                {
                    "entityName": "Trip:trip-123",
                    "observations": ["Updated trip information"],
                }
            ]
        )
        client.delete_entities = AsyncMock(return_value=["Trip:trip-123"])
        return client

    @pytest.fixture
    def sample_trip_data(self):
        """Create sample trip data for testing."""
        return {
            "user_id": "user-456",
            "title": "Test Trip",
            "description": "A test trip",
            "start_date": "2025-06-15",
            "end_date": "2025-06-30",
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
        self, mock_db_client, mock_memory_client, sample_trip_data
    ):
        """Test creating a trip using the TripStorageService."""
        # Arrange
        with (
            patch("src.utils.trip_storage_service.db_client", mock_db_client),
            patch("src.utils.trip_storage_service.memory_client", mock_memory_client),
        ):
            service = TripStorageService()

            # Act
            result = await service.create(sample_trip_data)

            # Assert
            assert result["trip_id"] == "trip-123"
            assert "entities_created" in result
            assert "relations_created" in result
            assert "primary_db" in result
            assert "graph_db" in result

            # Verify client calls
            mock_db_client.trips.create.assert_called_once()
            mock_memory_client.create_entities.assert_called_once()
            mock_memory_client.create_relations.assert_called_once()

    @pytest.mark.asyncio
    async def test_trip_service_retrieve(self, mock_db_client, mock_memory_client):
        """Test retrieving a trip using the TripStorageService."""
        # Arrange
        with (
            patch("src.utils.trip_storage_service.db_client", mock_db_client),
            patch("src.utils.trip_storage_service.memory_client", mock_memory_client),
        ):
            service = TripStorageService()

            # Act
            result = await service.retrieve("trip-123")

            # Assert
            assert result["id"] == "trip-123"
            assert result["title"] == "Test Trip"
            assert "knowledge_graph" in result
            assert result["knowledge_graph"]["trip_node"]["name"] == "Trip:trip-123"

            # Verify client calls
            mock_db_client.trips.get.assert_called_once_with("trip-123")
            mock_memory_client.open_nodes.assert_called_once()

    @pytest.mark.asyncio
    async def test_trip_service_update(self, mock_db_client, mock_memory_client):
        """Test updating a trip using the TripStorageService."""
        # Arrange
        with (
            patch("src.utils.trip_storage_service.db_client", mock_db_client),
            patch("src.utils.trip_storage_service.memory_client", mock_memory_client),
        ):
            service = TripStorageService()
            update_data = {
                "title": "Updated Trip Title",
                "description": "Updated trip description",
                "budget": 6000,
            }

            # Act
            result = await service.update("trip-123", update_data)

            # Assert
            assert result["trip_id"] == "trip-123"
            assert result["primary_db_updated"] is True
            assert result["graph_db_updated"] is True

            # Verify client calls
            mock_db_client.trips.update.assert_called_once()
            mock_memory_client.add_observations.assert_called_once()

    @pytest.mark.asyncio
    async def test_trip_service_delete(self, mock_db_client, mock_memory_client):
        """Test deleting a trip using the TripStorageService."""
        # Arrange
        with (
            patch("src.utils.trip_storage_service.db_client", mock_db_client),
            patch("src.utils.trip_storage_service.memory_client", mock_memory_client),
        ):
            service = TripStorageService()

            # Act
            result = await service.delete("trip-123")

            # Assert
            assert result["trip_id"] == "trip-123"
            assert result["primary_db_deleted"] is True
            assert result["graph_db_deleted"] is True

            # Verify client calls
            mock_db_client.trips.delete.assert_called_once_with("trip-123")
            mock_memory_client.delete_entities.assert_called_once_with(
                ["Trip:trip-123"]
            )

    @pytest.mark.asyncio
    async def test_creating_entity_helpers(self, mock_db_client, mock_memory_client):
        """Test the entity creation helper methods in TripStorageService."""
        # Arrange
        with (
            patch("src.utils.trip_storage_service.db_client", mock_db_client),
            patch("src.utils.trip_storage_service.memory_client", mock_memory_client),
        ):
            service = TripStorageService()

            # Test destination entity creation
            destination = {
                "name": "Paris",
                "country": "France",
                "type": "city",
                "description": "City of Light",
            }
            dest_entity = service._create_destination_entity(destination)
            assert dest_entity["name"] == "Paris"
            assert dest_entity["entityType"] == "Destination"
            assert "City of Light" in dest_entity["observations"]

            # Test accommodation entity creation
            accommodation = {
                "name": "Grand Hotel",
                "type": "hotel",
                "destination": "Paris",
                "description": "Luxury hotel in the city center",
                "price": 250,
            }
            acc_entity = service._create_accommodation_entity(accommodation)
            assert acc_entity["name"] == "Grand Hotel"
            assert acc_entity["entityType"] == "Accommodation"
            assert "Luxury hotel in the city center" in acc_entity["observations"]

            # Test activity entity creation
            activity = {
                "name": "Eiffel Tower Tour",
                "destination": "Paris",
                "type": "attraction",
                "description": "Visit the famous tower",
                "price": 20,
            }
            act_entity = service._create_activity_entity(activity)
            assert act_entity["name"] == "Eiffel Tower Tour"
            assert act_entity["entityType"] == "Activity"
            assert "Visit the famous tower" in act_entity["observations"]

    @pytest.mark.asyncio
    async def test_trip_service_with_error_handling(
        self, mock_db_client, mock_memory_client
    ):
        """Test error handling in TripStorageService."""
        # Arrange
        with (
            patch("src.utils.trip_storage_service.db_client", mock_db_client),
            patch("src.utils.trip_storage_service.memory_client", mock_memory_client),
        ):
            service = TripStorageService()

            # Setup error in db client
            mock_db_client.trips.get.side_effect = Exception("Database error")

            # Act & Assert - should handle error gracefully
            result = await service.retrieve("trip-123")
            assert "error" in result
            assert "Database error" in result["error"]

    @pytest.mark.asyncio
    async def test_entity_helper_methods(self, mock_db_client, mock_memory_client):
        """Test the entity helper methods in TripStorageService."""
        # Arrange
        with (
            patch("src.utils.trip_storage_service.db_client", mock_db_client),
            patch("src.utils.trip_storage_service.memory_client", mock_memory_client),
        ):
            service = TripStorageService()

            # Test with empty/invalid inputs
            assert service._create_destination_entity({}) is None
            assert service._create_accommodation_entity({}) is None
            assert service._create_activity_entity({}) is None
            assert service._create_event_entity({}) is None
            assert service._create_transportation_entity({}) is None

            # Test with minimal valid inputs
            dest = service._create_destination_entity({"name": "Paris"})
            assert dest is not None
            assert dest["name"] == "Paris"
            assert dest["entityType"] == "Destination"

            # Test with complete inputs
            transport = service._create_transportation_entity(
                {
                    "name": "Flight PA123",
                    "description": "Direct flight",
                    "from_destination": "Paris",
                    "to_destination": "London",
                    "departure_time": "08:00",
                    "arrival_time": "09:30",
                    "price": 150,
                    "type": "flight",
                }
            )
            assert transport is not None
            assert transport["name"] == "Flight PA123"
            assert transport["entityType"] == "Transportation"
            assert "Direct flight" in transport["observations"]
            assert transport["from_destination"] == "Paris"
            assert transport["to_destination"] == "London"

    @pytest.mark.asyncio
    async def test_retrieve_with_nonexistent_trip(
        self, mock_db_client, mock_memory_client
    ):
        """Test retrieving a non-existent trip."""
        # Arrange
        with (
            patch("src.utils.trip_storage_service.db_client", mock_db_client),
            patch("src.utils.trip_storage_service.memory_client", mock_memory_client),
        ):
            service = TripStorageService()
            mock_db_client.trips.get.return_value = None

            # Act
            result = await service.retrieve("nonexistent-id")

            # Assert
            assert "error" in result
            assert "Trip not found" in result["error"]

    @pytest.mark.asyncio
    async def test_update_with_memory_client_error(
        self, mock_db_client, mock_memory_client
    ):
        """Test updating a trip when the memory client has an error."""
        # Arrange
        with (
            patch("src.utils.trip_storage_service.db_client", mock_db_client),
            patch("src.utils.trip_storage_service.memory_client", mock_memory_client),
        ):
            service = TripStorageService()
            mock_db_client.trips.update.return_value = True
            mock_memory_client.open_nodes.return_value = []

            # Act
            result = await service.update("trip-123", {"title": "Updated Trip"})

            # Assert
            assert result["primary_db_updated"] is True
            assert result["graph_db_updated"] is False
