"""
End-to-end tests for complete trip planning user journeys.

Tests full user workflows from trip creation to booking completion,
involving multiple services and real API interactions.
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.factories import TripFactory, UserFactory
from tripsage.api.main import app


class TestTripPlanningJourney:
    """E2E tests for complete trip planning workflows."""

    @pytest.fixture
    def authenticated_client(self):
        """Create an authenticated HTTP client for testing."""
        client = TestClient(app)
        
        # Create test user and get auth token
        user_data = UserFactory.create()

        # Register user
        register_response = client.post(
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
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": user_data["email"],
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        return client

    def test_complete_trip_creation_workflow(self, authenticated_client):
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

        response = authenticated_client.post("/api/trips", json=trip_data)
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

        response = authenticated_client.post(
            "/api/accommodations/search", json=accommodation_search
        )
        assert response.status_code == 200

        accommodations = response.json()
        assert "accommodations" in accommodations
        assert accommodations["total"] > 0

        # Step 3: Get details for first accommodation
        first_accommodation = accommodations["accommodations"][0]
        accommodation_id = first_accommodation["id"]

        response = authenticated_client.get(f"/api/accommodations/{accommodation_id}")
        assert response.status_code == 200

        accommodation_details = response.json()
        assert accommodation_details["id"] == accommodation_id

        # Step 4: Add accommodation to trip
        add_accommodation_data = {
            "accommodation_id": accommodation_id,
            "check_in": trip_data["start_date"],
            "check_out": trip_data["end_date"],
            "guests": 2,
        }

        response = authenticated_client.post(
            f"/api/trips/{trip_id}/accommodations", json=add_accommodation_data
        )
        assert response.status_code == 201

        # Step 5: Search for flights
        flight_search = {
            "origin": "LAX",
            "destination": "NRT",
            "departure_date": trip_data["start_date"],
            "return_date": trip_data["end_date"],
            "passengers": 2,
            "cabin_class": "economy",
        }

        response = authenticated_client.post("/api/flights/search", json=flight_search)
        assert response.status_code == 200

        flights = response.json()
        assert "flights" in flights

        # Step 6: Get updated trip details
        response = authenticated_client.get(f"/api/trips/{trip_id}")
        assert response.status_code == 200

        updated_trip = response.json()
        assert updated_trip["id"] == trip_id
        assert len(updated_trip["accommodations"]) == 1

    def test_simplified_trip_workflow(self, authenticated_client):
        """Test a simplified trip creation and update workflow."""
        # Create basic trip
        trip_data = {
            "name": "Weekend Getaway",
            "destination": "San Francisco, CA",
            "start_date": (date.today() + timedelta(days=30)).isoformat(),
            "end_date": (date.today() + timedelta(days=32)).isoformat(),
            "budget": 1500.00,
            "currency": "USD",
            "travelers_count": 1,
            "trip_type": "business",
        }

        response = authenticated_client.post("/api/trips", json=trip_data)
        assert response.status_code == 201

        trip = response.json()
        trip_id = trip["id"]

        # Update trip
        update_data = {
            "budget": 2000.00,
            "description": "Updated business trip with extended stay",
        }

        response = authenticated_client.patch(f"/api/trips/{trip_id}", json=update_data)
        assert response.status_code == 200

        updated_trip = response.json()
        assert updated_trip["budget"] == 2000.00
        assert "extended stay" in updated_trip["description"]

        # List all trips
        response = authenticated_client.get("/api/trips")
        assert response.status_code == 200

        trips = response.json()
        assert len(trips) >= 1
        assert any(t["id"] == trip_id for t in trips)