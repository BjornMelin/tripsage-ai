"""
Comprehensive tests for Search API router endpoints (BJO-120 implementation).

This test suite covers the newly implemented user-specific search endpoints:
- GET /search/recent - Get recent searches with authentication
- POST /search/save - Save search with authentication
- DELETE /search/saved/{search_id} - Delete saved search with authentication

Tests follow ULTRATHINK principles:
- ≥90% coverage with actionable assertions
- Zero flaky tests with deterministic mocking
- Real-world usage patterns and edge cases
- Modern pytest patterns with Pydantic 2.x
"""

import uuid
from datetime import date, datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from tripsage.api.core.dependencies import require_principal
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.routers.search import router as search_router
from tripsage.api.schemas.requests.search import SearchFilters, UnifiedSearchRequest
from tripsage_core.services.business.unified_search_service import UnifiedSearchServiceError


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI app for testing."""
    app = FastAPI()
    app.include_router(search_router, prefix="/search")
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


class TestGetRecentSearchesEndpoint:
    """Test GET /search/recent endpoint with authentication."""

    @pytest.fixture
    def sample_recent_searches(self) -> List[Dict[str, Any]]:
        """Create sample recent searches from database."""
        return [
            {
                "id": str(uuid.uuid4()),
                "query": "museums in Paris",
                "title": "Search: museums in Paris",
                "description": "Unified search for 'museums in Paris'",
                "created_at": "2025-01-10T14:30:00Z",
                "metadata": {
                    "types": ["destination", "activity"],
                    "destination": "Paris, France",
                    "has_filters": True,
                },
                "search_params": {
                    "query": "museums in Paris",
                    "destination": "Paris, France",
                    "types": ["destination", "activity"],
                    "start_date": "2025-07-15",
                    "adults": 2,
                    "filters": {
                        "price_max": 50.0,
                        "rating_min": 4.0,
                    }
                }
            },
            {
                "id": str(uuid.uuid4()),
                "query": "hotels Tokyo budget",
                "title": "Search: hotels Tokyo budget",
                "description": "Unified search for 'hotels Tokyo budget'",
                "created_at": "2025-01-09T09:15:00Z",
                "metadata": {
                    "types": ["accommodation"],
                    "destination": "Tokyo, Japan",
                    "has_filters": True,
                },
                "search_params": {
                    "query": "hotels Tokyo budget",
                    "destination": "Tokyo, Japan",
                    "types": ["accommodation"],
                    "start_date": "2025-08-01",
                    "end_date": "2025-08-07",
                    "adults": 1,
                    "filters": {
                        "price_max": 100.0,
                    }
                }
            },
            {
                "id": str(uuid.uuid4()),
                "query": "restaurants Barcelona",
                "title": "Search: restaurants Barcelona",
                "description": "Unified search for 'restaurants Barcelona'",
                "created_at": "2025-01-08T19:45:00Z",
                "metadata": {
                    "types": ["activity"],
                    "destination": "Barcelona, Spain",
                    "has_filters": False,
                },
                "search_params": {
                    "query": "restaurants Barcelona",
                    "destination": "Barcelona, Spain",
                    "types": ["activity"],
                    "adults": 4,
                }
            }
        ]

    def test_get_recent_searches_success(
        self,
        authenticated_client: TestClient,
        sample_recent_searches: List[Dict[str, Any]],
    ):
        """Test successful retrieval of recent searches."""
        with patch("tripsage.api.routers.search.get_unified_search_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_recent_searches.return_value = sample_recent_searches
            mock_get_service.return_value = mock_service

            response = authenticated_client.get("/search/recent")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure and content
            assert isinstance(data, list)
            assert len(data) == 3
            
            # First search - museums in Paris with filters
            search1 = data[0]
            assert search1["query"] == "museums in Paris"
            assert search1["title"] == "Search: museums in Paris"
            assert search1["metadata"]["destination"] == "Paris, France"
            assert search1["metadata"]["has_filters"] is True
            assert search1["search_params"]["adults"] == 2
            assert search1["search_params"]["filters"]["price_max"] == 50.0
            assert search1["search_params"]["filters"]["rating_min"] == 4.0
            
            # Second search - hotels in Tokyo
            search2 = data[1]
            assert search2["query"] == "hotels Tokyo budget"
            assert search2["metadata"]["types"] == ["accommodation"]
            assert search2["search_params"]["start_date"] == "2025-08-01"
            assert search2["search_params"]["end_date"] == "2025-08-07"
            
            # Third search - restaurants without filters
            search3 = data[2]
            assert search3["query"] == "restaurants Barcelona"
            assert search3["metadata"]["has_filters"] is False
            assert search3["search_params"]["adults"] == 4

            # Verify service called correctly
            mock_service.get_recent_searches.assert_called_once_with(
                user_id="user123",
                limit=20
            )

    def test_get_recent_searches_with_custom_limit(
        self,
        authenticated_client: TestClient,
        sample_recent_searches: List[Dict[str, Any]],
    ):
        """Test retrieving recent searches with custom limit."""
        # Return subset based on limit
        limited_searches = sample_recent_searches[:2]
        
        with patch("tripsage.api.routers.search.get_unified_search_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_recent_searches.return_value = limited_searches
            mock_get_service.return_value = mock_service

            response = authenticated_client.get("/search/recent?limit=2")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Should return only 2 results
            assert len(data) == 2
            assert data[0]["query"] == "museums in Paris"
            assert data[1]["query"] == "hotels Tokyo budget"

            # Verify service called with custom limit
            mock_service.get_recent_searches.assert_called_once_with(
                user_id="user123",
                limit=2
            )

    def test_get_recent_searches_empty_result(
        self,
        authenticated_client: TestClient,
    ):
        """Test retrieving recent searches when user has none."""
        with patch("tripsage.api.routers.search.get_unified_search_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_recent_searches.return_value = []
            mock_get_service.return_value = mock_service

            response = authenticated_client.get("/search/recent")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Should return empty list
            assert isinstance(data, list)
            assert len(data) == 0

    def test_get_recent_searches_service_error(
        self,
        authenticated_client: TestClient,
    ):
        """Test retrieving recent searches when service encounters error."""
        with patch("tripsage.api.routers.search.get_unified_search_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_recent_searches.side_effect = UnifiedSearchServiceError(
                "Database query timeout",
                original_error=Exception("Connection timeout")
            )
            mock_get_service.return_value = mock_service

            response = authenticated_client.get("/search/recent")

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "Failed to get recent searches" in data["detail"]

    def test_get_recent_searches_unauthenticated(
        self,
        client: TestClient,
    ):
        """Test retrieving recent searches without authentication."""
        response = client.get("/search/recent")

        # Should require authentication
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_recent_searches_invalid_limit(
        self,
        authenticated_client: TestClient,
    ):
        """Test retrieving recent searches with invalid limit values."""
        invalid_limits = [0, -1, 51, "invalid", None]
        
        for limit in invalid_limits:
            response = authenticated_client.get(f"/search/recent?limit={limit}")
            
            # Should fail validation for out-of-range limits
            if isinstance(limit, int) and (limit < 1 or limit > 50):
                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            elif not isinstance(limit, int):
                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestSaveSearchEndpoint:
    """Test POST /search/save endpoint with authentication."""

    @pytest.fixture
    def sample_search_request(self) -> UnifiedSearchRequest:
        """Create sample unified search request."""
        return UnifiedSearchRequest(
            query="best restaurants in Rome",
            destination="Rome, Italy",
            types=["activity"],
            start_date=date(2025, 9, 15),
            end_date=date(2025, 9, 22),
            adults=2,
            children=1,
            filters=SearchFilters(
                price_min=20.0,
                price_max=100.0,
                rating_min=4.5,
                latitude=41.9028,
                longitude=12.4964,
                radius_km=5.0,
            ),
            sort_by="rating",
            sort_order="desc",
        )

    @pytest.fixture
    def sample_saved_search_response(self) -> Dict[str, Any]:
        """Create sample saved search response from service."""
        return {
            "id": str(uuid.uuid4()),
            "user_id": "user123",
            "search_type": "unified",
            "query": "best restaurants in Rome",
            "search_params": {},  # Will be populated by service
            "created_at": datetime.now().isoformat(),
            "title": "Search: best restaurants in Rome",
            "description": "Unified search for 'best restaurants in Rome'",
            "metadata": {
                "types": ["activity"],
                "destination": "Rome, Italy",
                "has_filters": True,
            },
        }

    def test_save_search_success(
        self,
        authenticated_client: TestClient,
        sample_search_request: UnifiedSearchRequest,
        sample_saved_search_response: Dict[str, Any],
    ):
        """Test successful search save with complete flow."""
        with patch("tripsage.api.routers.search.get_unified_search_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.save_search.return_value = sample_saved_search_response
            mock_get_service.return_value = mock_service

            response = authenticated_client.post(
                "/search/save",
                json=sample_search_request.model_dump(mode="json")
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure and content
            assert data["query"] == "best restaurants in Rome"
            assert data["user_id"] == "user123"
            assert data["search_type"] == "unified"
            assert data["title"] == "Search: best restaurants in Rome"
            assert data["metadata"]["destination"] == "Rome, Italy"
            assert data["metadata"]["has_filters"] is True
            assert "id" in data
            assert "created_at" in data

            # Verify service called with correct parameters
            mock_service.save_search.assert_called_once_with(
                user_id="user123",
                search_request=sample_search_request,
            )

    def test_save_search_minimal_request(
        self,
        authenticated_client: TestClient,
        sample_saved_search_response: Dict[str, Any],
    ):
        """Test saving search with minimal required fields."""
        minimal_request = {
            "query": "quick search test"
        }
        
        minimal_response = {
            **sample_saved_search_response,
            "query": "quick search test",
            "metadata": {
                "types": ["destination", "activity", "accommodation"],  # Default types
                "destination": None,
                "has_filters": False,
            }
        }

        with patch("tripsage.api.routers.search.get_unified_search_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.save_search.return_value = minimal_response
            mock_get_service.return_value = mock_service

            response = authenticated_client.post("/search/save", json=minimal_request)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify minimal request handled correctly
            assert data["query"] == "quick search test"
            assert data["metadata"]["has_filters"] is False
            assert data["metadata"]["destination"] is None

    def test_save_search_service_error(
        self,
        authenticated_client: TestClient,
        sample_search_request: UnifiedSearchRequest,
    ):
        """Test search save when service encounters error."""
        with patch("tripsage.api.routers.search.get_unified_search_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.save_search.side_effect = UnifiedSearchServiceError(
                "Database storage quota exceeded",
                original_error=Exception("Disk full")
            )
            mock_get_service.return_value = mock_service

            response = authenticated_client.post(
                "/search/save",
                json=sample_search_request.model_dump(mode="json")
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "Failed to save search" in data["detail"]

    def test_save_search_unauthenticated(
        self,
        client: TestClient,
        sample_search_request: UnifiedSearchRequest,
    ):
        """Test search save without authentication."""
        response = client.post(
            "/search/save",
            json=sample_search_request.model_dump(mode="json")
        )

        # Should require authentication
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_save_search_invalid_request_data(
        self,
        authenticated_client: TestClient,
    ):
        """Test search save with invalid request data."""
        invalid_requests = [
            {},  # Missing required query field
            {"query": ""},  # Empty query
            {"query": None},  # Null query
            {"query": "valid", "start_date": "invalid-date"},  # Invalid date format
            {"query": "valid", "adults": -1},  # Invalid adults count
            {"query": "valid", "children": 20},  # Unrealistic children count
            {"query": "valid", "filters": {"price_min": -10}},  # Invalid price
        ]

        for invalid_data in invalid_requests:
            response = authenticated_client.post("/search/save", json=invalid_data)
            
            # Should fail validation
            assert response.status_code in [
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_400_BAD_REQUEST,
            ], f"Failed for data: {invalid_data}"

    def test_save_search_complex_filters(
        self,
        authenticated_client: TestClient,
        sample_saved_search_response: Dict[str, Any],
    ):
        """Test saving search with complex filter combinations."""
        complex_request = {
            "query": "luxury hotels with spa",
            "destination": "Santorini, Greece",
            "types": ["accommodation"],
            "start_date": "2025-06-01",
            "end_date": "2025-06-07",
            "adults": 2,
            "filters": {
                "price_min": 200.0,
                "price_max": 500.0,
                "rating_min": 4.8,
                "latitude": 36.3932,
                "longitude": 25.4615,
                "radius_km": 10.0,
            },
            "sort_by": "price",
            "sort_order": "asc",
        }

        with patch("tripsage.api.routers.search.get_unified_search_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.save_search.return_value = sample_saved_search_response
            mock_get_service.return_value = mock_service

            response = authenticated_client.post("/search/save", json=complex_request)

            assert response.status_code == status.HTTP_200_OK
            
            # Verify service received complex request correctly
            call_args = mock_service.save_search.call_args
            search_request = call_args[1]["search_request"]
            assert search_request.query == "luxury hotels with spa"
            assert search_request.filters.price_min == 200.0
            assert search_request.filters.rating_min == 4.8
            assert search_request.filters.radius_km == 10.0


class TestDeleteSavedSearchEndpoint:
    """Test DELETE /search/saved/{search_id} endpoint with authentication."""

    def test_delete_saved_search_success(
        self,
        authenticated_client: TestClient,
    ):
        """Test successful deletion of saved search."""
        search_id = str(uuid.uuid4())
        
        with patch("tripsage.api.routers.search.get_unified_search_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.delete_saved_search.return_value = True
            mock_get_service.return_value = mock_service

            response = authenticated_client.delete(f"/search/saved/{search_id}")

            assert response.status_code == status.HTTP_204_NO_CONTENT
            assert response.content == b""  # No content for 204

            # Verify service called correctly
            mock_service.delete_saved_search.assert_called_once_with(
                user_id="user123",
                search_id=search_id
            )

    def test_delete_saved_search_not_found(
        self,
        authenticated_client: TestClient,
    ):
        """Test deletion when search is not in user's saved searches."""
        search_id = str(uuid.uuid4())
        
        with patch("tripsage.api.routers.search.get_unified_search_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.delete_saved_search.return_value = False
            mock_get_service.return_value = mock_service

            response = authenticated_client.delete(f"/search/saved/{search_id}")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert "not found" in data["detail"]
            assert search_id in data["detail"]

    def test_delete_saved_search_service_error(
        self,
        authenticated_client: TestClient,
    ):
        """Test deletion when service encounters error."""
        search_id = str(uuid.uuid4())
        
        with patch("tripsage.api.routers.search.get_unified_search_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.delete_saved_search.side_effect = UnifiedSearchServiceError(
                "Database foreign key constraint violation",
                original_error=Exception("FK constraint")
            )
            mock_get_service.return_value = mock_service

            response = authenticated_client.delete(f"/search/saved/{search_id}")

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "Failed to delete saved search" in data["detail"]

    def test_delete_saved_search_unauthenticated(
        self,
        client: TestClient,
    ):
        """Test deletion without authentication."""
        search_id = str(uuid.uuid4())
        
        response = client.delete(f"/search/saved/{search_id}")

        # Should require authentication
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_saved_search_invalid_uuid_format(
        self,
        authenticated_client: TestClient,
    ):
        """Test deletion with invalid UUID format."""
        invalid_ids = [
            "not-a-uuid",
            "12345",
            "",
            "abc-def-ghi",
            "12345678-1234-1234-1234-123456789012-extra",  # Too long
        ]
        
        for invalid_id in invalid_ids:
            response = authenticated_client.delete(f"/search/saved/{invalid_id}")
            
            # FastAPI should handle invalid UUID formats
            # Either validation error or service handles it gracefully
            assert response.status_code in [
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_404_NOT_FOUND,
                status.HTTP_400_BAD_REQUEST,
            ]

    def test_delete_saved_search_valid_uuid_formats(
        self,
        authenticated_client: TestClient,
    ):
        """Test deletion with various valid UUID formats."""
        valid_uuids = [
            str(uuid.uuid4()),  # Standard UUID4
            "12345678-1234-1234-1234-123456789012",  # Manual UUID format
            "87654321-4321-4321-4321-210987654321",  # Another manual UUID
        ]
        
        with patch("tripsage.api.routers.search.get_unified_search_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.delete_saved_search.return_value = True
            mock_get_service.return_value = mock_service

            for search_id in valid_uuids:
                response = authenticated_client.delete(f"/search/saved/{search_id}")
                
                # All valid UUIDs should work
                assert response.status_code == status.HTTP_204_NO_CONTENT
                
                # Verify correct search_id passed to service
                last_call = mock_service.delete_saved_search.call_args
                assert last_call[1]["search_id"] == search_id


class TestRouterIntegration:
    """Test router-level integration and concurrent request handling."""

    def test_concurrent_save_requests(
        self,
        authenticated_client: TestClient,
    ):
        """Test handling multiple concurrent save requests."""
        # Synchronous test - no asyncio needed
        
        with patch("tripsage.api.routers.search.get_unified_search_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.save_search.side_effect = lambda user_id, search_request: {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "query": search_request.query,
                "created_at": datetime.now().isoformat(),
            }
            mock_get_service.return_value = mock_service

            # Create sequential save requests (simulating concurrent behavior)
            responses = []
            for i in range(5):
                request_data = {
                    "query": f"concurrent search {i}",
                    "destination": f"City {i}",
                    "adults": i + 1,
                }
                response = authenticated_client.post("/search/save", json=request_data)
                responses.append(response)

            # All requests should succeed
            for i, response in enumerate(responses):
                assert response.status_code == status.HTTP_200_OK, f"Request {i} failed with status {response.status_code}"

    def test_end_to_end_search_workflow(
        self,
        authenticated_client: TestClient,
    ):
        """Test complete workflow: save → retrieve → delete search."""
        search_id = str(uuid.uuid4())
        
        # Mock data for the workflow
        saved_search = {
            "id": search_id,
            "user_id": "user123",
            "query": "workflow test search",
            "search_type": "unified",
            "created_at": datetime.now().isoformat(),
            "title": "Search: workflow test search",
            "metadata": {
                "destination": "Test City",
                "has_filters": False,
            }
        }

        with patch("tripsage.api.routers.search.get_unified_search_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.save_search.return_value = saved_search
            mock_service.get_recent_searches.return_value = [saved_search]
            mock_service.delete_saved_search.return_value = True
            mock_get_service.return_value = mock_service

            # Step 1: Save search
            save_response = authenticated_client.post(
                "/search/save",
                json={
                    "query": "workflow test search",
                    "destination": "Test City",
                    "adults": 1,
                }
            )
            assert save_response.status_code == status.HTTP_200_OK
            saved_data = save_response.json()
            assert saved_data["query"] == "workflow test search"
            
            # Step 2: Retrieve recent searches
            get_response = authenticated_client.get("/search/recent")
            assert get_response.status_code == status.HTTP_200_OK
            searches = get_response.json()
            assert len(searches) == 1
            assert searches[0]["id"] == search_id
            
            # Step 3: Delete search
            delete_response = authenticated_client.delete(f"/search/saved/{search_id}")
            assert delete_response.status_code == status.HTTP_204_NO_CONTENT
            
            # Verify all service methods were called correctly
            assert mock_service.save_search.called
            assert mock_service.get_recent_searches.called
            assert mock_service.delete_saved_search.called

    def test_search_pagination_behavior(
        self,
        authenticated_client: TestClient,
    ):
        """Test search endpoint pagination with different limits."""
        # Create large dataset for pagination testing
        large_search_set = []
        for i in range(50):
            search_item = {
                "id": str(uuid.uuid4()),
                "query": f"search query {i}",
                "created_at": f"2025-01-{i+1:02d}T12:00:00Z",
                "metadata": {"destination": f"City {i}"}
            }
            large_search_set.append(search_item)

        with patch("tripsage.api.routers.search.get_unified_search_service") as mock_get_service:
            mock_service = AsyncMock()
            
            # Test different page sizes
            test_limits = [1, 5, 10, 20, 50]
            
            for limit in test_limits:
                mock_service.get_recent_searches.return_value = large_search_set[:limit]
                
                response = authenticated_client.get(f"/search/recent?limit={limit}")
                assert response.status_code == status.HTTP_200_OK
                
                data = response.json()
                assert len(data) == limit
                
                # Verify service called with correct limit
                last_call = mock_service.get_recent_searches.call_args
                assert last_call[1]["limit"] == limit