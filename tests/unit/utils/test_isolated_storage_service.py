"""
Tests for the dual storage service pattern in isolation.

This test file focuses on testing the DualStorageService and TripStorageService
classes in isolation, without depending on settings and configurations.
"""

import abc
from typing import Any, Dict, Generic, List, Optional, TypeVar
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel


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


# Create a minimal version of the DualStorageService for testing
P = TypeVar("P", bound=BaseModel)  # Primary DB model
G = TypeVar("G", bound=BaseModel)  # Graph DB model


class DualStorageService(Generic[P, G], metaclass=abc.ABCMeta):
    """Base class for dual storage services in TripSage."""

    def __init__(self, primary_client: Any, graph_client: Any):
        """Initialize the dual storage service."""
        self.primary_client = primary_client
        self.graph_client = graph_client
        self.entity_type = self.__class__.__name__.replace("Service", "")

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an entity using the dual storage strategy."""
        try:
            # Step 1: Store structured data in primary database
            primary_id = await self._store_in_primary(data)

            # Step 2: Store unstructured data and relationships in graph database
            created_entities = await self._create_graph_entities(data, primary_id)
            created_relations = await self._create_graph_relations(
                data, primary_id, created_entities
            )

            return {
                f"{self.entity_type.lower()}_id": primary_id,
                "entities_created": len(created_entities),
                "relations_created": len(created_relations),
                "primary_db": {"id": primary_id},
                "graph_db": {
                    "entities": created_entities,
                    "relations": created_relations,
                },
            }
        except Exception as e:
            # Log error and return standard error response
            return {"error": str(e)}

    async def retrieve(
        self, entity_id: str, include_graph: bool = False
    ) -> Dict[str, Any]:
        """Retrieve an entity using the dual storage strategy."""
        try:
            # Step 1: Retrieve structured data from primary database
            primary_data = await self._retrieve_from_primary(entity_id)

            if not primary_data:
                return {"error": f"{self.entity_type} not found"}

            # Step 2: Retrieve graph data
            graph_data = await self._retrieve_from_graph(entity_id, include_graph)

            # Step 3: Combine the data
            combined_data = await self._combine_data(primary_data, graph_data)

            return combined_data
        except Exception as e:
            # Log error and return standard error response
            return {"error": str(e)}

    async def update(self, entity_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an entity using the dual storage strategy."""
        try:
            # Step 1: Update structured data in primary database
            primary_updated = await self._update_in_primary(entity_id, data)

            # Step 2: Update graph data
            graph_updated = await self._update_in_graph(entity_id, data)

            return {
                f"{self.entity_type.lower()}_id": entity_id,
                "primary_db_updated": primary_updated,
                "graph_db_updated": graph_updated,
            }
        except Exception as e:
            # Log error and return standard error response
            return {"error": str(e)}

    async def delete(self, entity_id: str) -> Dict[str, Any]:
        """Delete an entity using the dual storage strategy."""
        try:
            # Step 1: Delete from primary database
            primary_deleted = await self._delete_from_primary(entity_id)

            # Step 2: Delete from graph database
            graph_deleted = await self._delete_from_graph(entity_id)

            return {
                f"{self.entity_type.lower()}_id": entity_id,
                "primary_db_deleted": primary_deleted,
                "graph_db_deleted": graph_deleted,
            }
        except Exception as e:
            # Log error and return standard error response
            return {"error": str(e)}

    @abc.abstractmethod
    async def _store_in_primary(self, data: Dict[str, Any]) -> str:
        """Store structured data in the primary database."""
        pass

    @abc.abstractmethod
    async def _create_graph_entities(
        self, data: Dict[str, Any], entity_id: str
    ) -> List[Dict[str, Any]]:
        """Create entities for the entity in the graph database."""
        pass

    @abc.abstractmethod
    async def _create_graph_relations(
        self,
        data: Dict[str, Any],
        entity_id: str,
        created_entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Create relationships for the entity in the graph database."""
        pass

    @abc.abstractmethod
    async def _retrieve_from_primary(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve structured data from the primary database."""
        pass

    @abc.abstractmethod
    async def _retrieve_from_graph(
        self, entity_id: str, include_graph: bool = False
    ) -> Dict[str, Any]:
        """Retrieve graph data from the graph database."""
        pass

    @abc.abstractmethod
    async def _combine_data(
        self, primary_data: Dict[str, Any], graph_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine data from primary and graph databases."""
        pass

    @abc.abstractmethod
    async def _update_in_primary(self, entity_id: str, data: Dict[str, Any]) -> bool:
        """Update structured data in the primary database."""
        pass

    @abc.abstractmethod
    async def _update_in_graph(self, entity_id: str, data: Dict[str, Any]) -> bool:
        """Update graph data in the graph database."""
        pass

    @abc.abstractmethod
    async def _delete_from_primary(self, entity_id: str) -> bool:
        """Delete entity from the primary database."""
        pass

    @abc.abstractmethod
    async def _delete_from_graph(self, entity_id: str) -> bool:
        """Delete entity from the graph database."""
        pass


# Create a concrete implementation of DualStorageService for testing
class MockDualStorageService(DualStorageService[MockPrimaryModel, MockGraphModel]):
    """Concrete implementation of DualStorageService for testing."""

    # Override entity_type for testing
    def __init__(self, primary_client: Any, graph_client: Any):
        super().__init__(primary_client, graph_client)
        self.entity_type = "Entity"  # Make sure entity_type is predictable

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

    async def _retrieve_from_primary(self, entity_id: str) -> Optional[Dict[str, Any]]:
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

    async def _update_in_primary(self, entity_id: str, data: Dict[str, Any]) -> bool:
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
        result = await self.graph_client.delete_entities([f"Entity:{entity_id}"])
        return bool(result)


class TestDualStorageService:
    """Test class for the DualStorageService base class."""

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
        return MockDualStorageService(
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
        assert result["entity_id"] == "test-id-123"  # Uses entity_type.lower() + _id
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
    async def test_retrieve_with_graph(
        self, mock_service, mock_primary_client, mock_graph_client
    ):
        """Test retrieving with full graph."""
        # Act
        result = await mock_service.retrieve("test-id-123", include_graph=True)

        # Assert
        assert result["id"] == "test-id-123"
        assert "knowledge_graph" in result
        assert "nodes" in result["knowledge_graph"]
        assert len(result["knowledge_graph"]["nodes"]) == 2

        # Verify the client methods were called
        mock_primary_client.get.assert_called_once_with("test-id-123")
        mock_graph_client.search_nodes.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_not_found(self, mock_service, mock_primary_client):
        """Test retrieving a non-existent entity."""
        # Arrange
        mock_primary_client.get.return_value = None

        # Act
        result = await mock_service.retrieve("nonexistent-id")

        # Assert
        assert "error" in result
        assert "not found" in result["error"]

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

    @pytest.mark.asyncio
    async def test_error_handling_in_create(self, mock_service, mock_primary_client):
        """Test error handling in create method."""
        # Arrange
        mock_primary_client.create.side_effect = Exception("Database error")
        test_data = {"name": "Test Entity"}

        # Act
        result = await mock_service.create(test_data)

        # Assert
        assert "error" in result
        assert "Database error" in result["error"]

    @pytest.mark.asyncio
    async def test_error_handling_in_retrieve(self, mock_service, mock_primary_client):
        """Test error handling in retrieve method."""
        # Arrange
        mock_primary_client.get.side_effect = Exception("Database error")

        # Act
        result = await mock_service.retrieve("test-id-123")

        # Assert
        assert "error" in result
        assert "Database error" in result["error"]

    @pytest.mark.asyncio
    async def test_error_handling_in_update(self, mock_service, mock_primary_client):
        """Test error handling in update method."""
        # Arrange
        mock_primary_client.update.side_effect = Exception("Database error")

        # Act
        result = await mock_service.update("test-id-123", {"name": "Updated"})

        # Assert
        assert "error" in result
        assert "Database error" in result["error"]

    @pytest.mark.asyncio
    async def test_error_handling_in_delete(self, mock_service, mock_primary_client):
        """Test error handling in delete method."""
        # Arrange
        mock_primary_client.delete.side_effect = Exception("Database error")

        # Act
        result = await mock_service.delete("test-id-123")

        # Assert
        assert "error" in result
        assert "Database error" in result["error"]

    def test_entity_type_detection(self, mock_service):
        """Test that the entity_type is correctly extracted from the class name."""
        assert mock_service.entity_type == "Entity"  # We overrode this in __init__

        # Create a new service without overriding to test default behavior
        class TestService(DualStorageService[MockPrimaryModel, MockGraphModel]):
            async def _store_in_primary(self, data):
                pass

            async def _create_graph_entities(self, data, entity_id):
                pass

            async def _create_graph_relations(self, data, entity_id, created_entities):
                pass

            async def _retrieve_from_primary(self, entity_id):
                pass

            async def _retrieve_from_graph(self, entity_id, include_graph):
                pass

            async def _combine_data(self, primary_data, graph_data):
                pass

            async def _update_in_primary(self, entity_id, data):
                pass

            async def _update_in_graph(self, entity_id, data):
                pass

            async def _delete_from_primary(self, entity_id):
                pass

            async def _delete_from_graph(self, entity_id):
                pass

        test_service = TestService(MagicMock(), MagicMock())
        assert test_service.entity_type == "Test"  # Should extract from class name

    def test_cannot_instantiate_abstract_class(self):
        """Test that DualStorageService cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DualStorageService(primary_client=MagicMock(), graph_client=MagicMock())


# Test the concrete implementation to ensure it works correctly
class TestTripPattern:
    """
    Tests for the Trip implementation of the DualStorageService pattern.

    In this class, we create a simplified TripStorageService to demonstrate
    how a real implementation should work with our DualStorageService pattern.
    """

    # Create simplified Trip models for testing
    class TripPrimaryModel(BaseModel):
        """Model for Trip data in the primary database."""

        id: Optional[str] = None
        user_id: str
        title: str
        description: Optional[str] = None

    class TripGraphModel(BaseModel):
        """Model for Trip data in the graph database."""

        name: str
        entityType: str = "Trip"
        observations: List[str]

    # Create a concrete implementation for Trip
    class TripStorageService(DualStorageService[TripPrimaryModel, TripGraphModel]):
        """Trip-specific implementation of DualStorageService."""

        def __init__(self, primary_client: Any, graph_client: Any):
            super().__init__(primary_client, graph_client)
            self.entity_type = "Trip"  # Make sure entity_type is predictable

        def _create_destination_entity(
            self, destination: Dict[str, Any]
        ) -> Optional[Dict[str, Any]]:
            """Create a destination entity."""
            name = destination.get("name")
            if not name:
                return None

            observations = []
            if destination.get("description"):
                observations.append(destination.get("description"))

            return {
                "name": name,
                "entityType": "Destination",
                "observations": observations,
            }

        async def _store_in_primary(self, data: Dict[str, Any]) -> str:
            """Store trip in primary database."""
            result = await self.primary_client.trips.create(data)
            return result["id"]

        async def _create_graph_entities(
            self, data: Dict[str, Any], trip_id: str
        ) -> List[Dict[str, Any]]:
            """Create graph entities for trip."""
            entities = [
                {
                    "name": f"Trip:{trip_id}",
                    "entityType": "Trip",
                    "observations": [data.get("description", "No description")],
                }
            ]

            # Add destinations if present
            for dest in data.get("destinations", []):
                entity = self._create_destination_entity(dest)
                if entity:
                    entities.append(entity)

            return await self.graph_client.create_entities(entities)

        async def _create_graph_relations(
            self,
            data: Dict[str, Any],
            trip_id: str,
            created_entities: List[Dict[str, Any]],
        ) -> List[Dict[str, Any]]:
            """Create graph relations for trip."""
            relations = [
                {
                    "from": f"User:{data.get('user_id')}",
                    "relationType": "PLANS",
                    "to": f"Trip:{trip_id}",
                }
            ]

            # Add relations for destinations
            destinations = [
                e for e in created_entities if e.get("entityType") == "Destination"
            ]
            for dest in destinations:
                relations.append(
                    {
                        "from": f"Trip:{trip_id}",
                        "relationType": "INCLUDES",
                        "to": dest["name"],
                    }
                )

            return await self.graph_client.create_relations(relations)

        async def _retrieve_from_primary(
            self, trip_id: str
        ) -> Optional[Dict[str, Any]]:
            """Retrieve trip from primary database."""
            return await self.primary_client.trips.get(trip_id)

        async def _retrieve_from_graph(
            self, trip_id: str, include_graph: bool = False
        ) -> Dict[str, Any]:
            """Retrieve trip from graph database."""
            trip_node = await self.graph_client.open_nodes([f"Trip:{trip_id}"])
            result = {"trip_node": trip_node[0] if trip_node else None}

            if include_graph:
                related_nodes = await self.graph_client.search_nodes(f"Trip:{trip_id}")
                result["nodes"] = related_nodes

            return result

        async def _combine_data(
            self, primary_data: Dict[str, Any], graph_data: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Combine primary and graph data."""
            result = primary_data.copy()
            result["knowledge_graph"] = graph_data
            return result

        async def _update_in_primary(self, trip_id: str, data: Dict[str, Any]) -> bool:
            """Update trip in primary database."""
            return await self.primary_client.trips.update(trip_id, data)

        async def _update_in_graph(self, trip_id: str, data: Dict[str, Any]) -> bool:
            """Update trip in graph database."""
            if "description" in data:
                await self.graph_client.add_observations(
                    [
                        {
                            "entityName": f"Trip:{trip_id}",
                            "contents": [data["description"]],
                        }
                    ]
                )
                return True
            return False

        async def _delete_from_primary(self, trip_id: str) -> bool:
            """Delete trip from primary database."""
            return await self.primary_client.trips.delete(trip_id)

        async def _delete_from_graph(self, trip_id: str) -> bool:
            """Delete trip from graph database."""
            result = await self.graph_client.delete_entities([f"Trip:{trip_id}"])
            return bool(result)

    @pytest.fixture
    def mock_primary_client(self):
        """Create a mock primary database client."""
        client = MagicMock()
        client.trips = MagicMock()
        client.trips.create = AsyncMock(
            return_value={
                "id": "trip-123",
                "user_id": "user-456",
                "title": "Test Trip",
                "description": "A test trip",
            }
        )
        client.trips.get = AsyncMock(
            return_value={
                "id": "trip-123",
                "user_id": "user-456",
                "title": "Test Trip",
                "description": "A test trip",
            }
        )
        client.trips.update = AsyncMock(return_value=True)
        client.trips.delete = AsyncMock(return_value=True)
        return client

    @pytest.fixture
    def mock_graph_client(self):
        """Create a mock graph database client."""
        client = MagicMock()
        client.create_entities = AsyncMock(
            return_value=[
                {
                    "name": "Trip:trip-123",
                    "entityType": "Trip",
                    "observations": ["A test trip"],
                },
                {
                    "name": "Paris",
                    "entityType": "Destination",
                    "observations": ["Beautiful city"],
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
                {"from": "Trip:trip-123", "relationType": "INCLUDES", "to": "Paris"},
            ]
        )
        client.open_nodes = AsyncMock(
            return_value=[
                {
                    "name": "Trip:trip-123",
                    "entityType": "Trip",
                    "observations": ["A test trip"],
                }
            ]
        )
        client.search_nodes = AsyncMock(
            return_value=[
                {
                    "name": "Trip:trip-123",
                    "entityType": "Trip",
                    "observations": ["A test trip"],
                },
                {
                    "name": "Paris",
                    "entityType": "Destination",
                    "observations": ["Beautiful city"],
                },
            ]
        )
        client.add_observations = AsyncMock(return_value=True)
        client.delete_entities = AsyncMock(return_value=["Trip:trip-123"])
        return client

    @pytest.fixture
    def trip_service(self, mock_primary_client, mock_graph_client):
        """Create a TripStorageService instance."""
        return self.TripStorageService(
            primary_client=mock_primary_client, graph_client=mock_graph_client
        )

    @pytest.fixture
    def trip_data(self):
        """Sample trip data for testing."""
        return {
            "user_id": "user-456",
            "title": "Paris Trip",
            "description": "A trip to Paris",
            "destinations": [{"name": "Paris", "description": "Beautiful city"}],
        }

    @pytest.mark.asyncio
    async def test_trip_create(
        self, trip_service, mock_primary_client, mock_graph_client, trip_data
    ):
        """Test creating a trip."""
        # Act
        result = await trip_service.create(trip_data)

        # Assert
        assert result["trip_id"] == "trip-123"
        assert result["entities_created"] == 2  # Trip and destination
        assert result["relations_created"] == 2  # User-Trip and Trip-Destination

        # Verify client calls
        mock_primary_client.trips.create.assert_called_once_with(trip_data)
        mock_graph_client.create_entities.assert_called_once()
        mock_graph_client.create_relations.assert_called_once()

    @pytest.mark.asyncio
    async def test_destination_entity_creation(self, trip_service):
        """Test creating destination entities."""
        # Test with empty data
        result = trip_service._create_destination_entity({})
        assert result is None

        # Test with valid data
        result = trip_service._create_destination_entity(
            {"name": "Rome", "description": "Historic city"}
        )
        assert result["name"] == "Rome"
        assert result["entityType"] == "Destination"
        assert "Historic city" in result["observations"]

    @pytest.mark.asyncio
    async def test_trip_retrieve(
        self, trip_service, mock_primary_client, mock_graph_client
    ):
        """Test retrieving a trip."""
        # Act
        result = await trip_service.retrieve("trip-123")

        # Assert
        assert result["id"] == "trip-123"
        assert result["title"] == "Test Trip"
        assert "knowledge_graph" in result
        assert result["knowledge_graph"]["trip_node"]["name"] == "Trip:trip-123"

        # Verify client calls
        mock_primary_client.trips.get.assert_called_once_with("trip-123")
        mock_graph_client.open_nodes.assert_called_once()

    @pytest.mark.asyncio
    async def test_trip_update(
        self, trip_service, mock_primary_client, mock_graph_client
    ):
        """Test updating a trip."""
        # Arrange
        update_data = {"title": "Updated Trip", "description": "Updated description"}

        # Act
        result = await trip_service.update("trip-123", update_data)

        # Assert
        assert result["trip_id"] == "trip-123"
        assert result["primary_db_updated"] is True
        assert result["graph_db_updated"] is True

        # Verify client calls
        mock_primary_client.trips.update.assert_called_once_with(
            "trip-123", update_data
        )
        mock_graph_client.add_observations.assert_called_once()

    @pytest.mark.asyncio
    async def test_trip_delete(
        self, trip_service, mock_primary_client, mock_graph_client
    ):
        """Test deleting a trip."""
        # Act
        result = await trip_service.delete("trip-123")

        # Assert
        assert result["trip_id"] == "trip-123"
        assert result["primary_db_deleted"] is True
        assert result["graph_db_deleted"] is True

        # Verify client calls
        mock_primary_client.trips.delete.assert_called_once_with("trip-123")
        mock_graph_client.delete_entities.assert_called_once_with(["Trip:trip-123"])
