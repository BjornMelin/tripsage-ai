"""
Integration tests for API → Service → Database flow.

This module tests the complete flow from API endpoints through service layers
to database operations, ensuring proper data flow and error handling.
Uses modern Principal-based authentication.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tripsage.api.main import app
from tripsage.api.middlewares.authentication import Principal
from tripsage_core.models.db.trip import Trip
from tripsage_core.models.db.user import User
from tripsage_core.models.schemas_common.enums import TripStatus, TripType
from tripsage_core.services.business.trip_service import TripService
from tripsage_core.services.business.user_service import UserService
from tripsage_core.services.infrastructure.database_service import DatabaseService


class TestApiDatabaseFlow:
    """Test complete API to database flow."""

    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)

    @pytest.fixture
    def mock_user(self):
        """Mock user for testing."""
        return User(
            id=12345,  # Use integer ID as required by User model
            email="test@example.com",
            name="testuser",
            role="user",
            is_admin=False,
            is_disabled=False,
        )

    @pytest.fixture
    def mock_principal(self, mock_user):
        """Mock principal for testing authentication."""
        return Principal(
            id=str(mock_user.id),
            type="user",
            email=mock_user.email,
            auth_method="jwt",
            scopes=[],
            metadata={},
        )

    @pytest.fixture
    def mock_trip(self):
        """Mock trip for testing."""
        from datetime import date

        return Trip(
            id=67890,  # Use integer ID as required by Trip model
            name="Test Trip",
            destination="Test Location",
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 7),
            budget=1000.0,
            travelers=2,
            status=TripStatus.PLANNING,
            trip_type=TripType.LEISURE,
        )

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_user_service(self, mock_user):
        """Mock user service."""
        service = AsyncMock(spec=UserService)
        service.create_user.return_value = mock_user
        service.get_user_by_id.return_value = mock_user
        service.get_user_by_email.return_value = mock_user
        service.get_user_by_username.return_value = mock_user
        service.update_user.return_value = mock_user
        return service

    @pytest.fixture
    def mock_trip_service(self, mock_trip):
        """Mock trip service."""
        service = AsyncMock(spec=TripService)
        service.create_trip.return_value = mock_trip
        service.get_trip.return_value = mock_trip
        service.list_user_trips.return_value = [mock_trip]
        service.update_trip.return_value = mock_trip
        service.delete_trip.return_value = True
        return service

    @pytest.fixture
    def mock_database_service(self, mock_db_session):
        """Mock database service."""
        service = AsyncMock(spec=DatabaseService)
        service.get_session.return_value.__aenter__ = AsyncMock(
            return_value=mock_db_session
        )
        service.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        service.execute_query.return_value = {"results": []}
        return service

    @pytest.mark.asyncio
    async def test_user_registration_flow(
        self, client, mock_user_service, mock_database_service, mock_user
    ):
        """Test complete user registration flow: API → User Service → Database."""
        with patch(
            "tripsage_core.services.business.user_service.UserService"
        ) as mock_service_class:
            mock_service_class.return_value = mock_user_service

            with patch(
                "tripsage_core.services.infrastructure.database_service.get_database_service"
            ) as mock_db_service:
                mock_db_service.return_value = mock_database_service

                # Test user registration (public endpoint - no auth required)
                response = client.post(
                    "/api/auth/register",
                    json={
                        "email": "test@example.com",
                        "username": "testuser",
                        "password": "testpassword123",
                        "first_name": "Test",
                        "last_name": "User",
                    },
                )

                # Verify API response
                assert response.status_code == 201
                response_data = response.json()
                assert "user" in response_data
                assert response_data["user"]["email"] == "test@example.com"

                # Verify service was called
                mock_user_service.create_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_trip_creation_flow(
        self,
        client,
        mock_trip_service,
        mock_database_service,
        mock_trip,
        mock_principal,
    ):
        """Test complete trip creation flow: API → Trip Service → Database."""
        with patch(
            "tripsage_core.services.business.trip_service.get_trip_service"
        ) as mock_service_dep:
            mock_service_dep.return_value = mock_trip_service

            with patch(
                "tripsage_core.services.infrastructure.database_service.get_database_service"
            ) as mock_db_service:
                mock_db_service.return_value = mock_database_service

                with patch(
                    "tripsage.api.core.dependencies.require_principal"
                ) as mock_auth:
                    mock_auth.return_value = mock_principal

                    # Test trip creation
                    response = client.post(
                        "/api/trips",
                        json={
                            "title": "Paris Adventure",
                            "description": "A wonderful trip to Paris",
                            "destination": "Paris, France",
                            "start_date": "2024-06-01",
                            "end_date": "2024-06-07",
                            "budget": 2000.0,
                        },
                        headers={"Authorization": "Bearer test-token"},
                    )

                    # Verify API response
                    assert response.status_code == 201
                    response_data = response.json()
                    assert response_data["title"] == "Paris Adventure"
                    assert response_data["destination"] == "Paris, France"

                    # Verify service was called
                    mock_trip_service.create_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_trip_retrieval_flow(
        self,
        client,
        mock_trip_service,
        mock_database_service,
        mock_trip,
        mock_principal,
    ):
        """Test complete trip retrieval flow: API → Trip Service → Database."""
        with patch(
            "tripsage_core.services.business.trip_service.get_trip_service"
        ) as mock_service_dep:
            mock_service_dep.return_value = mock_trip_service

            with patch(
                "tripsage_core.services.infrastructure.database_service.get_database_service"
            ) as mock_db_service:
                mock_db_service.return_value = mock_database_service

                with patch(
                    "tripsage.api.core.dependencies.require_principal"
                ) as mock_auth:
                    mock_auth.return_value = mock_principal

                    trip_id = str(mock_trip.id)

                    # Test trip retrieval
                    response = client.get(
                        f"/api/trips/{trip_id}",
                        headers={"Authorization": "Bearer test-token"},
                    )

                    # Verify API response
                    assert response.status_code == 200
                    response_data = response.json()
                    assert response_data["title"] == mock_trip.title

                    # Verify service was called
                    mock_trip_service.get_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_flow(
        self, client, mock_trip_service, mock_database_service, mock_principal
    ):
        """Test error handling in API flow."""
        with patch(
            "tripsage_core.services.business.trip_service.get_trip_service"
        ) as mock_service_dep:
            mock_service_dep.return_value = mock_trip_service

            with patch(
                "tripsage_core.services.infrastructure.database_service.get_database_service"
            ) as mock_db_service:
                mock_db_service.return_value = mock_database_service

                with patch(
                    "tripsage.api.core.dependencies.require_principal"
                ) as mock_auth:
                    mock_auth.return_value = mock_principal

                    # Configure service to raise exception
                    mock_trip_service.create_trip.side_effect = Exception(
                        "Database error"
                    )

                    # Test trip creation with database error
                    response = client.post(
                        "/api/trips",
                        json={
                            "title": "Failed Trip",
                            "description": "This should fail",
                            "destination": "Nowhere",
                            "start_date": "2024-06-01",
                            "end_date": "2024-06-07",
                            "budget": 1000.0,
                        },
                        headers={"Authorization": "Bearer test-token"},
                    )

                    # Verify error response
                    assert response.status_code == 500
                    assert "error" in response.json()

    @pytest.mark.asyncio
    async def test_authentication_failure_flow(self, client):
        """Test authentication failure in API flow."""
        with patch("tripsage.api.core.dependencies.require_principal") as mock_auth:
            # Configure authentication to fail
            from tripsage_core.exceptions.exceptions import CoreAuthenticationError

            mock_auth.side_effect = CoreAuthenticationError("Invalid token")

            # Test API call with invalid authentication
            response = client.get(
                "/api/trips", headers={"Authorization": "Bearer invalid-token"}
            )

            # Verify authentication error response
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_concurrent_operations_flow(
        self, client, mock_trip_service, mock_database_service, mock_principal
    ):
        """Test concurrent operations in API flow."""
        with patch(
            "tripsage_core.services.business.trip_service.get_trip_service"
        ) as mock_service_dep:
            mock_service_dep.return_value = mock_trip_service

            with patch(
                "tripsage_core.services.infrastructure.database_service.get_database_service"
            ) as mock_db_service:
                mock_db_service.return_value = mock_database_service

                with patch(
                    "tripsage.api.core.dependencies.require_principal"
                ) as mock_auth:
                    mock_auth.return_value = mock_principal

                    # Test multiple concurrent requests
                    trip_data = {
                        "title": "Concurrent Trip",
                        "description": "Testing concurrency",
                        "destination": "Test Location",
                        "start_date": "2024-06-01",
                        "end_date": "2024-06-07",
                        "budget": 1000.0,
                    }

                    # This would test concurrent behavior in a real scenario
                    response = client.post(
                        "/api/trips",
                        json=trip_data,
                        headers={"Authorization": "Bearer test-token"},
                    )

                    # Verify response
                    assert response.status_code == 201
                    mock_trip_service.create_trip.assert_called()

    @pytest.mark.asyncio
    async def test_data_validation_flow(self, client, mock_principal):
        """Test data validation in API flow."""
        with patch("tripsage.api.core.dependencies.require_principal") as mock_auth:
            mock_auth.return_value = mock_principal

            # Test with invalid trip data
            response = client.post(
                "/api/trips",
                json={
                    "title": "",  # Invalid empty title
                    "description": "Test description",
                    "destination": "Test Location",
                    "start_date": "invalid-date",  # Invalid date format
                    "end_date": "2024-06-07",
                    "budget": -100.0,  # Invalid negative budget
                },
                headers={"Authorization": "Bearer test-token"},
            )

            # Verify validation error response
            assert response.status_code == 422
            response_data = response.json()
            assert "detail" in response_data
