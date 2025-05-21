"""Tests for trip-related endpoints.

This module provides tests for the trip-related endpoints in the TripSage API.
"""

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_trip(async_client: AsyncClient, auth_headers):
    """Test creating a new trip.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the trip service
    with patch(
        "tripsage.api.services.trip.TripService.create_trip", new_callable=AsyncMock
    ) as mock_create_trip:
        # Configure mock
        today = date.today()
        trip_id = UUID("12345678-1234-5678-1234-567812345678")
        mock_create_trip.return_value = {
            "id": trip_id,
            "user_id": "test-user-id",
            "title": "Test Trip",
            "description": "A test trip",
            "start_date": today,
            "end_date": today + timedelta(days=7),
            "duration_days": 7,
            "destinations": [
                {
                    "name": "Paris",
                    "country": "France",
                    "arrival_date": today,
                    "departure_date": today + timedelta(days=7),
                }
            ],
            "preferences": {
                "budget": {"total": 5000, "currency": "USD"},
                "accommodation": {"type": "hotel", "min_rating": 4},
            },
            "itinerary_id": None,
            "status": "planning",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # Send request
        response = await async_client.post(
            "/api/trips/",
            headers=auth_headers,
            json={
                "title": "Test Trip",
                "description": "A test trip",
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=7)).isoformat(),
                "destinations": [
                    {
                        "name": "Paris",
                        "country": "France",
                        "arrival_date": today.isoformat(),
                        "departure_date": (today + timedelta(days=7)).isoformat(),
                    }
                ],
                "preferences": {
                    "budget": {"total": 5000, "currency": "USD"},
                    "accommodation": {"type": "hotel", "min_rating": 4},
                },
            },
        )

        # Check response
        assert response.status_code == 201
        data = response.json()

        assert data["id"] == str(trip_id)
        assert data["title"] == "Test Trip"
        assert data["description"] == "A test trip"
        assert data["status"] == "planning"
        assert len(data["destinations"]) == 1
        assert data["destinations"][0]["name"] == "Paris"
        assert data["preferences"]["budget"]["total"] == 5000

        # Verify mock
        mock_create_trip.assert_called_once()


@pytest.mark.asyncio
async def test_list_trips(async_client: AsyncClient, auth_headers):
    """Test listing trips.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the trip service
    with patch(
        "tripsage.api.services.trip.TripService.list_trips", new_callable=AsyncMock
    ) as mock_list_trips:
        # Configure mock
        today = date.today()
        mock_list_trips.return_value = (
            [
                {
                    "id": UUID("12345678-1234-5678-1234-567812345678"),
                    "title": "Trip 1",
                    "start_date": today,
                    "end_date": today + timedelta(days=7),
                    "duration_days": 7,
                    "destinations": ["Paris", "London"],
                    "status": "planning",
                    "created_at": datetime.now(),
                },
                {
                    "id": UUID("87654321-8765-4321-8765-432187654321"),
                    "title": "Trip 2",
                    "start_date": today + timedelta(days=30),
                    "end_date": today + timedelta(days=37),
                    "duration_days": 7,
                    "destinations": ["Tokyo", "Kyoto"],
                    "status": "planning",
                    "created_at": datetime.now(),
                },
            ],
            2,  # Total count
        )

        # Send request
        response = await async_client.get(
            "/api/trips/",
            headers=auth_headers,
            params={"skip": 0, "limit": 10},
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert data["skip"] == 0
        assert data["limit"] == 10
        assert len(data["items"]) == 2

        assert data["items"][0]["title"] == "Trip 1"
        assert data["items"][0]["destinations"] == ["Paris", "London"]
        assert data["items"][1]["title"] == "Trip 2"
        assert data["items"][1]["destinations"] == ["Tokyo", "Kyoto"]

        # Verify mock
        mock_list_trips.assert_called_once_with(
            user_id="test-user-id", skip=0, limit=10
        )


@pytest.mark.asyncio
async def test_get_trip(async_client: AsyncClient, auth_headers):
    """Test getting a trip by ID.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the trip service
    with patch(
        "tripsage.api.services.trip.TripService.get_trip", new_callable=AsyncMock
    ) as mock_get_trip:
        # Configure mock
        today = date.today()
        trip_id = UUID("12345678-1234-5678-1234-567812345678")
        mock_get_trip.return_value = {
            "id": trip_id,
            "user_id": "test-user-id",
            "title": "Test Trip",
            "description": "A test trip",
            "start_date": today,
            "end_date": today + timedelta(days=7),
            "duration_days": 7,
            "destinations": [
                {
                    "name": "Paris",
                    "country": "France",
                    "arrival_date": today,
                    "departure_date": today + timedelta(days=7),
                }
            ],
            "preferences": {
                "budget": {"total": 5000, "currency": "USD"},
                "accommodation": {"type": "hotel", "min_rating": 4},
            },
            "itinerary_id": None,
            "status": "planning",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # Send request
        response = await async_client.get(
            f"/api/trips/{trip_id}",
            headers=auth_headers,
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(trip_id)
        assert data["title"] == "Test Trip"
        assert data["description"] == "A test trip"
        assert data["status"] == "planning"
        assert len(data["destinations"]) == 1
        assert data["destinations"][0]["name"] == "Paris"

        # Verify mock
        mock_get_trip.assert_called_once_with(user_id="test-user-id", trip_id=trip_id)


@pytest.mark.asyncio
async def test_get_trip_not_found(async_client: AsyncClient, auth_headers):
    """Test getting a non-existent trip.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the trip service
    with patch(
        "tripsage.api.services.trip.TripService.get_trip", new_callable=AsyncMock
    ) as mock_get_trip:
        # Configure mock
        trip_id = UUID("12345678-1234-5678-1234-567812345678")
        mock_get_trip.return_value = None  # Trip not found

        # Send request
        response = await async_client.get(
            f"/api/trips/{trip_id}",
            headers=auth_headers,
        )

        # Check response
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert f"Trip with ID {trip_id} not found" in data["detail"]

        # Verify mock
        mock_get_trip.assert_called_once_with(user_id="test-user-id", trip_id=trip_id)


@pytest.mark.asyncio
async def test_update_trip(async_client: AsyncClient, auth_headers):
    """Test updating a trip.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the trip service
    with patch(
        "tripsage.api.services.trip.TripService.update_trip", new_callable=AsyncMock
    ) as mock_update_trip:
        # Configure mock
        today = date.today()
        trip_id = UUID("12345678-1234-5678-1234-567812345678")
        mock_update_trip.return_value = {
            "id": trip_id,
            "user_id": "test-user-id",
            "title": "Updated Trip Title",
            "description": "Updated trip description",
            "start_date": today,
            "end_date": today + timedelta(days=10),  # Extended trip
            "duration_days": 10,
            "destinations": [
                {
                    "name": "Paris",
                    "country": "France",
                    "arrival_date": today,
                    "departure_date": today + timedelta(days=5),
                },
                {
                    "name": "London",
                    "country": "UK",
                    "arrival_date": today + timedelta(days=5),
                    "departure_date": today + timedelta(days=10),
                },
            ],
            "preferences": {
                "budget": {"total": 6000, "currency": "USD"},
                "accommodation": {"type": "hotel", "min_rating": 4},
            },
            "itinerary_id": None,
            "status": "planning",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # Send request
        response = await async_client.put(
            f"/api/trips/{trip_id}",
            headers=auth_headers,
            json={
                "title": "Updated Trip Title",
                "description": "Updated trip description",
                "end_date": (today + timedelta(days=10)).isoformat(),
                "destinations": [
                    {
                        "name": "Paris",
                        "country": "France",
                        "arrival_date": today.isoformat(),
                        "departure_date": (today + timedelta(days=5)).isoformat(),
                    },
                    {
                        "name": "London",
                        "country": "UK",
                        "arrival_date": (today + timedelta(days=5)).isoformat(),
                        "departure_date": (today + timedelta(days=10)).isoformat(),
                    },
                ],
            },
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(trip_id)
        assert data["title"] == "Updated Trip Title"
        assert data["description"] == "Updated trip description"
        assert len(data["destinations"]) == 2
        assert data["destinations"][0]["name"] == "Paris"
        assert data["destinations"][1]["name"] == "London"

        # Verify mock
        mock_update_trip.assert_called_once()


@pytest.mark.asyncio
async def test_update_trip_not_found(async_client: AsyncClient, auth_headers):
    """Test updating a non-existent trip.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the trip service
    with patch(
        "tripsage.api.services.trip.TripService.update_trip", new_callable=AsyncMock
    ) as mock_update_trip:
        # Configure mock
        trip_id = UUID("12345678-1234-5678-1234-567812345678")
        mock_update_trip.return_value = None  # Trip not found

        # Send request
        response = await async_client.put(
            f"/api/trips/{trip_id}",
            headers=auth_headers,
            json={"title": "Updated Trip Title"},
        )

        # Check response
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert f"Trip with ID {trip_id} not found" in data["detail"]

        # Verify mock
        mock_update_trip.assert_called_once()


@pytest.mark.asyncio
async def test_delete_trip(async_client: AsyncClient, auth_headers):
    """Test deleting a trip.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the trip service
    with patch(
        "tripsage.api.services.trip.TripService.delete_trip", new_callable=AsyncMock
    ) as mock_delete_trip:
        # Configure mock
        trip_id = UUID("12345678-1234-5678-1234-567812345678")
        mock_delete_trip.return_value = True  # Successfully deleted

        # Send request
        response = await async_client.delete(
            f"/api/trips/{trip_id}",
            headers=auth_headers,
        )

        # Check response
        assert response.status_code == 204
        assert response.content == b""  # No content for successful delete

        # Verify mock
        mock_delete_trip.assert_called_once_with(
            user_id="test-user-id", trip_id=trip_id
        )


@pytest.mark.asyncio
async def test_delete_trip_not_found(async_client: AsyncClient, auth_headers):
    """Test deleting a non-existent trip.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the trip service
    with patch(
        "tripsage.api.services.trip.TripService.delete_trip", new_callable=AsyncMock
    ) as mock_delete_trip:
        # Configure mock
        trip_id = UUID("12345678-1234-5678-1234-567812345678")
        mock_delete_trip.return_value = False  # Trip not found

        # Send request
        response = await async_client.delete(
            f"/api/trips/{trip_id}",
            headers=auth_headers,
        )

        # Check response
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert f"Trip with ID {trip_id} not found" in data["detail"]

        # Verify mock
        mock_delete_trip.assert_called_once_with(
            user_id="test-user-id", trip_id=trip_id
        )


@pytest.mark.asyncio
async def test_update_trip_preferences(async_client: AsyncClient, auth_headers):
    """Test updating trip preferences.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the trip service
    with patch(
        "tripsage.api.services.trip.TripService.update_trip_preferences",
        new_callable=AsyncMock,
    ) as mock_update_prefs:
        # Configure mock
        today = date.today()
        trip_id = UUID("12345678-1234-5678-1234-567812345678")
        mock_update_prefs.return_value = {
            "id": trip_id,
            "user_id": "test-user-id",
            "title": "Test Trip",
            "description": "A test trip",
            "start_date": today,
            "end_date": today + timedelta(days=7),
            "duration_days": 7,
            "destinations": [
                {
                    "name": "Paris",
                    "country": "France",
                }
            ],
            "preferences": {
                "budget": {"total": 6000, "currency": "EUR"},
                "accommodation": {"type": "apartment", "min_rating": 3},
                "transportation": {
                    "flight_preferences": {
                        "seat_class": "business",
                        "max_stops": 0,
                    }
                },
            },
            "itinerary_id": None,
            "status": "planning",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # New preferences to set
        new_preferences = {
            "budget": {"total": 6000, "currency": "EUR"},
            "accommodation": {"type": "apartment", "min_rating": 3},
            "transportation": {
                "flight_preferences": {
                    "seat_class": "business",
                    "max_stops": 0,
                }
            },
        }

        # Send request
        response = await async_client.post(
            f"/api/trips/{trip_id}/preferences",
            headers=auth_headers,
            json=new_preferences,
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(trip_id)
        assert data["preferences"]["budget"]["total"] == 6000
        assert data["preferences"]["budget"]["currency"] == "EUR"
        assert data["preferences"]["accommodation"]["type"] == "apartment"
        assert (
            data["preferences"]["transportation"]["flight_preferences"]["seat_class"]
            == "business"
        )

        # Verify mock
        mock_update_prefs.assert_called_once_with(
            user_id="test-user-id", trip_id=trip_id, preferences=new_preferences
        )


@pytest.mark.asyncio
async def test_get_trip_summary(async_client: AsyncClient, auth_headers):
    """Test getting a trip summary.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the trip service
    with patch(
        "tripsage.api.services.trip.TripService.get_trip_summary",
        new_callable=AsyncMock,
    ) as mock_get_summary:
        # Configure mock
        trip_id = UUID("12345678-1234-5678-1234-567812345678")
        mock_get_summary.return_value = {
            "id": trip_id,
            "title": "Test Trip",
            "date_range": "May 20-27, 2025",
            "duration_days": 7,
            "destinations": ["Paris", "London"],
            "accommodation_summary": "4-star hotels in city centers",
            "transportation_summary": "Economy flights with 1 connection, local metro",
            "budget_summary": {
                "total": 5000,
                "currency": "USD",
                "spent": 2500,
                "remaining": 2500,
                "breakdown": {
                    "accommodation": {"budget": 2000, "spent": 1800},
                    "transportation": {"budget": 1500, "spent": 500},
                    "food": {"budget": 1000, "spent": 200},
                    "activities": {"budget": 500, "spent": 0},
                },
            },
            "has_itinerary": True,
            "completion_percentage": 60,
        }

        # Send request
        response = await async_client.get(
            f"/api/trips/{trip_id}/summary",
            headers=auth_headers,
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(trip_id)
        assert data["title"] == "Test Trip"
        assert data["date_range"] == "May 20-27, 2025"
        assert data["destinations"] == ["Paris", "London"]
        assert data["completion_percentage"] == 60
        assert data["has_itinerary"] is True
        assert data["budget_summary"]["total"] == 5000
        assert data["budget_summary"]["spent"] == 2500
        assert data["budget_summary"]["remaining"] == 2500

        # Verify mock
        mock_get_summary.assert_called_once_with(
            user_id="test-user-id", trip_id=trip_id
        )
