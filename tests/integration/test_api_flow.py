"""
Integration tests for API → Service → Database flow.

This module tests the complete flow from API endpoints through service layers
to database operations, ensuring proper data flow and error handling.
"""

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tripsage.api.main import app
from tripsage_core.models.db.trip import Trip
from tripsage_core.models.db.user import User
from tripsage_core.services.business.auth_service import AuthenticationService
from tripsage_core.services.business.trip_service import TripService
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
            id=uuid4(),
            email="test@example.com",
            username="testuser",
            first_name="Test",
            last_name="User",
            is_active=True,
            api_keys={},
        )

    @pytest.fixture
    def mock_trip(self):
        """Mock trip for testing."""
        return Trip(
            id=uuid4(),
            user_id=uuid4(),
            title="Paris Adventure",
            description="A wonderful trip to Paris",
            destination="Paris, France",
            start_date="2024-06-01",
            end_date="2024-06-07",
            budget=2000.0,
            status="active",
        )

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        return session

    @pytest.fixture
    def mock_auth_service(self, mock_user):
        """Mock auth service."""
        service = AsyncMock(spec=AuthenticationService)
        service.get_user_by_id.return_value = mock_user
        service.validate_api_key.return_value = mock_user
        service.create_user.return_value = mock_user
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
        self, client, mock_auth_service, mock_database_service, mock_user
    ):
        """Test complete user registration flow: API → Auth Service → Database."""
        with patch(
            "tripsage_core.services.business.auth_service.AuthenticationService"
        ) as mock_service_class:
            mock_service_class.return_value = mock_auth_service

            with patch(
                "tripsage_core.services.infrastructure.database_service.get_database_service"
            ) as mock_db_service:
                mock_db_service.return_value = mock_database_service

                # Test user registration
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
                mock_auth_service.create_user.assert_called_once()
                call_args = mock_auth_service.create_user.call_args[0][0]
                assert call_args.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_trip_creation_flow(
        self, client, mock_trip_service, mock_database_service, mock_trip, mock_user
    ):
        """Test complete trip creation flow: API → Trip Service → Database."""
        with patch(
            "tripsage.api.services.trip_service.TripService"
        ) as mock_service_class:
            mock_service_class.return_value = mock_trip_service

            with patch(
                "tripsage_core.services.infrastructure.database_service.get_database_service"
            ) as mock_db_service:
                mock_db_service.return_value = mock_database_service

                with patch(
                    "tripsage.api.core.dependencies.verify_api_key"
                ) as mock_verify:
                    mock_verify.return_value = mock_user

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
                        headers={"Authorization": "Bearer test-api-key"},
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
        self, client, mock_trip_service, mock_database_service, mock_trip, mock_user
    ):
        """Test complete trip retrieval flow: API → Trip Service → Database."""
        with patch(
            "tripsage.api.services.trip_service.TripService"
        ) as mock_service_class:
            mock_service_class.return_value = mock_trip_service

            with patch(
                "tripsage_core.services.infrastructure.database_service.get_database_service"
            ) as mock_db_service:
                mock_db_service.return_value = mock_database_service

                with patch(
                    "tripsage.api.core.dependencies.verify_api_key"
                ) as mock_verify:
                    mock_verify.return_value = mock_user

                    trip_id = str(mock_trip.id)

                    # Test trip retrieval
                    response = client.get(
                        f"/api/trips/{trip_id}",
                        headers={"Authorization": "Bearer test-api-key"},
                    )

                    # Verify API response
                    assert response.status_code == 200
                    response_data = response.json()
                    assert response_data["title"] == "Paris Adventure"

                    # Verify service was called with correct ID
                    mock_trip_service.get_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_error_handling(
        self, client, mock_trip_service, mock_database_service, mock_user
    ):
        """Test error handling when database operations fail."""
        # Configure service to raise an exception
        mock_trip_service.create_trip.side_effect = Exception(
            "Database connection failed"
        )

        with patch(
            "tripsage.api.services.trip_service.TripService"
        ) as mock_service_class:
            mock_service_class.return_value = mock_trip_service

            with patch(
                "tripsage_core.services.infrastructure.database_service.get_database_service"
            ) as mock_db_service:
                mock_db_service.return_value = mock_database_service

                with patch(
                    "tripsage.api.core.dependencies.verify_api_key"
                ) as mock_verify:
                    mock_verify.return_value = mock_user

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
                        headers={"Authorization": "Bearer test-api-key"},
                    )

                    # Verify error response
                    assert response.status_code == 500

                    # Verify service was called (and failed)
                    mock_trip_service.create_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_authentication_failure_flow(self, client, mock_auth_service):
        """Test authentication failure in API flow."""
        # Configure auth service to reject the API key
        mock_auth_service.validate_api_key.side_effect = Exception("Invalid API key")

        with patch("tripsage.api.core.dependencies.verify_api_key") as mock_verify:
            mock_verify.side_effect = Exception("Invalid API key")

            # Test API call with invalid authentication
            response = client.get(
                "/api/trips", headers={"Authorization": "Bearer invalid-key"}
            )

            # Verify authentication failure
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_concurrent_database_operations(
        self, client, mock_trip_service, mock_database_service, mock_user
    ):
        """Test concurrent database operations through API."""
        with patch(
            "tripsage.api.services.trip_service.TripService"
        ) as mock_service_class:
            mock_service_class.return_value = mock_trip_service

            with patch(
                "tripsage_core.services.infrastructure.database_service.get_database_service"
            ) as mock_db_service:
                mock_db_service.return_value = mock_database_service

                with patch(
                    "tripsage.api.core.dependencies.verify_api_key"
                ) as mock_verify:
                    mock_verify.return_value = mock_user

                    # Simulate multiple concurrent trip creations
                    tasks = []
                    for i in range(3):
                        task = asyncio.create_task(
                            asyncio.to_thread(
                                client.post,
                                "/api/trips",
                                json={
                                    "title": f"Trip {i}",
                                    "description": f"Test trip {i}",
                                    "destination": f"Destination {i}",
                                    "start_date": "2024-06-01",
                                    "end_date": "2024-06-07",
                                    "budget": 1000.0 + i * 100,
                                },
                                headers={"Authorization": "Bearer test-api-key"},
                            )
                        )
                        tasks.append(task)

                    # Wait for all tasks to complete
                    responses = await asyncio.gather(*tasks)

                    # Verify all requests succeeded
                    for response in responses:
                        assert response.status_code == 201

                    # Verify service was called for each request
                    assert mock_trip_service.create_trip.call_count == 3
