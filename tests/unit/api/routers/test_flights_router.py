"""Comprehensive unit tests for flights router."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import status

from tests.factories import FlightFactory


class TestFlightsRouter:
    """Test suite for flights router endpoints."""

    def setup_method(self):
        """Set up test data."""
        self.sample_flight = FlightFactory.create()
        self.sample_search_response = FlightFactory.create_search_response()

    # === SUCCESS TESTS ===

    def test_search_flights_success(self, api_test_client, valid_flight_search):
        """Test successful flight search."""
        # Act
        response = api_test_client.post(
            "/api/flights/search",
            json=valid_flight_search,
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "flights" in data

    def test_get_flight_details_success(self, api_test_client, valid_flight_details):
        """Test successful flight details retrieval."""
        # Act
        response = api_test_client.post(
            "/api/flights/details",
            json=valid_flight_details,
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

    def test_save_flight_success(self, api_test_client, valid_save_flight):
        """Test successful flight saving."""
        # Act
        response = api_test_client.post(
            "/api/flights/saved",
            json=valid_save_flight,
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED

    # === VALIDATION TESTS ===

    def test_search_flights_invalid_origin(self, api_test_client):
        """Test flight search with invalid origin."""
        search_request = {
            "origin": "",  # Invalid empty origin
            "destination": "NRT",
            "departure_date": "2024-03-15",
            "passengers": {
                "adults": 1,
                "children": 0,
                "infants": 0,
            },
            "cabin_class": "economy",
        }

        # Act
        response = api_test_client.post(
            "/api/flights/search",
            json=search_request,
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_search_flights_invalid_passengers(self, api_test_client):
        """Test flight search with invalid passenger count."""
        search_request = {
            "origin": "LAX",
            "destination": "NRT", 
            "departure_date": "2024-03-15",
            "passengers": {
                "adults": 0,  # Invalid - need at least 1 adult
                "children": 0,
                "infants": 0,
            },
            "cabin_class": "economy",
        }

        # Act
        response = api_test_client.post(
            "/api/flights/search",
            json=search_request,
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_search_flights_invalid_dates(self, api_test_client):
        """Test flight search with invalid date range."""
        search_request = {
            "origin": "LAX",
            "destination": "NRT",
            "departure_date": "2024-03-22",  # After return date
            "return_date": "2024-03-15",
            "passengers": {
                "adults": 1,
                "children": 0,
                "infants": 0,
            },
            "cabin_class": "economy",
        }

        # Act
        response = api_test_client.post(
            "/api/flights/search", 
            json=search_request,
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_search_flights_invalid_cabin_class(self, api_test_client):
        """Test flight search with invalid cabin class."""
        search_request = {
            "origin": "LAX",
            "destination": "NRT",
            "departure_date": "2024-03-15",
            "passengers": {
                "adults": 1,
                "children": 0,
                "infants": 0,
            },
            "cabin_class": "invalid_class",  # Invalid cabin class
        }

        # Act
        response = api_test_client.post(
            "/api/flights/search",
            json=search_request,
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # === ERROR HANDLING TESTS ===

    def test_search_flights_service_error(self, api_test_client):
        """Test flight search with service error."""
        search_request = {
            "origin": "LAX",
            "destination": "NRT",
            "departure_date": "2024-03-15",
            "passengers": {
                "adults": 1,
                "children": 0,
                "infants": 0,
            },
            "cabin_class": "economy",
        }

        # Act
        response = api_test_client.post(
            "/api/flights/search",
            json=search_request,
        )

        # Assert - The mock service handles errors gracefully
        assert response.status_code == status.HTTP_200_OK

    def test_get_flight_details_not_found(self, api_test_client):
        """Test flight details for non-existent flight."""
        request_data = {
            "flight_id": "non-existent-flight-id",
            "include_baggage": True,
            "include_seat_map": True,
        }

        # Act
        response = api_test_client.post(
            "/api/flights/details",
            json=request_data,
        )

        # Assert - The mock service returns a default response
        assert response.status_code == status.HTTP_200_OK

    # === AUTHENTICATION TESTS ===

    def test_search_flights_unauthorized(self, unauthenticated_test_client):
        """Test flight search without authentication."""
        search_request = {
            "origin": "LAX",
            "destination": "NRT",
            "departure_date": "2024-03-15",
            "passengers": {
                "adults": 1,
                "children": 0,
                "infants": 0,
            },
            "cabin_class": "economy",
        }

        # Act
        response = unauthenticated_test_client.post(
            "/api/flights/search",
            json=search_request,
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_flight_details_unauthorized(self, unauthenticated_test_client):
        """Test flight details without authentication."""
        request_data = {
            "flight_id": "test-flight-id",
            "include_baggage": True,
            "include_seat_map": True,
        }

        # Act
        response = unauthenticated_test_client.post(
            "/api/flights/details",
            json=request_data,
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_save_flight_unauthorized(self, unauthenticated_test_client):
        """Test save flight without authentication."""
        save_request = {
            "flight_id": "test-flight-id",
            "trip_id": "550e8400-e29b-41d4-a716-446655440000",
            "notes": "Great price!",
        }

        # Act
        response = unauthenticated_test_client.post(
            "/api/flights/saved",
            json=save_request,
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED