"""Finalized unit tests for the flights router."""

from __future__ import annotations

from uuid import uuid4

from fastapi import status


class TestFlightsRouter:
    """Test suite covering the finalized flights API surface."""

    # === SUCCESS PATHS ===

    def test_search_flights_success(self, api_test_client, valid_flight_search):
        """Flight search returns 200 with structured response."""
        response = api_test_client.post("/api/flights/search", json=valid_flight_search)

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["search_id"]
        assert payload["offers"] == []
        assert payload["total_results"] == 0

    def test_get_flight_offer_success(self, api_test_client):
        """Flight offer lookup returns 200 when offer is known."""
        offer_id = "offer-123"
        response = api_test_client.get(f"/api/flights/offers/{offer_id}")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["id"] == offer_id
        assert payload["bookable"] is True

    def test_book_flight_success(self, api_test_client, valid_flight_booking_request):
        """Booking endpoint returns 201 with booking payload."""
        response = api_test_client.post(
            "/api/flights/bookings",
            json=valid_flight_booking_request,
        )

        assert response.status_code == status.HTTP_201_CREATED
        payload = response.json()
        assert payload["offer_id"] == valid_flight_booking_request["offer_id"]
        assert payload["status"].lower() == "booked"
        assert payload["cancellable"] is True

    def test_list_bookings_success(self, api_test_client):
        """Booking list returns 200 and a list response."""
        response = api_test_client.get("/api/flights/bookings")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert isinstance(payload, list)
        assert payload
        assert payload[0]["id"] == "booking-123"

    def test_cancel_booking_success(self, api_test_client):
        """Cancelling an existing booking yields 204."""
        booking_id = "booking-123"
        response = api_test_client.delete(f"/api/flights/bookings/{booking_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    # === VALIDATION ===

    def test_search_flights_invalid_origin(self, api_test_client):
        """Validation error returned when origin is blank."""
        request = {
            "origin": "",
            "destination": "NRT",
            "departure_date": "2024-03-15",
            "adults": 1,
        }

        response = api_test_client.post("/api/flights/search", json=request)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_search_flights_invalid_return_date(self, api_test_client):
        """Return date prior to departure fails validation."""
        request = {
            "origin": "LAX",
            "destination": "NRT",
            "departure_date": "2024-03-22",
            "return_date": "2024-03-15",
            "adults": 1,
        }

        response = api_test_client.post("/api/flights/search", json=request)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_book_flight_missing_passenger(self, api_test_client):
        """Booking without passengers fails schema validation."""
        request = {
            "offer_id": "offer-123",
            "passengers": [],
            "trip_id": str(uuid4()),
        }

        response = api_test_client.post("/api/flights/bookings", json=request)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # === AUTHENTICATION ===

    def test_search_flights_unauthorized(
        self, unauthenticated_test_client, valid_flight_search
    ):
        """Unauthenticated requests are rejected."""
        response = unauthenticated_test_client.post(
            "/api/flights/search",
            json=valid_flight_search,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_offer_unauthorized(self, unauthenticated_test_client):
        """Flight offer lookups require authentication."""
        response = unauthenticated_test_client.get("/api/flights/offers/offer-1")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_book_flight_unauthorized(
        self, unauthenticated_test_client, valid_flight_booking_request
    ):
        """Booking requires authentication."""
        response = unauthenticated_test_client.post(
            "/api/flights/bookings",
            json=valid_flight_booking_request,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_bookings_unauthorized(self, unauthenticated_test_client):
        """Booking list requires authentication."""
        response = unauthenticated_test_client.get("/api/flights/bookings")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cancel_booking_unauthorized(self, unauthenticated_test_client):
        """Booking cancellation requires authentication."""
        response = unauthenticated_test_client.delete(
            "/api/flights/bookings/booking-123"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
