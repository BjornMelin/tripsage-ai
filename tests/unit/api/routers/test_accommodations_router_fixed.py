"""Comprehensive unit tests for accommodation router with proper validation testing."""

from unittest.mock import AsyncMock

import pytest
from fastapi import status

from tests.factories import AccommodationFactory


class TestAccommodationRouter:
    """Test suite for accommodation router endpoints."""

    def setup_method(self):
        """Set up test data."""
        self.sample_accommodation = AccommodationFactory.create()

    # === SUCCESS TESTS ===

    def test_search_accommodations_success(
        self, api_test_client, authenticated_headers, valid_accommodation_search
    ):
        """Test successful accommodation search."""
        # Configure the mock that's already set up in conftest
        api_test_client.mock_accommodation_service.search_accommodations = AsyncMock(
            return_value={
                "listings": [self.sample_accommodation],
                "count": 1,
                "currency": "USD",
                "search_id": "test-search-id",
                "search_request": valid_accommodation_search,
            }
        )

        # Act
        response = api_test_client.post(
            "/api/accommodations/search",
            json=valid_accommodation_search,
            headers=authenticated_headers,
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "listings" in data
        assert data["count"] == 1

    def test_get_accommodation_details_success(
        self, api_test_client, authenticated_headers, valid_accommodation_details
    ):
        """Test successful accommodation details retrieval."""
        # Configure the mock that's already set up in conftest
        api_test_client.mock_accommodation_service.get_accommodation_details = AsyncMock(
            return_value={
                "listing": self.sample_accommodation,
                "availability": True,
                "total_price": 100.0,
            }
        )

        # Act
        response = api_test_client.post(
            "/api/accommodations/details",
            json=valid_accommodation_details,
            headers=authenticated_headers,
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

    def test_save_accommodation_success(
        self, api_test_client, authenticated_headers, valid_save_accommodation
    ):
        """Test successful accommodation saving."""
        # Configure the mock that's already set up in conftest
        saved_accommodation = {
            "id": "saved-123",
            "user_id": "test-user-id",
            "trip_id": valid_save_accommodation["trip_id"],
            "listing": self.sample_accommodation,
            "check_in": valid_save_accommodation["check_in"],
            "check_out": valid_save_accommodation["check_out"],
            "saved_at": "2024-01-01",
            "notes": valid_save_accommodation.get("notes"),
            "status": "SAVED",
        }
        api_test_client.mock_accommodation_service.save_accommodation = AsyncMock(
            return_value=saved_accommodation
        )

        # Act
        response = api_test_client.post(
            "/api/accommodations/saved",
            json=valid_save_accommodation,
            headers=authenticated_headers,
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED

    # === VALIDATION TESTS ===

    @pytest.mark.parametrize("adults", [0, -1, 17])  # Schema allows 1-16
    def test_search_accommodations_invalid_adults(
        self, api_test_client, authenticated_headers, adults
    ):
        """Test accommodation search with invalid adults count."""
        search_request = {
            "location": "Tokyo",
            "check_in": "2024-03-15",
            "check_out": "2024-03-18",
            "adults": adults,
        }

        # Act
        response = api_test_client.post(
            "/api/accommodations/search",
            json=search_request,
            headers=authenticated_headers,
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("location", ["", " "])  # Schema requires min_length=1
    def test_search_accommodations_invalid_location(
        self, api_test_client, authenticated_headers, location
    ):
        """Test accommodation search with invalid location."""
        
        search_request = {
            "location": location,
            "check_in": "2024-03-15",
            "check_out": "2024-03-18",
            "adults": 2,
        }

        # Act
        response = api_test_client.post(
            "/api/accommodations/search",
            json=search_request,
            headers=authenticated_headers,
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_search_accommodations_invalid_dates(
        self, api_test_client, authenticated_headers
    ):
        """Test accommodation search with invalid date range."""
        
        search_request = {
            "location": "Tokyo",
            "check_in": "2024-03-18",  # After check_out
            "check_out": "2024-03-15",
            "adults": 2,
        }

        # Act
        response = api_test_client.post(
            "/api/accommodations/search",
            json=search_request,
            headers=authenticated_headers,
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("children", [-1, 11])  # Schema allows 0-10
    def test_search_accommodations_invalid_children(
        self, api_test_client, authenticated_headers, children
    ):
        """Test accommodation search with invalid children count."""
        
        search_request = {
            "location": "Tokyo",
            "check_in": "2024-03-15",
            "check_out": "2024-03-18",
            "adults": 2,
            "children": children,
        }

        # Act
        response = api_test_client.post(
            "/api/accommodations/search",
            json=search_request,
            headers=authenticated_headers,
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("rooms", [0, 9])  # Schema allows 1-8
    def test_search_accommodations_invalid_rooms(
        self, api_test_client, authenticated_headers, rooms
    ):
        """Test accommodation search with invalid rooms count."""
        
        search_request = {
            "location": "Tokyo",
            "check_in": "2024-03-15",
            "check_out": "2024-03-18",
            "adults": 2,
            "rooms": rooms,
        }

        # Act
        response = api_test_client.post(
            "/api/accommodations/search",
            json=search_request,
            headers=authenticated_headers,
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # === ERROR HANDLING TESTS ===

    def test_get_accommodation_details_not_found(
        self, api_test_client, authenticated_headers
    ):
        """Test accommodation details retrieval for non-existent accommodation."""
        # Configure the mock to return None
        api_test_client.mock_accommodation_service.get_accommodation_details = AsyncMock(
            return_value=None
        )

        details_request = {"listing_id": "non-existent-id"}

        # Act
        response = api_test_client.post(
            "/api/accommodations/details",
            json=details_request,
            headers=authenticated_headers,
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_search_accommodations_service_error(
        self, api_test_client, authenticated_headers, valid_accommodation_search
    ):
        """Test accommodation search with service error."""
        # Configure the mock to raise an exception
        api_test_client.mock_accommodation_service.search_accommodations = AsyncMock(
            side_effect=Exception("Service unavailable")
        )

        # Act
        response = api_test_client.post(
            "/api/accommodations/search",
            json=valid_accommodation_search,
            headers=authenticated_headers,
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # === AUTHENTICATION TESTS ===

    def test_search_accommodations_unauthorized(self, unauthenticated_test_client, valid_accommodation_search):
        """Test accommodation search without authentication."""
        # Act
        response = unauthenticated_test_client.post(
            "/api/accommodations/search", 
            json=valid_accommodation_search
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_accommodation_details_unauthorized(self, unauthenticated_test_client, valid_accommodation_details):
        """Test accommodation details without authentication."""
        # Act
        response = unauthenticated_test_client.post(
            "/api/accommodations/details", 
            json=valid_accommodation_details
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_save_accommodation_unauthorized(self, unauthenticated_test_client, valid_save_accommodation):
        """Test save accommodation without authentication."""
        # Act
        response = unauthenticated_test_client.post(
            "/api/accommodations/saved", 
            json=valid_save_accommodation
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED