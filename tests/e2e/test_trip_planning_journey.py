"""
End-to-end tests for complete trip planning user journeys.

Tests full user workflows from trip creation to booking completion,
involving multiple services and real API interactions.
"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from tests.factories import TripFactory, UserFactory
from tripsage.api.main import app


class TestTripPlanningJourney:
    """E2E tests for complete trip planning workflows."""

    @pytest.fixture
    async def authenticated_client(self):
        """Create an authenticated HTTP client for testing."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create test user and get auth token
            user_data = UserFactory.create()

            # Register user
            register_response = await client.post(
                "/api/auth/register",
                json={
                    "email": user_data["email"],
                    "username": user_data["username"],
                    "password": "testpassword123",
                    "first_name": user_data["first_name"],
                    "last_name": user_data["last_name"],
                },
            )
            assert register_response.status_code == 201

            # Login to get token
            login_response = await client.post(
                "/api/auth/login",
                json={
                    "email": user_data["email"],
                    "password": "testpassword123",
                },
            )
            assert login_response.status_code == 200

            token = login_response.json()["access_token"]
            client.headers.update({"Authorization": f"Bearer {token}"})

            yield client

    @pytest.mark.asyncio
    async def test_complete_trip_creation_workflow(self, authenticated_client):
        """Test the complete workflow of creating a new trip."""
        # Step 1: Create a new trip
        trip_data = {
            "name": "Tokyo Adventure 2024",
            "description": "Exploring Japanese culture and cuisine",
            "destination": "Tokyo, Japan",
            "start_date": (date.today() + timedelta(days=60)).isoformat(),
            "end_date": (date.today() + timedelta(days=67)).isoformat(),
            "budget": 5000.00,
            "currency": "USD",
            "travelers_count": 2,
            "trip_type": "leisure",
        }

        response = await authenticated_client.post("/api/trips", json=trip_data)
        assert response.status_code == 201

        trip = response.json()
        assert trip["name"] == "Tokyo Adventure 2024"
        assert trip["destination"] == "Tokyo, Japan"
        assert trip["status"] == "planning"

        trip_id = trip["id"]

        # Step 2: Search for accommodations
        accommodation_search = {
            "destination": "Tokyo, Japan",
            "check_in": trip_data["start_date"],
            "check_out": trip_data["end_date"],
            "guests": 2,
            "filters": {
                "min_price": 100,
                "max_price": 400,
                "accommodation_type": "hotel",
            },
        }

        response = await authenticated_client.post(
            "/api/accommodations/search", json=accommodation_search
        )
        assert response.status_code == 200

        accommodations = response.json()
        assert "accommodations" in accommodations
        assert accommodations["total"] > 0

        # Step 3: Get details for first accommodation
        first_accommodation = accommodations["accommodations"][0]
        accommodation_id = first_accommodation["id"]

        response = await authenticated_client.get(
            f"/api/accommodations/{accommodation_id}"
        )
        assert response.status_code == 200

        details = response.json()
        assert details["id"] == accommodation_id
        assert "amenities" in details

        # Step 4: Check availability
        availability_params = {
            "check_in": trip_data["start_date"],
            "check_out": trip_data["end_date"],
            "guests": 2,
        }

        response = await authenticated_client.post(
            f"/api/accommodations/{accommodation_id}/availability",
            json=availability_params,
        )
        assert response.status_code == 200

        availability = response.json()
        assert availability["available"] is True
        assert "price_per_night" in availability

        # Step 5: Save accommodation to trip
        save_accommodation = {
            "trip_id": trip_id,
            "accommodation_id": accommodation_id,
            "check_in": trip_data["start_date"],
            "check_out": trip_data["end_date"],
            "price_per_night": availability["price_per_night"],
            "total_price": availability["total_price"],
        }

        response = await authenticated_client.post(
            "/api/trips/accommodations", json=save_accommodation
        )
        assert response.status_code == 201

        # Step 6: Search for flights
        flight_search = {
            "origin": "LAX",
            "destination": "NRT",
            "departure_date": trip_data["start_date"],
            "return_date": trip_data["end_date"],
            "passengers": 2,
            "cabin_class": "economy",
        }

        response = await authenticated_client.post(
            "/api/flights/search", json=flight_search
        )
        assert response.status_code == 200

        flights = response.json()
        assert "outbound" in flights
        assert "return" in flights
        assert len(flights["outbound"]) > 0

        # Step 7: Save flights to trip
        outbound_flight = flights["outbound"][0]
        return_flight = flights["return"][0]

        save_flights = {
            "trip_id": trip_id,
            "outbound_flight_id": outbound_flight["id"],
            "return_flight_id": return_flight["id"],
        }

        response = await authenticated_client.post(
            "/api/trips/flights", json=save_flights
        )
        assert response.status_code == 201

        # Step 8: Get complete trip details
        response = await authenticated_client.get(f"/api/trips/{trip_id}")
        assert response.status_code == 200

        complete_trip = response.json()
        assert complete_trip["id"] == trip_id
        assert len(complete_trip["accommodations"]) == 1
        assert len(complete_trip["flights"]) == 2  # Outbound + return

        # Step 9: Update trip status to booked
        response = await authenticated_client.patch(
            f"/api/trips/{trip_id}", json={"status": "booked"}
        )
        assert response.status_code == 200

        updated_trip = response.json()
        assert updated_trip["status"] == "booked"

    @pytest.mark.asyncio
    async def test_chat_based_trip_planning(self, authenticated_client):
        """Test trip planning through chat interface."""
        # Step 1: Start a chat session
        response = await authenticated_client.post("/api/chat/sessions")
        assert response.status_code == 201

        session = response.json()
        session_id = session["session_id"]

        # Step 2: Send initial trip planning message
        message_1 = {
            "message": "I want to plan a trip to Tokyo for 2 people in 2 months",
            "session_id": session_id,
        }

        response = await authenticated_client.post("/api/chat/message", json=message_1)
        assert response.status_code == 200

        chat_response = response.json()
        assert "message" in chat_response
        assert "tokyo" in chat_response["message"].lower()

        # Step 3: Provide more details
        message_2 = {
            "message": (
                "Budget is $5000, looking for 5-star hotels and business class flights"
            ),
            "session_id": session_id,
        }

        response = await authenticated_client.post("/api/chat/message", json=message_2)
        assert response.status_code == 200

        chat_response = response.json()
        assert "tool_calls" in chat_response
        # Should trigger accommodation/flight search tools

        # Step 4: Request specific dates
        message_3 = {
            "message": "Make it from March 15 to March 22, 2024",
            "session_id": session_id,
        }

        response = await authenticated_client.post("/api/chat/message", json=message_3)
        assert response.status_code == 200

        # Step 5: Get chat history
        response = await authenticated_client.get(
            f"/api/chat/sessions/{session_id}/history"
        )
        assert response.status_code == 200

        history = response.json()
        assert len(history["messages"]) >= 6  # 3 user + 3 assistant messages

        # Step 6: Check if trip was created through chat
        response = await authenticated_client.get("/api/trips")
        assert response.status_code == 200

        trips = response.json()
        # Chat should have created a trip
        assert len(trips["trips"]) > 0

    @pytest.mark.asyncio
    async def test_api_key_management_workflow(self, authenticated_client):
        """Test API key management for external services."""
        # Step 1: Get current API keys
        response = await authenticated_client.get("/api/keys")
        assert response.status_code == 200

        keys = response.json()
        assert "api_keys" in keys

        # Step 2: Add OpenAI API key
        add_key = {
            "service_name": "openai",
            "api_key": "sk-test-key-1234567890abcdef",
            "description": "OpenAI key for chat functionality",
        }

        response = await authenticated_client.post("/api/keys", json=add_key)
        assert response.status_code == 201

        created_key = response.json()
        assert created_key["service_name"] == "openai"
        assert created_key["is_active"] is True

        key_id = created_key["id"]

        # Step 3: Test API key validation
        response = await authenticated_client.post(f"/api/keys/{key_id}/validate")
        assert response.status_code == 200

        validation = response.json()
        assert "valid" in validation

        # Step 4: Update API key
        update_key = {
            "description": "Updated OpenAI key description",
            "is_active": True,
        }

        response = await authenticated_client.patch(
            f"/api/keys/{key_id}", json=update_key
        )
        assert response.status_code == 200

        # Step 5: Get usage statistics
        response = await authenticated_client.get(f"/api/keys/{key_id}/usage")
        assert response.status_code == 200

        usage = response.json()
        assert "usage_count" in usage
        assert "last_used" in usage

        # Step 6: Deactivate API key
        response = await authenticated_client.patch(
            f"/api/keys/{key_id}", json={"is_active": False}
        )
        assert response.status_code == 200

        # Step 7: Delete API key
        response = await authenticated_client.delete(f"/api/keys/{key_id}")
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_memory_and_personalization_workflow(self, authenticated_client):
        """Test memory system and personalization features."""
        # Step 1: Start chat session
        response = await authenticated_client.post("/api/chat/sessions")
        session = response.json()
        session_id = session["session_id"]

        # Step 2: Provide preferences through chat
        preferences_message = {
            "message": (
                "I prefer luxury hotels, business class flights, and I'm vegetarian"
            ),
            "session_id": session_id,
        }

        response = await authenticated_client.post(
            "/api/chat/message", json=preferences_message
        )
        assert response.status_code == 200

        # Step 3: Get memory/preferences
        response = await authenticated_client.get("/api/memory/preferences")
        assert response.status_code == 200

        preferences = response.json()
        assert "preferences" in preferences

        # Step 4: Plan another trip (should use memory)
        trip_message = {
            "message": "Plan another trip to Paris for next month",
            "session_id": session_id,
        }

        response = await authenticated_client.post(
            "/api/chat/message", json=trip_message
        )
        assert response.status_code == 200

        chat_response = response.json()
        # Should reference previous preferences
        assert (
            "luxury" in chat_response["message"].lower()
            or "business" in chat_response["message"].lower()
        )

        # Step 5: Get personalized recommendations
        response = await authenticated_client.get(
            "/api/recommendations/accommodations?destination=Paris"
        )
        assert response.status_code == 200

        recommendations = response.json()
        assert "recommendations" in recommendations
        # Should prioritize luxury hotels based on preferences

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, authenticated_client):
        """Test error handling and recovery in E2E workflows."""
        # Test 1: Invalid trip data
        invalid_trip = {
            "name": "",  # Invalid empty name
            "start_date": "2024-01-01",
            "end_date": "2023-12-31",  # End before start
            "budget": -1000,  # Negative budget
        }

        response = await authenticated_client.post("/api/trips", json=invalid_trip)
        assert response.status_code == 422

        error = response.json()
        assert "detail" in error

        # Test 2: Search with invalid parameters
        invalid_search = {
            "destination": "",
            "check_in": "invalid-date",
            "guests": 0,
        }

        response = await authenticated_client.post(
            "/api/accommodations/search", json=invalid_search
        )
        assert response.status_code == 422

        # Test 3: Access non-existent resources
        response = await authenticated_client.get("/api/trips/99999")
        assert response.status_code == 404

        # Test 4: Unauthorized access (remove auth header)
        original_headers = authenticated_client.headers.copy()
        del authenticated_client.headers["Authorization"]

        response = await authenticated_client.get("/api/trips")
        assert response.status_code == 401

        # Restore auth header
        authenticated_client.headers.update(original_headers)

    @pytest.mark.asyncio
    async def test_performance_with_large_data(self, authenticated_client):
        """Test system performance with larger datasets."""
        # Create multiple trips
        trips = []
        for i in range(10):
            trip_data = TripFactory.create(
                name=f"Trip {i}",
                destination=f"City {i}",
            )

            response = await authenticated_client.post("/api/trips", json=trip_data)
            assert response.status_code == 201
            trips.append(response.json())

        # Get all trips (should handle pagination)
        response = await authenticated_client.get("/api/trips?limit=5")
        assert response.status_code == 200

        trips_page = response.json()
        assert len(trips_page["trips"]) == 5
        assert trips_page["total"] == 10
        assert trips_page["has_more"] is True

        # Test search performance
        import time

        start_time = time.time()
        response = await authenticated_client.post(
            "/api/accommodations/search",
            json={
                "destination": "Tokyo, Japan",
                "check_in": (date.today() + timedelta(days=30)).isoformat(),
                "check_out": (date.today() + timedelta(days=37)).isoformat(),
                "guests": 2,
            },
        )
        end_time = time.time()

        assert response.status_code == 200
        # Should complete within reasonable time (adjust threshold as needed)
        assert (end_time - start_time) < 5.0  # 5 second timeout
