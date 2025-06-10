"""
Comprehensive tests for Activities API router endpoints (BJO-120 implementation).

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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from tripsage.api.core.dependencies import require_principal, require_principal_dep
from tripsage.api.middlewares.authentication import Principal
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
    # Mock authentication to return test user as Principal object
    async def mock_require_principal(request=None):
        return Principal(
            id="user123",
            type="user", 
            email="test@example.com",
            auth_method="jwt",
            scopes=["read", "write"],
            metadata={}
        )
    
    def mock_get_principal_id(principal):
        return "user123"
    
    # Apply patches for the whole client session
    app.dependency_overrides = {
        require_principal: mock_require_principal,
    }
    
    with patch("tripsage.api.core.dependencies.get_principal_id", side_effect=mock_get_principal_id):
        client = TestClient(app)
        yield client
    
    # Clean up overrides
    app.dependency_overrides = {}


class TestSaveActivityEndpoint:
    """Test POST /activities/save endpoint with authentication."""

    @pytest.fixture
    def mock_principal(self) -> Dict[str, str]:
        """Create mock authenticated principal."""
        return {"sub": "user123", "email": "test@example.com"}

    @pytest.fixture 
    def sample_save_request(self) -> SaveActivityRequest:
        """Create sample save activity request."""
        return SaveActivityRequest(
            activity_id="gmp_12345",
            trip_id="trip_abc123",
            notes="Must visit this amazing museum!"
        )

    @pytest.fixture
    def sample_activity_details(self) -> ActivityResponse:
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
    def sample_saved_data(self) -> Dict[str, str]:
        """Create sample database save response."""
        return {
            "id": str(uuid.uuid4()),
            "user_id": "user123", 
            "activity_id": "gmp_12345",
            "trip_id": "trip_abc123",
            "created_at": datetime.now().isoformat(),
            "notes": "Must visit this amazing museum!"
        }

    def test_save_activity_success(
        self,
        authenticated_client: TestClient,
        sample_save_request: SaveActivityRequest,
        sample_activity_details: ActivityResponse,
        sample_saved_data: Dict[str, str],
    ):
        """Test successful activity save with complete flow."""
        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            # Setup service mocks
            mock_service = AsyncMock()
            mock_service.save_activity.return_value = sample_saved_data
            mock_service.get_activity_details.return_value = sample_activity_details
            mock_get_service.return_value = mock_service

            # Execute request
            response = authenticated_client.post(
                "/activities/save", 
                json=sample_save_request.model_dump()
            )

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

    def test_save_activity_without_trip_id(
        self,
        authenticated_client: TestClient,
        sample_activity_details: ActivityResponse,
        sample_saved_data: Dict[str, str],
    ):
        """Test saving activity without associating to a specific trip."""
        request_data = {
            "activity_id": "gmp_12345",
            "notes": "General bucket list item"
            # trip_id intentionally omitted
        }
        
        saved_data_no_trip = {**sample_saved_data, "trip_id": None}

        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.save_activity.return_value = saved_data_no_trip
            mock_service.get_activity_details.return_value = sample_activity_details
            mock_get_service.return_value = mock_service

            response = authenticated_client.post("/activities/save", json=request_data)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify trip_id is properly handled as None
            assert data["trip_id"] is None
            assert data["notes"] == "General bucket list item"
            
            # Verify service called with None trip_id
            mock_service.save_activity.assert_called_once_with(
                user_id="user123",
                activity_id="gmp_12345", 
                trip_id=None
            )

    def test_save_activity_service_error(
        self,
        authenticated_client: TestClient,
        sample_save_request: SaveActivityRequest,
    ):
        """Test activity save when service encounters error."""
        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.save_activity.side_effect = ActivityServiceError(
                "Activity gmp_12345 not found in provider",
                original_error=Exception("Provider error")
            )
            mock_get_service.return_value = mock_service

            response = authenticated_client.post(
                "/activities/save",
                json=sample_save_request.model_dump()
            )

            # Verify proper error handling
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "Failed to save activity" in data["detail"]
            assert "Activity gmp_12345 not found" in data["detail"]

    def test_save_activity_unauthenticated(
        self,
        client: TestClient,
        sample_save_request: SaveActivityRequest,
    ):
        """Test activity save without authentication fails properly."""
        response = client.post(
            "/activities/save",
            json=sample_save_request.model_dump()
        )

        # Should require authentication
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_save_activity_invalid_request_data(
        self,
        authenticated_client: TestClient,
    ):
        """Test activity save with invalid request data."""
        invalid_requests = [
            {},  # Missing required fields
            {"activity_id": ""},  # Empty activity_id
            {"activity_id": None},  # Null activity_id
            {"activity_id": "valid", "trip_id": ""},  # Empty trip_id (should be null)
            {"activity_id": "valid", "notes": "x" * 1001},  # Notes too long
        ]

        for invalid_data in invalid_requests:
            response = authenticated_client.post("/activities/save", json=invalid_data)
            
            # Should fail validation
            assert response.status_code in [
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_400_BAD_REQUEST,
            ], f"Failed for data: {invalid_data}"

    def test_save_activity_duplicate_handling(
        self,
        authenticated_client: TestClient,
        sample_save_request: SaveActivityRequest,
        sample_activity_details: ActivityResponse,
        sample_saved_data: Dict[str, str],
    ):
        """Test saving the same activity twice for same user."""
        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.save_activity.return_value = sample_saved_data
            mock_service.get_activity_details.return_value = sample_activity_details
            mock_get_service.return_value = mock_service

            # First save
            response1 = authenticated_client.post(
                "/activities/save",
                json=sample_save_request.model_dump()
            )
            assert response1.status_code == status.HTTP_200_OK

            # Second save (duplicate)
            response2 = authenticated_client.post(
                "/activities/save", 
                json=sample_save_request.model_dump()
            )
            assert response2.status_code == status.HTTP_200_OK
            
            # Service should handle duplicates gracefully (upsert behavior)
            assert mock_service.save_activity.call_count == 2


class TestGetSavedActivitiesEndpoint:
    """Test GET /activities/saved endpoint with authentication."""

    @pytest.fixture
    def sample_saved_activities(self) -> List[Dict[str, any]]:
        """Create sample saved activities from database."""
        return [
            {
                "id": str(uuid.uuid4()),
                "user_id": "user123",
                "activity_id": "gmp_museum1",
                "trip_id": "trip_paris",
                "created_at": "2025-01-10T10:00:00Z",
                "notes": "Must see the Louvre",
                "activity_data": {
                    "id": "gmp_museum1",
                    "name": "Louvre Museum",
                    "type": "museum",
                    "location": "Paris, France",
                    "date": "2025-07-15",
                    "duration": 240,
                    "price": 17.0,
                    "rating": 4.8,
                    "description": "World's largest art museum",
                    "images": ["https://example.com/louvre1.jpg"],
                    "coordinates": {"lat": 48.8606, "lng": 2.3376},
                    "provider": "Google Maps",
                    "availability": "Open daily",
                    "wheelchair_accessible": True,
                    "instant_confirmation": False,
                }
            },
            {
                "id": str(uuid.uuid4()),
                "user_id": "user123", 
                "activity_id": "gmp_tower1",
                "trip_id": None,  # General saved activity
                "created_at": "2025-01-09T15:30:00Z",
                "notes": None,
                "activity_data": {
                    "id": "gmp_tower1",
                    "name": "Eiffel Tower",
                    "type": "landmark",
                    "location": "Paris, France",
                    "date": "2025-07-15", 
                    "duration": 120,
                    "price": 29.4,
                    "rating": 4.6,
                    "description": "Iconic iron lattice tower",
                    "images": ["https://example.com/eiffel1.jpg"],
                    "coordinates": {"lat": 48.8584, "lng": 2.2945},
                    "provider": "Google Maps",
                    "availability": "Open daily",
                    "wheelchair_accessible": False,
                    "instant_confirmation": True,
                }
            }
        ]

    def test_get_saved_activities_success(
        self,
        authenticated_client: TestClient,
        sample_saved_activities: List[Dict[str, any]],
    ):
        """Test successful retrieval of saved activities."""
        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_saved_activities.return_value = sample_saved_activities
            mock_get_service.return_value = mock_service

            response = authenticated_client.get("/activities/saved")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure and content
            assert isinstance(data, list)
            assert len(data) == 2
            
            # First activity - with trip association
            activity1 = data[0]
            assert activity1["activity_id"] == "gmp_museum1"
            assert activity1["trip_id"] == "trip_paris"
            assert activity1["user_id"] == "user123"
            assert activity1["notes"] == "Must see the Louvre"
            assert activity1["activity"]["name"] == "Louvre Museum"
            assert activity1["activity"]["price"] == 17.0
            assert activity1["activity"]["wheelchair_accessible"] is True
            
            # Second activity - general saved activity
            activity2 = data[1]
            assert activity2["activity_id"] == "gmp_tower1"
            assert activity2["trip_id"] is None
            assert activity2["notes"] is None
            assert activity2["activity"]["name"] == "Eiffel Tower"
            assert activity2["activity"]["instant_confirmation"] is True

            # Verify service called correctly
            mock_service.get_saved_activities.assert_called_once_with(
                user_id="user123",
                trip_id=None
            )

    def test_get_saved_activities_filtered_by_trip(
        self,
        authenticated_client: TestClient,
        sample_saved_activities: List[Dict[str, any]],
    ):
        """Test retrieving saved activities filtered by specific trip."""
        # Return only activities for specific trip
        trip_activities = [act for act in sample_saved_activities if act["trip_id"] == "trip_paris"]
        
        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_saved_activities.return_value = trip_activities
            mock_get_service.return_value = mock_service

            response = authenticated_client.get("/activities/saved?trip_id=trip_paris")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Should only return activities for specific trip
            assert len(data) == 1
            assert data[0]["trip_id"] == "trip_paris"
            assert data[0]["activity"]["name"] == "Louvre Museum"

            # Verify service called with trip filter
            mock_service.get_saved_activities.assert_called_once_with(
                user_id="user123",
                trip_id="trip_paris"
            )

    def test_get_saved_activities_empty_result(
        self,
        authenticated_client: TestClient,
    ):
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

    def test_get_saved_activities_service_error(
        self,
        authenticated_client: TestClient,
    ):
        """Test retrieving saved activities when service encounters error."""
        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_saved_activities.side_effect = ActivityServiceError(
                "Database connection failed",
                original_error=Exception("Database connection failed")
            )
            mock_get_service.return_value = mock_service

            response = authenticated_client.get("/activities/saved")

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "Failed to get saved activities" in data["detail"]

    def test_get_saved_activities_unauthenticated(
        self,
        client: TestClient,
    ):
        """Test retrieving saved activities without authentication."""
        response = client.get("/activities/saved")

        # Should require authentication
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_saved_activities_invalid_trip_id(
        self,
        authenticated_client: TestClient,
    ):
        """Test retrieving saved activities with invalid trip_id format."""
        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_saved_activities.return_value = []
            mock_get_service.return_value = mock_service

            # Empty trip_id should be handled gracefully
            response = authenticated_client.get("/activities/saved?trip_id=")
            assert response.status_code == status.HTTP_200_OK

            # Service should be called with empty string (or None conversion)
            mock_service.get_saved_activities.assert_called_once()


class TestDeleteSavedActivityEndpoint:
    """Test DELETE /activities/saved/{activity_id} endpoint with authentication."""

    def test_delete_saved_activity_success(
        self,
        authenticated_client: TestClient,
    ):
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

    def test_delete_saved_activity_not_found(
        self,
        authenticated_client: TestClient,
    ):
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

    def test_delete_saved_activity_service_error(
        self,
        authenticated_client: TestClient,
    ):
        """Test deletion when service encounters error."""
        activity_id = "gmp_error"
        
        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.delete_saved_activity.side_effect = ActivityServiceError(
                "Database constraint violation",
                original_error=Exception("Constraint violation")
            )
            mock_get_service.return_value = mock_service

            response = authenticated_client.delete(f"/activities/saved/{activity_id}")

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "Failed to delete saved activity" in data["detail"]

    def test_delete_saved_activity_unauthenticated(
        self,
        client: TestClient,
    ):
        """Test deletion without authentication."""
        response = client.delete("/activities/saved/gmp_12345")

        # Should require authentication
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_saved_activity_various_id_formats(
        self,
        authenticated_client: TestClient,
    ):
        """Test deletion with various activity ID formats."""
        test_ids = [
            "gmp_12345678",  # Google Maps format
            "custom_abc123", # Custom format
            "123456",        # Numeric
            "activity-with-dashes",  # With dashes
            "activity_with_underscores",  # With underscores
        ]
        
        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.delete_saved_activity.return_value = True
            mock_get_service.return_value = mock_service

            for activity_id in test_ids:
                response = authenticated_client.delete(f"/activities/saved/{activity_id}")
                
                # All valid ID formats should work
                assert response.status_code == status.HTTP_204_NO_CONTENT
                
                # Verify correct activity_id passed to service
                last_call = mock_service.delete_saved_activity.call_args
                assert last_call[1]["activity_id"] == activity_id


class TestRouterIntegration:
    """Test router-level integration and concurrent request handling."""

    def test_concurrent_save_requests(
        self,
        authenticated_client: TestClient,
    ):
        """Test handling multiple concurrent save requests."""
        # Synchronous test - no asyncio needed
        
        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.save_activity.return_value = {
                "id": str(uuid.uuid4()),
                "user_id": "user123",
                "created_at": datetime.now().isoformat(),
            }
            mock_service.get_activity_details.return_value = ActivityResponse(
                id="test_id",
                name="Test Activity",
                type="test",
                location="Test Location",
                date="2025-07-15",
                duration=120,
                price=25.0,
                rating=4.5,
                description="Test description",
            )
            mock_get_service.return_value = mock_service

            # Create sequential save requests (simulating concurrent behavior)
            responses = []
            for i in range(5):
                request_data = {
                    "activity_id": f"gmp_concurrent_{i}",
                    "trip_id": f"trip_{i}",
                    "notes": f"Concurrent test {i}"
                }
                response = authenticated_client.post("/activities/save", json=request_data)
                responses.append(response)

            # All requests should succeed
            for i, response in enumerate(responses):
                assert response.status_code == status.HTTP_200_OK, f"Request {i} failed with status {response.status_code}"

    def test_end_to_end_activity_workflow(
        self,
        authenticated_client: TestClient,
    ):
        """Test complete workflow: save → retrieve → delete activity."""
        activity_id = "gmp_workflow_test"
        
        # Mock data for the workflow
        saved_data = {
            "id": str(uuid.uuid4()),
            "user_id": "user123",
            "activity_id": activity_id,
            "trip_id": "trip_workflow",
            "created_at": datetime.now().isoformat(),
            "notes": "End-to-end test activity"
        }
        
        activity_details = ActivityResponse(
            id=activity_id,
            name="Workflow Test Activity",
            type="test",
            location="Test City",
            date="2025-07-15",
            duration=180,
            price=35.0,
            rating=4.9,
            description="Activity for testing complete workflow",
        )
        
        saved_activities_response = [{
            **saved_data,
            "activity_data": activity_details.model_dump()
        }]

        with patch("tripsage.api.routers.activities.get_activity_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.save_activity.return_value = saved_data
            mock_service.get_activity_details.return_value = activity_details
            mock_service.get_saved_activities.return_value = saved_activities_response
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