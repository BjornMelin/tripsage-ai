"""
Tests for the travel planning tools.

These tests verify the functionality of the planning tools used by the
TravelPlanningAgent, including plan creation, updates, and search result combination.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.planning_tools import (
    combine_search_results,
    create_travel_plan,
    update_travel_plan,
)


@pytest.fixture
def mock_redis_cache():
    """Mock for the Redis cache."""
    mock = MagicMock()
    mock.get = AsyncMock()
    mock.set = AsyncMock()
    return mock


@pytest.fixture
def mock_memory_client():
    """Mock for the memory MCP client."""
    mock = MagicMock()
    mock.create_entities = AsyncMock(return_value={"success": True})
    mock.create_relations = AsyncMock(return_value={"success": True})
    mock.add_observations = AsyncMock(return_value={"success": True})
    return mock


@pytest.fixture
def travel_plan_data():
    """Sample travel plan data."""
    return {
        "user_id": "user123",
        "title": "Summer Vacation",
        "destinations": ["Paris", "London"],
        "start_date": "2023-07-01",
        "end_date": "2023-07-14",
        "travelers": 2,
        "budget": 5000.0,
        "preferences": {
            "accommodation_type": "hotel",
            "max_flight_budget": 1500.0,
            "interests": ["history", "food"],
        },
    }


@pytest.fixture
def sample_flight_results():
    """Sample flight search results."""
    return {
        "offers": [
            {
                "id": "flight1",
                "airline": "Delta",
                "origin": "JFK",
                "destination": "CDG",
                "departure_date": "2023-07-01",
                "return_date": "2023-07-14",
                "total_amount": 1200.0,
                "currency": "USD",
            },
            {
                "id": "flight2",
                "airline": "United",
                "origin": "JFK",
                "destination": "CDG",
                "departure_date": "2023-07-01",
                "return_date": "2023-07-14",
                "total_amount": 1350.0,
                "currency": "USD",
            },
        ]
    }


@pytest.fixture
def sample_accommodation_results():
    """Sample accommodation search results."""
    return {
        "accommodations": [
            {
                "id": "hotel1",
                "name": "Grand Hotel Paris",
                "location": "Paris City Center",
                "price_per_night": 250.0,
                "total_price": 3250.0,
                "rating": 4.8,
            },
            {
                "id": "hotel2",
                "name": "Luxury Suites",
                "location": "8th Arrondissement",
                "price_per_night": 350.0,
                "total_price": 4550.0,
                "rating": 4.9,
            },
        ]
    }


@pytest.fixture
def sample_destination_info():
    """Sample destination information."""
    return {
        "name": "Paris",
        "country": "France",
        "highlights": [
            "Eiffel Tower",
            "Louvre Museum",
            "Notre Dame Cathedral",
            "Seine River Cruise",
            "Montmartre District",
        ],
        "tips": [
            "Paris Metro is the fastest way to get around the city",
            "Many museums are free on the first Sunday of the month",
            "Consider the Paris Pass for multiple attractions",
        ],
    }


class TestPlanningTools:
    """Tests for the travel planning tools."""

    @patch("src.agents.planning_tools.redis_cache")
    @patch("src.agents.planning_tools.get_memory_client")
    @patch("src.agents.planning_tools.datetime")
    async def test_create_travel_plan(
        self,
        mock_datetime,
        mock_get_memory_client,
        mock_redis,
        travel_plan_data,
        mock_memory_client,
    ):
        """Test creating a new travel plan."""
        # Setup mocks
        mock_datetime.now.return_value = datetime(2023, 5, 15, 12, 0, 0)
        mock_redis.set = AsyncMock()
        mock_get_memory_client.return_value = mock_memory_client

        # Execute create_travel_plan
        result = await create_travel_plan(travel_plan_data)

        # Verify plan was created with correct data
        assert result["success"] is True
        assert "plan_id" in result
        assert result["message"] == "Travel plan created successfully"
        assert result["plan"]["user_id"] == travel_plan_data["user_id"]
        assert result["plan"]["title"] == travel_plan_data["title"]
        assert result["plan"]["destinations"] == travel_plan_data["destinations"]
        assert result["plan"]["start_date"] == travel_plan_data["start_date"]
        assert result["plan"]["budget"] == travel_plan_data["budget"]
        assert "components" in result["plan"]
        assert "flights" in result["plan"]["components"]
        assert "accommodations" in result["plan"]["components"]

        # Verify plan was cached
        mock_redis.set.assert_called_once()
        cache_args = mock_redis.set.call_args
        assert cache_args[0][0].startswith("travel_plan:")
        assert cache_args[0][1] == result["plan"]

        # Verify memory entities were created
        mock_memory_client.create_entities.assert_called_once()
        entity_args = mock_memory_client.create_entities.call_args
        assert len(entity_args[0][0]) == 1
        assert entity_args[0][0][0]["entityType"] == "TravelPlan"

        # Verify memory relations were created
        mock_memory_client.create_relations.assert_called_once()
        relation_args = mock_memory_client.create_relations.call_args
        assert len(relation_args[0][0]) == 3  # User relation + 2 destination relations

    @patch("src.agents.planning_tools.redis_cache")
    @patch("src.agents.planning_tools.get_memory_client")
    @patch("src.agents.planning_tools.datetime")
    async def test_update_travel_plan(
        self,
        mock_datetime,
        mock_get_memory_client,
        mock_redis,
        travel_plan_data,
        mock_memory_client,
    ):
        """Test updating an existing travel plan."""
        # Setup mocks
        mock_datetime.now.return_value = datetime(2023, 5, 15, 14, 0, 0)
        mock_get_memory_client.return_value = mock_memory_client

        # Create a cached plan for testing updates
        plan_id = "plan_20230515120000"
        existing_plan = {
            "plan_id": plan_id,
            "user_id": travel_plan_data["user_id"],
            "title": travel_plan_data["title"],
            "destinations": travel_plan_data["destinations"],
            "start_date": travel_plan_data["start_date"],
            "end_date": travel_plan_data["end_date"],
            "travelers": travel_plan_data["travelers"],
            "budget": travel_plan_data["budget"],
            "preferences": travel_plan_data["preferences"],
            "created_at": "2023-05-15T12:00:00",
            "updated_at": "2023-05-15T12:00:00",
            "components": {
                "flights": [],
                "accommodations": [],
                "activities": [],
                "transportation": [],
                "notes": [],
            },
        }
        mock_redis.get = AsyncMock(return_value=existing_plan)
        mock_redis.set = AsyncMock()

        # Define update parameters
        update_params = {
            "plan_id": plan_id,
            "user_id": travel_plan_data["user_id"],
            "updates": {
                "budget": 6000.0,
                "title": "Extended Summer Vacation",
                "end_date": "2023-07-21",
            },
        }

        # Execute update_travel_plan
        result = await update_travel_plan(update_params)

        # Verify plan was updated
        assert result["success"] is True
        assert result["plan_id"] == plan_id
        assert result["message"] == "Travel plan updated successfully"
        assert result["plan"]["budget"] == 6000.0
        assert result["plan"]["title"] == "Extended Summer Vacation"
        assert result["plan"]["end_date"] == "2023-07-21"
        assert result["plan"]["updated_at"] == "2023-05-15T14:00:00"

        # Verify plan was cached
        mock_redis.set.assert_called_once()

        # Verify memory observations were added
        mock_memory_client.add_observations.assert_called_once()
        observation_args = mock_memory_client.add_observations.call_args
        assert len(observation_args[0][0]) == 1
        assert len(observation_args[0][0][0]["contents"]) == 3

    @patch("src.agents.planning_tools.redis_cache")
    async def test_update_travel_plan_not_found(self, mock_redis):
        """Test updating a non-existent travel plan."""
        # Setup mocks
        mock_redis.get = AsyncMock(return_value=None)

        # Define update parameters
        update_params = {
            "plan_id": "nonexistent_plan",
            "user_id": "user123",
            "updates": {
                "budget": 6000.0,
            },
        }

        # Execute update_travel_plan
        result = await update_travel_plan(update_params)

        # Verify error response
        assert result["success"] is False
        assert "not found" in result["error"]

    @patch("src.agents.planning_tools.redis_cache")
    async def test_update_travel_plan_unauthorized(self, mock_redis):
        """Test updating a plan with wrong user ID."""
        # Setup mocks
        existing_plan = {
            "plan_id": "plan_123",
            "user_id": "user123",
            "title": "Summer Vacation",
            "destinations": ["Paris"],
            "created_at": "2023-05-15T12:00:00",
            "updated_at": "2023-05-15T12:00:00",
        }
        mock_redis.get = AsyncMock(return_value=existing_plan)

        # Define update parameters with wrong user
        update_params = {
            "plan_id": "plan_123",
            "user_id": "wrong_user",
            "updates": {
                "budget": 6000.0,
            },
        }

        # Execute update_travel_plan
        result = await update_travel_plan(update_params)

        # Verify error response
        assert result["success"] is False
        assert "Unauthorized" in result["error"]

    async def test_combine_search_results(
        self,
        sample_flight_results,
        sample_accommodation_results,
        sample_destination_info,
    ):
        """Test combining search results into recommendations."""
        # Create sample activity results
        sample_activity_results = {
            "activities": [
                {
                    "id": "activity1",
                    "name": "Eiffel Tower Tour",
                    "location": "Paris",
                    "price_per_person": 25.0,
                    "rating": 4.7,
                },
                {
                    "id": "activity2",
                    "name": "Louvre Museum Visit",
                    "location": "Paris",
                    "price_per_person": 20.0,
                    "rating": 4.9,
                },
                {
                    "id": "activity3",
                    "name": "Seine River Cruise",
                    "location": "Paris",
                    "price_per_person": 35.0,
                    "rating": 4.6,
                },
                {
                    "id": "activity4",
                    "name": "Walking Tour of Montmartre",
                    "location": "Paris",
                    "price_per_person": 15.0,
                    "rating": 4.5,
                },
                {
                    "id": "activity5",
                    "name": "Arc de Triomphe Visit",
                    "location": "Paris",
                    "price_per_person": 12.0,
                    "rating": 4.4,
                },
            ]
        }

        # Combine parameters
        combine_params = {
            "flight_results": sample_flight_results,
            "accommodation_results": sample_accommodation_results,
            "activity_results": sample_activity_results,
            "destination_info": sample_destination_info,
            "user_preferences": {
                "interests": ["history", "architecture"],
                "budget_sensitivity": "medium",
            },
        }

        # Execute combine_search_results
        result = await combine_search_results(combine_params)

        # Verify results were combined successfully
        assert result["success"] is True
        assert "combined_results" in result
        assert "recommendations" in result["combined_results"]
        assert "flights" in result["combined_results"]["recommendations"]
        assert "accommodations" in result["combined_results"]["recommendations"]
        assert "activities" in result["combined_results"]["recommendations"]
        assert "total_estimated_cost" in result["combined_results"]
        assert "destination_highlights" in result["combined_results"]
        assert "travel_tips" in result["combined_results"]

        # Verify recommendations contain expected data
        assert len(result["combined_results"]["recommendations"]["flights"]) > 0
        assert len(result["combined_results"]["recommendations"]["accommodations"]) > 0
        assert len(result["combined_results"]["recommendations"]["activities"]) > 0

        # Verify flights are sorted by price (lowest first)
        flights = result["combined_results"]["recommendations"]["flights"]
        if len(flights) >= 2:
            assert flights[0]["total_amount"] <= flights[1]["total_amount"]

        # Verify activities are sorted by rating (highest first)
        activities = result["combined_results"]["recommendations"]["activities"]
        if len(activities) >= 2:
            assert activities[0]["rating"] >= activities[1]["rating"]

        # Verify destination highlights and tips are included
        assert len(result["combined_results"]["destination_highlights"]) > 0
        assert len(result["combined_results"]["travel_tips"]) > 0
