"""Comprehensive unit tests for accommodation router."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests.factories import AccommodationFactory
from tripsage_core.exceptions import CoreResourceNotFoundError


class TestAccommodationRouter:
    """Test suite for accommodation router endpoints."""

    def setup_method(self):
        """Set up test client and mocks."""
        # Mock cache service before importing app
        self.cache_patch = patch("tripsage_core.services.infrastructure.cache_service.get_cache_service")
        mock_get_cache = self.cache_patch.start()
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=True)
        mock_cache.delete = AsyncMock(return_value=True)
        mock_cache.exists = AsyncMock(return_value=False)
        mock_cache.ping = AsyncMock(return_value=True)
        mock_cache._connected = True
        mock_get_cache.return_value = mock_cache
        
        # Import app after patching
        from tripsage.api.main import app
        self.client = TestClient(app)
        self.mock_service = Mock()
        self.sample_accommodation = AccommodationFactory.create()
        
    def teardown_method(self):
        """Clean up patches."""
        self.cache_patch.stop()

    @patch("tripsage.api.routers.accommodations.get_accommodation_service")
    @patch("tripsage.api.routers.accommodations.require_principal_dep")
    def test_search_accommodations_success(self, mock_auth, mock_service_dep):
        """Test successful accommodation search."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.search_accommodations.return_value = {
            "accommodations": [self.sample_accommodation],
            "total_count": 1,
            "page": 1,
            "per_page": 10,
        }

        search_request = {
            "destination": "Tokyo",
            "check_in": "2024-03-15",
            "check_out": "2024-03-18",
            "guests": 2,
        }

        # Act
        response = self.client.post(
            "/api/accommodations/search",
            json=search_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "accommodations" in data
        assert len(data["accommodations"]) == 1
        assert data["total_count"] == 1
        self.mock_service.search_accommodations.assert_called_once()

    @patch("tripsage.api.routers.accommodations.get_accommodation_service")
    @patch("tripsage.api.routers.accommodations.require_principal_dep")
    def test_search_accommodations_invalid_dates(self, mock_auth, mock_service_dep):
        """Test accommodation search with invalid date range."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service

        search_request = {
            "destination": "Tokyo",
            "check_in": "2024-03-18",  # After check_out
            "check_out": "2024-03-15",
            "guests": 2,
        }

        # Act
        response = self.client.post(
            "/api/accommodations/search",
            json=search_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("tripsage.api.routers.accommodations.get_accommodation_service")
    @patch("tripsage.api.routers.accommodations.require_principal_dep")
    def test_get_accommodation_details_success(self, mock_auth, mock_service_dep):
        """Test successful accommodation details retrieval."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        accommodation_id = "test-accommodation-id"
        self.mock_service.get_accommodation_details.return_value = (
            self.sample_accommodation
        )

        # Act
        response = self.client.get(
            f"/api/accommodations/{accommodation_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == self.sample_accommodation["id"]
        self.mock_service.get_accommodation_details.assert_called_once_with(
            accommodation_id
        )

    @patch("tripsage.api.routers.accommodations.get_accommodation_service")
    @patch("tripsage.api.routers.accommodations.require_principal_dep")
    def test_get_accommodation_details_not_found(self, mock_auth, mock_service_dep):
        """Test accommodation details retrieval for non-existent accommodation."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        accommodation_id = "non-existent-id"
        self.mock_service.get_accommodation_details.side_effect = (
            CoreResourceNotFoundError("Accommodation not found")
        )

        # Act
        response = self.client.get(
            f"/api/accommodations/{accommodation_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("tripsage.api.routers.accommodations.get_accommodation_service")
    @patch("tripsage.api.routers.accommodations.require_principal_dep")
    def test_save_accommodation_success(self, mock_auth, mock_service_dep):
        """Test successful accommodation saving."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        saved_accommodation = {**self.sample_accommodation, "is_saved": True}
        self.mock_service.save_accommodation.return_value = saved_accommodation

        save_request = {
            "accommodation_id": "test-accommodation-id",
            "notes": "Great location!",
        }

        # Act
        response = self.client.post(
            "/api/accommodations/save",
            json=save_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_saved"] is True
        self.mock_service.save_accommodation.assert_called_once()

    def test_search_accommodations_unauthorized(self):
        """Test accommodation search without authentication."""
        search_request = {
            "destination": "Tokyo",
            "check_in": "2024-03-15",
            "check_out": "2024-03-18",
            "guests": 2,
        }

        response = self.client.post("/api/accommodations/search", json=search_request)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("tripsage.api.routers.accommodations.get_accommodation_service")
    @patch("tripsage.api.routers.accommodations.require_principal_dep")
    def test_search_accommodations_service_error(self, mock_auth, mock_service_dep):
        """Test accommodation search with service error."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.search_accommodations.side_effect = Exception(
            "Service unavailable"
        )

        search_request = {
            "destination": "Tokyo",
            "check_in": "2024-03-15",
            "check_out": "2024-03-18",
            "guests": 2,
        }

        # Act
        response = self.client.post(
            "/api/accommodations/search",
            json=search_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.parametrize("guests", [0, -1, 21])
    def test_search_accommodations_invalid_guests(self, guests):
        """Test accommodation search with invalid guest count."""
        search_request = {
            "destination": "Tokyo",
            "check_in": "2024-03-15",
            "check_out": "2024-03-18",
            "guests": guests,
        }

        response = self.client.post(
            "/api/accommodations/search",
            json=search_request,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("destination", ["", None, " "])
    def test_search_accommodations_invalid_destination(self, destination):
        """Test accommodation search with invalid destination."""
        search_request = {
            "destination": destination,
            "check_in": "2024-03-15",
            "check_out": "2024-03-18",
            "guests": 2,
        }

        response = self.client.post(
            "/api/accommodations/search",
            json=search_request,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
