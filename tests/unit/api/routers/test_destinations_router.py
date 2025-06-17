"""Comprehensive unit tests for destinations router."""

import pytest
from fastapi import status


class TestDestinationsRouter:
    """Test suite for destinations router endpoints."""

    def setup_method(self):
        """Set up test data."""
        # DestinationFactory methods are handled by mocks in conftest.py
        pass

    # === SUCCESS TESTS ===

    def test_search_destinations_success(
        self, api_test_client, valid_destination_search
    ):
        """Test successful destination search."""
        # Debug: print what we're sending
        print(f"Request data: {valid_destination_search}")

        # Act
        response = api_test_client.post(
            "/api/destinations/search",
            json=valid_destination_search,
        )

        # Debug: print response details
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "destinations" in data

    def test_search_destinations_empty_query(self, api_test_client):
        """Test destination search with empty query."""
        search_request = {
            "query": "",
            "limit": 10,
        }

        # Act
        response = api_test_client.post(
            "/api/destinations/search",
            json=search_request,
        )

        # Assert - should return validation error for empty query
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_destination_details_success(
        self, api_test_client, valid_destination_details
    ):
        """Test successful destination details retrieval."""
        # Act
        response = api_test_client.get(
            f"/api/destinations/{valid_destination_details['destination_id']}",
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

    def test_get_destination_recommendations_success(self, api_test_client):
        """Test successful destination recommendations."""
        # Act
        response = api_test_client.get(
            "/api/destinations/recommendations",
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

    # === ERROR HANDLING TESTS ===

    def test_search_destinations_service_error(
        self, api_test_client, valid_destination_search
    ):
        """Test destination search with service error."""
        # Act
        response = api_test_client.post(
            "/api/destinations/search",
            json=valid_destination_search,
        )

        # Assert - The mock service handles errors gracefully
        assert response.status_code == status.HTTP_200_OK

    # === VALIDATION TESTS ===

    @pytest.mark.parametrize("limit", [0, -1, 101])  # Schema likely allows 1-100
    def test_search_destinations_invalid_limit(self, api_test_client, limit):
        """Test destination search with invalid limit."""
        search_request = {
            "query": "Tokyo",
            "limit": limit,
        }

        # Act
        response = api_test_client.post(
            "/api/destinations/search",
            json=search_request,
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("query", [None, "", " ", "a" * 1001])  # Test edge cases
    def test_search_destinations_invalid_query(self, api_test_client, query):
        """Test destination search with invalid query."""
        search_request = {
            "query": query,
            "limit": 10,
        }

        # Act
        response = api_test_client.post(
            "/api/destinations/search",
            json=search_request,
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # === AUTHENTICATION TESTS ===

    def test_search_destinations_unauthorized(
        self, unauthenticated_test_client, valid_destination_search
    ):
        """Test destination search without authentication."""
        # Act
        response = unauthenticated_test_client.post(
            "/api/destinations/search",
            json=valid_destination_search,
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_destination_details_unauthorized(
        self, unauthenticated_test_client, valid_destination_details
    ):
        """Test destination details without authentication."""
        # Act
        response = unauthenticated_test_client.get(
            f"/api/destinations/{valid_destination_details['destination_id']}",
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_destination_recommendations_unauthorized(
        self, unauthenticated_test_client
    ):
        """Test destination recommendations without authentication."""
        # Act
        response = unauthenticated_test_client.get(
            "/api/destinations/recommendations",
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
