"""Accommodation tools that delegate to the domain AccommodationService."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from typing import Any

from agents.tool_context import ToolContext

from agents import function_tool
from tripsage.agents.service_registry import ServiceRegistry
from tripsage_core.services.business.accommodation_service import (
    AccommodationBookingRequest,
    AccommodationSearchRequest,
    AccommodationService,
    PropertyType,
)
from tripsage_core.utils.decorator_utils import with_error_handling
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


def _parse_iso_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - validation path
        raise ValueError(f"{field_name} must be ISO formatted (YYYY-MM-DD)") from exc


def _coerce_property_types(
    property_types: Iterable[str] | None,
) -> list[PropertyType] | None:
    if not property_types:
        return None
    normalized: list[PropertyType] = []
    for raw in property_types:
        try:
            normalized.append(PropertyType(raw.lower()))
        except ValueError as exc:
            raise ValueError(f"Unsupported property type: {raw}") from exc
    return normalized


def _get_service_registry(
    ctx: ToolContext[Any],
) -> ServiceRegistry:
    registry = ctx.context.get("service_registry")
    if registry is None:
        raise ValueError("service_registry missing from tool context")
    if not hasattr(registry, "get_required_service"):
        raise TypeError("tool context service_registry is missing required API")
    return registry


def _get_accommodation_service(
    ctx: ToolContext[Any],
) -> AccommodationService:
    registry = _get_service_registry(ctx)
    service = registry.get_required_service("accommodation_service")
    required_methods = (
        "search_accommodations",
        "get_listing_details",
        "book_accommodation",
    )
    if not all(hasattr(service, method) for method in required_methods):
        raise TypeError("service_registry did not provide an AccommodationService")
    return service


# pylint: disable=too-many-positional-arguments
@with_error_handling()
async def search_accommodations(
    ctx: ToolContext[Any],
    location: str,
    check_in: str,
    check_out: str,
    user_id: str,
    *,
    trip_id: str | None = None,
    guests: int = 1,
    min_price: float | None = None,
    max_price: float | None = None,
    property_types: Sequence[str] | None = None,
    amenities: Sequence[str] | None = None,
    instant_book: bool | None = None,
    free_cancellation: bool | None = None,
) -> dict[str, Any]:
    """Search for accommodations using the domain AccommodationService."""
    service = _get_accommodation_service(ctx)

    request_metadata: dict[str, Any] = {
        "tool": "accommodations_tools.search_accommodations",
        "actor_id": getattr(ctx, "actor_id", None),
    }
    request = AccommodationSearchRequest(
        user_id=user_id,
        trip_id=trip_id,
        location=location.strip(),
        check_in=_parse_iso_date(check_in, "check_in"),
        check_out=_parse_iso_date(check_out, "check_out"),
        guests=guests,
        adults=None,
        children=None,
        infants=None,
        min_price=min_price,
        max_price=max_price,
        property_types=_coerce_property_types(property_types),
        amenities=list(amenities) if amenities else None,
        bedrooms=None,
        beds=None,
        bathrooms=None,
        accessibility_features=None,
        instant_book=instant_book,
        free_cancellation=free_cancellation,
        max_distance_km=None,
        min_rating=None,
        sort_by="relevance",
        sort_order="asc",
        currency="USD",
        metadata=request_metadata,
    )

    logger.info("Searching accommodations for %s", request.location)
    response = await service.search_accommodations(request)
    return {
        "status": "success",
        "search_id": response.search_id,
        "total_results": response.total_results,
        "results_returned": response.results_returned,
        "min_price": response.min_price,
        "max_price": response.max_price,
        "avg_price": response.avg_price,
        "cached": response.cached,
        "listings": [listing.model_dump() for listing in response.listings],
        "search_parameters": response.search_parameters.model_dump(),
    }


@with_error_handling()
async def get_accommodation_details(
    ctx: ToolContext[Any],
    listing_id: str,
    user_id: str,
) -> dict[str, Any]:
    """Retrieve a single accommodation listing in detail."""
    service = _get_accommodation_service(ctx)
    listing = await service.get_listing_details(listing_id, user_id)
    if listing is None:
        return {
            "status": "not_found",
            "listing_id": listing_id,
            "message": "Accommodation listing not found",
        }
    return {
        "status": "success",
        "listing": listing.model_dump(),
    }


# pylint: disable=too-many-positional-arguments
@with_error_handling()
async def book_accommodation(
    ctx: ToolContext[Any],
    user_id: str,
    listing_id: str,
    check_in: str,
    check_out: str,
    guests: int,
    guest_name: str,
    guest_email: str,
    guest_phone: str | None = None,
    hold_only: bool = False,
    special_requests: str | None = None,
    trip_id: str | None = None,
) -> dict[str, Any]:
    """Book an accommodation listing through the domain service."""
    service = _get_accommodation_service(ctx)

    booking_request = AccommodationBookingRequest(
        listing_id=listing_id,
        check_in=_parse_iso_date(check_in, "check_in"),
        check_out=_parse_iso_date(check_out, "check_out"),
        guests=guests,
        guest_name=guest_name,
        guest_email=guest_email,
        guest_phone=guest_phone,
        special_requests=special_requests,
        trip_id=trip_id,
        payment_method=None,
        hold_only=hold_only,
        metadata=None,
    )

    logger.info("Booking accommodation %s for user %s", listing_id, user_id)
    booking = await service.book_accommodation(user_id, booking_request)
    return {
        "status": "success",
        "booking": booking.model_dump(),
    }


search_accommodations_tool = function_tool(search_accommodations)
get_accommodation_details_tool = function_tool(get_accommodation_details)
book_accommodation_tool = function_tool(book_accommodation)


__all__ = [
    "book_accommodation",
    "book_accommodation_tool",
    "get_accommodation_details",
    "get_accommodation_details_tool",
    "search_accommodations",
    "search_accommodations_tool",
]
