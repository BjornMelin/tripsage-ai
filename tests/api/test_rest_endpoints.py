"""Tests for the remaining API endpoints.

This module provides tests for flights, accommodations, destinations, and
itineraries endpoints in the TripSage API.
"""

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from httpx import AsyncClient


# Flight tests
@pytest.mark.asyncio
async def test_search_flights(async_client: AsyncClient, auth_headers):
    """Test searching for flights.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the flight service
    with patch(
        "tripsage.api.services.flight.FlightService.search_flights",
        new_callable=AsyncMock,
    ) as mock_search:
        # Configure mock
        today = date.today()
        mock_search.return_value = {
            "results": [
                {
                    "id": "flight-offer-1",
                    "origin": "JFK",
                    "destination": "LHR",
                    "departure_date": today,
                    "return_date": today + timedelta(days=7),
                    "airline": "AA",
                    "airline_name": "American Airlines",
                    "price": 850.00,
                    "currency": "USD",
                    "cabin_class": "economy",
                    "stops": 0,
                    "duration_minutes": 425,
                    "segments": [
                        {
                            "departure_airport": "JFK",
                            "arrival_airport": "LHR",
                            "departure_time": "2025-05-20T18:00:00Z",
                            "arrival_time": "2025-05-21T06:05:00Z",
                            "flight_number": "AA100",
                            "duration_minutes": 425,
                        }
                    ],
                    "booking_link": "https://example.com/booking/1",
                }
            ],
            "count": 1,
            "currency": "USD",
            "search_id": "search-12345",
            "trip_id": "12345678-1234-5678-1234-567812345678",
            "min_price": 850.00,
            "max_price": 850.00,
            "search_request": {
                "origin": "JFK",
                "destination": "LHR",
                "departure_date": today.isoformat(),
                "return_date": (today + timedelta(days=7)).isoformat(),
                "adults": 1,
                "cabin_class": "economy",
            },
        }

        # Send request
        response = await async_client.post(
            "/api/flights/search",
            headers=auth_headers,
            json={
                "origin": "JFK",
                "destination": "LHR",
                "departure_date": today.isoformat(),
                "return_date": (today + timedelta(days=7)).isoformat(),
                "adults": 1,
                "cabin_class": "economy",
            },
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["count"] == 1
        assert data["currency"] == "USD"
        assert len(data["results"]) == 1
        assert data["results"][0]["origin"] == "JFK"
        assert data["results"][0]["destination"] == "LHR"
        assert data["results"][0]["price"] == 850.00

        # Verify mock
        mock_search.assert_called_once()


@pytest.mark.asyncio
async def test_save_flight(async_client: AsyncClient, auth_headers):
    """Test saving a flight offer.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the flight service
    with patch(
        "tripsage.api.services.flight.FlightService.save_flight",
        new_callable=AsyncMock,
    ) as mock_save:
        # Configure mock
        today = date.today()
        trip_id = UUID("12345678-1234-5678-1234-567812345678")
        saved_id = UUID("98765432-9876-5432-9876-543298765432")

        mock_save.return_value = {
            "id": saved_id,
            "user_id": "test-user-id",
            "trip_id": trip_id,
            "offer": {
                "id": "flight-offer-1",
                "origin": "JFK",
                "destination": "LHR",
                "departure_date": today,
                "return_date": today + timedelta(days=7),
                "airline": "AA",
                "airline_name": "American Airlines",
                "price": 850.00,
                "currency": "USD",
                "cabin_class": "economy",
                "stops": 0,
                "duration_minutes": 425,
                "segments": [
                    {
                        "departure_airport": "JFK",
                        "arrival_airport": "LHR",
                        "departure_time": "2025-05-20T18:00:00Z",
                        "arrival_time": "2025-05-21T06:05:00Z",
                        "flight_number": "AA100",
                        "duration_minutes": 425,
                    }
                ],
            },
            "saved_at": datetime.now(),
            "notes": "Good direct flight option",
        }

        # Send request
        response = await async_client.post(
            "/api/flights/save",
            headers=auth_headers,
            json={
                "offer_id": "flight-offer-1",
                "trip_id": str(trip_id),
                "notes": "Good direct flight option",
            },
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(saved_id)
        assert data["trip_id"] == str(trip_id)
        assert data["offer"]["id"] == "flight-offer-1"
        assert data["offer"]["origin"] == "JFK"
        assert data["offer"]["destination"] == "LHR"
        assert data["notes"] == "Good direct flight option"

        # Verify mock
        mock_save.assert_called_once()


# Accommodation tests
@pytest.mark.asyncio
async def test_search_accommodations(async_client: AsyncClient, auth_headers):
    """Test searching for accommodations.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the accommodation service
    with patch(
        "tripsage.api.services.accommodation.AccommodationService.search_accommodations",
        new_callable=AsyncMock,
    ) as mock_search:
        # Configure mock
        today = date.today()
        mock_search.return_value = {
            "listings": [
                {
                    "id": "accom-listing-1",
                    "name": "Luxury Hotel Downtown",
                    "description": "Beautiful hotel in city center",
                    "property_type": "hotel",
                    "location": {
                        "address": "123 Main St",
                        "city": "London",
                        "country": "UK",
                        "latitude": 51.5074,
                        "longitude": -0.1278,
                    },
                    "price_per_night": 250.00,
                    "currency": "USD",
                    "rating": 4.8,
                    "review_count": 350,
                    "amenities": [
                        {"name": "Free WiFi"},
                        {"name": "Swimming Pool"},
                        {"name": "Gym"},
                    ],
                    "images": [
                        {"url": "https://example.com/hotel1.jpg", "is_primary": True}
                    ],
                    "max_guests": 2,
                    "bedrooms": 1,
                    "beds": 1,
                    "bathrooms": 1,
                    "check_in_time": "15:00",
                    "check_out_time": "11:00",
                    "cancellation_policy": "flexible",
                    "total_price": 1750.00,
                    "url": "https://example.com/hotel1",
                    "source": "booking",
                }
            ],
            "count": 1,
            "currency": "USD",
            "search_id": "search-67890",
            "trip_id": "12345678-1234-5678-1234-567812345678",
            "min_price": 250.00,
            "max_price": 250.00,
            "avg_price": 250.00,
            "search_request": {
                "location": "London",
                "check_in": today.isoformat(),
                "check_out": (today + timedelta(days=7)).isoformat(),
                "adults": 2,
                "rooms": 1,
            },
        }

        # Send request
        response = await async_client.post(
            "/api/accommodations/search",
            headers=auth_headers,
            json={
                "location": "London",
                "check_in": today.isoformat(),
                "check_out": (today + timedelta(days=7)).isoformat(),
                "adults": 2,
                "rooms": 1,
            },
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["count"] == 1
        assert data["currency"] == "USD"
        assert len(data["listings"]) == 1
        assert data["listings"][0]["name"] == "Luxury Hotel Downtown"
        assert data["listings"][0]["price_per_night"] == 250.00
        assert data["listings"][0]["total_price"] == 1750.00

        # Verify mock
        mock_search.assert_called_once()


@pytest.mark.asyncio
async def test_get_accommodation_details(async_client: AsyncClient, auth_headers):
    """Test getting accommodation details.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the accommodation service
    with patch(
        "tripsage.api.services.accommodation.AccommodationService.get_accommodation_details",
        new_callable=AsyncMock,
    ) as mock_get:
        # Configure mock
        today = date.today()
        mock_get.return_value = {
            "listing": {
                "id": "accom-listing-1",
                "name": "Luxury Hotel Downtown",
                "description": "Beautiful hotel in city center",
                "property_type": "hotel",
                "location": {
                    "address": "123 Main St",
                    "city": "London",
                    "country": "UK",
                    "latitude": 51.5074,
                    "longitude": -0.1278,
                },
                "price_per_night": 250.00,
                "currency": "USD",
                "rating": 4.8,
                "review_count": 350,
                "amenities": [
                    {"name": "Free WiFi"},
                    {"name": "Swimming Pool"},
                    {"name": "Gym"},
                ],
                "images": [
                    {"url": "https://example.com/hotel1.jpg", "is_primary": True}
                ],
                "max_guests": 2,
                "bedrooms": 1,
                "beds": 1,
                "bathrooms": 1,
                "check_in_time": "15:00",
                "check_out_time": "11:00",
                "cancellation_policy": "flexible",
                "total_price": 1750.00,
                "url": "https://example.com/hotel1",
                "source": "booking",
            },
            "availability": True,
            "total_price": 1750.00,
        }

        # Send request
        response = await async_client.post(
            "/api/accommodations/details",
            headers=auth_headers,
            json={
                "listing_id": "accom-listing-1",
                "check_in": today.isoformat(),
                "check_out": (today + timedelta(days=7)).isoformat(),
                "adults": 2,
            },
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["availability"] is True
        assert data["total_price"] == 1750.00
        assert data["listing"]["id"] == "accom-listing-1"
        assert data["listing"]["name"] == "Luxury Hotel Downtown"
        assert data["listing"]["price_per_night"] == 250.00

        # Verify mock
        mock_get.assert_called_once()


# Destinations tests
@pytest.mark.asyncio
async def test_search_destinations(async_client: AsyncClient, auth_headers):
    """Test searching for destinations.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the destination service
    with patch(
        "tripsage.api.services.destination.DestinationService.search_destinations",
        new_callable=AsyncMock,
    ) as mock_search:
        # Configure mock
        mock_search.return_value = {
            "destinations": [
                {
                    "id": "dest-1",
                    "name": "Paris",
                    "country": "France",
                    "region": "Île-de-France",
                    "city": "Paris",
                    "description": "The City of Light",
                    "categories": ["city", "cultural", "historical"],
                    "latitude": 48.8566,
                    "longitude": 2.3522,
                    "timezone": "Europe/Paris",
                    "currency": "EUR",
                    "language": "French",
                    "images": [
                        {
                            "url": "https://example.com/paris.jpg",
                            "is_primary": True,
                            "attribution": "Tourism Board",
                        }
                    ],
                    "points_of_interest": [
                        {
                            "name": "Eiffel Tower",
                            "category": "landmark",
                            "description": "Famous iron tower",
                            "address": "Champ de Mars, 5 Av. Anatole France",
                            "latitude": 48.8584,
                            "longitude": 2.2945,
                            "rating": 4.7,
                        }
                    ],
                    "best_time_to_visit": ["April", "May", "June", "September"],
                    "travel_advisory": "Exercise normal precautions",
                    "visa_requirements": "Schengen visa required for many countries",
                    "local_transportation": "Metro, bus, taxis",
                    "popular_activities": [
                        "Visiting museums",
                        "Dining",
                        "Shopping",
                        "River cruises",
                    ],
                    "safety_rating": 4.2,
                }
            ],
            "count": 1,
            "query": "Paris",
        }

        # Send request
        response = await async_client.post(
            "/api/destinations/search",
            headers=auth_headers,
            json={
                "query": "Paris",
                "categories": ["city", "cultural"],
                "include_weather": True,
                "include_attractions": True,
            },
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["count"] == 1
        assert data["query"] == "Paris"
        assert len(data["destinations"]) == 1
        assert data["destinations"][0]["name"] == "Paris"
        assert data["destinations"][0]["country"] == "France"
        assert (
            "Eiffel Tower" in data["destinations"][0]["points_of_interest"][0]["name"]
        )
        assert "cultural" in data["destinations"][0]["categories"]

        # Verify mock
        mock_search.assert_called_once()


@pytest.mark.asyncio
async def test_get_destination_details(async_client: AsyncClient, auth_headers):
    """Test getting destination details.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the destination service
    with patch(
        "tripsage.api.services.destination.DestinationService.get_destination_details",
        new_callable=AsyncMock,
    ) as mock_get:
        # Configure mock
        mock_get.return_value = {
            "destination": {
                "id": "dest-1",
                "name": "Paris",
                "country": "France",
                "region": "Île-de-France",
                "city": "Paris",
                "description": "The City of Light",
                "categories": ["city", "cultural", "historical"],
                "latitude": 48.8566,
                "longitude": 2.3522,
                "timezone": "Europe/Paris",
                "currency": "EUR",
                "language": "French",
                "images": [
                    {
                        "url": "https://example.com/paris.jpg",
                        "is_primary": True,
                        "attribution": "Tourism Board",
                    }
                ],
                "points_of_interest": [
                    {
                        "name": "Eiffel Tower",
                        "category": "landmark",
                        "description": "Famous iron tower",
                        "address": "Champ de Mars, 5 Av. Anatole France",
                        "latitude": 48.8584,
                        "longitude": 2.2945,
                        "rating": 4.7,
                    },
                    {
                        "name": "Louvre Museum",
                        "category": "museum",
                        "description": "World's largest art museum",
                        "address": "Rue de Rivoli, 75001",
                        "latitude": 48.8606,
                        "longitude": 2.3376,
                        "rating": 4.8,
                    },
                ],
                "weather": {
                    "season": "Spring",
                    "temperature_high_celsius": 20,
                    "temperature_low_celsius": 12,
                    "precipitation_mm": 25,
                    "humidity_percent": 65,
                    "conditions": "Partly cloudy with occasional rain",
                    "best_time_to_visit": ["April", "May", "June", "September"],
                },
                "best_time_to_visit": ["April", "May", "June", "September"],
                "travel_advisory": "Exercise normal precautions",
                "visa_requirements": "Schengen visa required for many nationalities",
                "local_transportation": "Metro, bus, taxis",
                "popular_activities": [
                    "Visiting museums",
                    "Dining",
                    "Shopping",
                    "River cruises",
                ],
                "safety_rating": 4.2,
            }
        }

        # Send request
        response = await async_client.post(
            "/api/destinations/details",
            headers=auth_headers,
            json={
                "destination_id": "dest-1",
                "include_weather": True,
                "include_attractions": True,
            },
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["destination"]["id"] == "dest-1"
        assert data["destination"]["name"] == "Paris"
        assert data["destination"]["country"] == "France"
        assert len(data["destination"]["points_of_interest"]) == 2
        assert "weather" in data["destination"]
        assert data["destination"]["weather"]["season"] == "Spring"

        # Verify mock
        mock_get.assert_called_once()


# Itineraries tests
@pytest.mark.asyncio
async def test_create_itinerary(async_client: AsyncClient, auth_headers):
    """Test creating an itinerary.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the itinerary service
    with patch(
        "tripsage.api.services.itinerary.ItineraryService.create_itinerary",
        new_callable=AsyncMock,
    ) as mock_create:
        # Configure mock
        itinerary_id = "itin-12345"
        today = date.today()

        mock_create.return_value = {
            "id": itinerary_id,
            "user_id": "test-user-id",
            "title": "Paris Vacation",
            "description": "A week in Paris",
            "status": "draft",
            "start_date": today,
            "end_date": today + timedelta(days=6),
            "days": [
                {
                    "date": today,
                    "items": [],
                    "notes": "Arrival day",
                },
                {
                    "date": today + timedelta(days=1),
                    "items": [],
                    "notes": "Explore city center",
                },
            ],
            "destinations": ["dest-1"],
            "total_budget": 5000,
            "budget_spent": 0,
            "currency": "USD",
            "share_settings": {
                "visibility": "private",
                "shared_with": [],
                "editable_by": [],
            },
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "tags": ["vacation", "europe"],
        }

        # Send request
        response = await async_client.post(
            "/api/itineraries/",
            headers=auth_headers,
            json={
                "title": "Paris Vacation",
                "description": "A week in Paris",
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=6)).isoformat(),
                "destinations": ["dest-1"],
                "total_budget": 5000,
                "currency": "USD",
                "tags": ["vacation", "europe"],
            },
        )

        # Check response
        assert response.status_code == 201
        data = response.json()

        assert data["id"] == itinerary_id
        assert data["title"] == "Paris Vacation"
        assert data["description"] == "A week in Paris"
        assert data["status"] == "draft"
        assert len(data["days"]) == 2
        assert data["days"][0]["notes"] == "Arrival day"
        assert data["total_budget"] == 5000
        assert data["tags"] == ["vacation", "europe"]

        # Verify mock
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_check_conflicts(async_client: AsyncClient, auth_headers):
    """Test checking for conflicts in an itinerary.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the itinerary service
    with patch(
        "tripsage.api.services.itinerary.ItineraryService.check_conflicts",
        new_callable=AsyncMock,
    ) as mock_check:
        # Configure mock
        itinerary_id = "itin-12345"

        mock_check.return_value = {
            "has_conflicts": True,
            "conflicts": [
                {
                    "type": "time_overlap",
                    "date": "2025-05-20",
                    "items": [
                        {
                            "id": "item-1",
                            "title": "Museum Visit",
                            "time_slot": {"start_time": "10:00", "end_time": "13:00"},
                        },
                        {
                            "id": "item-2",
                            "title": "Guided Tour",
                            "time_slot": {"start_time": "11:00", "end_time": "14:00"},
                        },
                    ],
                    "message": "Time slot overlap between Museum Visit and Guided Tour",
                },
                {
                    "type": "accommodation_gap",
                    "date": "2025-05-22",
                    "message": "No accommodation booked for 2025-05-22",
                },
            ],
        }

        # Send request
        response = await async_client.get(
            f"/api/itineraries/{itinerary_id}/conflicts",
            headers=auth_headers,
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["has_conflicts"] is True
        assert len(data["conflicts"]) == 2
        assert data["conflicts"][0]["type"] == "time_overlap"
        assert "Museum Visit" in data["conflicts"][0]["message"]
        assert data["conflicts"][1]["type"] == "accommodation_gap"

        # Verify mock
        mock_check.assert_called_once_with(
            user_id="test-user-id", itinerary_id=itinerary_id
        )


@pytest.mark.asyncio
async def test_optimize_itinerary(async_client: AsyncClient, auth_headers):
    """Test optimizing an itinerary.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the itinerary service
    with patch(
        "tripsage.api.services.itinerary.ItineraryService.optimize_itinerary",
        new_callable=AsyncMock,
    ) as mock_optimize:
        # Configure mock
        itinerary_id = "itin-12345"
        today = date.today()

        # Create sample itineraries for original and optimized versions
        original_itinerary = {
            "id": itinerary_id,
            "user_id": "test-user-id",
            "title": "Paris Vacation",
            "status": "draft",
            "days": [
                {
                    "date": today,
                    "items": [
                        {
                            "id": "item-1",
                            "type": "activity",
                            "title": "Eiffel Tower",
                            "time_slot": {"start_time": "14:00", "end_time": "16:00"},
                        },
                        {
                            "id": "item-2",
                            "type": "activity",
                            "title": "Louvre Museum",
                            "time_slot": {"start_time": "10:00", "end_time": "13:00"},
                        },
                    ],
                },
            ],
        }

        optimized_itinerary = {
            "id": itinerary_id,
            "user_id": "test-user-id",
            "title": "Paris Vacation",
            "status": "draft",
            "days": [
                {
                    "date": today,
                    "items": [
                        {
                            "id": "item-2",
                            "type": "activity",
                            "title": "Louvre Museum",
                            "time_slot": {"start_time": "10:00", "end_time": "13:00"},
                        },
                        {
                            "id": "item-1",
                            "type": "activity",
                            "title": "Eiffel Tower",
                            "time_slot": {"start_time": "14:00", "end_time": "16:00"},
                        },
                    ],
                },
            ],
        }

        mock_optimize.return_value = {
            "original_itinerary": original_itinerary,
            "optimized_itinerary": optimized_itinerary,
            "changes": [
                {
                    "type": "reorder",
                    "item_id": "item-1",
                    "description": "Reordered activities for optimal timing",
                }
            ],
            "optimization_score": 0.85,
        }

        # Send request
        response = await async_client.post(
            f"/api/itineraries/{itinerary_id}/optimize",
            headers=auth_headers,
            json={
                "settings": {
                    "prioritize": ["time", "convenience"],
                    "minimize_travel_time": True,
                    "include_breaks": True,
                    "break_duration_minutes": 30,
                    "start_day_time": "09:00",
                    "end_day_time": "20:00",
                },
            },
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert "original_itinerary" in data
        assert "optimized_itinerary" in data
        assert "changes" in data
        assert len(data["changes"]) == 1
        assert data["changes"][0]["type"] == "reorder"
        assert data["optimization_score"] == 0.85

        # Verify mock
        mock_optimize.assert_called_once()


@pytest.mark.asyncio
async def test_add_item_to_itinerary(async_client: AsyncClient, auth_headers):
    """Test adding an item to an itinerary.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the itinerary service
    with patch(
        "tripsage.api.services.itinerary.ItineraryService.add_itinerary_item",
        new_callable=AsyncMock,
    ) as mock_add_item:
        # Configure mock
        itinerary_id = "itin-12345"
        today = date.today()

        mock_add_item.return_value = {
            "id": "item-3",
            "type": "activity",
            "title": "Seine River Cruise",
            "description": "Evening cruise on the Seine",
            "date": today,
            "time_slot": {
                "start_time": "19:00",
                "end_time": "21:00",
                "duration_minutes": 120,
            },
            "location": {
                "name": "Seine River Cruise Dock",
                "address": "Port de la Bourdonnais, 75007 Paris",
                "coordinates": {"latitude": 48.8588, "longitude": 2.2943},
            },
            "cost": 35.00,
            "currency": "EUR",
            "booking_reference": "SEINE123",
            "is_flexible": False,
        }

        # Send request
        response = await async_client.post(
            f"/api/itineraries/{itinerary_id}/items",
            headers=auth_headers,
            json={
                "type": "activity",
                "title": "Seine River Cruise",
                "description": "Evening cruise on the Seine",
                "date": today.isoformat(),
                "time_slot": {
                    "start_time": "19:00",
                    "end_time": "21:00",
                    "duration_minutes": 120,
                },
                "location": {
                    "name": "Seine River Cruise Dock",
                    "address": "Port de la Bourdonnais, 75007 Paris",
                    "coordinates": {"latitude": 48.8588, "longitude": 2.2943},
                },
                "cost": 35.00,
                "currency": "EUR",
                "booking_reference": "SEINE123",
                "activity_details": {
                    "activity_type": "tour",
                    "duration_minutes": 120,
                    "booking_required": True,
                    "guided": True,
                },
            },
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "item-3"
        assert data["type"] == "activity"
        assert data["title"] == "Seine River Cruise"
        assert data["time_slot"]["start_time"] == "19:00"
        assert data["time_slot"]["end_time"] == "21:00"
        assert data["cost"] == 35.00
        assert data["currency"] == "EUR"

        # Verify mock
        mock_add_item.assert_called_once()
