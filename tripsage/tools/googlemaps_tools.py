"""
Google Maps function tools for TripSage.

This module provides OpenAI Agents SDK function tools for Google Maps operations,
allowing agents to geocode addresses, search for places, get directions,
calculate distances, and other location-based services using the Google Maps MCP
through the abstraction layer.
"""

from typing import Any, Dict, List, Optional

from agents import function_tool

from tripsage.mcp_abstraction.manager import mcp_manager
from tripsage.tools.schemas.googlemaps import (
    DirectionsParams,
    DistanceMatrixParams,
    ElevationParams,
    GeocodeParams,
    PlaceDetailsParams,
    PlaceField,
    PlaceSearchParams,
    ReverseGeocodeParams,
    TimeZoneParams,
    TravelMode,
)
from tripsage.utils.error_handling import with_error_handling
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


@function_tool
@with_error_handling
async def geocode_tool(
    address: Optional[str] = None,
    place_id: Optional[str] = None,
    components: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Convert an address to geographic coordinates.

    Args:
        address: Address to geocode
            (e.g., "1600 Amphitheatre Parkway, Mountain View, CA")
        place_id: Google Maps place ID to geocode (alternative to address)
        components: Component filters (e.g., {"country": "US"})

    Returns:
        Dictionary with geocoding results
    """
    try:
        # Validate parameters
        params = GeocodeParams(
            address=address,
            place_id=place_id,
            components=components,
        )
    except ValueError as e:
        return {"error": str(e)}

    logger.info(f"Geocoding: {params.model_dump(exclude_none=True)}")

    try:
        # Call the Google Maps MCP through the abstraction layer
        result = await mcp_manager.invoke(
            mcp_name="google_maps",
            method_name="geocode",
            params=params.model_dump(exclude_none=True),
        )

        # Parse the response for better usability
        locations = []
        for loc in result.results:
            geometry = loc.geometry
            locations.append(
                {
                    "place_id": loc.place_id,
                    "formatted_address": loc.formatted_address,
                    "location": {
                        "lat": geometry["location"]["lat"],
                        "lng": geometry["location"]["lng"],
                    },
                    "address_components": loc.address_components,
                    "types": loc.types,
                }
            )

        formatted_result = ""
        if locations:
            formatted_result = f"Found {len(locations)} locations:\n"
            for i, loc in enumerate(locations):
                formatted_result += (
                    f"{i + 1}. {loc['formatted_address']} "
                    f"({loc['location']['lat']}, {loc['location']['lng']})\n"
                )
        else:
            formatted_result = "No locations found."

        return {
            "status": result.status,
            "locations": locations,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error geocoding address: {str(e)}")
        return {"error": f"Failed to geocode address: {str(e)}"}


@function_tool
@with_error_handling
async def reverse_geocode_tool(
    lat: float,
    lng: float,
    result_type: Optional[str] = None,
    location_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert geographic coordinates to an address.

    Args:
        lat: Latitude coordinate
        lng: Longitude coordinate
        result_type: Filter result types (e.g., "street_address")
        location_type: Filter location types (e.g., "ROOFTOP")

    Returns:
        Dictionary with reverse geocoding results
    """
    try:
        # Validate parameters
        params = ReverseGeocodeParams(
            lat=lat,
            lng=lng,
            result_type=result_type,
            location_type=location_type,
        )
    except ValueError as e:
        return {"error": str(e)}

    logger.info(f"Reverse geocoding: {params.model_dump(exclude_none=True)}")

    try:
        # Call the Google Maps MCP through the abstraction layer
        result = await mcp_manager.invoke(
            mcp_name="google_maps",
            method_name="reverse_geocode",
            params=params.model_dump(exclude_none=True),
        )

        # Parse the response for better usability
        locations = []
        for loc in result.results:
            locations.append(
                {
                    "place_id": loc.place_id,
                    "formatted_address": loc.formatted_address,
                    "address_components": loc.address_components,
                    "types": loc.types,
                }
            )

        formatted_result = ""
        if locations:
            coord_str = f"({lat}, {lng})"
            matches = len(locations)
            formatted_result = f"Found {matches} results for coordinates {coord_str}:\n"
            for i, loc in enumerate(locations):
                formatted_result += f"{i + 1}. {loc['formatted_address']}\n"
        else:
            formatted_result = f"No address found for coordinates ({lat}, {lng})."

        return {
            "status": result.status,
            "locations": locations,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error reverse geocoding: {str(e)}")
        return {"error": f"Failed to reverse geocode coordinates: {str(e)}"}


@function_tool
@with_error_handling
async def place_search_tool(
    query: Optional[str] = None,
    location: Optional[Dict[str, float]] = None,
    radius: Optional[int] = None,
    type: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    open_now: bool = False,
) -> Dict[str, Any]:
    """Search for places near a location.

    Args:
        query: Search query (e.g., "restaurants")
        location: Dict with "lat" and "lng" fields for the search center
        radius: Search radius in meters
        type: Place type (e.g., "restaurant", "museum")
        min_price: Minimum price level (0-4)
        max_price: Maximum price level (0-4)
        open_now: Whether to return only places that are open now

    Returns:
        Dictionary with place search results
    """
    try:
        # Validate parameters
        params = PlaceSearchParams(
            query=query,
            location=location,
            radius=radius,
            type=type,
            min_price=min_price,
            max_price=max_price,
            open_now=open_now,
        )
    except ValueError as e:
        return {"error": str(e)}

    logger.info(f"Searching places: {params.model_dump(exclude_none=True)}")

    try:
        # Call the Google Maps MCP through the abstraction layer
        result = await mcp_manager.invoke(
            mcp_name="google_maps",
            method_name="search_places",
            params=params.model_dump(exclude_none=True),
        )

        # Parse the response for better usability
        places = []
        for place in result.results:
            places.append(
                {
                    "place_id": place.place_id,
                    "name": place.name,
                    "formatted_address": place.formatted_address,
                    "location": {
                        "lat": place.geometry["location"]["lat"],
                        "lng": place.geometry["location"]["lng"],
                    },
                    "types": place.types,
                    "rating": place.rating,
                    "user_ratings_total": place.user_ratings_total,
                    "price_level": place.price_level,
                    "vicinity": place.vicinity,
                }
            )

        formatted_result = ""
        if places:
            if query:
                formatted_result = f"Found {len(places)} places matching '{query}':\n"
            else:
                formatted_result = f"Found {len(places)} places:\n"
            for i, place in enumerate(places):
                rating_info = (
                    f" ({place['rating']} ⭐ {place['user_ratings_total']} reviews)"
                    if place.get("rating")
                    else ""
                )
                place_loc = place.get("vicinity", place.get("formatted_address", ""))
                num = i + 1
                name = place["name"]
                formatted_result += f"{num}. {name}{rating_info}\n   {place_loc}\n"
        else:
            formatted_result = "No places found."

        return {
            "status": result.status,
            "places": places,
            "next_page_token": result.next_page_token,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error searching places: {str(e)}")
        return {"error": f"Failed to search places: {str(e)}"}


@function_tool
@with_error_handling
async def place_details_tool(
    place_id: str,
    fields: Optional[List[PlaceField]] = None,
) -> Dict[str, Any]:
    """Get detailed information about a specific place.

    Args:
        place_id: Google Maps place ID
        fields: List of fields to include in the response
            (e.g., ["name", "rating", "photos"])

    Returns:
        Dictionary with place details
    """
    try:
        # Validate parameters
        params = PlaceDetailsParams(
            place_id=place_id,
            fields=fields,
        )
    except ValueError as e:
        return {"error": str(e)}

    logger.info(f"Getting place details for {place_id}")

    try:
        # Call the Google Maps MCP through the abstraction layer
        result = await mcp_manager.invoke(
            mcp_name="google_maps",
            method_name="get_place_details",
            params=params.model_dump(exclude_none=True),
        )

        # Process result
        place = result.result
        details = {
            "place_id": place.place_id,
            "name": place.name,
            "formatted_address": place.formatted_address,
            "location": {
                "lat": place.geometry["location"]["lat"],
                "lng": place.geometry["location"]["lng"],
            },
            "types": place.types,
            "formatted_phone_number": place.formatted_phone_number,
            "international_phone_number": place.international_phone_number,
            "website": place.website,
            "rating": place.rating,
            "user_ratings_total": place.user_ratings_total,
            "price_level": place.price_level,
            "reviews": place.reviews,
            "opening_hours": place.opening_hours,
            "utc_offset": place.utc_offset,
        }

        # Create formatted result
        formatted_result = f"{place.name}\n"
        formatted_result += f"Address: {place.formatted_address}\n"
        if place.formatted_phone_number:
            formatted_result += f"Phone: {place.formatted_phone_number}\n"
        if place.website:
            formatted_result += f"Website: {place.website}\n"
        if place.rating:
            reviews = place.user_ratings_total
            formatted_result += f"Rating: {place.rating} ⭐ ({reviews} reviews)\n"
        if place.opening_hours and "weekday_text" in place.opening_hours:
            formatted_result += "Hours:\n"
            for hours in place.opening_hours["weekday_text"]:
                formatted_result += f"  {hours}\n"

        return {
            "status": result.status,
            "details": details,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error getting place details: {str(e)}")
        return {"error": f"Failed to get place details: {str(e)}"}


@function_tool
@with_error_handling
async def directions_tool(
    origin: str,
    destination: str,
    mode: TravelMode = TravelMode.driving,
    waypoints: Optional[List[str]] = None,
    avoid: Optional[List[str]] = None,
    arrival_time: Optional[int] = None,
    departure_time: Optional[int] = None,
    alternatives: bool = False,
) -> Dict[str, Any]:
    """Get directions between locations.

    Args:
        origin: Starting location (address, coords, or place_id)
        destination: Ending location (address, coords, or place_id)
        mode: Travel mode (driving, walking, bicycling, transit)
        waypoints: List of waypoints to include in the route
        avoid: Features to avoid (tolls, highways, ferries)
        arrival_time: Desired arrival time (epoch timestamp)
        departure_time: Desired departure time (epoch timestamp)
        alternatives: Whether to return alternative routes

    Returns:
        Dictionary with directions information
    """
    try:
        # Validate parameters
        params = DirectionsParams(
            origin=origin,
            destination=destination,
            mode=mode,
            waypoints=waypoints,
            avoid=avoid,
            arrival_time=arrival_time,
            departure_time=departure_time,
            alternatives=alternatives,
        )
    except ValueError as e:
        return {"error": str(e)}

    logger.info(f"Getting directions from {origin} to {destination} via {mode}")

    try:
        # Call the Google Maps MCP through the abstraction layer
        result = await mcp_manager.invoke(
            mcp_name="google_maps",
            method_name="get_directions",
            params=params.model_dump(exclude_none=True),
        )

        # Process routes
        routes = []
        for route in result.routes:
            route_info = {
                "summary": route.summary,
                "distance": route.legs[0].distance,
                "duration": route.legs[0].duration,
                "start_address": route.legs[0].start_address,
                "end_address": route.legs[0].end_address,
                "steps": [
                    {
                        "distance": step.distance,
                        "duration": step.duration,
                        "html_instructions": step.html_instructions,
                        "travel_mode": step.travel_mode,
                    }
                    for step in route.legs[0].steps
                ],
            }
            routes.append(route_info)

        # Create formatted result
        formatted_result = ""
        if routes:
            route = routes[0]  # Use the first (recommended) route
            formatted_result = (
                f"Directions from {route['start_address']} to {route['end_address']}:\n"
                f"Distance: {route['distance']['text']}\n"
                f"Duration: {route['duration']['text']}\n\n"
                "Steps:\n"
            )
            for i, step in enumerate(route["steps"]):
                # Remove HTML tags from instructions
                # (a proper implementation would use a proper HTML parser)
                instructions = step["html_instructions"]
                instructions = (
                    instructions.replace("<b>", "")
                    .replace("</b>", "")
                    .replace("<div>", "\n")
                    .replace("</div>", "")
                )
                formatted_result += (
                    f"{i + 1}. {instructions}\n"
                    f"   ({step['distance']['text']}, {step['duration']['text']})\n"
                )
        else:
            formatted_result = f"No directions found from {origin} to {destination}."

        return {
            "status": result.status,
            "routes": routes,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error getting directions: {str(e)}")
        return {"error": f"Failed to get directions: {str(e)}"}


@function_tool
@with_error_handling
async def distance_matrix_tool(
    origins: List[str],
    destinations: List[str],
    mode: TravelMode = TravelMode.driving,
    avoid: Optional[List[str]] = None,
    departure_time: Optional[int] = None,
) -> Dict[str, Any]:
    """Calculate distances and travel times between multiple origins and destinations.

    Args:
        origins: List of starting locations
        destinations: List of ending locations
        mode: Travel mode (driving, walking, bicycling, transit)
        avoid: Features to avoid (tolls, highways, ferries)
        departure_time: Desired departure time (epoch timestamp)

    Returns:
        Dictionary with distance matrix information
    """
    try:
        # Validate parameters
        params = DistanceMatrixParams(
            origins=origins,
            destinations=destinations,
            mode=mode,
            avoid=avoid,
            departure_time=departure_time,
        )
    except ValueError as e:
        return {"error": str(e)}

    logger.info(
        f"Calculating distance matrix: {len(origins)} origins, "
        f"{len(destinations)} destinations"
    )

    try:
        # Call the Google Maps MCP through the abstraction layer
        result = await mcp_manager.invoke(
            mcp_name="google_maps",
            method_name="distance_matrix",
            params=params.model_dump(exclude_none=True),
        )

        # Process matrix
        matrix = []
        for i, row in enumerate(result.rows):
            row_data = []
            for j, element in enumerate(row.elements):
                row_data.append(
                    {
                        "origin": origins[i],
                        "destination": destinations[j],
                        "status": element.status,
                        "distance": element.distance,
                        "duration": element.duration,
                    }
                )
            matrix.append(row_data)

        # Create formatted result
        formatted_result = "Distance Matrix:\n"
        for i, row in enumerate(matrix):
            formatted_result += f"From {origins[i]}:\n"
            for element in row:
                if element["status"] == "OK":
                    formatted_result += (
                        f"  To {element['destination']}: "
                        f"{element['distance']['text']} "
                        f"({element['duration']['text']})\n"
                    )
                else:
                    formatted_result += (
                        f"  To {element['destination']}: Unable to calculate "
                        f"({element['status']})\n"
                    )

        return {
            "status": result.status,
            "origin_addresses": result.origin_addresses,
            "destination_addresses": result.destination_addresses,
            "matrix": matrix,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error calculating distance matrix: {str(e)}")
        return {"error": f"Failed to calculate distance matrix: {str(e)}"}


@function_tool
@with_error_handling
async def elevation_tool(
    locations: List[Dict[str, float]],
) -> Dict[str, Any]:
    """Get elevation data for locations.

    Args:
        locations: List of locations as dicts with "lat" and "lng" fields

    Returns:
        Dictionary with elevation information
    """
    try:
        # Validate parameters
        params = ElevationParams(
            locations=locations,
        )
    except ValueError as e:
        return {"error": str(e)}

    logger.info(f"Getting elevation for {len(locations)} locations")

    try:
        # Call the Google Maps MCP through the abstraction layer
        result = await mcp_manager.invoke(
            mcp_name="google_maps",
            method_name="get_elevation",
            params=params.model_dump(exclude_none=True),
        )

        # Process results
        elevations = []
        for i, result_item in enumerate(result.results):
            elevations.append(
                {
                    "location": locations[i],
                    "elevation": result_item.elevation,
                    "resolution": result_item.resolution,
                }
            )

        # Create formatted result
        formatted_result = "Elevation Results:\n"
        for i, elev in enumerate(elevations):
            formatted_result += (
                f"{i + 1}. ({elev['location']['lat']}, {elev['location']['lng']}): "
                f"{elev['elevation']:.1f} meters\n"
            )

        return {
            "status": result.status,
            "elevations": elevations,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error getting elevation data: {str(e)}")
        return {"error": f"Failed to get elevation data: {str(e)}"}


@function_tool
@with_error_handling
async def timezone_tool(
    location: Dict[str, float], timestamp: Optional[int] = None
) -> Dict[str, Any]:
    """Get timezone information for a location.

    Args:
        location: Dict with "lat" and "lng" fields
        timestamp: Unix timestamp (defaults to current time)

    Returns:
        Dictionary with timezone information
    """
    try:
        # Validate parameters
        params = TimeZoneParams(
            location=location,
            timestamp=timestamp,
        )
    except ValueError as e:
        return {"error": str(e)}

    logger.info(f"Getting timezone for location: {location}")

    try:
        # Call the Google Maps MCP through the abstraction layer
        result = await mcp_manager.invoke(
            mcp_name="google_maps",
            method_name="get_timezone",
            params=params.model_dump(exclude_none=True),
        )

        # Process result
        timezone_info = {
            "timezone_id": result.timezone_id,
            "timezone_name": result.timezone_id.replace("_", " "),
            "dst_offset": result.dst_offset,
            "raw_offset": result.raw_offset,
        }

        # Calculate total offset in hours
        total_offset_seconds = timezone_info["dst_offset"] + timezone_info["raw_offset"]
        total_offset_hours = total_offset_seconds / 3600
        offset_sign = "+" if total_offset_hours >= 0 else ""
        timezone_info["total_offset"] = f"{offset_sign}{total_offset_hours:.1f}"

        # Create formatted result
        formatted_result = (
            f"Timezone: {timezone_info['timezone_name']}\n"
            f"({timezone_info['timezone_id']})\n"
            f"UTC Offset: {timezone_info['total_offset']} hours\n"
        )

        return {
            "status": result.status,
            "timezone": timezone_info,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error getting timezone information: {str(e)}")
        return {"error": f"Failed to get timezone information: {str(e)}"}
