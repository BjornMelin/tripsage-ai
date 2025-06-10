"""
Simplified comprehensive tests for Activities API router endpoints (BJO-120 implementation).

This test suite covers the newly implemented user-specific activity endpoints:
- POST /activities/save - Save activity with authentication
- GET /activities/saved - Get saved activities with authentication  
- DELETE /activities/saved/{activity_id} - Delete saved activity with authentication

Tests follow ULTRATHINK principles:
- ≥90% coverage with actionable assertions
- Zero flaky tests with deterministic mocking
- Real-world usage patterns and edge cases
- Modern pytest patterns with Pydantic 2.x
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from tripsage.api.core.dependencies import require_principal
from tripsage.api.routers.activities import router as activities_router
from tripsage.api.schemas.requests.activities import SaveActivityRequest
from tripsage.api.schemas.responses.activities import (
    ActivityCoordinates,
    ActivityResponse,
    SavedActivityResponse,
)
from tripsage_core.services.business.activity_service import ActivityServiceError


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI app for testing."""
    app = FastAPI()
    app.include_router(activities_router, prefix="/activities")
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client for unauthenticated requests."""
    return TestClient(app)


@pytest.fixture 
def authenticated_client(app: FastAPI) -> TestClient:
    """Create authenticated test client for testing."""
    # Mock authentication to return test user
    async def mock_require_principal(request=None):
        return {"sub": "user123", "email": "test@example.com"}
    
    # Apply dependency override
    app.dependency_overrides = {
        require_principal: mock_require_principal,
    }
    
    with patch("tripsage.api.core.dependencies.get_principal_id") as mock_get_id:
        mock_get_id.return_value = "user123"
        
        client = TestClient(app)
        yield client
    
    # Clean up overrides
    app.dependency_overrides = {}


@pytest.fixture
def sample_activity_details() -> ActivityResponse:
    """Create sample activity details response."""
    return ActivityResponse(
        id="gmp_12345",
        name="Metropolitan Museum of Art",
        type="museum",
        location="1000 5th Ave, New York, NY 10028",
        date="2025-07-15",
        duration=180,
        price=25.0,
        rating=4.7,
        description="World's largest art museum with 2M+ works",
        images=["https://example.com/met1.jpg"],
        coordinates=ActivityCoordinates(lat=40.7794, lng=-73.9632),
        provider="Google Maps",
        availability="Open today 10AM-5PM",
        wheelchair_accessible=True,
        instant_confirmation=False,
    )


@pytest.fixture
def sample_saved_data() -> Dict[str, str]:
    """Create sample database save response."""
    return {
        "id": str(uuid.uuid4()),
        "user_id": "user123", 
        "activity_id": "gmp_12345",
        "trip_id": "trip_abc123",
        "created_at": datetime.now().isoformat(),
        "notes": "Must visit this amazing museum!",
        "activity_data": {
            "id": "gmp_12345",
            "name": "Metropolitan Museum of Art",
            "type": "museum",
            "location": "1000 5th Ave, New York, NY 10028",
            "date": "2025-07-15",
            "duration": 180,
            "price": 25.0,
            "rating": 4.7,
            "description": "World's largest art museum with 2M+ works",
            "images": ["https://example.com/met1.jpg"],
            "coordinates": {"lat": 40.7794, "lng": -73.9632},
            "provider": "Google Maps",
            "availability": "Open today 10AM-5PM",
            "wheelchair_accessible": True,
            "instant_confirmation": False,
        }
    }


class TestSaveActivityEndpoint:
    """Test POST /activities/save endpoint with authentication."""

    def test_save_activity_success(
        self,
        authenticated_client: TestClient,
        sample_activity_details: ActivityResponse,
        sample_saved_data: Dict[str, str],
    ):
        """Test successful activity save with complete flow."""
        request_data = {
            "activity_id": "gmp_12345",
            "trip_id": "trip_abc123",
            "notes": "Must visit this amazing museum!"
        }

        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            # Setup service mocks
            mock_service = AsyncMock()
            mock_service.save_activity.return_value = sample_saved_data
            mock_service.get_activity_details.return_value = sample_activity_details
            mock_get_service.return_value = mock_service

            # Execute request
            response = authenticated_client.post("/activities/save", json=request_data)

            # Verify response structure and content
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Actionable assertions for real-world usage
            assert data["activity_id"] == "gmp_12345"
            assert data["trip_id"] == "trip_abc123"
            assert data["user_id"] == "user123"
            assert data["notes"] == "Must visit this amazing museum!"
            assert "saved_at" in data
            
            # Verify nested activity details
            assert data["activity"]["name"] == "Metropolitan Museum of Art"
            assert data["activity"]["price"] == 25.0
            assert data["activity"]["rating"] == 4.7
            assert data["activity"]["wheelchair_accessible"] is True

            # Verify service calls with correct parameters
            mock_service.save_activity.assert_called_once_with(
                user_id="user123",
                activity_id="gmp_12345",
                trip_id="trip_abc123"
            )
            mock_service.get_activity_details.assert_called_once_with("gmp_12345")

    def test_save_activity_service_error(
        self,
        authenticated_client: TestClient,
    ):
        """Test activity save when service encounters error."""
        request_data = {
            "activity_id": "gmp_12345",
            "trip_id": "trip_abc123",
            "notes": "Test notes"
        }

        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.save_activity.side_effect = ActivityServiceError(
                "Activity gmp_12345 not found in provider",
                original_error=Exception("Provider error")
            )
            mock_get_service.return_value = mock_service

            response = authenticated_client.post("/activities/save", json=request_data)

            # Verify proper error handling
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "Failed to save activity" in data["detail"]

    def test_save_activity_unauthenticated(self, client: TestClient):
        """Test activity save without authentication fails properly."""
        request_data = {
            "activity_id": "gmp_12345",
            "trip_id": "trip_abc123",
            "notes": "Test notes"
        }
        
        response = client.post("/activities/save", json=request_data)

        # Should require authentication
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetSavedActivitiesEndpoint:
    """Test GET /activities/saved endpoint with authentication."""

    def test_get_saved_activities_success(
        self,
        authenticated_client: TestClient,
        sample_saved_data: Dict[str, str],
    ):
        """Test successful retrieval of saved activities."""
        saved_activities = [sample_saved_data]

        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_saved_activities.return_value = saved_activities
            mock_get_service.return_value = mock_service

            response = authenticated_client.get("/activities/saved")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure and content
            assert isinstance(data, list)
            assert len(data) == 1
            
            activity = data[0]
            assert activity["activity_id"] == "gmp_12345"
            assert activity["trip_id"] == "trip_abc123"
            assert activity["user_id"] == "user123"
            assert activity["activity"]["name"] == "Metropolitan Museum of Art"

            # Verify service called correctly
            mock_service.get_saved_activities.assert_called_once_with(
                user_id="user123",
                trip_id=None
            )

    def test_get_saved_activities_empty_result(self, authenticated_client: TestClient):
        """Test retrieving saved activities when user has none."""
        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_saved_activities.return_value = []
            mock_get_service.return_value = mock_service

            response = authenticated_client.get("/activities/saved")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Should return empty list
            assert isinstance(data, list)
            assert len(data) == 0

    def test_get_saved_activities_unauthenticated(self, client: TestClient):
        """Test retrieving saved activities without authentication."""
        response = client.get("/activities/saved")

        # Should require authentication
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestDeleteSavedActivityEndpoint:
    """Test DELETE /activities/saved/{activity_id} endpoint with authentication."""

    def test_delete_saved_activity_success(self, authenticated_client: TestClient):
        """Test successful deletion of saved activity."""
        activity_id = "gmp_12345"
        
        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.delete_saved_activity.return_value = True
            mock_get_service.return_value = mock_service

            response = authenticated_client.delete(f"/activities/saved/{activity_id}")

            assert response.status_code == status.HTTP_204_NO_CONTENT
            assert response.content == b""  # No content for 204

            # Verify service called correctly
            mock_service.delete_saved_activity.assert_called_once_with(
                user_id="user123",
                activity_id="gmp_12345"
            )

    def test_delete_saved_activity_not_found(self, authenticated_client: TestClient):
        """Test deletion when activity is not in user's saved activities."""
        activity_id = "gmp_nonexistent"
        
        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.delete_saved_activity.return_value = False
            mock_get_service.return_value = mock_service

            response = authenticated_client.delete(f"/activities/saved/{activity_id}")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert "not found" in data["detail"]
            assert activity_id in data["detail"]

    def test_delete_saved_activity_unauthenticated(self, client: TestClient):
        """Test deletion without authentication."""
        response = client.delete("/activities/saved/gmp_12345")

        # Should require authentication
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestRouterIntegration:
    """Test router-level integration and workflow testing."""

    def test_end_to_end_activity_workflow(
        self,
        authenticated_client: TestClient,
        sample_activity_details: ActivityResponse,
        sample_saved_data: Dict[str, str],
    ):
        """Test complete workflow: save → retrieve → delete activity."""
        activity_id = "gmp_workflow_test"
        
        # Update sample data for workflow
        workflow_saved_data = {**sample_saved_data, "activity_id": activity_id}
        workflow_activity_details = ActivityResponse(
            **sample_activity_details.model_dump(), id=activity_id
        )

        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.save_activity.return_value = workflow_saved_data
            mock_service.get_activity_details.return_value = workflow_activity_details
            mock_service.get_saved_activities.return_value = [workflow_saved_data]
            mock_service.delete_saved_activity.return_value = True
            mock_get_service.return_value = mock_service

            # Step 1: Save activity
            save_response = authenticated_client.post(
                "/activities/save",
                json={
                    "activity_id": activity_id,
                    "trip_id": "trip_workflow",
                    "notes": "End-to-end test activity"
                }
            )
            assert save_response.status_code == status.HTTP_200_OK
            
            # Step 2: Retrieve saved activities
            get_response = authenticated_client.get("/activities/saved")
            assert get_response.status_code == status.HTTP_200_OK
            activities = get_response.json()
            assert len(activities) == 1
            assert activities[0]["activity_id"] == activity_id
            
            # Step 3: Delete activity
            delete_response = authenticated_client.delete(f"/activities/saved/{activity_id}")
            assert delete_response.status_code == status.HTTP_204_NO_CONTENT
            
            # Verify all service methods were called correctly
            assert mock_service.save_activity.called
            assert mock_service.get_saved_activities.called
            assert mock_service.delete_saved_activity.called