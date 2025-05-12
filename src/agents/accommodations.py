"""
Accommodation search for the TripSage travel planning system.

This module provides tools for searching for accommodations across different providers
using MCP clients, with support for Airbnb via the OpenBnB MCP server and additional
accommodation services (hotels, etc.) through dedicated MCP servers or API integrations.
"""

from typing import Any, Dict, List, Optional

from ..cache.redis_cache import redis_cache
from ..mcp.accommodations import (
    AccommodationSearchParams,
    create_accommodation_client,
)
from ..utils.logging import get_module_logger

logger = get_module_logger(__name__)


class AccommodationSearchTool:
    """
    Tool for searching accommodations across different providers.

    This tool provides a unified interface for searching accommodations from
    multiple providers, including:
    - Airbnb (via OpenBnB MCP server)
    - Other hotel/accommodation sources (via specific API integrations)

    It handles parameter validation, provider selection, result normalization,
    and caching for efficient repeated searches.
    """

    def __init__(self):
        """Initialize the accommodation search tool."""
        logger.info("Initialized Accommodation Search Tool")

    async def search_accommodations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for accommodations based on location and filters.

        This tool uses the integrated accommodation MCP clients to search
        for available accommodations from multiple providers. Currently supports:
        - Airbnb (via OpenBnB MCP server)
        - Other accommodation sources can be added as they become available

        Args:
            params: Search parameters including location and filters
                   Key parameters:
                   - location: Location to search in
                   - checkin/checkout: Travel dates
                   - adults/children: Traveler count
                   - source: Provider to search ("airbnb", future: "booking", "hotels", etc.)
                   - property_type: Type of property to filter for
                   - min_price/max_price: Price range filters
                   - min_rating: Minimum rating filter

        Returns:
            Search results with accommodation options
        """
        try:
            # Validate parameters
            search_params = AccommodationSearchParams(**params)

            # Select source
            source = search_params.source.lower()

            # Get client for the selected source
            try:
                client = create_accommodation_client(source)
            except ValueError:
                return {
                    "error": f"Unsupported accommodation source: {source}",
                    "available_sources": ["airbnb"],  # Update this list as more sources are added
                    "message": "Currently, only Airbnb is supported for accommodations search. " +
                              "Hotel search via Booking.com integration is planned for future releases."
                }

            # Extract search parameters
            location = search_params.location
            checkin = search_params.checkin
            checkout = search_params.checkout
            adults = search_params.adults
            children = search_params.children
            min_price = search_params.min_price
            max_price = search_params.max_price
            property_type = (
                search_params.property_type.value
                if search_params.property_type
                else None
            )

            # Cache key for results - include more parameters for better cache precision
            cache_key = (
                f"accommodation_search:{source}:{location}:{checkin}:{checkout}:{adults}:" +
                f"{children}:{min_price}:{max_price}:{property_type}",
            )
            cached_result = await redis_cache.get(cache_key)

            if cached_result:
                logger.info("Using cached accommodation search results")
                return {
                    **cached_result,
                    "cache_hit": True,
                }

            # Perform search based on source
            if source == "airbnb":
                # Use Airbnb MCP client
                results = await client.search_accommodations(
                    location=location,
                    checkin=checkin,
                    checkout=checkout,
                    adults=adults,
                    children=children,
                    min_price=min_price,
                    max_price=max_price,
                    property_type=property_type,
                    store_results=True,
                )

                # Cache results
                await redis_cache.set(
                    cache_key,
                    results.model_dump(),
                    ttl=3600,  # 1 hour
                )

                # Return formatted results
                return {
                    "source": "airbnb",
                    "location": location,
                    "count": results.count,
                    "listings": results.listings,
                    "search_params": {
                        "location": location,
                        "checkin": checkin,
                        "checkout": checkout,
                        "adults": adults,
                        "children": children,
                        "min_price": min_price,
                        "max_price": max_price,
                        "property_type": property_type,
                    },
                    "error": results.error,
                    "cache_hit": False,
                }
            # Future implementation for other sources
            # elif source == "booking":
            #     # Add Booking.com API integration
            #     pass
            # elif source == "hotels":
            #     # Add Hotels integration
            #     pass
            else:
                # This should not happen, but just in case
                return {
                    "error": f"Source {source} is configured but not implemented",
                    "available_sources": ["airbnb"],
                    "message": "Currently, only Airbnb is supported for accommodations search. " +
                              "Additional sources will be added in future releases."
                }

        except Exception as e:
            logger.error("Accommodation search error: %s", str(e))
            return {
                "error": f"Accommodation search error: {str(e)}",
                "search_params": params,
            }

    async def get_accommodation_details(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific accommodation.

        Retrieves detailed information for a specific accommodation listing,
        including amenities, pricing, host details, and more. Currently supports:
        - Airbnb listings (via OpenBnB MCP)
        - Additional accommodation sources can be added as they become available

        Args:
            params: Parameters including accommodation ID and source
                   Key parameters:
                   - id: Unique ID of the accommodation
                   - source: Provider ("airbnb", future: "booking", "hotels", etc.)
                   - checkin/checkout: Travel dates (optional)
                   - adults: Number of adult guests (optional)

        Returns:
            Detailed accommodation information
        """
        try:
            # Required parameters
            if "id" not in params:
                return {"error": "Missing required parameter: id"}

            accommodation_id = params["id"]
            source = params.get("source", "airbnb").lower()

            # Optional parameters
            checkin = params.get("checkin")
            checkout = params.get("checkout")
            adults = params.get("adults")

            # Cache key
            cache_key = (
                f"accommodation_details:{source}:{accommodation_id}:{checkin}:{checkout}:{adults}",
            )
            cached_result = await redis_cache.get(cache_key)

            if cached_result:
                logger.info("Using cached accommodation details")
                return {
                    **cached_result,
                    "cache_hit": True,
                }

            # Get client for the selected source
            try:
                client = create_accommodation_client(source)
            except ValueError:
                return {
                    "error": f"Unsupported accommodation source: {source}",
                    "available_sources": ["airbnb"],  # Update this list as more sources are added
                    "message": "Currently, only Airbnb is supported for accommodation details. " +
                              "Hotel details via Booking.com integration is planned for future releases."
                }

            # Get details based on source
            if source == "airbnb":
                # Use Airbnb MCP client
                details = await client.get_listing_details(
                    listing_id=accommodation_id,
                    checkin=checkin,
                    checkout=checkout,
                    adults=adults,
                    store_results=True,
                )

                # Cache results
                await redis_cache.set(
                    cache_key,
                    details.model_dump(),
                    ttl=3600 * 24,  # 24 hours
                )

                return {
                    "source": "airbnb",
                    "id": details.id,
                    "name": details.name,
                    "description": details.description,
                    "url": details.url,
                    "location": details.location,
                    "property_type": details.property_type,
                    "host": details.host.model_dump(),
                    "price_per_night": details.price_per_night,
                    "price_total": details.price_total,
                    "rating": details.rating,
                    "reviews_count": details.reviews_count,
                    "amenities": details.amenities,
                    "images": details.images,
                    "beds": details.beds,
                    "bedrooms": details.bedrooms,
                    "bathrooms": details.bathrooms,
                    "max_guests": details.max_guests,
                    "cache_hit": False,
                }
            # Future implementation for other sources
            # elif source == "booking":
            #     # Add Booking.com API integration
            #     pass
            # elif source == "hotels":
            #     # Add Hotels integration
            #     pass
            else:
                # This should not happen, but just in case
                return {
                    "error": f"Source {source} is configured but not implemented",
                    "available_sources": ["airbnb"],
                    "message": "Currently, only Airbnb is supported for accommodation details. " +
                              "Additional sources will be added in future releases."
                }

        except Exception as e:
            logger.error("Accommodation details error: %s", str(e))
            return {
                "error": f"Accommodation details error: {str(e)}",
                "params": params,
            }


# Create a singleton instance
accommodation_tool = AccommodationSearchTool()


# Define function tools for OpenAI Agents SDK
async def search_airbnb_rentals(
    location: str,
    checkin: Optional[str] = None,
    checkout: Optional[str] = None,
    adults: int = 1,
    children: Optional[int] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    property_type: Optional[str] = None,
    min_rating: Optional[float] = None,
) -> Dict[str, Any]:
    """Search for Airbnb rental options based on location and filters.

    This tool searches for available Airbnb rentals in the specified location,
    applying any provided filters such as dates, price range, and property type.
    Results include pricing, ratings, and basic amenity information.

    Args:
        location: Location to search for accommodations
        checkin: Check-in date in YYYY-MM-DD format
        checkout: Check-out date in YYYY-MM-DD format
        adults: Number of adults (default: 1)
        children: Number of children
        min_price: Minimum price per night
        max_price: Maximum price per night
        property_type: Type of property (apartment, house, hotel, etc.)
        min_rating: Minimum rating (0-5)

    Returns:
        Search results with available Airbnb rental options
    """
    params = {
        "location": location,
        "source": "airbnb",
        "checkin": checkin,
        "checkout": checkout,
        "adults": adults,
        "children": children,
        "min_price": min_price,
        "max_price": max_price,
        "property_type": property_type,
        "min_rating": min_rating,
    }

    return await accommodation_tool.search_accommodations(params)


async def get_airbnb_listing_details(
    listing_id: str,
    checkin: Optional[str] = None,
    checkout: Optional[str] = None,
    adults: int = 1,
) -> Dict[str, Any]:
    """Get detailed information about a specific Airbnb listing.

    This tool retrieves comprehensive details about an Airbnb listing,
    including description, amenities, host information, and pricing.
    Use this for getting complete information about a specific property
    identified from search results.

    Args:
        listing_id: Airbnb listing ID
        checkin: Check-in date in YYYY-MM-DD format
        checkout: Check-out date in YYYY-MM-DD format
        adults: Number of adults (default: 1)

    Returns:
        Detailed information about the Airbnb listing
    """
    params = {
        "id": listing_id,
        "source": "airbnb",
        "checkin": checkin,
        "checkout": checkout,
        "adults": adults,
    }

    return await accommodation_tool.get_accommodation_details(params)


async def search_accommodations(
    location: str,
    source: str = "airbnb",
    checkin: Optional[str] = None,
    checkout: Optional[str] = None,
    adults: int = 1,
    children: Optional[int] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    property_type: Optional[str] = None,
    min_rating: Optional[float] = None,
) -> Dict[str, Any]:
    """Search for accommodations across different providers based
    on location and filters.

    This tool searches for available accommodations from the specified source,
    applying any provided filters. It provides a unified interface for accessing
    multiple accommodation providers.

    Currently supported providers:
    - "airbnb": Airbnb rentals via OpenBnB MCP

    Future planned integrations:
    - "booking": Hotels and accommodations via Booking.com
    - "hotels": Additional hotel search providers

    Use the 'source' parameter to select which provider to search.

    Args:
        location: Location to search for accommodations
        source: Accommodation source (currently only "airbnb")
        checkin: Check-in date in YYYY-MM-DD format
        checkout: Check-out date in YYYY-MM-DD format
        adults: Number of adults (default: 1)
        children: Number of children
        min_price: Minimum price per night
        max_price: Maximum price per night
        property_type: Type of property (apartment, house, hotel, etc.)
        min_rating: Minimum rating (0-5)

    Returns:
        Search results with available accommodation options
    """
    params = {
        "location": location,
        "source": source,
        "checkin": checkin,
        "checkout": checkout,
        "adults": adults,
        "children": children,
        "min_price": min_price,
        "max_price": max_price,
        "property_type": property_type,
        "min_rating": min_rating,
    }

    return await accommodation_tool.search_accommodations(params)
