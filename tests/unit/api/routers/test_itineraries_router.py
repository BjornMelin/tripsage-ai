"""
Clean tests for itineraries router.

Tests the actual implemented itinerary management functionality.
Follows TripSage standards for focused, actionable testing.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from tripsage.api.middlewares.authentication import Principal
from tripsage.api.routers.itineraries import (
    add_item_to_itinerary,
    check_itinerary_conflicts,
    create_itinerary,
    delete_itinerary,
    delete_itinerary_item,
    get_itinerary,
    get_itinerary_item,
    list_itineraries,
    optimize_itinerary,
    search_itineraries,
    update_itinerary,
    update_itinerary_item,
)
from tripsage.api.schemas.itineraries import (
    ItineraryCreateRequest,
    ItineraryItemCreateRequest,
    ItineraryItemUpdateRequest,
    ItineraryOptimizeRequest,
    ItinerarySearchRequest,
    ItineraryUpdateRequest,
)
from tripsage_core.exceptions.exceptions import CoreResourceNotFoundError
from tripsage_core.services.business.itinerary_service import ItineraryService


class TestItinerariesRouter:
    """Test itineraries router functionality by testing functions directly."""

    @pytest.fixture
    def mock_principal(self):
        """Mock authenticated principal."""
        return Principal(
            id="user123", type="user", email="test@example.com", auth_method="jwt"
        )

    @pytest.fixture
    def mock_itinerary_service(self):
        """Mock itinerary service."""
        service = MagicMock(spec=ItineraryService)
        # Configure common async methods
        service.create_itinerary = AsyncMock()
        service.list_itineraries = AsyncMock()
        service.search_itineraries = AsyncMock()
        service.get_itinerary = AsyncMock()
        service.update_itinerary = AsyncMock()
        service.delete_itinerary = AsyncMock()
        service.add_item_to_itinerary = AsyncMock()
        service.get_item = AsyncMock()
        service.update_item = AsyncMock()
        service.delete_item = AsyncMock()
        service.check_conflicts = AsyncMock()
        service.optimize_itinerary = AsyncMock()
        return service

    @pytest.fixture
    def sample_create_request(self):
        """Sample itinerary creation request."""
        return ItineraryCreateRequest(
            title="Tokyo Adventure",
            description="5-day trip exploring Tokyo",
            start_date="2024-05-01",
            end_date="2024-05-05",
            destinations=["Tokyo, Japan"],
            total_budget=5000.0,
            currency="USD",
            tags=["adventure", "culture"],
        )

    @pytest.fixture
    def sample_update_request(self):
        """Sample itinerary update request."""
        return ItineraryUpdateRequest(
            title="Updated Tokyo Trip", description="Updated description"
        )

    @pytest.fixture
    def sample_search_request(self):
        """Sample itinerary search request."""
        return ItinerarySearchRequest(
            query="Tokyo",
            start_date_from="2024-05-01",
            start_date_to="2024-05-31",
            destinations=["Tokyo, Japan"],
            page=1,
            page_size=10,
        )

    @pytest.fixture
    def sample_item_create_request(self):
        """Sample itinerary item creation request."""
        from datetime import date, time

        from tripsage.api.schemas.itineraries import (
            ItineraryItemType,
            Location,
            TimeSlot,
        )

        return ItineraryItemCreateRequest(
            item_type=ItineraryItemType.ACTIVITY,
            title="Visit Tokyo Tower",
            description="Iconic Tokyo landmark with great city views",
            item_date=date(2024, 5, 1),
            time_slot=TimeSlot(start_time=time(10, 0), end_time=time(12, 0)),
            location=Location(latitude=35.6586, longitude=139.7454, name="Tokyo Tower"),
            cost=1000.0,
            currency="JPY",
        )

    @pytest.fixture
    def sample_item_update_request(self):
        """Sample itinerary item update request."""
        return ItineraryItemUpdateRequest(
            title="Updated Activity", notes="Updated notes for the activity"
        )

    @pytest.fixture
    def sample_optimize_request(self):
        """Sample itinerary optimization request."""
        from tripsage.api.schemas.itineraries import OptimizationSetting

        return ItineraryOptimizeRequest(
            itinerary_id="itinerary123", settings=OptimizationSetting.TIME
        )

    async def test_create_itinerary_success(
        self, mock_principal, mock_itinerary_service, sample_create_request
    ):
        """Test successful itinerary creation."""
        expected_itinerary = {
            "id": "itinerary123",
            "title": "Tokyo Adventure",
            "description": "5-day trip exploring Tokyo",
            "start_date": "2024-05-01",
            "end_date": "2024-05-05",
            "destinations": ["Tokyo, Japan"],
            "status": "active",
            "user_id": "user123",
            "created_at": "2024-01-01T00:00:00Z",
        }
        mock_itinerary_service.create_itinerary.return_value = expected_itinerary

        result = await create_itinerary(
            sample_create_request, mock_principal, mock_itinerary_service
        )

        mock_itinerary_service.create_itinerary.assert_called_once_with(
            "user123", sample_create_request
        )
        assert result == expected_itinerary
        assert result["title"] == "Tokyo Adventure"

    async def test_create_itinerary_invalid_data(
        self, mock_principal, mock_itinerary_service, sample_create_request
    ):
        """Test itinerary creation with invalid data."""
        mock_itinerary_service.create_itinerary.side_effect = ValueError(
            "Invalid date range"
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_itinerary(
                sample_create_request, mock_principal, mock_itinerary_service
            )

        assert exc_info.value.status_code == 400
        assert "Invalid date range" in str(exc_info.value.detail)

    async def test_list_itineraries_success(
        self, mock_principal, mock_itinerary_service
    ):
        """Test successful itinerary listing."""
        expected_itineraries = [
            {
                "id": "itinerary1",
                "title": "Tokyo Adventure",
                "destinations": ["Tokyo, Japan"],
                "start_date": "2024-05-01",
                "end_date": "2024-05-05",
            },
            {
                "id": "itinerary2",
                "title": "Kyoto Temple Tour",
                "destinations": ["Kyoto, Japan"],
                "start_date": "2024-06-01",
                "end_date": "2024-06-03",
            },
        ]
        mock_itinerary_service.list_itineraries.return_value = expected_itineraries

        result = await list_itineraries(mock_principal, mock_itinerary_service)

        mock_itinerary_service.list_itineraries.assert_called_once_with("user123")
        assert result == expected_itineraries
        assert len(result) == 2

    async def test_list_itineraries_empty(self, mock_principal, mock_itinerary_service):
        """Test itinerary listing when user has no itineraries."""
        mock_itinerary_service.list_itineraries.return_value = []

        result = await list_itineraries(mock_principal, mock_itinerary_service)

        assert result == []

    async def test_search_itineraries_success(
        self, mock_principal, mock_itinerary_service, sample_search_request
    ):
        """Test successful itinerary search."""
        expected_response = {
            "itineraries": [
                {
                    "id": "itinerary1",
                    "title": "Tokyo Adventure",
                    "destinations": ["Tokyo, Japan"],
                }
            ],
            "total_count": 1,
            "page": 1,
            "per_page": 10,
        }
        mock_itinerary_service.search_itineraries.return_value = expected_response

        result = await search_itineraries(
            sample_search_request, mock_principal, mock_itinerary_service
        )

        mock_itinerary_service.search_itineraries.assert_called_once_with(
            "user123", sample_search_request
        )
        assert result == expected_response
        assert "itineraries" in result
        assert "total_count" in result

    async def test_search_itineraries_no_results(
        self, mock_principal, mock_itinerary_service
    ):
        """Test itinerary search with no results."""
        search_request = ItinerarySearchRequest(
            query="Nonexistent", page=1, page_size=10
        )
        expected_response = {
            "itineraries": [],
            "total_count": 0,
            "page": 1,
            "per_page": 10,
        }
        mock_itinerary_service.search_itineraries.return_value = expected_response

        result = await search_itineraries(
            search_request, mock_principal, mock_itinerary_service
        )

        assert result["itineraries"] == []
        assert result["total_count"] == 0

    async def test_get_itinerary_success(self, mock_principal, mock_itinerary_service):
        """Test successful itinerary retrieval."""
        itinerary_id = "itinerary123"
        expected_itinerary = {
            "id": itinerary_id,
            "title": "Tokyo Adventure",
            "description": "5-day trip exploring Tokyo",
            "user_id": "user123",
            "items": [
                {"id": "item1", "title": "Visit Tokyo Tower", "location": "Tokyo Tower"}
            ],
        }
        mock_itinerary_service.get_itinerary.return_value = expected_itinerary

        result = await get_itinerary(
            itinerary_id, mock_principal, mock_itinerary_service
        )

        mock_itinerary_service.get_itinerary.assert_called_once_with(
            "user123", itinerary_id
        )
        assert result == expected_itinerary
        assert result["id"] == itinerary_id

    async def test_get_itinerary_not_found(
        self, mock_principal, mock_itinerary_service
    ):
        """Test itinerary retrieval for non-existent itinerary."""
        itinerary_id = "nonexistent"
        mock_itinerary_service.get_itinerary.side_effect = CoreResourceNotFoundError(
            "Itinerary not found"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_itinerary(itinerary_id, mock_principal, mock_itinerary_service)

        assert exc_info.value.status_code == 404
        assert "Itinerary not found" in str(exc_info.value.detail)

    async def test_update_itinerary_success(
        self, mock_principal, mock_itinerary_service, sample_update_request
    ):
        """Test successful itinerary update."""
        itinerary_id = "itinerary123"
        expected_updated = {
            "id": itinerary_id,
            "title": "Updated Tokyo Trip",
            "description": "Updated description",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_itinerary_service.update_itinerary.return_value = expected_updated

        result = await update_itinerary(
            itinerary_id, sample_update_request, mock_principal, mock_itinerary_service
        )

        mock_itinerary_service.update_itinerary.assert_called_once_with(
            "user123", itinerary_id, sample_update_request
        )
        assert result == expected_updated
        assert result["title"] == "Updated Tokyo Trip"

    async def test_update_itinerary_not_found(
        self, mock_principal, mock_itinerary_service, sample_update_request
    ):
        """Test itinerary update for non-existent itinerary."""
        itinerary_id = "nonexistent"
        mock_itinerary_service.update_itinerary.side_effect = CoreResourceNotFoundError(
            "Itinerary not found"
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_itinerary(
                itinerary_id,
                sample_update_request,
                mock_principal,
                mock_itinerary_service,
            )

        assert exc_info.value.status_code == 404
        assert "Itinerary not found" in str(exc_info.value.detail)

    async def test_update_itinerary_invalid_data(
        self, mock_principal, mock_itinerary_service, sample_update_request
    ):
        """Test itinerary update with invalid data."""
        itinerary_id = "itinerary123"
        mock_itinerary_service.update_itinerary.side_effect = ValueError(
            "Invalid update data"
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_itinerary(
                itinerary_id,
                sample_update_request,
                mock_principal,
                mock_itinerary_service,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid update data" in str(exc_info.value.detail)

    async def test_delete_itinerary_success(
        self, mock_principal, mock_itinerary_service
    ):
        """Test successful itinerary deletion."""
        itinerary_id = "itinerary123"
        mock_itinerary_service.delete_itinerary.return_value = None

        # Should not raise an exception and return None
        result = await delete_itinerary(
            itinerary_id, mock_principal, mock_itinerary_service
        )

        mock_itinerary_service.delete_itinerary.assert_called_once_with(
            "user123", itinerary_id
        )
        assert result is None

    async def test_delete_itinerary_not_found(
        self, mock_principal, mock_itinerary_service
    ):
        """Test itinerary deletion for non-existent itinerary."""
        itinerary_id = "nonexistent"
        mock_itinerary_service.delete_itinerary.side_effect = CoreResourceNotFoundError(
            "Itinerary not found"
        )

        with pytest.raises(HTTPException) as exc_info:
            await delete_itinerary(itinerary_id, mock_principal, mock_itinerary_service)

        assert exc_info.value.status_code == 404
        assert "Itinerary not found" in str(exc_info.value.detail)

    async def test_add_item_to_itinerary_success(
        self, mock_principal, mock_itinerary_service, sample_item_create_request
    ):
        """Test successful addition of item to itinerary."""
        itinerary_id = "itinerary123"
        expected_item = {
            "id": "item123",
            "title": "Visit Tokyo Tower",
            "description": "Iconic Tokyo landmark with great city views",
            "item_date": "2024-05-01",
            "location": "Tokyo Tower, Tokyo",
            "item_type": "activity",
            "itinerary_id": itinerary_id,
        }
        mock_itinerary_service.add_item_to_itinerary.return_value = expected_item

        result = await add_item_to_itinerary(
            itinerary_id,
            sample_item_create_request,
            mock_principal,
            mock_itinerary_service,
        )

        mock_itinerary_service.add_item_to_itinerary.assert_called_once_with(
            "user123", itinerary_id, sample_item_create_request
        )
        assert result == expected_item
        assert result["title"] == "Visit Tokyo Tower"

    async def test_add_item_to_itinerary_not_found(
        self, mock_principal, mock_itinerary_service, sample_item_create_request
    ):
        """Test adding item to non-existent itinerary."""
        itinerary_id = "nonexistent"
        mock_itinerary_service.add_item_to_itinerary.side_effect = (
            CoreResourceNotFoundError("Itinerary not found")
        )

        with pytest.raises(HTTPException) as exc_info:
            await add_item_to_itinerary(
                itinerary_id,
                sample_item_create_request,
                mock_principal,
                mock_itinerary_service,
            )

        assert exc_info.value.status_code == 404
        assert "Itinerary not found" in str(exc_info.value.detail)

    async def test_add_item_invalid_data(
        self, mock_principal, mock_itinerary_service, sample_item_create_request
    ):
        """Test adding item with invalid data."""
        itinerary_id = "itinerary123"
        mock_itinerary_service.add_item_to_itinerary.side_effect = ValueError(
            "Invalid time range"
        )

        with pytest.raises(HTTPException) as exc_info:
            await add_item_to_itinerary(
                itinerary_id,
                sample_item_create_request,
                mock_principal,
                mock_itinerary_service,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid time range" in str(exc_info.value.detail)

    async def test_get_itinerary_item_success(
        self, mock_principal, mock_itinerary_service
    ):
        """Test successful itinerary item retrieval."""
        itinerary_id = "itinerary123"
        item_id = "item123"
        expected_item = {
            "id": item_id,
            "title": "Visit Tokyo Tower",
            "location": "Tokyo Tower, Tokyo",
            "itinerary_id": itinerary_id,
        }
        mock_itinerary_service.get_item.return_value = expected_item

        result = await get_itinerary_item(
            itinerary_id, item_id, mock_principal, mock_itinerary_service
        )

        mock_itinerary_service.get_item.assert_called_once_with(
            "user123", itinerary_id, item_id
        )
        assert result == expected_item
        assert result["id"] == item_id

    async def test_get_itinerary_item_not_found(
        self, mock_principal, mock_itinerary_service
    ):
        """Test itinerary item retrieval for non-existent item."""
        itinerary_id = "itinerary123"
        item_id = "nonexistent"
        mock_itinerary_service.get_item.side_effect = CoreResourceNotFoundError(
            "Item not found"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_itinerary_item(
                itinerary_id, item_id, mock_principal, mock_itinerary_service
            )

        assert exc_info.value.status_code == 404
        assert "Item not found" in str(exc_info.value.detail)

    async def test_update_itinerary_item_success(
        self, mock_principal, mock_itinerary_service, sample_item_update_request
    ):
        """Test successful itinerary item update."""
        itinerary_id = "itinerary123"
        item_id = "item123"
        expected_updated_item = {
            "id": item_id,
            "title": "Updated Activity",
            "notes": "Updated notes for the activity",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_itinerary_service.update_item.return_value = expected_updated_item

        result = await update_itinerary_item(
            itinerary_id,
            item_id,
            sample_item_update_request,
            mock_principal,
            mock_itinerary_service,
        )

        mock_itinerary_service.update_item.assert_called_once_with(
            "user123", itinerary_id, item_id, sample_item_update_request
        )
        assert result == expected_updated_item
        assert result["title"] == "Updated Activity"

    async def test_update_itinerary_item_not_found(
        self, mock_principal, mock_itinerary_service, sample_item_update_request
    ):
        """Test itinerary item update for non-existent item."""
        itinerary_id = "itinerary123"
        item_id = "nonexistent"
        mock_itinerary_service.update_item.side_effect = CoreResourceNotFoundError(
            "Item not found"
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_itinerary_item(
                itinerary_id,
                item_id,
                sample_item_update_request,
                mock_principal,
                mock_itinerary_service,
            )

        assert exc_info.value.status_code == 404
        assert "Item not found" in str(exc_info.value.detail)

    async def test_update_itinerary_item_invalid_data(
        self, mock_principal, mock_itinerary_service, sample_item_update_request
    ):
        """Test itinerary item update with invalid data."""
        itinerary_id = "itinerary123"
        item_id = "item123"
        mock_itinerary_service.update_item.side_effect = ValueError("Invalid item data")

        with pytest.raises(HTTPException) as exc_info:
            await update_itinerary_item(
                itinerary_id,
                item_id,
                sample_item_update_request,
                mock_principal,
                mock_itinerary_service,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid item data" in str(exc_info.value.detail)

    async def test_delete_itinerary_item_success(
        self, mock_principal, mock_itinerary_service
    ):
        """Test successful itinerary item deletion."""
        itinerary_id = "itinerary123"
        item_id = "item123"
        mock_itinerary_service.delete_item.return_value = None

        # Should not raise an exception and return None
        result = await delete_itinerary_item(
            itinerary_id, item_id, mock_principal, mock_itinerary_service
        )

        mock_itinerary_service.delete_item.assert_called_once_with(
            "user123", itinerary_id, item_id
        )
        assert result is None

    async def test_delete_itinerary_item_not_found(
        self, mock_principal, mock_itinerary_service
    ):
        """Test itinerary item deletion for non-existent item."""
        itinerary_id = "itinerary123"
        item_id = "nonexistent"
        mock_itinerary_service.delete_item.side_effect = CoreResourceNotFoundError(
            "Item not found"
        )

        with pytest.raises(HTTPException) as exc_info:
            await delete_itinerary_item(
                itinerary_id, item_id, mock_principal, mock_itinerary_service
            )

        assert exc_info.value.status_code == 404
        assert "Item not found" in str(exc_info.value.detail)

    async def test_check_itinerary_conflicts_success(
        self, mock_principal, mock_itinerary_service
    ):
        """Test successful conflict checking."""
        itinerary_id = "itinerary123"
        expected_conflicts = {
            "has_conflicts": False,
            "conflicts": [],
            "suggestions": ["Consider adding buffer time between activities"],
            "total_items_checked": 5,
        }
        mock_itinerary_service.check_conflicts.return_value = expected_conflicts

        result = await check_itinerary_conflicts(
            itinerary_id, mock_principal, mock_itinerary_service
        )

        mock_itinerary_service.check_conflicts.assert_called_once_with(
            "user123", itinerary_id
        )
        assert result == expected_conflicts
        assert "has_conflicts" in result
        assert "conflicts" in result

    async def test_check_itinerary_conflicts_with_conflicts(
        self, mock_principal, mock_itinerary_service
    ):
        """Test conflict checking when conflicts exist."""
        itinerary_id = "itinerary123"
        expected_conflicts = {
            "has_conflicts": True,
            "conflicts": [
                {
                    "type": "time_overlap",
                    "items": ["item1", "item2"],
                    "description": "Activities overlap in time",
                }
            ],
            "suggestions": ["Adjust timing for overlapping activities"],
            "total_items_checked": 5,
        }
        mock_itinerary_service.check_conflicts.return_value = expected_conflicts

        result = await check_itinerary_conflicts(
            itinerary_id, mock_principal, mock_itinerary_service
        )

        assert result["has_conflicts"] is True
        assert len(result["conflicts"]) == 1

    async def test_check_itinerary_conflicts_not_found(
        self, mock_principal, mock_itinerary_service
    ):
        """Test conflict checking for non-existent itinerary."""
        itinerary_id = "nonexistent"
        mock_itinerary_service.check_conflicts.side_effect = CoreResourceNotFoundError(
            "Itinerary not found"
        )

        with pytest.raises(HTTPException) as exc_info:
            await check_itinerary_conflicts(
                itinerary_id, mock_principal, mock_itinerary_service
            )

        assert exc_info.value.status_code == 404
        assert "Itinerary not found" in str(exc_info.value.detail)

    async def test_optimize_itinerary_success(
        self, mock_principal, mock_itinerary_service, sample_optimize_request
    ):
        """Test successful itinerary optimization."""
        expected_optimization = {
            "optimized_itinerary": {
                "id": "itinerary123",
                "title": "Optimized Tokyo Trip",
                "items": [
                    {"id": "item1", "title": "Activity 1", "order_index": 1},
                    {"id": "item2", "title": "Activity 2", "order_index": 2},
                ],
            },
            "improvements": [
                "Reduced travel time by 30 minutes",
                "Optimized attraction visit order",
            ],
            "optimization_score": 0.85,
            "time_saved_minutes": 30,
            "cost_saved": 500.0,
        }
        mock_itinerary_service.optimize_itinerary.return_value = expected_optimization

        result = await optimize_itinerary(
            sample_optimize_request, mock_principal, mock_itinerary_service
        )

        mock_itinerary_service.optimize_itinerary.assert_called_once_with(
            "user123", sample_optimize_request
        )
        assert result == expected_optimization
        assert "optimized_itinerary" in result
        assert "improvements" in result

    async def test_optimize_itinerary_not_found(
        self, mock_principal, mock_itinerary_service, sample_optimize_request
    ):
        """Test optimization for non-existent itinerary."""
        mock_itinerary_service.optimize_itinerary.side_effect = (
            CoreResourceNotFoundError("Itinerary not found")
        )

        with pytest.raises(HTTPException) as exc_info:
            await optimize_itinerary(
                sample_optimize_request, mock_principal, mock_itinerary_service
            )

        assert exc_info.value.status_code == 404
        assert "Itinerary not found" in str(exc_info.value.detail)

    async def test_optimize_itinerary_invalid_request(
        self, mock_principal, mock_itinerary_service, sample_optimize_request
    ):
        """Test optimization with invalid request."""
        mock_itinerary_service.optimize_itinerary.side_effect = ValueError(
            "Invalid optimization settings"
        )

        with pytest.raises(HTTPException) as exc_info:
            await optimize_itinerary(
                sample_optimize_request, mock_principal, mock_itinerary_service
            )

        assert exc_info.value.status_code == 400
        assert "Invalid optimization settings" in str(exc_info.value.detail)
