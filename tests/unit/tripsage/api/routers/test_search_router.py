"""
Comprehensive tests for Search API router.

Tests cover:
- Unified search endpoint functionality
- Search suggestions endpoint
- Error handling for various failure scenarios
- HTTP status codes and response formats
- Input validation and query parameters
- Service integration and mocking
- Search history endpoints (not implemented)
"""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from tripsage.api.schemas.requests.search import (
    SearchFilters,
    UnifiedSearchRequest,
)
from tripsage.api.schemas.responses.search import (
    SearchFacet,
    SearchMetadata,
    SearchResultItem,
    UnifiedSearchResponse,
)
from tripsage_core.services.business.unified_search_service import (
    UnifiedSearchServiceError,
)


class TestUnifiedSearchEndpoint:
    """Test /search/unified endpoint."""

    @pytest.fixture
    def sample_search_result(self):
        """Create sample search result item."""
        return SearchResultItem(
            id="result_123",
            type="activity",
            title="Metropolitan Museum of Art",
            description="World-renowned art museum with extensive collections",
            price=25.0,
            currency="USD",
            location="New York, NY",
            rating=4.6,
            relevance_score=0.95,
            match_reasons=["High rating match", "Location match"],
            quick_actions=[
                {"action": "view", "label": "View Details"},
                {"action": "book", "label": "Book Now"},
            ],
            metadata={
                "activity_type": "cultural",
                "duration": 180,
                "provider": "Google Maps",
            },
        )

    @pytest.fixture
    def sample_search_metadata(self):
        """Create sample search metadata."""
        return SearchMetadata(
            total_results=10,
            returned_results=10,
            search_time_ms=250,
            search_id="search_abc123",
            providers_queried=["destination", "activity", "accommodation"],
            provider_errors=None,
        )

    @pytest.fixture
    def sample_search_facet(self):
        """Create sample search facet."""
        return SearchFacet(
            field="type",
            label="Type",
            type="terms",
            values=[
                {"value": "activity", "label": "Activities", "count": 5},
                {"value": "destination", "label": "Destinations", "count": 3},
                {"value": "accommodation", "label": "Hotels", "count": 2},
            ],
        )

    @pytest.fixture
    def sample_unified_response(
        self, sample_search_result, sample_search_metadata, sample_search_facet
    ):
        """Create sample unified search response."""
        return UnifiedSearchResponse(
            results=[sample_search_result],
            facets=[sample_search_facet],
            metadata=sample_search_metadata,
            results_by_type={
                "activity": [sample_search_result],
                "destination": [],
                "accommodation": [],
            },
            errors=None,
        )

    @pytest.fixture
    def sample_search_request(self):
        """Create sample unified search request."""
        return UnifiedSearchRequest(
            query="museums in New York",
            destination="New York, NY",
            start_date=date(2025, 7, 15),
            end_date=date(2025, 7, 20),
            types=["destination", "activity"],
            adults=2,
            children=0,
            infants=0,
            sort_by="relevance",
            sort_order="desc",
        )

    async def test_unified_search_success(
        self, async_client: AsyncClient, sample_search_request, sample_unified_response
    ):
        """Test successful unified search."""
        with patch(
            "tripsage.api.routers.search.get_unified_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.unified_search.return_value = sample_unified_response
            mock_get_service.return_value = mock_service

            response = await async_client.post(
                "/search/unified", json=sample_search_request.model_dump()
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert len(data["results"]) == 1
            assert data["results"][0]["title"] == "Metropolitan Museum of Art"
            assert data["results"][0]["type"] == "activity"
            assert data["results"][0]["price"] == 25.0
            assert data["results"][0]["rating"] == 4.6
            assert data["metadata"]["total_results"] == 10
            assert data["metadata"]["search_time_ms"] == 250
            assert len(data["facets"]) == 1
            assert data["facets"][0]["field"] == "type"

            # Verify service was called correctly
            mock_service.unified_search.assert_called_once()

    async def test_unified_search_empty_results(
        self, async_client: AsyncClient, sample_search_request
    ):
        """Test unified search with no results."""
        empty_response = UnifiedSearchResponse(
            results=[],
            facets=[],
            metadata=SearchMetadata(
                total_results=0,
                returned_results=0,
                search_time_ms=100,
                search_id="empty_search",
                providers_queried=["activity"],
            ),
            results_by_type={"activity": []},
            errors=None,
        )

        with patch(
            "tripsage.api.routers.search.get_unified_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.unified_search.return_value = empty_response
            mock_get_service.return_value = mock_service

            response = await async_client.post(
                "/search/unified", json=sample_search_request.model_dump()
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert len(data["results"]) == 0
            assert data["metadata"]["total_results"] == 0
            assert data["metadata"]["search_id"] == "empty_search"

    async def test_unified_search_with_filters(self, async_client: AsyncClient):
        """Test unified search with filters."""
        request_with_filters = UnifiedSearchRequest(
            query="hotels near museum",
            destination="Paris, France",
            types=["accommodation", "activity"],
            filters=SearchFilters(
                price_min=50.0,
                price_max=200.0,
                rating_min=4.0,
                latitude=48.8566,
                longitude=2.3522,
                radius_km=5.0,
            ),
        )

        empty_response = UnifiedSearchResponse(
            results=[],
            facets=[],
            metadata=SearchMetadata(
                total_results=0,
                returned_results=0,
                search_time_ms=150,
                search_id="filtered_search",
                providers_queried=["accommodation", "activity"],
            ),
            results_by_type={},
            errors=None,
        )

        with patch(
            "tripsage.api.routers.search.get_unified_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.unified_search.return_value = empty_response
            mock_get_service.return_value = mock_service

            response = await async_client.post(
                "/search/unified", json=request_with_filters.model_dump()
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Verify filters were passed to service
            call_args = mock_service.unified_search.call_args[0][0]
            assert call_args.filters.price_min == 50.0
            assert call_args.filters.price_max == 200.0
            assert call_args.filters.rating_min == 4.0

    async def test_unified_search_service_error(
        self, async_client: AsyncClient, sample_search_request
    ):
        """Test unified search with service error."""
        with patch(
            "tripsage.api.routers.search.get_unified_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.unified_search.side_effect = UnifiedSearchServiceError(
                "External API timeout"
            )
            mock_get_service.return_value = mock_service

            response = await async_client.post(
                "/search/unified", json=sample_search_request.model_dump()
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()

            assert "Search failed" in data["detail"]
            assert "External API timeout" in data["detail"]

    async def test_unified_search_unexpected_error(
        self, async_client: AsyncClient, sample_search_request
    ):
        """Test unified search with unexpected error."""
        with patch(
            "tripsage.api.routers.search.get_unified_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.unified_search.side_effect = Exception(
                "Database connection lost"
            )
            mock_get_service.return_value = mock_service

            response = await async_client.post(
                "/search/unified", json=sample_search_request.model_dump()
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()

            assert "An unexpected error occurred" in data["detail"]
            assert (
                "Database connection lost" not in data["detail"]
            )  # Should not expose internal error

    async def test_unified_search_invalid_request_data(self, async_client: AsyncClient):
        """Test unified search with invalid request data."""
        invalid_request = {
            "query": "",  # Empty query
            "start_date": "invalid-date",  # Invalid date format
            "adults": -1,  # Invalid adults count
            "sort_order": "invalid",  # Invalid sort order
        }

        response = await async_client.post("/search/unified", json=invalid_request)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_unified_search_missing_required_fields(
        self, async_client: AsyncClient
    ):
        """Test unified search with missing required fields."""
        incomplete_request = {
            # Missing query field
            "destination": "New York, NY"
        }

        response = await async_client.post("/search/unified", json=incomplete_request)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_unified_search_various_types(
        self, async_client: AsyncClient, sample_unified_response
    ):
        """Test unified search with different type combinations."""
        type_combinations = [
            ["destination"],
            ["activity"],
            ["accommodation"],
            ["destination", "activity"],
            ["activity", "accommodation"],
            ["destination", "activity", "accommodation"],
            [],  # No types specified
        ]

        with patch(
            "tripsage.api.routers.search.get_unified_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.unified_search.return_value = sample_unified_response
            mock_get_service.return_value = mock_service

            for types in type_combinations:
                request_data = {
                    "query": "test search",
                    "destination": "Test City",
                    "types": types,
                }

                response = await async_client.post("/search/unified", json=request_data)

                assert response.status_code == status.HTTP_200_OK

    async def test_unified_search_with_provider_errors(self, async_client: AsyncClient):
        """Test unified search with provider errors."""
        response_with_errors = UnifiedSearchResponse(
            results=[],
            facets=[],
            metadata=SearchMetadata(
                total_results=0,
                returned_results=0,
                search_time_ms=500,
                search_id="error_search",
                providers_queried=["activity", "accommodation"],
                provider_errors={"accommodation": "API rate limit exceeded"},
            ),
            results_by_type={"activity": []},
            errors={"accommodation": "API rate limit exceeded"},
        )

        with patch(
            "tripsage.api.routers.search.get_unified_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.unified_search.return_value = response_with_errors
            mock_get_service.return_value = mock_service

            request_data = {
                "query": "hotels and activities",
                "destination": "Test City",
                "types": ["activity", "accommodation"],
            }

            response = await async_client.post("/search/unified", json=request_data)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "errors" in data
            assert "accommodation" in data["errors"]
            assert "API rate limit exceeded" in data["errors"]["accommodation"]


class TestSearchSuggestionsEndpoint:
    """Test /search/suggest endpoint."""

    async def test_search_suggestions_success(self, async_client: AsyncClient):
        """Test successful search suggestions."""
        mock_suggestions = [
            "Paris, France",
            "museums in Paris",
            "Paris restaurants",
            "Paris tours",
            "Paris hotels",
        ]

        with patch(
            "tripsage.api.routers.search.get_unified_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_search_suggestions.return_value = mock_suggestions
            mock_get_service.return_value = mock_service

            response = await async_client.get("/search/suggest?query=paris&limit=5")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert isinstance(data, list)
            assert len(data) == 5
            assert "Paris, France" in data
            assert "museums in Paris" in data

            # Verify service was called correctly
            mock_service.get_search_suggestions.assert_called_once_with("paris", 5)

    async def test_search_suggestions_empty_query(self, async_client: AsyncClient):
        """Test search suggestions with empty query."""
        response = await async_client.get("/search/suggest?query=&limit=5")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_search_suggestions_missing_query(self, async_client: AsyncClient):
        """Test search suggestions with missing query parameter."""
        response = await async_client.get("/search/suggest?limit=5")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_search_suggestions_invalid_limit(self, async_client: AsyncClient):
        """Test search suggestions with invalid limit values."""
        test_cases = [
            (
                "?query=test&limit=0",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ),  # Below minimum
            (
                "?query=test&limit=25",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ),  # Above maximum
            ("?query=test&limit=-5", status.HTTP_422_UNPROCESSABLE_ENTITY),  # Negative
            (
                "?query=test&limit=abc",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ),  # Non-numeric
        ]

        for query_params, expected_status in test_cases:
            response = await async_client.get(f"/search/suggest{query_params}")
            assert response.status_code == expected_status

    async def test_search_suggestions_default_limit(self, async_client: AsyncClient):
        """Test search suggestions with default limit."""
        mock_suggestions = ["suggestion"] * 10

        with patch(
            "tripsage.api.routers.search.get_unified_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_search_suggestions.return_value = mock_suggestions
            mock_get_service.return_value = mock_service

            response = await async_client.get("/search/suggest?query=test")

            assert response.status_code == status.HTTP_200_OK

            # Verify default limit of 10 was used
            mock_service.get_search_suggestions.assert_called_once_with("test", 10)

    async def test_search_suggestions_various_queries(self, async_client: AsyncClient):
        """Test search suggestions with various query patterns."""
        test_queries = [
            "new",
            "new york",
            "new york restaurants",
            "things to do",
            "hotels near",
            "123",  # Numeric
            "café",  # Unicode
            "a",  # Single character
            "x" * 100,  # Maximum length
        ]

        with patch(
            "tripsage.api.routers.search.get_unified_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_search_suggestions.return_value = ["suggestion"]
            mock_get_service.return_value = mock_service

            for query in test_queries:
                response = await async_client.get(
                    f"/search/suggest?query={query}&limit=5"
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert isinstance(data, list)

    async def test_search_suggestions_service_error(self, async_client: AsyncClient):
        """Test search suggestions with service error."""
        with patch(
            "tripsage.api.routers.search.get_unified_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_search_suggestions.side_effect = UnifiedSearchServiceError(
                "Suggestion service down"
            )
            mock_get_service.return_value = mock_service

            response = await async_client.get("/search/suggest?query=test&limit=5")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()

            assert "Failed to get suggestions" in data["detail"]
            assert "Suggestion service down" in data["detail"]

    async def test_search_suggestions_unexpected_error(self, async_client: AsyncClient):
        """Test search suggestions with unexpected error."""
        with patch(
            "tripsage.api.routers.search.get_unified_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_search_suggestions.side_effect = Exception(
                "Redis connection failed"
            )
            mock_get_service.return_value = mock_service

            response = await async_client.get("/search/suggest?query=test&limit=5")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()

            assert "An unexpected error occurred" in data["detail"]
            assert (
                "Redis connection failed" not in data["detail"]
            )  # Should not expose internal error


class TestRecentSearchesEndpoint:
    """Test /search/recent endpoint (not implemented)."""

    async def test_get_recent_searches_empty_list(self, async_client: AsyncClient):
        """Test get recent searches returns empty list."""
        response = await async_client.get("/search/recent")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 0


class TestSaveSearchEndpoint:
    """Test /search/save endpoint (not implemented)."""

    async def test_save_search_not_implemented(self, async_client: AsyncClient):
        """Test save search endpoint returns not implemented."""
        request_data = {
            "query": "museums in paris",
            "destination": "Paris, France",
            "types": ["activity"],
        }

        response = await async_client.post("/search/save", json=request_data)

        assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
        data = response.json()

        assert "user authentication implementation" in data["detail"]

    async def test_save_search_invalid_data(self, async_client: AsyncClient):
        """Test save search with invalid data format."""
        invalid_data = {"invalid_field": "value"}

        response = await async_client.post("/search/save", json=invalid_data)

        # Should validate input before hitting the not implemented logic
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_501_NOT_IMPLEMENTED,
        ]


class TestDeleteSavedSearchEndpoint:
    """Test /search/saved/{search_id} endpoint."""

    async def test_delete_saved_search_not_implemented(self, async_client: AsyncClient):
        """Test delete saved search endpoint returns not implemented."""
        search_id = "search_123"

        response = await async_client.delete(f"/search/saved/{search_id}")

        assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
        data = response.json()

        assert "user authentication implementation" in data["detail"]

    async def test_delete_saved_search_various_ids(self, async_client: AsyncClient):
        """Test delete saved search with various ID formats."""
        test_ids = ["search_123456", "abc123", "123", "test-search-id"]

        for search_id in test_ids:
            response = await async_client.delete(f"/search/saved/{search_id}")

            # All should return not implemented
            assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED


class TestRouterIntegration:
    """Test router-level integration."""

    async def test_router_mounting_and_paths(self, async_client: AsyncClient):
        """Test that all router paths are accessible."""
        # Test that paths exist (even if not fully implemented)
        test_cases = [
            ("POST", "/search/unified", {"query": "test"}),
            ("GET", "/search/suggest?query=test", None),
            ("GET", "/search/recent", None),
            ("POST", "/search/save", {"query": "test"}),
            ("DELETE", "/search/saved/test123", None),
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
        """Test handling concurrent requests to search endpoints."""
        import asyncio

        with patch(
            "tripsage.api.routers.search.get_unified_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.unified_search.return_value = UnifiedSearchResponse(
                results=[],
                facets=[],
                metadata=SearchMetadata(
                    total_results=0,
                    returned_results=0,
                    search_time_ms=100,
                    search_id="concurrent",
                    providers_queried=[],
                ),
                results_by_type={},
                errors=None,
            )
            mock_get_service.return_value = mock_service

            # Create multiple concurrent requests
            tasks = []
            for i in range(5):
                task = async_client.post(
                    "/search/unified",
                    json={"query": f"test query {i}", "destination": f"City {i}"},
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks)

            # All requests should succeed
            for response in responses:
                assert response.status_code == status.HTTP_200_OK


class TestInputValidation:
    """Test comprehensive input validation."""

    async def test_query_length_validation(self, async_client: AsyncClient):
        """Test query length validation for suggestions endpoint."""
        test_cases = [
            ("", status.HTTP_422_UNPROCESSABLE_ENTITY),  # Too short
            ("a", status.HTTP_200_OK),  # Minimum length
            ("x" * 100, status.HTTP_200_OK),  # Maximum length
            ("x" * 101, status.HTTP_422_UNPROCESSABLE_ENTITY),  # Too long
        ]

        with patch(
            "tripsage.api.routers.search.get_unified_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_search_suggestions.return_value = ["suggestion"]
            mock_get_service.return_value = mock_service

            for query, expected_status in test_cases:
                response = await async_client.get(
                    f"/search/suggest?query={query}&limit=5"
                )
                assert response.status_code == expected_status

    async def test_limit_boundary_validation(self, async_client: AsyncClient):
        """Test limit boundary validation for suggestions endpoint."""
        with patch(
            "tripsage.api.routers.search.get_unified_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_search_suggestions.return_value = ["suggestion"]
            mock_get_service.return_value = mock_service

            # Test boundary values
            test_cases = [
                (1, status.HTTP_200_OK),  # Minimum
                (20, status.HTTP_200_OK),  # Maximum
                (10, status.HTTP_200_OK),  # Default
            ]

            for limit, expected_status in test_cases:
                response = await async_client.get(
                    f"/search/suggest?query=test&limit={limit}"
                )
                assert response.status_code == expected_status

    async def test_special_characters_in_query(self, async_client: AsyncClient):
        """Test handling of special characters in search queries."""
        special_queries = [
            "café",  # Unicode
            "bücher",  # Umlaut
            "naïve",  # Diacritic
            "résumé",  # Accent
            "日本",  # Japanese
            "москва",  # Cyrillic
            "test@query",  # At symbol
            "query with spaces",  # Spaces
            "query-with-dashes",  # Dashes
            "query_with_underscores",  # Underscores
        ]

        with patch(
            "tripsage.api.routers.search.get_unified_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_search_suggestions.return_value = ["suggestion"]
            mock_get_service.return_value = mock_service

            for query in special_queries:
                response = await async_client.get(
                    "/search/suggest", params={"query": query, "limit": 5}
                )
                assert response.status_code == status.HTTP_200_OK


class TestErrorHandling:
    """Test comprehensive error handling."""

    async def test_malformed_json(self, async_client: AsyncClient):
        """Test handling of malformed JSON in requests."""
        response = await async_client.post(
            "/search/unified",
            content="{'invalid': json}",  # Invalid JSON
            headers={"content-type": "application/json"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_large_request_payload(self, async_client: AsyncClient):
        """Test handling of unusually large request payloads."""
        large_request = {
            "query": "x" * 1000,  # Very large query
            "destination": "y" * 1000,  # Very large destination
            "types": ["activity"] * 100,  # Large types list
        }

        with patch(
            "tripsage.api.routers.search.get_unified_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.unified_search.return_value = UnifiedSearchResponse(
                results=[],
                facets=[],
                metadata=SearchMetadata(
                    total_results=0,
                    returned_results=0,
                    search_time_ms=100,
                    search_id="large",
                    providers_queried=[],
                ),
                results_by_type={},
                errors=None,
            )
            mock_get_service.return_value = mock_service

            response = await async_client.post("/search/unified", json=large_request)

            # Should handle large payloads gracefully
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]


class TestLogging:
    """Test logging functionality."""

    async def test_request_logging(self, async_client: AsyncClient):
        """Test that requests are properly logged."""
        with (
            patch("tripsage.api.routers.search.logger") as mock_logger,
            patch(
                "tripsage.api.routers.search.get_unified_search_service"
            ) as mock_get_service,
        ):
            mock_service = AsyncMock()
            mock_service.unified_search.return_value = UnifiedSearchResponse(
                results=[],
                facets=[],
                metadata=SearchMetadata(
                    total_results=0,
                    returned_results=0,
                    search_time_ms=100,
                    search_id="log_test",
                    providers_queried=[],
                ),
                results_by_type={},
                errors=None,
            )
            mock_get_service.return_value = mock_service

            await async_client.post(
                "/search/unified",
                json={"query": "test query", "destination": "Test City"},
            )

            # Verify logging calls
            mock_logger.info.assert_called()

            # Check that query is logged
            log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            assert any("test query" in call for call in log_calls)

    async def test_error_logging(self, async_client: AsyncClient):
        """Test that errors are properly logged."""
        with (
            patch("tripsage.api.routers.search.logger") as mock_logger,
            patch(
                "tripsage.api.routers.search.get_unified_search_service"
            ) as mock_get_service,
        ):
            mock_service = AsyncMock()
            mock_service.unified_search.side_effect = UnifiedSearchServiceError(
                "Test error"
            )
            mock_get_service.return_value = mock_service

            await async_client.post(
                "/search/unified",
                json={"query": "test query", "destination": "Test City"},
            )

            # Verify error logging
            mock_logger.error.assert_called()

            # Check that error details are logged
            error_calls = [call.args[0] for call in mock_logger.error.call_args_list]
            assert any("service error" in call for call in error_calls)

    async def test_suggestions_logging(self, async_client: AsyncClient):
        """Test that suggestion requests are properly logged."""
        with (
            patch("tripsage.api.routers.search.logger") as mock_logger,
            patch(
                "tripsage.api.routers.search.get_unified_search_service"
            ) as mock_get_service,
        ):
            mock_service = AsyncMock()
            mock_service.get_search_suggestions.return_value = ["suggestion"]
            mock_get_service.return_value = mock_service

            await async_client.get("/search/suggest?query=paris&limit=5")

            # Verify logging calls
            mock_logger.info.assert_called()

            # Check that query and limit are logged
            log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            assert any("paris" in call for call in log_calls)
            assert any("limit: 5" in call for call in log_calls)
