"""Unit tests covering the public accommodation tools.

# pyright: reportCallIssue=false
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest
from agents.tool_context import ToolContext

from tripsage.tools.accommodations_tools import (
    book_accommodation,
    get_accommodation_details,
    search_accommodations,
)
from tripsage_core.services.business.accommodation_service import (
    AccommodationBooking,
    AccommodationListing,
    AccommodationSearchRequest,
    AccommodationSearchResponse,
    BookingStatus,
    PropertyType,
)


class DummyRegistry:
    """Minimal registry stub for tool tests."""

    def __init__(self, service):
        """Store the provided accommodation service."""
        self._service = service

    def get_required_service(self, service_name: str):
        """Return the stored service when the accommodation key is requested."""
        assert service_name == "accommodation_service"
        return self._service


def _sample_listing() -> AccommodationListing:
    return AccommodationListing.model_validate(
        {
            "id": "listing-1",
            "user_id": "user-1",
            "name": "Test Hotel",
            "description": "Lovely stay",
            "property_type": PropertyType.HOTEL,
            "location": {
                "address": "123 Example St",
                "city": "Testville",
                "country": "USA",
            },
            "price_per_night": 180.0,
            "total_price": None,
            "currency": "USD",
            "rating": 4.5,
            "review_count": 10,
            "max_guests": 4,
        }
    )


def _make_context(registry: DummyRegistry) -> ToolContext[dict[str, Any]]:
    return ToolContext(
        context={"service_registry": registry},
        tool_name="test_tool",
        tool_call_id="test_call",
        tool_arguments="{}",
    )


@pytest.mark.asyncio
async def test_search_accommodations_serializes_response():
    """Serialize search results into JSON-friendly payloads."""
    listing = _sample_listing()
    search_request = AccommodationSearchRequest.model_validate(
        {
            "user_id": "user-1",
            "trip_id": "trip-1",
            "location": "Testville",
            "check_in": date(2025, 5, 1),
            "check_out": date(2025, 5, 5),
            "guests": 2,
        }
    )
    response = AccommodationSearchResponse(
        search_id="search-123",
        user_id="user-1",
        trip_id="trip-1",
        listings=[listing],
        search_parameters=search_request,
        total_results=1,
        results_returned=1,
        min_price=150.0,
        max_price=200.0,
        avg_price=175.0,
        search_duration_ms=100,
        cached=False,
    )

    service = AsyncMock()
    service.search_accommodations.return_value = response
    registry = DummyRegistry(service)
    ctx = _make_context(registry)

    result = await search_accommodations(
        ctx=ctx,
        location="Testville",
        check_in="2025-05-01",
        check_out="2025-05-05",
        user_id="user-1",
        trip_id="trip-1",
        guests=2,
    )

    assert result["status"] == "success"
    assert result["total_results"] == 1
    assert result["listings"][0]["id"] == "listing-1"
    service.search_accommodations.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_accommodation_details_handles_not_found():
    """Expose not_found status when the domain lookup fails."""
    service = AsyncMock()
    service.get_listing_details.return_value = None
    registry = DummyRegistry(service)
    ctx = _make_context(registry)

    result = await get_accommodation_details(
        ctx=ctx,
        listing_id="missing",
        user_id="user-1",
    )

    assert result["status"] == "not_found"
    service.get_listing_details.assert_awaited_once_with("missing", "user-1")


@pytest.mark.asyncio
async def test_book_accommodation_returns_booking_dump():
    """Return the booking payload from the domain service call."""
    booking = AccommodationBooking(
        id="booking-1",
        user_id="user-1",
        trip_id=None,
        guest_name="Test Guest",
        guest_email="guest@example.com",
        guest_phone="+15551234567",
        listing_id="listing-1",
        confirmation_number="CONF123",
        property_name="Test Hotel",
        property_type=PropertyType.HOTEL,
        location=_sample_listing().location,
        check_in=date(2025, 5, 1),
        check_out=date(2025, 5, 5),
        nights=4,
        guests=2,
        price_per_night=180.0,
        total_price=720.0,
        currency="USD",
        status=BookingStatus.BOOKED,
        booked_at=datetime.now(UTC),
        cancellation_policy=None,
        host=None,
        special_requests=None,
        hold_only=False,
        payment_method="credit_card",
        metadata={},
        created_at=datetime.now(UTC),
    )

    service = AsyncMock()
    service.book_accommodation.return_value = booking
    registry = DummyRegistry(service)
    ctx = _make_context(registry)

    result = await book_accommodation(
        ctx=ctx,
        user_id="user-1",
        listing_id="listing-1",
        check_in="2025-05-01",
        check_out="2025-05-05",
        guests=2,
        guest_name="John Doe",
        guest_email="john@example.com",
    )

    assert result["status"] == "success"
    assert result["booking"]["id"] == "booking-1"
    service.book_accommodation.assert_awaited_once()
