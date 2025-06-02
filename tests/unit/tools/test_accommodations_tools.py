"""
Tests for accommodation tools with dependency injection.

This module tests the refactored accommodation tools that use ServiceRegistry
for dependency injection and delegate to core services.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from tripsage.agents.service_registry import ServiceRegistry
from tripsage.tools.accommodations_tools import (
    book_accommodation_tool,
    get_airbnb_listing_details_tool,
    search_accommodations_tool,
    search_airbnb_rentals_tool,
)


class TestAccommodationTools:
    """Tests for accommodation tools with dependency injection."""

    @pytest.mark.asyncio
    async def test_search_airbnb_rentals_success(self):
        """Test searching Airbnb rentals successfully."""
        mock_accommodation_service = MagicMock()
        mock_accommodation_service.search_accommodations = AsyncMock(
            return_value={
                "status": "success",
                "listings": [
                    {
                        "id": "listing1",
                        "name": "Cozy Paris Apartment",
                        "price": {"per_night": 150},
                        "rating": 4.8,
                        "location": "Paris, France",
                    }
                ],
                "total_count": 1,
            }
        )

        registry = ServiceRegistry(accommodation_service=mock_accommodation_service)

        result = await search_airbnb_rentals_tool(
            location="Paris",
            service_registry=registry,
            checkin="2024-06-01",
            checkout="2024-06-05",
            adults=2,
        )

        assert result["source"] == "airbnb"
        assert result["location"] == "Paris"
        assert result["count"] == 1
        assert result["listings"][0]["name"] == "Cozy Paris Apartment"

        # Verify service was called with correct parameters
        mock_accommodation_service.search_accommodations.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_airbnb_rentals_no_results(self):
        """Test searching Airbnb rentals with no results."""
        mock_accommodation_service = MagicMock()
        mock_accommodation_service.search_accommodations = AsyncMock(
            return_value={"status": "error", "error": "No results found"}
        )

        registry = ServiceRegistry(accommodation_service=mock_accommodation_service)

        result = await search_airbnb_rentals_tool(
            location="Remote Location", service_registry=registry
        )

        assert result["source"] == "airbnb"
        assert result["count"] == 0
        assert result["listings"] == []
        assert result["error"] == "No results found"

    @pytest.mark.asyncio
    async def test_get_airbnb_listing_details_success(self):
        """Test getting Airbnb listing details successfully."""
        mock_accommodation_service = MagicMock()
        mock_accommodation_service.get_accommodation_details = AsyncMock(
            return_value={
                "status": "success",
                "details": {
                    "id": "listing1",
                    "name": "Luxury Paris Apartment",
                    "description": "Beautiful apartment in central Paris",
                    "amenities": ["WiFi", "Kitchen", "Pool"],
                    "price": {"per_night": 200},
                },
            }
        )

        registry = ServiceRegistry(accommodation_service=mock_accommodation_service)

        result = await get_airbnb_listing_details_tool(
            listing_id="listing1", service_registry=registry
        )

        assert result["id"] == "listing1"
        assert result["name"] == "Luxury Paris Apartment"
        assert "WiFi" in result["amenities"]

    @pytest.mark.asyncio
    async def test_search_accommodations_tool_airbnb(self):
        """Test generic accommodation search tool with Airbnb source."""
        mock_accommodation_service = MagicMock()
        mock_accommodation_service.search_accommodations = AsyncMock(
            return_value={
                "status": "success",
                "listings": [{"id": "test1", "name": "Test Listing"}],
            }
        )

        registry = ServiceRegistry(accommodation_service=mock_accommodation_service)

        result = await search_accommodations_tool(
            location="Tokyo", service_registry=registry, source="airbnb"
        )

        assert result["source"] == "airbnb"

    @pytest.mark.asyncio
    async def test_search_accommodations_tool_unsupported_source(self):
        """Test generic accommodation search with unsupported source."""
        registry = ServiceRegistry()

        result = await search_accommodations_tool(
            location="Tokyo", service_registry=registry, source="booking"
        )

        assert "error" in result
        assert "Unsupported accommodation source" in result["error"]

    @pytest.mark.asyncio
    async def test_book_accommodation_tool_success(self):
        """Test booking accommodation successfully."""
        mock_accommodation_service = MagicMock()
        mock_accommodation_service.book_accommodation = AsyncMock(
            return_value={
                "status": "success",
                "booking_id": "booking123",
                "confirmation": "ABC123",
            }
        )

        registry = ServiceRegistry(accommodation_service=mock_accommodation_service)

        result = await book_accommodation_tool(
            listing_id="listing1",
            service_registry=registry,
            checkin="2024-06-01",
            checkout="2024-06-05",
            adults=2,
        )

        assert result["status"] == "success"
        assert result["booking_id"] == "booking123"

    @pytest.mark.asyncio
    async def test_service_registry_missing_accommodation_service(self):
        """Test tools behavior when accommodation service is not available."""
        registry = ServiceRegistry()  # No accommodation service

        with pytest.raises(
            ValueError, match="Required service accommodation_service not available"
        ):
            await search_airbnb_rentals_tool(
                location="Paris", service_registry=registry
            )


class TestAccommodationToolsParameterHandling:
    """Tests for accommodation tools parameter handling."""

    @pytest.mark.asyncio
    async def test_search_with_all_parameters(self):
        """Test search with all optional parameters."""
        mock_accommodation_service = MagicMock()
        mock_accommodation_service.search_accommodations = AsyncMock(
            return_value={"status": "success", "listings": []}
        )

        registry = ServiceRegistry(accommodation_service=mock_accommodation_service)

        await search_airbnb_rentals_tool(
            location="Paris",
            service_registry=registry,
            checkin="2024-06-01",
            checkout="2024-06-05",
            adults=2,
            children=1,
            min_price=100,
            max_price=300,
            property_type="apartment",
            min_rating=4.0,
            superhost=True,
            min_beds=2,
            min_bedrooms=1,
            min_bathrooms=1,
            amenities=["WiFi", "Pool"],
        )

        # Verify all parameters were passed to service
        call_args = mock_accommodation_service.search_accommodations.call_args[1]
        assert call_args["location"] == "Paris"
        assert call_args["adults"] == 2
        assert call_args["children"] == 1
        assert call_args["min_price"] == 100
        assert call_args["max_price"] == 300
        assert call_args["property_type"] == "apartment"
        assert call_args["amenities"] == ["WiFi", "Pool"]

    @pytest.mark.asyncio
    async def test_search_with_minimal_parameters(self):
        """Test search with only required parameters."""
        mock_accommodation_service = MagicMock()
        mock_accommodation_service.search_accommodations = AsyncMock(
            return_value={"status": "success", "listings": []}
        )

        registry = ServiceRegistry(accommodation_service=mock_accommodation_service)

        await search_airbnb_rentals_tool(location="Tokyo", service_registry=registry)

        # Verify required parameters were passed
        call_args = mock_accommodation_service.search_accommodations.call_args[1]
        assert call_args["location"] == "Tokyo"
        assert call_args["adults"] == 1  # Default value
        assert call_args["source"] == "airbnb"
