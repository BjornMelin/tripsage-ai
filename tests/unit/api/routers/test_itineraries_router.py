"""Comprehensive unit tests for itineraries router."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests.factories import ItineraryFactory
from tripsage.api.main import app


class TestItinerariesRouter:
    """Test suite for itineraries router endpoints."""

    def setup_method(self):
        """Set up test client and mocks."""
        self.client = TestClient(app)
        self.mock_service = Mock()
        self.sample_itinerary = ItineraryFactory.create()
        self.sample_itinerary_item = ItineraryFactory.create_item()
        self.sample_search_response = ItineraryFactory.create_search_response()
        self.sample_conflict_response = ItineraryFactory.create_conflict_response()
        self.sample_optimize_response = ItineraryFactory.create_optimize_response()

    @patch("tripsage.api.routers.itineraries.get_itinerary_service")
    @patch("tripsage.api.routers.itineraries.require_principal_dep")
    def test_create_itinerary_success(self, mock_auth, mock_service_dep):
        """Test successful itinerary creation."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.create_itinerary = AsyncMock(
            return_value=self.sample_itinerary
        )

        create_request = {
            "name": "Tokyo Adventure",
            "description": "5-day trip to Tokyo",
            "start_date": "2024-05-01",
            "end_date": "2024-05-05",
            "destination": "Tokyo, Japan",
        }

        # Act
        response = self.client.post(
            "/api/itineraries",
            json=create_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["name"] == "Tokyo Adventure"
        self.mock_service.create_itinerary.assert_called_once()

    @patch("tripsage.api.routers.itineraries.get_itinerary_service")
    @patch("tripsage.api.routers.itineraries.require_principal_dep")
    def test_create_itinerary_invalid_data(self, mock_auth, mock_service_dep):
        """Test itinerary creation with invalid data."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.create_itinerary = AsyncMock(
            side_effect=ValueError("Invalid date range")
        )

        create_request = {
            "name": "Invalid Trip",
            "start_date": "2024-05-05",
            "end_date": "2024-05-01",  # End before start
        }

        # Act
        response = self.client.post(
            "/api/itineraries",
            json=create_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("tripsage.api.routers.itineraries.get_itinerary_service")
    @patch("tripsage.api.routers.itineraries.require_principal_dep")
    def test_list_itineraries_success(self, mock_auth, mock_service_dep):
        """Test successful itinerary listing."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        itineraries = [self.sample_itinerary]
        self.mock_service.list_itineraries = AsyncMock(return_value=itineraries)

        # Act
        response = self.client.get(
            "/api/itineraries", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        self.mock_service.list_itineraries.assert_called_once_with("test-user-id")

    @patch("tripsage.api.routers.itineraries.get_itinerary_service")
    @patch("tripsage.api.routers.itineraries.require_principal_dep")
    def test_search_itineraries_success(self, mock_auth, mock_service_dep):
        """Test successful itinerary search."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.search_itineraries = AsyncMock(
            return_value=self.sample_search_response
        )

        search_request = {
            "destination": "Tokyo",
            "start_date": "2024-05-01",
            "end_date": "2024-05-31",
            "limit": 10,
        }

        # Act
        response = self.client.post(
            "/api/itineraries/search",
            json=search_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "itineraries" in data
        assert "total_count" in data
        self.mock_service.search_itineraries.assert_called_once()

    @patch("tripsage.api.routers.itineraries.get_itinerary_service")
    @patch("tripsage.api.routers.itineraries.require_principal_dep")
    def test_get_itinerary_success(self, mock_auth, mock_service_dep):
        """Test successful itinerary retrieval."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        itinerary_id = "test-itinerary-id"
        self.mock_service.get_itinerary = AsyncMock(return_value=self.sample_itinerary)

        # Act
        response = self.client.get(
            f"/api/itineraries/{itinerary_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == self.sample_itinerary["id"]
        self.mock_service.get_itinerary.assert_called_once_with(
            "test-user-id", itinerary_id
        )

    @patch("tripsage.api.routers.itineraries.get_itinerary_service")
    @patch("tripsage.api.routers.itineraries.require_principal_dep")
    def test_get_itinerary_not_found(self, mock_auth, mock_service_dep):
        """Test itinerary retrieval for non-existent itinerary."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        itinerary_id = "non-existent-id"

        from tripsage_core.exceptions.exceptions import CoreResourceNotFoundError

        self.mock_service.get_itinerary = AsyncMock(
            side_effect=CoreResourceNotFoundError("Itinerary not found")
        )

        # Act
        response = self.client.get(
            f"/api/itineraries/{itinerary_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("tripsage.api.routers.itineraries.get_itinerary_service")
    @patch("tripsage.api.routers.itineraries.require_principal_dep")
    def test_update_itinerary_success(self, mock_auth, mock_service_dep):
        """Test successful itinerary update."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        itinerary_id = "test-itinerary-id"
        updated_itinerary = {**self.sample_itinerary, "name": "Updated Tokyo Trip"}
        self.mock_service.update_itinerary = AsyncMock(return_value=updated_itinerary)

        update_request = {
            "name": "Updated Tokyo Trip",
            "description": "Updated description",
        }

        # Act
        response = self.client.put(
            f"/api/itineraries/{itinerary_id}",
            json=update_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Tokyo Trip"
        self.mock_service.update_itinerary.assert_called_once()

    @patch("tripsage.api.routers.itineraries.get_itinerary_service")
    @patch("tripsage.api.routers.itineraries.require_principal_dep")
    def test_delete_itinerary_success(self, mock_auth, mock_service_dep):
        """Test successful itinerary deletion."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        itinerary_id = "test-itinerary-id"
        self.mock_service.delete_itinerary = AsyncMock(return_value=True)

        # Act
        response = self.client.delete(
            f"/api/itineraries/{itinerary_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        self.mock_service.delete_itinerary.assert_called_once_with(
            "test-user-id", itinerary_id
        )

    @patch("tripsage.api.routers.itineraries.get_itinerary_service")
    @patch("tripsage.api.routers.itineraries.require_principal_dep")
    def test_add_item_to_itinerary_success(self, mock_auth, mock_service_dep):
        """Test successful addition of item to itinerary."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        itinerary_id = "test-itinerary-id"
        self.mock_service.add_item_to_itinerary = AsyncMock(
            return_value=self.sample_itinerary_item
        )

        item_request = {
            "name": "Visit Tokyo Tower",
            "description": "Iconic Tokyo landmark",
            "start_time": "2024-05-01T10:00:00Z",
            "end_time": "2024-05-01T12:00:00Z",
            "location": "Tokyo Tower, Tokyo",
            "item_type": "attraction",
        }

        # Act
        response = self.client.post(
            f"/api/itineraries/{itinerary_id}/items",
            json=item_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Visit Tokyo Tower"
        self.mock_service.add_item_to_itinerary.assert_called_once()

    @patch("tripsage.api.routers.itineraries.get_itinerary_service")
    @patch("tripsage.api.routers.itineraries.require_principal_dep")
    def test_get_itinerary_item_success(self, mock_auth, mock_service_dep):
        """Test successful itinerary item retrieval."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        itinerary_id = "test-itinerary-id"
        item_id = "test-item-id"
        self.mock_service.get_item = AsyncMock(return_value=self.sample_itinerary_item)

        # Act
        response = self.client.get(
            f"/api/itineraries/{itinerary_id}/items/{item_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == self.sample_itinerary_item["id"]
        self.mock_service.get_item.assert_called_once_with(
            "test-user-id", itinerary_id, item_id
        )

    @patch("tripsage.api.routers.itineraries.get_itinerary_service")
    @patch("tripsage.api.routers.itineraries.require_principal_dep")
    def test_update_itinerary_item_success(self, mock_auth, mock_service_dep):
        """Test successful itinerary item update."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        itinerary_id = "test-itinerary-id"
        item_id = "test-item-id"
        updated_item = {**self.sample_itinerary_item, "name": "Updated Activity"}
        self.mock_service.update_item = AsyncMock(return_value=updated_item)

        update_request = {"name": "Updated Activity", "notes": "Updated notes"}

        # Act
        response = self.client.put(
            f"/api/itineraries/{itinerary_id}/items/{item_id}",
            json=update_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Activity"
        self.mock_service.update_item.assert_called_once()

    @patch("tripsage.api.routers.itineraries.get_itinerary_service")
    @patch("tripsage.api.routers.itineraries.require_principal_dep")
    def test_delete_itinerary_item_success(self, mock_auth, mock_service_dep):
        """Test successful itinerary item deletion."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        itinerary_id = "test-itinerary-id"
        item_id = "test-item-id"
        self.mock_service.delete_item = AsyncMock(return_value=True)

        # Act
        response = self.client.delete(
            f"/api/itineraries/{itinerary_id}/items/{item_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        self.mock_service.delete_item.assert_called_once_with(
            "test-user-id", itinerary_id, item_id
        )

    @patch("tripsage.api.routers.itineraries.get_itinerary_service")
    @patch("tripsage.api.routers.itineraries.require_principal_dep")
    def test_check_itinerary_conflicts_success(self, mock_auth, mock_service_dep):
        """Test successful conflict checking."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        itinerary_id = "test-itinerary-id"
        self.mock_service.check_conflicts = AsyncMock(
            return_value=self.sample_conflict_response
        )

        # Act
        response = self.client.get(
            f"/api/itineraries/{itinerary_id}/conflicts",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "conflicts" in data
        assert "has_conflicts" in data
        self.mock_service.check_conflicts.assert_called_once_with(
            "test-user-id", itinerary_id
        )

    @patch("tripsage.api.routers.itineraries.get_itinerary_service")
    @patch("tripsage.api.routers.itineraries.require_principal_dep")
    def test_optimize_itinerary_success(self, mock_auth, mock_service_dep):
        """Test successful itinerary optimization."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.optimize_itinerary = AsyncMock(
            return_value=self.sample_optimize_response
        )

        optimize_request = {
            "itinerary_id": "test-itinerary-id",
            "optimization_type": "time",
            "preferences": {
                "minimize_travel_time": True,
                "prefer_popular_attractions": False,
            },
        }

        # Act
        response = self.client.post(
            "/api/itineraries/optimize",
            json=optimize_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "optimized_itinerary" in data
        assert "improvements" in data
        self.mock_service.optimize_itinerary.assert_called_once()

    def test_create_itinerary_unauthorized(self):
        """Test itinerary creation without authentication."""
        create_request = {
            "name": "Tokyo Adventure",
            "start_date": "2024-05-01",
            "end_date": "2024-05-05",
        }

        response = self.client.post("/api/itineraries", json=create_request)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_itineraries_unauthorized(self):
        """Test itinerary listing without authentication."""
        response = self.client.get("/api/itineraries")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("tripsage.api.routers.itineraries.get_itinerary_service")
    @patch("tripsage.api.routers.itineraries.require_principal_dep")
    def test_create_itinerary_service_error(self, mock_auth, mock_service_dep):
        """Test itinerary creation with service error."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.create_itinerary = AsyncMock(
            side_effect=Exception("Service unavailable")
        )

        create_request = {
            "name": "Tokyo Adventure",
            "start_date": "2024-05-01",
            "end_date": "2024-05-05",
        }

        # Act
        response = self.client.post(
            "/api/itineraries",
            json=create_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.parametrize("name", ["", None, " ", "a" * 256])
    def test_create_itinerary_invalid_name(self, name):
        """Test itinerary creation with invalid name values."""
        create_request = {
            "name": name,
            "start_date": "2024-05-01",
            "end_date": "2024-05-05",
        }

        response = self.client.post(
            "/api/itineraries",
            json=create_request,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_itinerary_missing_required_fields(self):
        """Test itinerary creation with missing required fields."""
        create_request = {"description": "Missing name and dates"}

        response = self.client.post(
            "/api/itineraries",
            json=create_request,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("invalid_id", ["", "invalid-uuid", "123", None])
    def test_get_itinerary_invalid_id(self, invalid_id):
        """Test itinerary retrieval with invalid ID format."""
        if invalid_id is None:
            response = self.client.get(
                "/api/itineraries/", headers={"Authorization": "Bearer test-token"}
            )
        else:
            response = self.client.get(
                f"/api/itineraries/{invalid_id}",
                headers={"Authorization": "Bearer test-token"},
            )

        # Note: FastAPI validates path parameters, so invalid UUIDs may return 422
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_404_NOT_FOUND,
        ]
