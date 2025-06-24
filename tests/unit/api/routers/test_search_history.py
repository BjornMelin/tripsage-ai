"""
Unit tests for search history endpoints.

Tests authentication-dependent search history functionality.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from tripsage.api.routers.search import (
    delete_saved_search,
    get_recent_searches,
    save_search,
)
from tripsage.api.schemas.requests.search import UnifiedSearchRequest
from tripsage_core.services.business.search_history_service import SearchHistoryService


class TestSearchHistoryEndpoints:
    """Test search history endpoints functionality."""

    @pytest.fixture
    def mock_user_id(self):
        """Mock authenticated user ID."""
        return "user123"

    @pytest.fixture
    def mock_search_history_service(self):
        """Mock search history service."""
        service = MagicMock(spec=SearchHistoryService)
        service.get_recent_searches = AsyncMock()
        service.save_search = AsyncMock()
        service.delete_saved_search = AsyncMock()
        return service

    @pytest.fixture
    def sample_search_request(self):
        """Sample search request."""
        return UnifiedSearchRequest(
            query="Tokyo hotels",
            resource_types=["accommodation"],
            filters={
                "min_price": 100,
                "max_price": 300,
                "rating": 4.0,
            },
            destination="Tokyo, Japan",
        )

    @pytest.fixture
    def sample_search_history(self):
        """Sample search history entries."""
        return [
            {
                "id": str(uuid4()),
                "user_id": "user123",
                "query": "Tokyo hotels",
                "resource_types": ["accommodation"],
                "filters": {
                    "min_price": 100,
                    "max_price": 300,
                    "rating": 4.0,
                },
                "destination": "Tokyo, Japan",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": str(uuid4()),
                "user_id": "user123",
                "query": "Paris activities",
                "resource_types": ["activity"],
                "filters": {"category": "sightseeing"},
                "destination": "Paris, France",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ]

    @patch("tripsage.api.routers.search.get_search_history_service")
    async def test_get_recent_searches_success(
        self,
        mock_get_service,
        mock_user_id,
        mock_search_history_service,
        sample_search_history,
    ):
        """Test successful retrieval of recent searches."""
        # Setup mock
        mock_get_service.return_value = mock_search_history_service
        mock_search_history_service.get_recent_searches.return_value = (
            sample_search_history
        )

        # Call endpoint
        result = await get_recent_searches(
            user_id=mock_user_id,
        )

        # Verify
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["query"] == "Tokyo hotels"
        assert result[1]["query"] == "Paris activities"
        # Verify the service was called (limit might be wrapped in Query object)
        assert mock_search_history_service.get_recent_searches.called
        call_args = mock_search_history_service.get_recent_searches.call_args
        assert call_args[0][0] == "user123"  # First positional arg is user_id

    @patch("tripsage.api.routers.search.get_search_history_service")
    async def test_get_recent_searches_with_limit(
        self, mock_get_service, mock_user_id, mock_search_history_service
    ):
        """Test retrieval of recent searches with custom limit."""
        # Setup mock
        mock_get_service.return_value = mock_search_history_service
        mock_search_history_service.get_recent_searches.return_value = []

        # Call endpoint with limit
        result = await get_recent_searches(
            limit=5,
            user_id=mock_user_id,
        )

        # Verify
        assert isinstance(result, list)
        assert len(result) == 0
        mock_search_history_service.get_recent_searches.assert_called_once_with(
            "user123", limit=5
        )

    @patch("tripsage.api.routers.search.get_search_history_service")
    async def test_get_recent_searches_empty(
        self, mock_get_service, mock_user_id, mock_search_history_service
    ):
        """Test retrieval when no recent searches exist."""
        # Setup mock to return empty list
        mock_get_service.return_value = mock_search_history_service
        mock_search_history_service.get_recent_searches.return_value = []

        # Call endpoint
        result = await get_recent_searches(
            user_id=mock_user_id,
        )

        # Verify
        assert isinstance(result, list)
        assert len(result) == 0
        mock_search_history_service.get_recent_searches.assert_called_once()

    @patch("tripsage.api.routers.search.get_search_history_service")
    async def test_save_search_success(
        self,
        mock_get_service,
        mock_user_id,
        mock_search_history_service,
        sample_search_request,
    ):
        """Test successful saving of a search."""
        # Setup mock
        saved_search_id = str(uuid4())
        mock_get_service.return_value = mock_search_history_service
        mock_search_history_service.save_search.return_value = {
            "id": saved_search_id,
            "user_id": "user123",
            **sample_search_request.model_dump(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Call endpoint
        result = await save_search(
            request=sample_search_request,
            user_id=mock_user_id,
        )

        # Verify
        assert isinstance(result, dict)
        assert result["id"] == saved_search_id
        assert result["message"] == "Search saved successfully"
        mock_search_history_service.save_search.assert_called_once()

    @patch("tripsage.api.routers.search.get_search_history_service")
    async def test_save_search_service_error(
        self,
        mock_get_service,
        mock_user_id,
        mock_search_history_service,
        sample_search_request,
    ):
        """Test save search when service raises an error."""
        # Setup mock to raise error
        mock_get_service.return_value = mock_search_history_service
        mock_search_history_service.save_search.side_effect = Exception(
            "Database error"
        )

        # Call endpoint and expect 500
        with pytest.raises(HTTPException) as exc_info:
            await save_search(
                request=sample_search_request,
                user_id=mock_user_id,
            )

        assert exc_info.value.status_code == 500
        assert "Failed to save search" in exc_info.value.detail

    @patch("tripsage.api.routers.search.get_search_history_service")
    async def test_delete_saved_search_success(
        self, mock_get_service, mock_user_id, mock_search_history_service
    ):
        """Test successful deletion of a saved search."""
        # Setup
        search_id = str(uuid4())
        mock_get_service.return_value = mock_search_history_service
        mock_search_history_service.delete_saved_search.return_value = True

        # Call endpoint
        await delete_saved_search(
            search_id=search_id,
            user_id=mock_user_id,
        )

        # Verify - should return 204 No Content (no return value)
        mock_search_history_service.delete_saved_search.assert_called_once_with(
            "user123", search_id
        )

    @patch("tripsage.api.routers.search.get_search_history_service")
    async def test_delete_saved_search_not_found(
        self, mock_get_service, mock_user_id, mock_search_history_service
    ):
        """Test deletion when search is not found."""
        # Setup
        search_id = str(uuid4())
        mock_get_service.return_value = mock_search_history_service
        mock_search_history_service.delete_saved_search.return_value = False

        # Call endpoint and expect 404
        with pytest.raises(HTTPException) as exc_info:
            await delete_saved_search(
                search_id=search_id,
                user_id=mock_user_id,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Saved search not found"

    @patch("tripsage.api.routers.search.get_search_history_service")
    async def test_delete_saved_search_service_error(
        self, mock_get_service, mock_user_id, mock_search_history_service
    ):
        """Test deletion when service raises an error."""
        # Setup
        search_id = str(uuid4())
        mock_get_service.return_value = mock_search_history_service
        mock_search_history_service.delete_saved_search.side_effect = Exception(
            "Database error"
        )

        # Call endpoint and expect 500
        with pytest.raises(HTTPException) as exc_info:
            await delete_saved_search(
                search_id=search_id,
                user_id=mock_user_id,
            )

        assert exc_info.value.status_code == 500
        assert "Failed to delete saved search" in exc_info.value.detail
