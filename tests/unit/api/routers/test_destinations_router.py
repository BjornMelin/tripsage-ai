"""Comprehensive unit tests for destinations router."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests.factories import DestinationFactory
from tripsage.api.main import app


class TestDestinationsRouter:
    """Test suite for destinations router endpoints."""

    def setup_method(self):
        """Set up test client and mocks."""
        self.client = TestClient(app)
        self.mock_service = Mock()
        self.sample_destination = DestinationFactory.create()
        self.sample_search_response = DestinationFactory.create_search_response()
        self.sample_details_response = DestinationFactory.create_details_response()
        self.sample_saved_destination = DestinationFactory.create_saved_destination()

    @patch("tripsage.api.routers.destinations.get_destination_service")
    @patch("tripsage.api.routers.destinations.require_principal_dep")
    def test_search_destinations_success(self, mock_auth, mock_service_dep):
        """Test successful destination search."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.search_destinations = AsyncMock(
            return_value=self.sample_search_response
        )

        search_request = {
            "query": "Tokyo",
            "country": "Japan",
            "location_type": "city",
            "limit": 10,
        }

        # Act
        response = self.client.post(
            "/api/destinations/search",
            json=search_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "destinations" in data
        assert "total_count" in data
        self.mock_service.search_destinations.assert_called_once()

    @patch("tripsage.api.routers.destinations.get_destination_service")
    @patch("tripsage.api.routers.destinations.require_principal_dep")
    def test_search_destinations_empty_query(self, mock_auth, mock_service_dep):
        """Test destination search with empty query."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service

        search_request = {"query": "", "limit": 10}

        # Act
        response = self.client.post(
            "/api/destinations/search",
            json=search_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("tripsage.api.routers.destinations.get_destination_service")
    @patch("tripsage.api.routers.destinations.require_principal_dep")
    def test_get_destination_details_success(self, mock_auth, mock_service_dep):
        """Test successful destination details retrieval."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        destination_id = "test-destination-id"
        self.mock_service.get_destination_details = AsyncMock(
            return_value=self.sample_details_response
        )

        # Act
        response = self.client.get(
            f"/api/destinations/{destination_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "name" in data
        assert "location" in data
        self.mock_service.get_destination_details.assert_called_once_with(
            destination_id
        )

    @patch("tripsage.api.routers.destinations.get_destination_service")
    @patch("tripsage.api.routers.destinations.require_principal_dep")
    def test_get_destination_details_not_found(self, mock_auth, mock_service_dep):
        """Test destination details retrieval for non-existent destination."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        destination_id = "non-existent-id"

        from tripsage_core.exceptions.exceptions import CoreResourceNotFoundError

        self.mock_service.get_destination_details = AsyncMock(
            side_effect=CoreResourceNotFoundError("Destination not found")
        )

        # Act
        response = self.client.get(
            f"/api/destinations/{destination_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("tripsage.api.routers.destinations.get_destination_service")
    @patch("tripsage.api.routers.destinations.require_principal_dep")
    def test_save_destination_success(self, mock_auth, mock_service_dep):
        """Test successful destination saving."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        destination_id = "test-destination-id"
        notes = "Beautiful city to visit"

        self.mock_service.save_destination = AsyncMock(
            return_value=self.sample_saved_destination
        )

        # Act
        response = self.client.post(
            f"/api/destinations/save/{destination_id}?notes={notes}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "destination_id" in data
        assert "user_id" in data
        self.mock_service.save_destination.assert_called_once_with(
            "test-user-id", destination_id, notes
        )

    @patch("tripsage.api.routers.destinations.get_destination_service")
    @patch("tripsage.api.routers.destinations.require_principal_dep")
    def test_save_destination_not_found(self, mock_auth, mock_service_dep):
        """Test saving non-existent destination."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        destination_id = "non-existent-id"

        from tripsage_core.exceptions.exceptions import CoreResourceNotFoundError

        self.mock_service.save_destination = AsyncMock(
            side_effect=CoreResourceNotFoundError("Destination not found")
        )

        # Act
        response = self.client.post(
            f"/api/destinations/save/{destination_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("tripsage.api.routers.destinations.get_destination_service")
    @patch("tripsage.api.routers.destinations.require_principal_dep")
    def test_get_saved_destinations_success(self, mock_auth, mock_service_dep):
        """Test successful retrieval of saved destinations."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        saved_destinations = [self.sample_saved_destination]

        self.mock_service.get_saved_destinations = AsyncMock(
            return_value=saved_destinations
        )

        # Act
        response = self.client.get(
            "/api/destinations/saved", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        self.mock_service.get_saved_destinations.assert_called_once_with("test-user-id")

    @patch("tripsage.api.routers.destinations.get_destination_service")
    @patch("tripsage.api.routers.destinations.require_principal_dep")
    def test_get_saved_destinations_empty(self, mock_auth, mock_service_dep):
        """Test retrieval of saved destinations when none exist."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service

        self.mock_service.get_saved_destinations = AsyncMock(return_value=[])

        # Act
        response = self.client.get(
            "/api/destinations/saved", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @patch("tripsage.api.routers.destinations.get_destination_service")
    @patch("tripsage.api.routers.destinations.require_principal_dep")
    def test_delete_saved_destination_success(self, mock_auth, mock_service_dep):
        """Test successful deletion of saved destination."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        destination_id = "test-destination-id"

        self.mock_service.delete_saved_destination = AsyncMock(return_value=True)

        # Act
        response = self.client.delete(
            f"/api/destinations/saved/{destination_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        self.mock_service.delete_saved_destination.assert_called_once_with(
            "test-user-id", destination_id
        )

    @patch("tripsage.api.routers.destinations.get_destination_service")
    @patch("tripsage.api.routers.destinations.require_principal_dep")
    def test_delete_saved_destination_not_found(self, mock_auth, mock_service_dep):
        """Test deletion of non-existent saved destination."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        destination_id = "non-existent-id"

        from tripsage_core.exceptions.exceptions import CoreResourceNotFoundError

        self.mock_service.delete_saved_destination = AsyncMock(
            side_effect=CoreResourceNotFoundError("Saved destination not found")
        )

        # Act
        response = self.client.delete(
            f"/api/destinations/saved/{destination_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("tripsage.api.routers.destinations.get_destination_service")
    @patch("tripsage.api.routers.destinations.require_principal_dep")
    def test_search_points_of_interest_success(self, mock_auth, mock_service_dep):
        """Test successful points of interest search."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        points_of_interest = [
            {
                "id": "poi1",
                "name": "Tokyo Tower",
                "type": "landmark",
                "location": {"latitude": 35.6586, "longitude": 139.7454},
            }
        ]

        self.mock_service.search_points_of_interest = AsyncMock(
            return_value=points_of_interest
        )

        search_request = {
            "query": "landmarks in Tokyo",
            "location_type": "point_of_interest",
        }

        # Act
        response = self.client.post(
            "/api/destinations/points-of-interest",
            json=search_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "Tokyo Tower"

    @patch("tripsage.api.routers.destinations.get_destination_service")
    @patch("tripsage.api.routers.destinations.require_principal_dep")
    def test_get_destination_recommendations_success(self, mock_auth, mock_service_dep):
        """Test successful destination recommendations retrieval."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        recommendations = [self.sample_destination]

        self.mock_service.get_destination_recommendations = AsyncMock(
            return_value=recommendations
        )

        # Act
        response = self.client.get(
            "/api/destinations/recommendations",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        self.mock_service.get_destination_recommendations.assert_called_once_with(
            "test-user-id"
        )

    def test_search_destinations_unauthorized(self):
        """Test destination search without authentication."""
        search_request = {"query": "Tokyo", "limit": 10}

        response = self.client.post("/api/destinations/search", json=search_request)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_destination_details_unauthorized(self):
        """Test destination details without authentication."""
        response = self.client.get("/api/destinations/test-id")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_save_destination_unauthorized(self):
        """Test save destination without authentication."""
        response = self.client.post("/api/destinations/save/test-id")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_saved_destinations_unauthorized(self):
        """Test get saved destinations without authentication."""
        response = self.client.get("/api/destinations/saved")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_saved_destination_unauthorized(self):
        """Test delete saved destination without authentication."""
        response = self.client.delete("/api/destinations/saved/test-id")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("tripsage.api.routers.destinations.get_destination_service")
    @patch("tripsage.api.routers.destinations.require_principal_dep")
    def test_search_destinations_service_error(self, mock_auth, mock_service_dep):
        """Test destination search with service error."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.search_destinations = AsyncMock(
            side_effect=Exception("Service unavailable")
        )

        search_request = {"query": "Tokyo", "limit": 10}

        # Act
        response = self.client.post(
            "/api/destinations/search",
            json=search_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.parametrize("limit", [0, -1, 101])
    def test_search_destinations_invalid_limit(self, limit):
        """Test destination search with invalid limit values."""
        search_request = {"query": "Tokyo", "limit": limit}

        response = self.client.post(
            "/api/destinations/search",
            json=search_request,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("query", [None, "", " ", "a" * 1001])
    def test_search_destinations_invalid_query(self, query):
        """Test destination search with invalid query values."""
        search_request = {"query": query, "limit": 10}

        response = self.client.post(
            "/api/destinations/search",
            json=search_request,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
