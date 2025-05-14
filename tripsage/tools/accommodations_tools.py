"""
Accommodation search tools for TripSage agents.

This module provides function tools for searching accommodations across
different providers using MCP clients.
"""

from typing import Any, Dict, List, Optional

from openai_agents_sdk import function_tool

from tripsage.tools.schemas.accommodations import (
    AccommodationSearchParams,
    AccommodationType,
    AirbnbListingDetails,
    AirbnbSearchParams,
    AirbnbSearchResult,
)
from tripsage.utils.client_utils import validate_and_call_mcp_tool
from tripsage.utils.error_handling import with_error_handling
from tripsage.utils.logging import get_logger
from tripsage.utils.settings import settings

# Set up logger
logger = get_logger(__name__)


@function_tool
@with_error_handling
async def search_airbnb_rentals_tool(
    location: str,
    checkin: Optional[str] = None,
    checkout: Optional[str] = None,
    adults: int = 1,
    children: Optional[int] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    property_type: Optional[str] = None,
    min_rating: Optional[float] = None,
    superhost: Optional[bool] = None,
    min_beds: Optional[int] = None,
    min_bedrooms: Optional[int] = None,
    min_bathrooms: Optional[int] = None,
    amenities: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Search for Airbnb rental options based on location and filters.

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
        superhost: Filter for superhosts only
        min_beds: Minimum number of beds
        min_bedrooms: Minimum number of bedrooms
        min_bathrooms: Minimum number of bathrooms
        amenities: List of required amenities (e.g., ["pool", "wifi"])

    Returns:
        Search results with available Airbnb rental options
    """
    try:
        logger.info(f"Searching Airbnb rentals in {location}")

        # Convert property_type string to enum if provided
        property_type_enum = None
        if property_type:
            try:
                property_type_enum = AccommodationType(property_type.lower())
            except ValueError:
                logger.warning(
                    f"Invalid property type: {property_type}. Using default (all)."
                )
                property_type_enum = AccommodationType.ALL

        # Prepare search params
        search_params = {
            "location": location,
            "adults": adults,
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
        if property_type_enum:
            search_params["property_type"] = property_type_enum
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

        # Create validated model
        validated_params = AirbnbSearchParams(**search_params)

        # Call the MCP
        result = await validate_and_call_mcp_tool(
            endpoint=settings.accommodations_mcp.endpoint,
            tool_name="search_airbnb",
            params=validated_params.model_dump(by_alias=True),
            response_model=AirbnbSearchResult,
            timeout=settings.accommodations_mcp.timeout,
            server_name="Accommodations MCP",
        )

        # Apply post-search filtering for min_rating (if provided)
        filtered_listings = result.listings
        if min_rating is not None:
            filtered_listings = [
                listing
                for listing in filtered_listings
                if listing.rating is not None and listing.rating >= min_rating
            ]

        # Format results for agent consumption
        formatted_listings = []
        for listing in filtered_listings[:20]:  # Limit to 20 listings for readability
            formatted_listing = {
                "id": listing.id,
                "name": listing.name,
                "url": listing.url,
                "image": listing.image,
                "superhost": listing.superhost,
                "price": {
                    "total": listing.price_total,
                    "per_night": listing.price_per_night,
                    "currency": listing.currency,
                    "formatted": listing.price_string,
                },
                "rating": listing.rating,
                "reviews_count": listing.reviews_count,
                "location": listing.location_info,
                "property_type": listing.property_type,
                "details": {
                    "beds": listing.beds,
                    "bedrooms": listing.bedrooms,
                    "bathrooms": listing.bathrooms,
                    "max_guests": listing.max_guests,
                },
                "amenities": listing.amenities if listing.amenities else [],
            }
            formatted_listings.append(formatted_listing)

        # Return search results
        return {
            "source": "airbnb",
            "location": location,
            "count": len(filtered_listings),
            "original_count": result.count,
            "listings": formatted_listings,
            "search_params": {
                "location": location,
                "checkin": checkin,
                "checkout": checkout,
                "adults": adults,
                "children": children,
                "min_price": min_price,
                "max_price": max_price,
                "property_type": property_type,
                "min_rating": min_rating,
            },
            "error": result.error,
        }

    except Exception as e:
        logger.error(f"Error searching Airbnb rentals: {str(e)}")
        raise


@function_tool
@with_error_handling
async def get_airbnb_listing_details_tool(
    listing_id: str,
    checkin: Optional[str] = None,
    checkout: Optional[str] = None,
    adults: int = 1,
) -> Dict[str, Any]:
    """Get detailed information about a specific Airbnb listing.

    Args:
        listing_id: Airbnb listing ID
        checkin: Check-in date in YYYY-MM-DD format
        checkout: Check-out date in YYYY-MM-DD format
        adults: Number of adults (default: 1)

    Returns:
        Detailed information about the Airbnb listing
    """
    try:
        logger.info(f"Getting details for Airbnb listing: {listing_id}")

        # Prepare params
        params = {
            "listing_id": listing_id,
        }

        # Add optional parameters
        if checkin:
            params["checkin"] = checkin
        if checkout:
            params["checkout"] = checkout
        if adults:
            params["adults"] = adults

        # Call the MCP
        result = await validate_and_call_mcp_tool(
            endpoint=settings.accommodations_mcp.endpoint,
            tool_name="get_airbnb_details",
            params=params,
            response_model=AirbnbListingDetails,
            timeout=settings.accommodations_mcp.timeout,
            server_name="Accommodations MCP",
        )

        # Format results for agent consumption
        formatted_details = {
            "id": result.id,
            "name": result.name,
            "url": result.url,
            "description": result.description,
            "host": {
                "name": result.host.name,
                "image": result.host.image,
                "superhost": result.host.superhost,
                "response_rate": result.host.response_rate,
                "response_time": result.host.response_time,
                "joined_date": result.host.joined_date,
                "languages": result.host.languages if result.host.languages else [],
            },
            "location": result.location,
            "coordinates": result.coordinates,
            "property_type": result.property_type,
            "details": {
                "bedrooms": result.bedrooms,
                "beds": result.beds,
                "bathrooms": result.bathrooms,
                "max_guests": result.max_guests,
            },
            "amenities": result.amenities,
            "price": {
                "per_night": result.price_per_night,
                "total": result.price_total,
                "currency": result.currency,
            },
            "rating": result.rating,
            "reviews_count": result.reviews_count,
            "reviews_summary": result.reviews_summary,
            "images": result.images,
            "check_in_time": result.check_in_time,
            "check_out_time": result.check_out_time,
            "house_rules": result.house_rules if result.house_rules else [],
            "cancellation_policy": result.cancellation_policy,
        }

        return formatted_details

    except Exception as e:
        logger.error(f"Error getting Airbnb listing details: {str(e)}")
        raise


@function_tool
@with_error_handling
async def search_accommodations_tool(
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
    amenities: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Search for accommodations across different providers based on location and filters.

    Args:
        location: Location to search for accommodations
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
    try:
        logger.info(f"Searching {source} accommodations in {location}")

        # Check if source is supported
        if source.lower() != "airbnb":
            return {
                "error": f"Unsupported accommodation source: {source}",
                "available_sources": ["airbnb"],
                "message": (
                    "Currently, only Airbnb is supported for accommodations "
                    "search. Hotel search via Booking.com integration is planned "
                    "for future releases."
                ),
            }

        # Convert property_type string to enum if provided
        property_type_enum = None
        if property_type:
            try:
                property_type_enum = AccommodationType(property_type.lower())
            except ValueError:
                logger.warning(
                    f"Invalid property type: {property_type}. Using default (all)."
                )

        # Prepare search params
        search_params = {
            "location": location,
            "source": source,
            "adults": adults,
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
        if property_type_enum:
            search_params["property_type"] = property_type_enum
        if min_rating is not None:
            search_params["min_rating"] = min_rating
        if amenities:
            search_params["amenities"] = amenities

        # Create validated model
        validated_params = AccommodationSearchParams(**search_params)

        # Call the MCP
        # If source is "airbnb", use the direct tool
        if source.lower() == "airbnb":
            return await search_airbnb_rentals_tool(
                location=location,
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

        # For future sources, implement specific logic here

    except Exception as e:
        logger.error(f"Error searching accommodations: {str(e)}")
        raise
