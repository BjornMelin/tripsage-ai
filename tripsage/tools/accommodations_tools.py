"""
Accommodation search tools for TripSage agents.

This module provides function tools for searching accommodations.
Refactored to be lean wrappers that delegate to core services.
"""

from typing import Any, Optional

try:
    from agents import function_tool
except ImportError:
    from unittest.mock import MagicMock

    function_tool = MagicMock

from tripsage.agents.service_registry import ServiceRegistry
from tripsage_core.utils.decorator_utils import with_error_handling
from tripsage_core.utils.logging_utils import get_logger

# Set up logger
logger = get_logger(__name__)

@function_tool
@with_error_handling()
async def search_airbnb_rentals_tool(
    location: str,
    service_registry: ServiceRegistry,
    checkin: str | None = None,
    checkout: str | None = None,
    adults: int = 1,
    children: int | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    property_type: str | None = None,
    min_rating: float | None = None,
    superhost: bool | None = None,
    min_beds: int | None = None,
    min_bedrooms: int | None = None,
    min_bathrooms: int | None = None,
    amenities: list[str] | None = None,
) -> dict[str, Any]:
    """Search for Airbnb rental options based on location and filters.

    Args:
        location: Location to search for accommodations
        service_registry: Service registry for accessing services
        checkin: Check-in date in YYYY-MM-DD format
        checkout: Check-out date in YYYY-MM-DD format
        adults: Number of adults (default: 1)
        children: Number of children
        min_price: Minimum price per night
        max_price: Maximum price per night
        property_type: Type of property (apartment, house, hotel, etc.)
        min_rating: Minimum rating (0-5)
        superhost: Filter for superhosts only
        min_beds: Minimum number of beds
        min_bedrooms: Minimum number of bedrooms
        min_bathrooms: Minimum number of bathrooms
        amenities: List of required amenities (e.g., ["pool", "wifi"])

    Returns:
        Search results with available Airbnb rental options
    """
    logger.info(f"Searching Airbnb rentals in {location}")

    # Get accommodation service from registry
    accommodation_service = service_registry.get_required_service(
        "accommodation_service"
    )

    # Prepare search parameters
    search_params = {
        "location": location,
        "adults": adults,
        "source": "airbnb",
    }

    # Add optional parameters
    if checkin:
        search_params["checkin"] = checkin
    if checkout:
        search_params["checkout"] = checkout
    if children is not None:
        search_params["children"] = children
    if min_price is not None:
        search_params["min_price"] = min_price
    if max_price is not None:
        search_params["max_price"] = max_price
    if property_type:
        search_params["property_type"] = property_type
    if min_rating is not None:
        search_params["min_rating"] = min_rating
    if superhost is not None:
        search_params["superhost"] = superhost
    if min_beds is not None:
        search_params["min_beds"] = min_beds
    if min_bedrooms is not None:
        search_params["min_bedrooms"] = min_bedrooms
    if min_bathrooms is not None:
        search_params["min_bathrooms"] = min_bathrooms
    if amenities:
        search_params["amenities"] = amenities

    # Use accommodation service to search
    result = await accommodation_service.search_accommodations(**search_params)

    # Format results for agent consumption
    if result.get("status") == "success" and result.get("listings"):
        formatted_listings = []
        for listing in result["listings"][:20]:  # Limit to 20 listings
            formatted_listing = {
                "id": listing.get("id"),
                "name": listing.get("name"),
                "url": listing.get("url"),
                "image": listing.get("image"),
                "superhost": listing.get("superhost"),
                "price": listing.get("price", {}),
                "rating": listing.get("rating"),
                "reviews_count": listing.get("reviews_count"),
                "location": listing.get("location"),
                "property_type": listing.get("property_type"),
                "details": listing.get("details", {}),
                "amenities": listing.get("amenities", []),
            }
            formatted_listings.append(formatted_listing)

        return {
            "source": "airbnb",
            "location": location,
            "count": len(formatted_listings),
            "original_count": result.get("total_count", len(formatted_listings)),
            "listings": formatted_listings,
            "search_params": search_params,
            "error": None,
            "cache_hit": result.get("cache_hit", False),
        }
    else:
        return {
            "source": "airbnb",
            "location": location,
            "count": 0,
            "listings": [],
            "search_params": search_params,
            "error": result.get("error", "No results found"),
            "cache_hit": False,
        }

@function_tool
@with_error_handling()
async def get_airbnb_listing_details_tool(
    listing_id: str,
    service_registry: ServiceRegistry,
    checkin: str | None = None,
    checkout: str | None = None,
    adults: int = 1,
) -> dict[str, Any]:
    """Get detailed information about a specific Airbnb listing.

    Args:
        listing_id: Airbnb listing ID
        service_registry: Service registry for accessing services
        checkin: Check-in date in YYYY-MM-DD format
        checkout: Check-out date in YYYY-MM-DD format
        adults: Number of adults (default: 1)

    Returns:
        Detailed information about the Airbnb listing
    """
    logger.info(f"Getting details for Airbnb listing: {listing_id}")

    # Get accommodation service from registry
    accommodation_service = service_registry.get_required_service(
        "accommodation_service"
    )

    # Get listing details through service
    result = await accommodation_service.get_accommodation_details(
        listing_id=listing_id,
        source="airbnb",
        checkin=checkin,
        checkout=checkout,
        adults=adults,
    )

    if result.get("status") == "success" and result.get("details"):
        details = result["details"]
        return {
            "id": details.get("id"),
            "name": details.get("name"),
            "url": details.get("url"),
            "description": details.get("description"),
            "host": details.get("host", {}),
            "location": details.get("location"),
            "coordinates": details.get("coordinates"),
            "property_type": details.get("property_type"),
            "details": details.get("details", {}),
            "amenities": details.get("amenities", []),
            "price": details.get("price", {}),
            "rating": details.get("rating"),
            "reviews_count": details.get("reviews_count"),
            "reviews_summary": details.get("reviews_summary"),
            "images": details.get("images", []),
            "check_in_time": details.get("check_in_time"),
            "check_out_time": details.get("check_out_time"),
            "house_rules": details.get("house_rules", []),
            "cancellation_policy": details.get("cancellation_policy"),
            "cache_hit": result.get("cache_hit", False),
        }
    else:
        return {
            "error": result.get("error", "Failed to get listing details"),
            "listing_id": listing_id,
        }

@function_tool
@with_error_handling()
async def search_accommodations_tool(
    location: str,
    service_registry: ServiceRegistry,
    source: str = "airbnb",
    checkin: str | None = None,
    checkout: str | None = None,
    adults: int = 1,
    children: int | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    property_type: str | None = None,
    min_rating: float | None = None,
    amenities: list[str] | None = None,
) -> dict[str, Any]:
    """Search for accommodations across different providers.

    Args:
        location: Location to search for accommodations
        service_registry: Service registry for accessing services
        source: Accommodation source (airbnb, booking, hotels)
        checkin: Check-in date in YYYY-MM-DD format
        checkout: Check-out date in YYYY-MM-DD format
        adults: Number of adults (default: 1)
        children: Number of children
        min_price: Minimum price per night
        max_price: Maximum price per night
        property_type: Type of property (apartment, house, hotel, etc.)
        min_rating: Minimum rating (0-5)
        amenities: List of required amenities (e.g., ["pool", "wifi"])

    Returns:
        Search results with available accommodation options
    """
    logger.info(f"Searching {source} accommodations in {location}")

    # Currently, delegate to airbnb search
    if source.lower() == "airbnb":
        return await search_airbnb_rentals_tool(
            location=location,
            service_registry=service_registry,
            checkin=checkin,
            checkout=checkout,
            adults=adults,
            children=children,
            min_price=min_price,
            max_price=max_price,
            property_type=property_type,
            min_rating=min_rating,
            amenities=amenities,
        )
    else:
        return {
            "error": f"Unsupported accommodation source: {source}",
            "available_sources": ["airbnb"],
            "message": (
                "Currently, only Airbnb is supported for accommodations search. "
                "Hotel search via Booking.com integration is planned for future "
                "releases."
            ),
        }

@function_tool
@with_error_handling()
async def book_accommodation_tool(
    listing_id: str,
    service_registry: ServiceRegistry,
    source: str = "airbnb",
    checkin: str = None,
    checkout: str = None,
    adults: int = 1,
    children: int = 0,
    guest_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Initiate accommodation booking process.

    Args:
        listing_id: Accommodation listing ID
        service_registry: Service registry for accessing services
        source: Booking source (airbnb, booking, etc.)
        checkin: Check-in date in YYYY-MM-DD format
        checkout: Check-out date in YYYY-MM-DD format
        adults: Number of adults
        children: Number of children
        guest_details: Guest information for booking

    Returns:
        Booking initiation result
    """
    logger.info(f"Initiating booking for {source} listing: {listing_id}")

    # Get accommodation service from registry
    accommodation_service = service_registry.get_required_service(
        "accommodation_service"
    )

    # Initiate booking through service
    result = await accommodation_service.book_accommodation(
        listing_id=listing_id,
        source=source,
        checkin=checkin,
        checkout=checkout,
        adults=adults,
        children=children,
        guest_details=guest_details,
    )

    return result
