"""
Integration tests for accommodation search and booking workflows.

Tests the full workflow from search request to booking completion,
including MCP integration, caching, and data persistence.
"""

from datetime import date, timedelta

import pytest

from tests.factories import AccommodationFactory, SearchFactory
from tripsage_core.services.business.accommodation_service import AccommodationService


class TestAccommodationWorkflow:
    """Integration tests for accommodation search and booking workflows."""

    @pytest.fixture
    async def accommodation_service(self, mock_mcp_manager, mock_web_operations_cache):
        """Create AccommodationService with mocked dependencies."""
        service = AccommodationService()
        service.mcp_manager = mock_mcp_manager
        service.cache = mock_web_operations_cache
        return service

    @pytest.mark.asyncio
    async def test_search_accommodation_full_workflow(
        self, accommodation_service, mock_mcp_manager
    ):
        """Test complete accommodation search workflow."""
        # Arrange
        search_params = SearchFactory.create_accommodation_search()
        mock_results = [
            AccommodationFactory.create(id=i, name=f"Hotel {i}") for i in range(1, 6)
        ]

        mock_mcp_manager.invoke.return_value = {
            "listings": mock_results,
            "count": 5,
            "has_more": False,
        }

        # Act
        results = await accommodation_service.search_accommodations(
            destination=search_params["destination"],
            check_in=search_params["check_in"],
            check_out=search_params["check_out"],
            guests=search_params["guests"],
            filters={
                "min_price": search_params["min_price"],
                "max_price": search_params["max_price"],
                "accommodation_type": search_params["accommodation_type"],
            },
        )

        # Assert
        assert len(results["accommodations"]) == 5
        assert results["total"] == 5
        assert not results["has_more"]

        # Verify MCP was called with correct parameters
        mock_mcp_manager.invoke.assert_called_once()
        call_args = mock_mcp_manager.invoke.call_args
        assert "search" in call_args[0][0].lower()  # Method name

        # Verify search parameters were passed correctly
        params = call_args[0][1]
        assert params["destination"] == "Tokyo, Japan"
        assert params["check_in"] == search_params["check_in"]

    @pytest.mark.asyncio
    async def test_search_with_caching(
        self, accommodation_service, mock_web_operations_cache
    ):
        """Test that search results are properly cached."""
        # Arrange
        search_params = SearchFactory.create_accommodation_search()
        cached_results = SearchFactory.create_search_results(3)

        # First call - cache miss, should invoke MCP
        mock_web_operations_cache.get.return_value = None
        mock_web_operations_cache.set.return_value = True

        # Act - First search (cache miss)
        results1 = await accommodation_service.search_accommodations(
            destination=search_params["destination"],
            check_in=search_params["check_in"],
            check_out=search_params["check_out"],
            guests=search_params["guests"],
        )

        # Assert cache was checked and updated
        mock_web_operations_cache.get.assert_called_once()
        mock_web_operations_cache.set.assert_called_once()

        # Arrange for second call - cache hit
        mock_web_operations_cache.reset_mock()
        mock_web_operations_cache.get.return_value = cached_results

        # Act - Second search (cache hit)
        results2 = await accommodation_service.search_accommodations(
            destination=search_params["destination"],
            check_in=search_params["check_in"],
            check_out=search_params["check_out"],
            guests=search_params["guests"],
        )

        # Assert cache was used, MCP not called again
        mock_web_operations_cache.get.assert_called_once()
        mock_web_operations_cache.set.assert_not_called()
        assert results2 == cached_results

    @pytest.mark.asyncio
    async def test_get_accommodation_details_workflow(
        self, accommodation_service, mock_mcp_manager
    ):
        """Test retrieving detailed accommodation information."""
        # Arrange
        accommodation_id = "hotel-123"
        mock_details = AccommodationFactory.create(
            id=accommodation_id,
            name="Luxury Tokyo Hotel",
            amenities={"list": ["spa", "pool", "wifi", "gym", "restaurant"]},
            images=["img1.jpg", "img2.jpg", "img3.jpg"],
        )

        mock_mcp_manager.invoke.return_value = mock_details

        # Act
        details = await accommodation_service.get_accommodation_details(
            accommodation_id
        )

        # Assert
        assert details["name"] == "Luxury Tokyo Hotel"
        assert len(details["amenities"]["list"]) == 5
        assert len(details["images"]) == 3

        # Verify MCP was called correctly
        mock_mcp_manager.invoke.assert_called_once()
        call_args = mock_mcp_manager.invoke.call_args
        assert "details" in call_args[0][0].lower()  # Method name
        assert call_args[0][1] == accommodation_id  # Accommodation ID

    @pytest.mark.asyncio
    async def test_check_availability_workflow(
        self, accommodation_service, mock_mcp_manager
    ):
        """Test checking accommodation availability for specific dates."""
        # Arrange
        accommodation_id = "hotel-123"
        check_in = date.today() + timedelta(days=30)
        check_out = check_in + timedelta(days=7)
        guests = 2

        mock_mcp_manager.invoke.return_value = {
            "available": True,
            "price_per_night": 250.00,
            "total_price": 1750.00,
            "available_rooms": ["Standard Room", "Deluxe Room"],
            "cancellation_policy": "free_cancellation_24h",
        }

        # Act
        availability = await accommodation_service.check_availability(
            accommodation_id=accommodation_id,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
        )

        # Assert
        assert availability["available"] is True
        assert availability["price_per_night"] == 250.00
        assert availability["total_price"] == 1750.00
        assert len(availability["available_rooms"]) == 2

        # Verify MCP was called with correct parameters
        mock_mcp_manager.invoke.assert_called_once()
        call_args = mock_mcp_manager.invoke.call_args
        assert "availability" in call_args[0][0].lower()
        params = call_args[0][1]
        assert params["accommodation_id"] == accommodation_id
        assert params["check_in"] == check_in
        assert params["guests"] == guests

    @pytest.mark.asyncio
    async def test_booking_workflow(self, accommodation_service, mock_mcp_manager):
        """Test the complete booking workflow."""
        # Arrange
        booking_data = {
            "accommodation_id": "hotel-123",
            "check_in": date.today() + timedelta(days=30),
            "check_out": date.today() + timedelta(days=37),
            "guests": 2,
            "room_type": "Deluxe Room",
            "guest_details": {
                "primary_guest": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "phone": "+1-555-0123",
                }
            },
        }

        mock_mcp_manager.invoke.return_value = {
            "booking_id": "booking-456",
            "status": "confirmed",
            "confirmation_code": "ABC123",
            "total_amount": 1750.00,
            "currency": "USD",
        }

        # Act
        booking_result = await accommodation_service.create_booking(**booking_data)

        # Assert
        assert booking_result["booking_id"] == "booking-456"
        assert booking_result["status"] == "confirmed"
        assert booking_result["confirmation_code"] == "ABC123"
        assert booking_result["total_amount"] == 1750.00

        # Verify MCP was called for booking
        mock_mcp_manager.invoke.assert_called_once()
        call_args = mock_mcp_manager.invoke.call_args
        assert "book" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_search_error_handling(self, accommodation_service, mock_mcp_manager):
        """Test error handling during accommodation search."""
        # Arrange
        search_params = SearchFactory.create_accommodation_search()
        mock_mcp_manager.invoke.side_effect = Exception("MCP connection error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await accommodation_service.search_accommodations(
                destination=search_params["destination"],
                check_in=search_params["check_in"],
                check_out=search_params["check_out"],
                guests=search_params["guests"],
            )

        assert "MCP connection error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cache_invalidation_workflow(
        self, accommodation_service, mock_web_operations_cache
    ):
        """Test cache invalidation when data changes."""
        # Arrange
        search_params = SearchFactory.create_accommodation_search()

        # Act - Trigger cache invalidation
        await accommodation_service.invalidate_search_cache(
            destination=search_params["destination"]
        )

        # Assert
        mock_web_operations_cache.invalidate_pattern.assert_called_once()
        pattern = mock_web_operations_cache.invalidate_pattern.call_args[0][0]
        assert "tokyo" in pattern.lower()

    @pytest.mark.asyncio
    async def test_search_with_filters_workflow(
        self, accommodation_service, mock_mcp_manager
    ):
        """Test accommodation search with complex filters."""
        # Arrange
        search_params = SearchFactory.create_accommodation_search()
        complex_filters = {
            "min_price": 100.00,
            "max_price": 300.00,
            "accommodation_type": "hotel",
            "amenities": ["wifi", "pool", "gym"],
            "rating_min": 4.0,
            "distance_max": 5.0,  # km from center
        }

        mock_results = [AccommodationFactory.create() for _ in range(3)]
        mock_mcp_manager.invoke.return_value = {
            "listings": mock_results,
            "count": 3,
            "filters_applied": complex_filters,
        }

        # Act
        results = await accommodation_service.search_accommodations(
            destination=search_params["destination"],
            check_in=search_params["check_in"],
            check_out=search_params["check_out"],
            guests=search_params["guests"],
            filters=complex_filters,
        )

        # Assert
        assert len(results["accommodations"]) == 3
        assert results["filters_applied"] == complex_filters

        # Verify filters were passed to MCP
        call_args = mock_mcp_manager.invoke.call_args
        params = call_args[0][1]
        assert params["filters"]["min_price"] == 100.00
        assert "wifi" in params["filters"]["amenities"]

    @pytest.mark.asyncio
    async def test_pagination_workflow(self, accommodation_service, mock_mcp_manager):
        """Test pagination in search results."""
        # Arrange
        search_params = SearchFactory.create_accommodation_search()
        page_1_results = [AccommodationFactory.create(id=i) for i in range(1, 11)]
        page_2_results = [AccommodationFactory.create(id=i) for i in range(11, 16)]

        # First page
        mock_mcp_manager.invoke.return_value = {
            "listings": page_1_results,
            "count": 10,
            "total": 15,
            "page": 1,
            "has_more": True,
        }

        # Act - First page
        results_page_1 = await accommodation_service.search_accommodations(
            destination=search_params["destination"],
            check_in=search_params["check_in"],
            check_out=search_params["check_out"],
            guests=search_params["guests"],
            page=1,
            limit=10,
        )

        # Assert first page
        assert len(results_page_1["accommodations"]) == 10
        assert results_page_1["has_more"] is True
        assert results_page_1["page"] == 1

        # Arrange second page
        mock_mcp_manager.invoke.return_value = {
            "listings": page_2_results,
            "count": 5,
            "total": 15,
            "page": 2,
            "has_more": False,
        }

        # Act - Second page
        results_page_2 = await accommodation_service.search_accommodations(
            destination=search_params["destination"],
            check_in=search_params["check_in"],
            check_out=search_params["check_out"],
            guests=search_params["guests"],
            page=2,
            limit=10,
        )

        # Assert second page
        assert len(results_page_2["accommodations"]) == 5
        assert results_page_2["has_more"] is False
        assert results_page_2["page"] == 2

    @pytest.mark.asyncio
    async def test_concurrent_searches(self, accommodation_service, mock_mcp_manager):
        """Test handling concurrent accommodation searches."""
        import asyncio

        # Arrange
        search_params = [
            SearchFactory.create_accommodation_search(destination="Tokyo, Japan"),
            SearchFactory.create_accommodation_search(destination="Osaka, Japan"),
            SearchFactory.create_accommodation_search(destination="Kyoto, Japan"),
        ]

        mock_mcp_manager.invoke.return_value = {
            "listings": [AccommodationFactory.create()],
            "count": 1,
        }

        # Act
        tasks = [
            accommodation_service.search_accommodations(
                destination=params["destination"],
                check_in=params["check_in"],
                check_out=params["check_out"],
                guests=params["guests"],
            )
            for params in search_params
        ]

        results = await asyncio.gather(*tasks)

        # Assert
        assert len(results) == 3
        assert all(len(result["accommodations"]) == 1 for result in results)

        # Verify MCP was called for each search
        assert mock_mcp_manager.invoke.call_count == 3
