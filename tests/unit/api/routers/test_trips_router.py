"""Comprehensive unit tests for trips router."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests.factories import TripFactory
from tripsage.api.main import app


class TestTripsRouter:
    """Test suite for trips router endpoints."""

    def setup_method(self):
        """Set up test client and mocks."""
        self.client = TestClient(app)
        self.mock_trip_service = Mock()

        # Sample test data
        self.sample_trip = TripFactory.create()
        self.sample_trip_id = str(uuid4())

        self.sample_create_request = {
            "title": "Summer Vacation in Europe",
            "description": "A wonderful two-week trip through Europe",
            "start_date": "2024-06-01",
            "end_date": "2024-06-15",
            "destinations": [
                {
                    "name": "Paris",
                    "country": "France",
                    "city": "Paris",
                    "arrival_date": "2024-06-01",
                    "departure_date": "2024-06-05",
                    "duration_days": 4,
                },
                {
                    "name": "Rome",
                    "country": "Italy",
                    "city": "Rome",
                    "arrival_date": "2024-06-05",
                    "departure_date": "2024-06-10",
                    "duration_days": 5,
                },
            ],
            "preferences": {
                "budget": {
                    "total": 5000,
                    "currency": "USD",
                    "accommodation_budget": 2000,
                    "transportation_budget": 1500,
                    "food_budget": 1000,
                    "activities_budget": 500,
                },
                "accommodation": {
                    "type": "hotel",
                    "min_rating": 4.0,
                    "amenities": ["wifi", "breakfast"],
                    "location_preference": "city_center",
                },
            },
        }

        self.sample_trip_response = {
            "id": self.sample_trip_id,
            "user_id": "test-user-id",
            "title": "Summer Vacation in Europe",
            "description": "A wonderful two-week trip through Europe",
            "start_date": "2024-06-01",
            "end_date": "2024-06-15",
            "duration_days": 14,
            "destinations": self.sample_create_request["destinations"],
            "preferences": self.sample_create_request["preferences"],
            "itinerary_id": None,
            "status": "planning",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

    @patch("tripsage.api.routers.trips.get_trip_service")
    @patch("tripsage.api.routers.trips.require_principal_dep")
    def test_create_trip_success(self, mock_auth, mock_service_dep):
        """Test successful trip creation."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_trip_service
        self.mock_trip_service.create_trip = AsyncMock(
            return_value=self.sample_trip_response
        )

        # Act
        response = self.client.post(
            "/api/trips/",
            json=self.sample_create_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == "Summer Vacation in Europe"
        assert data["duration_days"] == 14
        assert len(data["destinations"]) == 2
        assert data["status"] == "planning"
        self.mock_trip_service.create_trip.assert_called_once()

    def test_create_trip_unauthorized(self):
        """Test trip creation without authentication."""
        # Act
        response = self.client.post("/api/trips/", json=self.sample_create_request)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_trip_invalid_dates(self):
        """Test trip creation with invalid dates (end before start)."""
        # Arrange
        invalid_request = {
            **self.sample_create_request,
            "start_date": "2024-06-15",
            "end_date": "2024-06-01",  # End before start
        }

        # Act
        response = self.client.post(
            "/api/trips/",
            json=invalid_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_trip_missing_title(self):
        """Test trip creation without required title."""
        # Arrange
        invalid_request = {
            **self.sample_create_request,
            "title": "",  # Empty title
        }

        # Act
        response = self.client.post(
            "/api/trips/",
            json=invalid_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_trip_no_destinations(self):
        """Test trip creation without destinations."""
        # Arrange
        invalid_request = {
            **self.sample_create_request,
            "destinations": [],  # No destinations
        }

        # Act
        response = self.client.post(
            "/api/trips/",
            json=invalid_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("tripsage.api.routers.trips.get_trip_service")
    @patch("tripsage.api.routers.trips.require_principal_dep")
    def test_create_trip_service_error(self, mock_auth, mock_service_dep):
        """Test trip creation with service error."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_trip_service
        self.mock_trip_service.create_trip = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Act
        response = self.client.post(
            "/api/trips/",
            json=self.sample_create_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @patch("tripsage.api.routers.trips.get_trip_service")
    @patch("tripsage.api.routers.trips.require_principal_dep")
    def test_get_trip_success(self, mock_auth, mock_service_dep):
        """Test successful trip retrieval."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_trip_service
        self.mock_trip_service.get_trip = AsyncMock(
            return_value=self.sample_trip_response
        )

        # Act
        response = self.client.get(
            f"/api/trips/{self.sample_trip_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == self.sample_trip_id
        assert data["title"] == "Summer Vacation in Europe"
        self.mock_trip_service.get_trip.assert_called_once_with(
            self.sample_trip_id, "test-user-id"
        )

    @patch("tripsage.api.routers.trips.get_trip_service")
    @patch("tripsage.api.routers.trips.require_principal_dep")
    def test_get_trip_not_found(self, mock_auth, mock_service_dep):
        """Test trip retrieval for non-existent trip."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_trip_service
        self.mock_trip_service.get_trip = AsyncMock(return_value=None)

        # Act
        response = self.client.get(
            "/api/trips/nonexistent-id", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Trip not found" in response.json()["detail"]

    @patch("tripsage.api.routers.trips.get_trip_service")
    @patch("tripsage.api.routers.trips.require_principal_dep")
    def test_get_trip_access_denied(self, mock_auth, mock_service_dep):
        """Test trip retrieval with access denied."""
        # Arrange
        mock_auth.return_value = Mock(id="different-user-id")
        mock_service_dep.return_value = self.mock_trip_service
        from fastapi import HTTPException

        self.mock_trip_service.get_trip = AsyncMock(
            side_effect=HTTPException(status_code=403, detail="Access denied")
        )

        # Act
        response = self.client.get(
            f"/api/trips/{self.sample_trip_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("tripsage.api.routers.trips.get_trip_service")
    @patch("tripsage.api.routers.trips.require_principal_dep")
    def test_list_trips_success(self, mock_auth, mock_service_dep):
        """Test successful trip listing."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_trip_service

        sample_trips = [
            {
                "id": str(uuid4()),
                "title": "Europe Trip",
                "start_date": "2024-06-01",
                "end_date": "2024-06-15",
                "duration_days": 14,
                "destinations": ["Paris", "Rome"],
                "status": "planning",
                "created_at": "2024-01-01T00:00:00Z",
            },
            {
                "id": str(uuid4()),
                "title": "Asia Adventure",
                "start_date": "2024-09-01",
                "end_date": "2024-09-21",
                "duration_days": 20,
                "destinations": ["Tokyo", "Bangkok"],
                "status": "booked",
                "created_at": "2024-02-01T00:00:00Z",
            },
        ]

        trip_list_response = {"items": sample_trips, "total": 2, "skip": 0, "limit": 10}

        self.mock_trip_service.list_trips = AsyncMock(return_value=trip_list_response)

        # Act
        response = self.client.get(
            "/api/trips/?skip=0&limit=10",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2
        assert data["skip"] == 0
        assert data["limit"] == 10
        self.mock_trip_service.list_trips.assert_called_once_with("test-user-id", 0, 10)

    @patch("tripsage.api.routers.trips.get_trip_service")
    @patch("tripsage.api.routers.trips.require_principal_dep")
    def test_list_trips_with_pagination(self, mock_auth, mock_service_dep):
        """Test trip listing with custom pagination."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_trip_service
        self.mock_trip_service.list_trips = AsyncMock(
            return_value={"items": [], "total": 25, "skip": 20, "limit": 5}
        )

        # Act
        response = self.client.get(
            "/api/trips/?skip=20&limit=5",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["skip"] == 20
        assert data["limit"] == 5
        assert data["total"] == 25

    @patch("tripsage.api.routers.trips.get_trip_service")
    @patch("tripsage.api.routers.trips.require_principal_dep")
    def test_update_trip_success(self, mock_auth, mock_service_dep):
        """Test successful trip update."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_trip_service

        update_request = {
            "title": "Updated Europe Trip",
            "description": "Updated description",
            "end_date": "2024-06-20",
        }

        updated_trip = {
            **self.sample_trip_response,
            "title": "Updated Europe Trip",
            "description": "Updated description",
            "end_date": "2024-06-20",
            "duration_days": 19,
        }

        self.mock_trip_service.update_trip = AsyncMock(return_value=updated_trip)

        # Act
        response = self.client.put(
            f"/api/trips/{self.sample_trip_id}",
            json=update_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Updated Europe Trip"
        assert data["description"] == "Updated description"
        assert data["duration_days"] == 19
        self.mock_trip_service.update_trip.assert_called_once()

    @patch("tripsage.api.routers.trips.get_trip_service")
    @patch("tripsage.api.routers.trips.require_principal_dep")
    def test_update_trip_not_found(self, mock_auth, mock_service_dep):
        """Test updating non-existent trip."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_trip_service
        from fastapi import HTTPException

        self.mock_trip_service.update_trip = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Trip not found")
        )

        # Act
        response = self.client.put(
            "/api/trips/nonexistent-id",
            json={"title": "Updated Title"},
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_trip_invalid_dates(self):
        """Test trip update with invalid dates."""
        # Arrange
        update_request = {
            "start_date": "2024-06-15",
            "end_date": "2024-06-01",  # End before start
        }

        # Act
        response = self.client.put(
            f"/api/trips/{self.sample_trip_id}",
            json=update_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("tripsage.api.routers.trips.get_trip_service")
    @patch("tripsage.api.routers.trips.require_principal_dep")
    def test_delete_trip_success(self, mock_auth, mock_service_dep):
        """Test successful trip deletion."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_trip_service
        self.mock_trip_service.delete_trip = AsyncMock(return_value=True)

        # Act
        response = self.client.delete(
            f"/api/trips/{self.sample_trip_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        self.mock_trip_service.delete_trip.assert_called_once_with(
            self.sample_trip_id, "test-user-id"
        )

    @patch("tripsage.api.routers.trips.get_trip_service")
    @patch("tripsage.api.routers.trips.require_principal_dep")
    def test_delete_trip_not_found(self, mock_auth, mock_service_dep):
        """Test deletion of non-existent trip."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_trip_service
        self.mock_trip_service.delete_trip = AsyncMock(return_value=False)

        # Act
        response = self.client.delete(
            "/api/trips/nonexistent-id", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("tripsage.api.routers.trips.get_trip_service")
    @patch("tripsage.api.routers.trips.require_principal_dep")
    def test_get_trip_summary_success(self, mock_auth, mock_service_dep):
        """Test successful trip summary retrieval."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_trip_service

        sample_summary = {
            "id": self.sample_trip_id,
            "title": "Summer Vacation in Europe",
            "date_range": "Jun 1-15, 2024",
            "duration_days": 14,
            "destinations": ["Paris", "Rome"],
            "accommodation_summary": "4-star hotels in city centers",
            "transportation_summary": "Economy flights, local transit",
            "budget_summary": {
                "total": 5000,
                "currency": "USD",
                "spent": 1500,
                "remaining": 3500,
                "breakdown": {
                    "accommodation": {"budget": 2000, "spent": 800},
                    "transportation": {"budget": 1500, "spent": 700},
                    "food": {"budget": 1000, "spent": 0},
                    "activities": {"budget": 500, "spent": 0},
                },
            },
            "has_itinerary": True,
            "completion_percentage": 75,
        }

        self.mock_trip_service.get_trip_summary = AsyncMock(return_value=sample_summary)

        # Act
        response = self.client.get(
            f"/api/trips/{self.sample_trip_id}/summary",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == self.sample_trip_id
        assert data["completion_percentage"] == 75
        assert data["has_itinerary"] is True
        assert "budget_summary" in data

    @patch("tripsage.api.routers.trips.get_trip_service")
    @patch("tripsage.api.routers.trips.require_principal_dep")
    def test_update_trip_preferences_success(self, mock_auth, mock_service_dep):
        """Test successful trip preferences update."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_trip_service

        preferences_request = {
            "budget": {"total": 6000, "currency": "USD", "accommodation_budget": 2500},
            "accommodation": {"type": "luxury_hotel", "min_rating": 5.0},
        }

        updated_trip = {**self.sample_trip_response, "preferences": preferences_request}

        self.mock_trip_service.update_trip_preferences = AsyncMock(
            return_value=updated_trip
        )

        # Act
        response = self.client.put(
            f"/api/trips/{self.sample_trip_id}/preferences",
            json=preferences_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["preferences"]["budget"]["total"] == 6000
        assert data["preferences"]["accommodation"]["min_rating"] == 5.0

    @patch("tripsage.api.routers.trips.get_trip_service")
    @patch("tripsage.api.routers.trips.require_principal_dep")
    def test_duplicate_trip_success(self, mock_auth, mock_service_dep):
        """Test successful trip duplication."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_trip_service

        duplicated_trip = {
            **self.sample_trip_response,
            "id": str(uuid4()),
            "title": "Copy of Summer Vacation in Europe",
            "status": "draft",
        }

        self.mock_trip_service.duplicate_trip = AsyncMock(return_value=duplicated_trip)

        # Act
        response = self.client.post(
            f"/api/trips/{self.sample_trip_id}/duplicate",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "Copy of" in data["title"]
        assert data["status"] == "draft"
        assert data["id"] != self.sample_trip_id

    def test_list_trips_unauthorized(self):
        """Test trip listing without authentication."""
        # Act
        response = self.client.get("/api/trips/")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_trip_unauthorized(self):
        """Test trip retrieval without authentication."""
        # Act
        response = self.client.get(f"/api/trips/{self.sample_trip_id}")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_trip_unauthorized(self):
        """Test trip update without authentication."""
        # Act
        response = self.client.put(
            f"/api/trips/{self.sample_trip_id}", json={"title": "Updated Title"}
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_trip_unauthorized(self):
        """Test trip deletion without authentication."""
        # Act
        response = self.client.delete(f"/api/trips/{self.sample_trip_id}")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "skip,limit",
        [
            (-1, 10),  # Invalid skip
            (0, 0),  # Invalid limit
            (0, 101),  # Limit too high
            (0, -1),  # Negative limit
        ],
    )
    def test_list_trips_invalid_pagination(self, skip, limit):
        """Test trip listing with invalid pagination parameters."""
        # Act
        response = self.client.get(
            f"/api/trips/?skip={skip}&limit={limit}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_trip_title_too_long(self):
        """Test trip creation with title exceeding maximum length."""
        # Arrange
        invalid_request = {
            **self.sample_create_request,
            "title": "x" * 101,  # Exceeds max length of 100
        }

        # Act
        response = self.client.post(
            "/api/trips/",
            json=invalid_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_trip_description_too_long(self):
        """Test trip creation with description exceeding maximum length."""
        # Arrange
        invalid_request = {
            **self.sample_create_request,
            "description": "x" * 501,  # Exceeds max length of 500
        }

        # Act
        response = self.client.post(
            "/api/trips/",
            json=invalid_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("tripsage.api.routers.trips.get_trip_service")
    @patch("tripsage.api.routers.trips.require_principal_dep")
    def test_search_trips_success(self, mock_auth, mock_service_dep):
        """Test successful trip search."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_trip_service

        search_results = {
            "items": [self.sample_trip_response],
            "total": 1,
            "skip": 0,
            "limit": 10,
        }

        self.mock_trip_service.search_trips = AsyncMock(return_value=search_results)

        # Act
        response = self.client.get(
            "/api/trips/search?q=Europe&status=planning",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1

    @patch("tripsage.api.routers.trips.get_trip_service")
    @patch("tripsage.api.routers.trips.require_principal_dep")
    def test_get_trip_itinerary_success(self, mock_auth, mock_service_dep):
        """Test successful trip itinerary retrieval."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_trip_service

        sample_itinerary = {
            "id": str(uuid4()),
            "trip_id": self.sample_trip_id,
            "items": [
                {
                    "id": str(uuid4()),
                    "name": "Visit Eiffel Tower",
                    "description": "Iconic landmark visit",
                    "start_time": "2024-06-01T10:00:00Z",
                    "end_time": "2024-06-01T12:00:00Z",
                    "location": "Eiffel Tower, Paris",
                }
            ],
            "total_items": 1,
        }

        self.mock_trip_service.get_trip_itinerary = AsyncMock(
            return_value=sample_itinerary
        )

        # Act
        response = self.client.get(
            f"/api/trips/{self.sample_trip_id}/itinerary",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["trip_id"] == self.sample_trip_id
        assert len(data["items"]) == 1
        assert data["total_items"] == 1

    @patch("tripsage.api.routers.trips.get_trip_service")
    @patch("tripsage.api.routers.trips.require_principal_dep")
    def test_export_trip_success(self, mock_auth, mock_service_dep):
        """Test successful trip export."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_trip_service

        export_data = {
            "format": "pdf",
            "download_url": "https://example.com/exports/trip-123.pdf",
            "expires_at": "2024-01-02T00:00:00Z",
        }

        self.mock_trip_service.export_trip = AsyncMock(return_value=export_data)

        # Act
        response = self.client.post(
            f"/api/trips/{self.sample_trip_id}/export?format=pdf",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["format"] == "pdf"
        assert "download_url" in data
        assert "expires_at" in data
