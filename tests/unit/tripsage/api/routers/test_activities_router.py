"""
Comprehensive tests for Activities API router.

Tests cover:
- Activity search endpoint functionality
- Activity details retrieval
- Error handling for various failure scenarios
- HTTP status codes and response formats
- Input validation and edge cases
- Service integration and mocking
"""

from datetime import date
from unittest.mock import AsyncMock, patch
from typing import List

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import AsyncClient

from tripsage.api.schemas.requests.activities import (
    ActivitySearchRequest,
    SaveActivityRequest,
)
from tripsage.api.schemas.responses.activities import (
    ActivityResponse,
    ActivitySearchResponse,
    ActivityCoordinates,
    SavedActivityResponse,
)
from tripsage_core.exceptions.exceptions import CoreServiceError


class TestActivitySearchEndpoint:
    """Test /activities/search endpoint."""

    @pytest.fixture
    def sample_activity_response(self):
        """Create sample activity response."""
        return ActivityResponse(
            id="gmp_test123",
            name="Metropolitan Museum of Art",
            type="cultural",
            location="1000 5th Ave, New York, NY 10028",
            date="2025-07-15",
            duration=180,
            price=25.0,
            rating=4.6,
            description="World-renowned art museum with extensive collections",
            images=[],
            provider="Google Maps",
            availability="Open now",
            wheelchair_accessible=True,
            instant_confirmation=False,
            coordinates=ActivityCoordinates(lat=40.7794, lng=-73.9632)
        )

    @pytest.fixture
    def sample_search_response(self, sample_activity_response):
        """Create sample search response."""
        return ActivitySearchResponse(
            activities=[sample_activity_response],
            total=1,
            skip=0,
            limit=20,
            search_id="search_123",
            filters_applied={"destination": "New York, NY"},
            cached=False
        )

    @pytest.fixture
    def sample_search_request(self):
        """Create sample search request."""
        return ActivitySearchRequest(
            destination="New York, NY",
            start_date=date(2025, 7, 15),
            categories=["cultural"],
            rating=4.0,
            duration=300,
            wheelchair_accessible=False
        )

    async def test_search_activities_success(self, async_client: AsyncClient, sample_search_request, sample_search_response):
        """Test successful activity search."""
        with patch('tripsage.api.routers.activities.get_activity_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.search_activities.return_value = sample_search_response
            mock_get_service.return_value = mock_service
            
            response = await async_client.post(
                "/activities/search",
                json=sample_search_request.model_dump()
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["total"] == 1
            assert len(data["activities"]) == 1
            assert data["activities"][0]["name"] == "Metropolitan Museum of Art"
            assert data["activities"][0]["type"] == "cultural"
            assert data["activities"][0]["price"] == 25.0
            assert data["activities"][0]["rating"] == 4.6
            assert data["search_id"] == "search_123"
            
            # Verify service was called correctly
            mock_service.search_activities.assert_called_once()
            call_args = mock_service.search_activities.call_args[0][0]
            assert call_args.destination == "New York, NY"

    async def test_search_activities_empty_results(self, async_client: AsyncClient, sample_search_request):
        """Test activity search with no results."""
        empty_response = ActivitySearchResponse(
            activities=[],
            total=0,
            skip=0,
            limit=20,
            search_id="empty_search",
            filters_applied={"destination": "Remote Location"},
            cached=False
        )
        
        with patch('tripsage.api.routers.activities.get_activity_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.search_activities.return_value = empty_response
            mock_get_service.return_value = mock_service
            
            response = await async_client.post(
                "/activities/search",
                json=sample_search_request.model_dump()
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["total"] == 0
            assert len(data["activities"]) == 0
            assert data["search_id"] == "empty_search"

    async def test_search_activities_service_error(self, async_client: AsyncClient, sample_search_request):
        """Test activity search with service error."""
        with patch('tripsage.api.routers.activities.get_activity_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.search_activities.side_effect = CoreServiceError("Google Maps API error")
            mock_get_service.return_value = mock_service
            
            response = await async_client.post(
                "/activities/search",
                json=sample_search_request.model_dump()
            )
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            
            assert "Activity search failed" in data["detail"]
            assert "Google Maps API error" in data["detail"]

    async def test_search_activities_unexpected_error(self, async_client: AsyncClient, sample_search_request):
        """Test activity search with unexpected error."""
        with patch('tripsage.api.routers.activities.get_activity_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.search_activities.side_effect = Exception("Unexpected error")
            mock_get_service.return_value = mock_service
            
            response = await async_client.post(
                "/activities/search",
                json=sample_search_request.model_dump()
            )
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            
            assert "An unexpected error occurred" in data["detail"]
            assert "Unexpected error" not in data["detail"]  # Should not expose internal error

    async def test_search_activities_invalid_request_data(self, async_client: AsyncClient):
        """Test activity search with invalid request data."""
        invalid_request = {
            "destination": "",  # Empty destination
            "start_date": "invalid-date",  # Invalid date format
            "rating": 6.0  # Invalid rating (should be 0-5)
        }
        
        response = await async_client.post(
            "/activities/search",
            json=invalid_request
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_search_activities_missing_required_fields(self, async_client: AsyncClient):
        """Test activity search with missing required fields."""
        incomplete_request = {
            # Missing destination and start_date
            "categories": ["cultural"]
        }
        
        response = await async_client.post(
            "/activities/search",
            json=incomplete_request
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_search_activities_various_categories(self, async_client: AsyncClient, sample_search_response):
        """Test activity search with different category combinations."""
        categories_to_test = [
            ["cultural"],
            ["adventure", "outdoor"],
            ["food", "entertainment"],
            []  # No categories
        ]
        
        with patch('tripsage.api.routers.activities.get_activity_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.search_activities.return_value = sample_search_response
            mock_get_service.return_value = mock_service
            
            for categories in categories_to_test:
                request_data = {
                    "destination": "Test City",
                    "start_date": "2025-07-15",
                    "categories": categories
                }
                
                response = await async_client.post(
                    "/activities/search",
                    json=request_data
                )
                
                assert response.status_code == status.HTTP_200_OK


class TestActivityDetailsEndpoint:
    """Test /activities/{activity_id} endpoint."""

    @pytest.fixture
    def sample_activity_details(self):
        """Create sample activity details response."""
        return ActivityResponse(
            id="gmp_detailed123",
            name="Detailed Museum",
            type="cultural",
            location="456 Museum Ave, New York, NY",
            date="2025-07-15",
            duration=240,
            price=30.0,
            rating=4.8,
            description="An amazing museum with detailed collections and interactive exhibits",
            images=["image1.jpg", "image2.jpg"],
            provider="Google Maps",
            availability="Open now",
            wheelchair_accessible=True,
            instant_confirmation=False,
            coordinates=ActivityCoordinates(lat=40.7829, lng=-73.9654),
            meeting_point="Main entrance on 5th Avenue",
            languages=["English", "Spanish", "French"]
        )

    async def test_get_activity_details_success(self, async_client: AsyncClient, sample_activity_details):
        """Test successful activity details retrieval."""
        activity_id = "gmp_detailed123"
        
        with patch('tripsage.api.routers.activities.get_activity_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_activity_details.return_value = sample_activity_details
            mock_get_service.return_value = mock_service
            
            response = await async_client.get(f"/activities/{activity_id}")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["id"] == activity_id
            assert data["name"] == "Detailed Museum"
            assert data["type"] == "cultural"
            assert data["price"] == 30.0
            assert data["rating"] == 4.8
            assert data["wheelchair_accessible"] is True
            assert data["meeting_point"] == "Main entrance on 5th Avenue"
            assert len(data["languages"]) == 3
            
            # Verify service was called correctly
            mock_service.get_activity_details.assert_called_once_with(activity_id)

    async def test_get_activity_details_not_found(self, async_client: AsyncClient):
        """Test activity details when activity not found."""
        activity_id = "nonexistent_activity"
        
        with patch('tripsage.api.routers.activities.get_activity_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_activity_details.return_value = None
            mock_get_service.return_value = mock_service
            
            response = await async_client.get(f"/activities/{activity_id}")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            
            assert "not found" in data["detail"]
            assert activity_id in data["detail"]

    async def test_get_activity_details_service_error(self, async_client: AsyncClient):
        """Test activity details with service error."""
        activity_id = "error_activity"
        
        with patch('tripsage.api.routers.activities.get_activity_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_activity_details.side_effect = CoreServiceError("Place details API error")
            mock_get_service.return_value = mock_service
            
            response = await async_client.get(f"/activities/{activity_id}")
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            
            assert "Failed to get activity details" in data["detail"]

    async def test_get_activity_details_unexpected_error(self, async_client: AsyncClient):
        """Test activity details with unexpected error."""
        activity_id = "error_activity"
        
        with patch('tripsage.api.routers.activities.get_activity_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_activity_details.side_effect = Exception("Database connection lost")
            mock_get_service.return_value = mock_service
            
            response = await async_client.get(f"/activities/{activity_id}")
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            
            assert "An unexpected error occurred" in data["detail"]
            assert "Database connection lost" not in data["detail"]  # Should not expose internal error

    async def test_get_activity_details_invalid_id_format(self, async_client: AsyncClient):
        """Test activity details with various ID formats."""
        test_ids = [
            "gmp_123456",  # Google Maps format
            "custom_abc123",  # Custom format
            "123",  # Numeric
            "test-activity-id",  # With dashes
            "test_activity_id",  # With underscores
        ]
        
        with patch('tripsage.api.routers.activities.get_activity_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_activity_details.return_value = None
            mock_get_service.return_value = mock_service
            
            for activity_id in test_ids:
                response = await async_client.get(f"/activities/{activity_id}")
                
                # All should be valid ID formats, just not found
                assert response.status_code == status.HTTP_404_NOT_FOUND


class TestSaveActivityEndpoint:
    """Test /activities/save endpoint (not implemented)."""

    async def test_save_activity_not_implemented(self, async_client: AsyncClient):
        """Test save activity endpoint returns not implemented."""
        request_data = {
            "activity_id": "gmp_test123",
            "user_id": "user123",
            "notes": "Want to visit this museum"
        }
        
        response = await async_client.post(
            "/activities/save",
            json=request_data
        )
        
        assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
        data = response.json()
        
        assert "user authentication implementation" in data["detail"]

    async def test_save_activity_invalid_data(self, async_client: AsyncClient):
        """Test save activity with invalid data format."""
        invalid_data = {
            "invalid_field": "value"
        }
        
        response = await async_client.post(
            "/activities/save",
            json=invalid_data
        )
        
        # Should validate input before hitting the not implemented logic
        assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_501_NOT_IMPLEMENTED]


class TestGetSavedActivitiesEndpoint:
    """Test /activities/saved endpoint."""

    async def test_get_saved_activities_empty_list(self, async_client: AsyncClient):
        """Test get saved activities returns empty list."""
        response = await async_client.get("/activities/saved")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 0


class TestDeleteSavedActivityEndpoint:
    """Test /activities/saved/{activity_id} endpoint."""

    async def test_delete_saved_activity_not_implemented(self, async_client: AsyncClient):
        """Test delete saved activity endpoint returns not implemented."""
        activity_id = "gmp_test123"
        
        response = await async_client.delete(f"/activities/saved/{activity_id}")
        
        assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
        data = response.json()
        
        assert "user authentication implementation" in data["detail"]

    async def test_delete_saved_activity_various_ids(self, async_client: AsyncClient):
        """Test delete saved activity with various ID formats."""
        test_ids = [
            "gmp_123456",
            "custom_abc123",
            "123",
            "test-activity-id"
        ]
        
        for activity_id in test_ids:
            response = await async_client.delete(f"/activities/saved/{activity_id}")
            
            # All should return not implemented
            assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED


class TestRouterIntegration:
    """Test router-level integration."""

    async def test_router_mounting_and_paths(self, async_client: AsyncClient):
        """Test that all router paths are accessible."""
        # Test that paths exist (even if not fully implemented)
        test_cases = [
            ("POST", "/activities/search", {"destination": "Test", "start_date": "2025-07-15"}),
            ("GET", "/activities/test123", None),
            ("POST", "/activities/save", {"activity_id": "test"}),
            ("GET", "/activities/saved", None),
            ("DELETE", "/activities/saved/test123", None),
        ]
        
        for method, path, json_data in test_cases:
            if method == "POST":
                response = await async_client.post(path, json=json_data)
            elif method == "GET":
                response = await async_client.get(path)
            elif method == "DELETE":
                response = await async_client.delete(path)
            
            # Should not return 404 (path not found)
            assert response.status_code != status.HTTP_404_NOT_FOUND

    async def test_concurrent_requests(self, async_client: AsyncClient):
        """Test handling concurrent requests to activity endpoints."""
        import asyncio
        
        with patch('tripsage.api.routers.activities.get_activity_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.search_activities.return_value = ActivitySearchResponse(
                activities=[], total=0, skip=0, limit=20, search_id="concurrent_test",
                filters_applied={}, cached=False
            )
            mock_get_service.return_value = mock_service
            
            # Create multiple concurrent requests
            tasks = []
            for i in range(5):
                task = async_client.post(
                    "/activities/search",
                    json={
                        "destination": f"City {i}",
                        "start_date": "2025-07-15"
                    }
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks)
            
            # All requests should succeed
            for response in responses:
                assert response.status_code == status.HTTP_200_OK


class TestErrorHandling:
    """Test comprehensive error handling."""

    async def test_malformed_json(self, async_client: AsyncClient):
        """Test handling of malformed JSON in requests."""
        # Manually construct request with invalid JSON
        response = await async_client.post(
            "/activities/search",
            content="{'invalid': json}",  # Invalid JSON
            headers={"content-type": "application/json"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_missing_content_type(self, async_client: AsyncClient):
        """Test handling requests with missing content-type."""
        response = await async_client.post(
            "/activities/search",
            content='{"destination": "Test City", "start_date": "2025-07-15"}',
            # No content-type header
        )
        
        # FastAPI should handle this gracefully
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]

    async def test_large_request_payload(self, async_client: AsyncClient):
        """Test handling of unusually large request payloads."""
        large_request = {
            "destination": "Test City",
            "start_date": "2025-07-15",
            "categories": ["cultural"] * 1000,  # Very large categories list
            "notes": "x" * 10000  # Large notes field
        }
        
        with patch('tripsage.api.routers.activities.get_activity_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.search_activities.return_value = ActivitySearchResponse(
                activities=[], total=0, skip=0, limit=20, search_id="large_test",
                filters_applied={}, cached=False
            )
            mock_get_service.return_value = mock_service
            
            response = await async_client.post(
                "/activities/search",
                json=large_request
            )
            
            # Should handle large payloads gracefully
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]


class TestLogging:
    """Test logging functionality."""

    async def test_request_logging(self, async_client: AsyncClient):
        """Test that requests are properly logged."""
        with patch('tripsage.api.routers.activities.logger') as mock_logger, \
             patch('tripsage.api.routers.activities.get_activity_service') as mock_get_service:
            
            mock_service = AsyncMock()
            mock_service.search_activities.return_value = ActivitySearchResponse(
                activities=[], total=0, skip=0, limit=20, search_id="log_test",
                filters_applied={}, cached=False
            )
            mock_get_service.return_value = mock_service
            
            await async_client.post(
                "/activities/search",
                json={"destination": "Test City", "start_date": "2025-07-15"}
            )
            
            # Verify logging calls
            mock_logger.info.assert_called()
            
            # Check that destination is logged
            log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            assert any("Test City" in call for call in log_calls)

    async def test_error_logging(self, async_client: AsyncClient):
        """Test that errors are properly logged."""
        with patch('tripsage.api.routers.activities.logger') as mock_logger, \
             patch('tripsage.api.routers.activities.get_activity_service') as mock_get_service:
            
            mock_service = AsyncMock()
            mock_service.search_activities.side_effect = CoreServiceError("Test error")
            mock_get_service.return_value = mock_service
            
            await async_client.post(
                "/activities/search",
                json={"destination": "Test City", "start_date": "2025-07-15"}
            )
            
            # Verify error logging
            mock_logger.error.assert_called()
            
            # Check that error details are logged
            error_calls = [call.args[0] for call in mock_logger.error.call_args_list]
            assert any("Activity service error" in call for call in error_calls)