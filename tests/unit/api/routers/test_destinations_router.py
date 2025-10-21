"""Finalized unit tests for the destinations router."""

from __future__ import annotations

import pytest
from fastapi import status


class TestDestinationsRouter:
    """Test suite covering the finalized destination endpoints."""

    # === SUCCESS PATHS ===

    def test_search_destinations_success(
        self, api_test_client, valid_destination_search
    ):
        """Search returns 200 with destinations list."""
        response = api_test_client.post(
            "/api/destinations/search",
            json=valid_destination_search,
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert "destinations" in payload
        assert payload["count"] == len(payload["destinations"])

    def test_get_destination_details_success(
        self, api_test_client, valid_destination_details
    ):
        """Details endpoint returns 200 when destination exists."""
        response = api_test_client.get(
            f"/api/destinations/{valid_destination_details['destination_id']}"
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert "destination" in payload

    def test_save_destination_success(
        self, api_test_client, valid_saved_destination_request
    ):
        """Save endpoint returns 201 and saved payload."""
        response = api_test_client.post(
            "/api/destinations/saved",
            json=valid_saved_destination_request,
        )

        assert response.status_code == status.HTTP_201_CREATED
        payload = response.json()
        assert payload["destination"]["name"]
        assert payload["trip_id"] == valid_saved_destination_request["trip_id"]

    def test_list_saved_destinations_success(self, api_test_client):
        """Saved destinations endpoint returns list."""
        response = api_test_client.get("/api/destinations/saved")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert isinstance(payload, list)

    def test_recommendations_success(
        self, api_test_client, valid_destination_recommendations
    ):
        """Recommendations endpoint returns 200 and list of items."""
        response = api_test_client.post(
            "/api/destinations/recommendations",
            json=valid_destination_recommendations,
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert isinstance(payload, list)

    # === VALIDATION ===

    @pytest.mark.parametrize("limit", [0, -1, 101])
    def test_search_destinations_invalid_limit(self, api_test_client, limit):
        """Invalid limits result in 422."""
        payload = {"query": "Tokyo", "limit": limit}

        response = api_test_client.post("/api/destinations/search", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("query", ["", " ", None])
    def test_search_destinations_invalid_query(self, api_test_client, query):
        """Blank or missing query fails validation."""
        payload = {"query": query, "limit": 5}

        response = api_test_client.post("/api/destinations/search", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_save_destination_missing_trip(self, api_test_client):
        """Trip ID must be provided when saving."""
        payload = {
            "destination_id": "dest-1",
            "notes": "test",
            "priority": 2,
        }

        response = api_test_client.post("/api/destinations/saved", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # === AUTHENTICATION ===

    def test_search_destinations_unauthorized(
        self, unauthenticated_test_client, valid_destination_search
    ):
        """Unauthenticated search requests are rejected."""
        response = unauthenticated_test_client.post(
            "/api/destinations/search",
            json=valid_destination_search,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_destination_details_unauthorized(
        self, unauthenticated_test_client, valid_destination_details
    ):
        """Details endpoint requires authentication."""
        response = unauthenticated_test_client.get(
            f"/api/destinations/{valid_destination_details['destination_id']}"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_save_destination_unauthorized(
        self, unauthenticated_test_client, valid_saved_destination_request
    ):
        """Saving destinations requires authentication."""
        response = unauthenticated_test_client.post(
            "/api/destinations/saved",
            json=valid_saved_destination_request,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_saved_destinations_unauthorized(
        self, unauthenticated_test_client,
    ):
        """Listing saved destinations requires authentication."""
        response = unauthenticated_test_client.get("/api/destinations/saved")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_recommendations_unauthorized(
        self, unauthenticated_test_client, valid_destination_recommendations
    ):
        """Recommendations endpoint requires authentication."""
        response = unauthenticated_test_client.post(
            "/api/destinations/recommendations",
            json=valid_destination_recommendations,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
