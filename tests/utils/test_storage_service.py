"""
Tests for the refactored Dual Storage Service pattern.

These tests verify that the TripStorageService correctly handles dual
storage operations with both Supabase and Neo4j via the Memory MCP.
"""

import os
from datetime import date
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel

# Import path takes care of the environment setup via conftest.py

# Import modules being tested
from src.utils.dual_storage import trip_service
from src.utils.dual_storage_service import DualStorageService


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
        "user_id": str(uuid4()),
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


class TestErrorHandlingDecorators:
    """Test suite for the error handling decorators."""
    
    @pytest.mark.asyncio
    async def test_with_error_handling_decorator(self):
        """Test the with_error_handling decorator on sync and async functions."""
        # Import here to avoid circular imports
        from src.utils.error_decorators import with_error_handling
        
        # Test sync function with error handling
        @with_error_handling
        def sync_function_with_error() -> Dict[str, Any]:
            raise ValueError("Sync function error")
        
        # Test async function with error handling
        @with_error_handling
        async def async_function_with_error() -> Dict[str, Any]:
            raise ValueError("Async function error")
        
        # Execute and verify sync function
        result = sync_function_with_error()
        assert "error" in result
        assert "Sync function error" in result["error"]
        
        # Execute and verify async function
        result = await async_function_with_error()
        assert "error" in result
        assert "Async function error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_ensure_memory_client_initialized(self):
        """Test the ensure_memory_client_initialized decorator."""
        # Import here to avoid circular imports
        from src.utils.decorators import ensure_memory_client_initialized
        
        # Create mock memory client
        mock_memory_client = MagicMock()
        mock_memory_client.initialize = AsyncMock()
        
        # Define test function with decorator
        @ensure_memory_client_initialized
        async def test_function() -> Dict[str, Any]:
            return {"success": True}
        
        # Patch the memory client
        with patch('src.mcp.memory.client.memory_client', mock_memory_client):
            # Call the function
            result = await test_function()
            
            # Verify initialization was called
            mock_memory_client.initialize.assert_called_once()
            assert result == {"success": True}
    
    @pytest.mark.asyncio
    async def test_memory_client_initialization_error(self):
        """Test error handling in memory client initialization."""
        # Import here to avoid circular imports
        from src.utils.decorators import ensure_memory_client_initialized
        
        # Create mock memory client that raises exception
        mock_memory_client = MagicMock()
        mock_memory_client.initialize = AsyncMock(side_effect=Exception("Connection error"))
        
        # Define test function with decorator
        @ensure_memory_client_initialized
        async def test_function() -> Dict[str, Any]:
            return {"success": True}
        
        # Patch the memory client
        with patch('src.mcp.memory.client.memory_client', mock_memory_client):
            # Call the function - should handle error gracefully
            result = await test_function()
            
            # Verify error was handled
            assert "error" in result
            assert "Connection error" in result["error"]


class TestTripStorageService:
    """Test suite for the TripStorageService class."""

    @pytest.mark.asyncio
    async def test_create(self, mock_db_client, mock_memory_client, sample_trip_data):
        """Test creating a trip using the TripStorageService."""
        # Arrange
        trip_id = str(uuid4())
        user_id = sample_trip_data["user_id"]
        
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
        assert result["primary_db"]["id"] == trip_id
        
    @pytest.mark.asyncio
    async def test_error_handling_in_create(self, mock_db_client, mock_memory_client, sample_trip_data):
        """Test error handling when creating a trip."""
        # Arrange - set up the db client to raise an exception
        mock_db_client.trips.create.side_effect = Exception("Database connection error")
        
        # Act
        result = await trip_service.create(sample_trip_data)
        
        # Assert
        assert "error" in result
        assert "Database connection error" in result["error"]
        
    @pytest.mark.asyncio
    async def test_error_handling_in_retrieve(self, mock_db_client, mock_memory_client):
        """Test error handling when retrieving a trip."""
        # Arrange - set up the db client to raise an exception
        mock_db_client.trips.get.side_effect = Exception("Database retrieval error")
        
        # Act
        result = await trip_service.retrieve("nonexistent-id")
        
        # Assert
        assert "error" in result
        assert "Database retrieval error" in result["error"]
        
    @pytest.mark.asyncio
    async def test_error_handling_in_update(self, mock_db_client, mock_memory_client):
        """Test error handling when updating a trip."""
        # Arrange - set up the db client to raise an exception
        mock_db_client.trips.update.side_effect = Exception("Database update error")
        
        # Act
        result = await trip_service.update("test-id", {"title": "Updated Trip"})
        
        # Assert
        assert "error" in result
        assert "Database update error" in result["error"]
        
    @pytest.mark.asyncio
    async def test_error_handling_in_delete(self, mock_db_client, mock_memory_client):
        """Test error handling when deleting a trip."""
        # Arrange - set up the db client to raise an exception
        mock_db_client.trips.delete.side_effect = Exception("Database deletion error")
        
        # Act
        result = await trip_service.delete("test-id")
        
        # Assert
        assert "error" in result
        assert "Database deletion error" in result["error"]

    @pytest.mark.asyncio
    async def test_retrieve(self, mock_db_client, mock_memory_client):
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
        
        assert "knowledge_graph" in result
        assert result["knowledge_graph"]["trip_node"] == trip_node

    @pytest.mark.asyncio
    async def test_retrieve_with_graph(self, mock_db_client, mock_memory_client):
        """Test retrieving a trip with graph using the TripStorageService."""
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
        search_results = [
            {"name": f"Trip:{trip_id}"},
            {"name": "Miami"},
            {"name": "Beachfront Resort"},
        ]
        
        mock_db_client.trips.get.return_value = db_trip
        mock_memory_client.open_nodes.return_value = [trip_node]
        mock_memory_client.search_nodes.return_value = search_results

        # Act
        result = await trip_service.retrieve(trip_id, include_graph=True)

        # Assert
        mock_db_client.trips.get.assert_called_once_with(trip_id)
        mock_memory_client.search_nodes.assert_called_once_with(f"Trip:{trip_id}")
        
        assert "knowledge_graph" in result
        assert "nodes" in result["knowledge_graph"]

    @pytest.mark.asyncio
    async def test_update(self, mock_db_client, mock_memory_client):
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
    async def test_delete(self, mock_db_client, mock_memory_client):
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
        
    @pytest.mark.asyncio
    async def test_entity_helper_methods(self, patch_both_clients):
        """Test the entity helper methods in TripStorageService."""
        # Test with empty/invalid inputs
        assert trip_service._create_destination_entity({}) is None
        assert trip_service._create_accommodation_entity({}) is None
        assert trip_service._create_activity_entity({}) is None
        assert trip_service._create_event_entity({}) is None
        assert trip_service._create_transportation_entity({}) is None
        
        # Test with minimal valid inputs
        dest = trip_service._create_destination_entity({"name": "Paris"})
        assert dest is not None
        assert dest["name"] == "Paris"
        assert dest["entityType"] == "Destination"
        assert dest["observations"] == []
        
        # Test with complete inputs for destination
        full_dest = trip_service._create_destination_entity({
            "name": "Rome",
            "country": "Italy",
            "type": "city",
            "description": "Historic city with beautiful architecture"
        })
        assert full_dest["name"] == "Rome"
        assert full_dest["country"] == "Italy"
        assert full_dest["type"] == "city"
        assert "Historic city with beautiful architecture" in full_dest["observations"]
        assert "Located in Italy" in full_dest["observations"]
        
        # Test accommodation entity
        acc = trip_service._create_accommodation_entity({
            "name": "Luxury Hotel",
            "type": "hotel",
            "destination": "Paris",
            "description": "5-star hotel",
            "address": "123 Main St",
            "price": 250
        })
        assert acc["name"] == "Luxury Hotel"
        assert acc["entityType"] == "Accommodation" 
        assert acc["type"] == "hotel"
        assert acc["destination"] == "Paris"
        assert "5-star hotel" in acc["observations"]
        assert "Located at 123 Main St" in acc["observations"]
        assert "Price: $250 per night" in acc["observations"]
        
        # Test activity entity
        act = trip_service._create_activity_entity({
            "name": "Museum Tour",
            "type": "cultural",
            "destination": "Paris",
            "description": "Tour of the Louvre",
            "duration": "3 hours",
            "price": 30
        })
        assert act["name"] == "Museum Tour"
        assert act["entityType"] == "Activity"
        assert act["type"] == "cultural"
        assert act["destination"] == "Paris"
        assert "Tour of the Louvre" in act["observations"]
        assert "Duration: 3 hours" in act["observations"]
        assert "Price: $30" in act["observations"]
        
        # Test event entity
        event = trip_service._create_event_entity({
            "name": "Opera Night",
            "type": "entertainment",
            "destination": "Paris",
            "description": "Classical opera performance",
            "start_time": "19:00",
            "end_time": "22:00",
            "location": "Paris Opera House"
        })
        assert event["name"] == "Opera Night"
        assert event["entityType"] == "Event"
        assert event["type"] == "entertainment"
        assert event["destination"] == "Paris"
        assert "Classical opera performance" in event["observations"]
        assert "From 19:00 to 22:00" in event["observations"]
        assert "Located at Paris Opera House" in event["observations"]
        
        # Test transportation entity
        transport = trip_service._create_transportation_entity({
            "name": "Flight AF1234",
            "type": "flight",
            "from_destination": "Paris",
            "to_destination": "Rome",
            "description": "Air France flight",
            "departure_time": "10:00",
            "arrival_time": "12:30",
            "price": 200
        })
        assert transport["name"] == "Flight AF1234"
        assert transport["entityType"] == "Transportation"
        assert transport["type"] == "flight"
        assert transport["from_destination"] == "Paris"
        assert transport["to_destination"] == "Rome"
        assert "Air France flight" in transport["observations"]
        assert "Departure: 10:00, Arrival: 12:30" in transport["observations"]
        assert "Price: $200" in transport["observations"]

    @pytest.mark.asyncio
    async def test_error_handling_in_create(self, mock_db_client, mock_memory_client, sample_trip_data):
        """Test error handling when creating a trip."""
        # Arrange - set up the db client to raise an exception
        mock_db_client.trips.create.side_effect = Exception("Database connection error")
        
        # Act
        result = await trip_service.create(sample_trip_data)
        
        # Assert
        assert "error" in result
        assert "Database connection error" in result["error"]


class TestDualStorageServiceInheritance:
    """Test that DualStorageService can be properly extended."""

    def test_service_inheritance(self):
        """Test that TripStorageService extends DualStorageService."""
        assert isinstance(trip_service, DualStorageService)
    
    def test_abstract_methods_implementation(self):
        """Test that all abstract methods of DualStorageService are implemented."""
        # Get the list of abstract methods from DualStorageService
        abstract_methods = [
            "_store_in_primary",
            "_create_graph_entities",
            "_create_graph_relations",
            "_retrieve_from_primary",
            "_retrieve_from_graph",
            "_combine_data",
            "_update_in_primary", 
            "_update_in_graph",
            "_delete_from_primary",
            "_delete_from_graph"
        ]
        
        # Verify that trip_service has all these methods implemented
        for method_name in abstract_methods:
            assert hasattr(trip_service, method_name)
            assert callable(getattr(trip_service, method_name))
            
    def test_entity_type_detection(self):
        """Test that the entity_type is correctly extracted from the class name."""
        assert trip_service.entity_type == "Trip"
        
    def test_instantiation_with_correct_clients(self):
        """Test that the service is instantiated with the correct clients."""
        with patch('src.utils.trip_storage_service.db_client') as mock_db, \
             patch('src.utils.trip_storage_service.memory_client') as mock_memory:
            from src.utils.trip_storage_service import TripStorageService
            service = TripStorageService()
            
            # Verify clients are correctly assigned
            assert service.primary_client is mock_db
            assert service.graph_client is mock_memory
            
    def test_cannot_instantiate_abstract_class(self):
        """Test that DualStorageService cannot be instantiated directly."""
        from src.utils.dual_storage_service import DualStorageService
        from pydantic import BaseModel
        from typing import TypeVar
        
        P = TypeVar("P", bound=BaseModel)
        G = TypeVar("G", bound=BaseModel)
        
        # Attempting to instantiate the abstract class should raise TypeError
        with pytest.raises(TypeError):
            DualStorageService[P, G](primary_client=MagicMock(), graph_client=MagicMock())